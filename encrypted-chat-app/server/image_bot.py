"""
Integrated Image Bot Service - non-Discord logic ported from botUpdated.py.
Searches and streams images from Rule34 and Danbooru APIs.
"""

import json
import os
import random
import threading
import xml.etree.ElementTree as ET
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import requests
from curl_cffi import requests as curi_requests


VERBOSE_LOGS = False


def log_info(message: str):
    print(message)


def log_verbose(message: str):
    if VERBOSE_LOGS:
        print(message)


class ImageBotConfig:
    """Configuration for the image bot."""

    def __init__(self):
        self.danbooru_username = os.getenv("DANBOORU_USER", "")
        self.danbooru_api_key = os.getenv("DANBOORU_API_KEY", "")
        self.rule34_user_id = os.getenv("RULE34_USER_ID", "")
        self.rule34_api_key = os.getenv("RULE34_API_KEY", "")
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        self.blacklist_tags = set()
        self.saved_tags = set()
        self.start_tags = set()
        self.image_history = []
        self.max_history = 200
        # Helpful startup signal to verify systemd env propagation without exposing secrets.
        log_info(
            "ImageBot credentials loaded: "
            f"danbooru_user={'yes' if bool(self.danbooru_username) else 'no'}, "
            f"danbooru_key={'yes' if bool(self.danbooru_api_key) else 'no'}, "
            f"rule34_user={'yes' if bool(self.rule34_user_id) else 'no'}, "
            f"rule34_key={'yes' if bool(self.rule34_api_key) else 'no'}"
        )


class ImageBot:
    """Handles image search and streaming from APIs."""

    BUFFER_LOW_MARK = 30
    RANDOM_FALLBACK_TAGS = ["rating:explicit", "1girl", "solo"]

    def __init__(self):
        self.config = ImageBotConfig()
        self._post_buffer = deque()
        self._buffer_lock = threading.Lock()
        self._refill_in_progress = False
        self._buffer_signature: Tuple[str, ...] = tuple()
        self.load_blacklist()
        self.load_saved_tags()

    @staticmethod
    def parse_tag_list(tags: str) -> List[str]:
        """Parse comma-separated tags."""
        if not tags:
            return []
        return [t.strip() for t in tags.split(",") if t.strip()]

    @staticmethod
    def format_tags_for_log(tags, max_tags: int = 10) -> str:
        """Pretty-print tags with truncation for logs/messages."""
        if not tags:
            return "(no tags)"

        if isinstance(tags, str):
            parts = [t for t in tags.split() if t.strip()]
        elif isinstance(tags, list):
            parts = [str(t).strip() for t in tags if str(t).strip()]
        else:
            parts = [str(tags).strip()]

        shown = parts[:max_tags]
        hidden_count = max(len(parts) - max_tags, 0)
        suffix = f" (+{hidden_count} more)" if hidden_count else ""
        return " | ".join(shown) + suffix

    @staticmethod
    def _to_int(value, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def matches_search_query(tag_name: str, query: str) -> bool:
        """Check if a tag matches the search query."""
        name = str(tag_name or "").strip().lower()
        q = str(query or "").strip().lower()
        if not name or not q:
            return False

        # Exact and token-style matches: trap, trap_*, *_trap, *_trap_*.
        if name == q:
            return True
        if name.startswith(f"{q}_"):
            return True
        if name.endswith(f"_{q}"):
            return True
        if f"_{q}_" in name:
            return True

        # Keep useful prefix-style matches (e.g. trapped, trapinch) while excluding strap.
        return name.startswith(q)

    def load_blacklist(self):
        """Load blacklist from file if it exists."""
        blacklist_file = "blacklist_tags.json"
        if not os.path.exists(blacklist_file):
            return

        try:
            with open(blacklist_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self.config.blacklist_tags = {
                    str(tag).strip().lower()
                    for tag in data
                    if str(tag).strip()
                }
        except Exception as e:
            print(f"Failed to load blacklist: {e}")

    def save_blacklist(self):
        """Save blacklist to file."""
        try:
            tags = sorted(tag for tag in self.config.blacklist_tags if tag.strip())
            with open("blacklist_tags.json", "w", encoding="utf-8") as f:
                json.dump(tags, f, ensure_ascii=True, indent=2)
        except Exception as e:
            print(f"Failed to save blacklist: {e}")

    def load_saved_tags(self):
        """Load saved/start tags from file if it exists."""
        tags_file = "saved_tags.json"
        if not os.path.exists(tags_file):
            return

        try:
            with open(tags_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                saved = data.get("saved_tags", [])
                start = data.get("start_tags", [])
                if isinstance(saved, list):
                    self.config.saved_tags = {str(tag).strip() for tag in saved if str(tag).strip()}
                if isinstance(start, list):
                    self.config.start_tags = {str(tag).strip() for tag in start if str(tag).strip()}
        except Exception as e:
            print(f"Failed to load saved tags: {e}")

    def save_saved_tags(self):
        """Persist saved/start tags to disk."""
        try:
            payload = {
                "saved_tags": sorted(self.config.saved_tags),
                "start_tags": sorted(self.config.start_tags),
            }
            with open("saved_tags.json", "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=True, indent=2)
        except Exception as e:
            print(f"Failed to save tags: {e}")

    def add_tags(self, tags: str) -> Dict:
        """Add tags to saved and start pools."""
        tag_list = self.parse_tag_list(tags)
        before = len(self.config.saved_tags)
        self.config.saved_tags.update(tag_list)
        self.config.start_tags.update(tag_list)
        added = len(self.config.saved_tags) - before
        self.save_saved_tags()
        return {
            "added": added,
            "saved_tags": sorted(self.config.saved_tags),
            "start_tags": sorted(self.config.start_tags),
        }

    def remove_tags(self, tags: str) -> Dict:
        """Remove tags from saved and start pools."""
        numeric = str(tags or "").strip()
        if numeric.isdigit():
            remove_count = int(numeric)
            if remove_count <= 0:
                return {
                    "removed": 0,
                    "saved_tags": sorted(self.config.saved_tags),
                    "start_tags": sorted(self.config.start_tags),
                }

            # Deterministic removal order matches displayed taglist order.
            ordered_saved = sorted(self.config.saved_tags)
            to_remove = ordered_saved[:remove_count]
            removed = len(to_remove)
            for tag in to_remove:
                self.config.saved_tags.discard(tag)
                self.config.start_tags.discard(tag)

            self.save_saved_tags()
            return {
                "removed": removed,
                "saved_tags": sorted(self.config.saved_tags),
                "start_tags": sorted(self.config.start_tags),
            }

        tag_list = self.parse_tag_list(tags)
        removed = 0

        saved_lookup = {t.lower(): t for t in self.config.saved_tags}
        start_lookup = {t.lower(): t for t in self.config.start_tags}

        for tag in tag_list:
            lower = tag.lower()
            if lower in saved_lookup:
                self.config.saved_tags.discard(saved_lookup[lower])
                removed += 1
            if lower in start_lookup:
                self.config.start_tags.discard(start_lookup[lower])

        self.save_saved_tags()
        return {
            "removed": removed,
            "saved_tags": sorted(self.config.saved_tags),
            "start_tags": sorted(self.config.start_tags),
        }

    def clear_tags(self) -> Dict:
        """Clear saved and start tag pools."""
        removed = len(self.config.saved_tags)
        self.config.saved_tags.clear()
        self.config.start_tags.clear()
        self.save_saved_tags()
        return {
            "removed": removed,
            "saved_tags": [],
            "start_tags": [],
        }

    def get_saved_tags(self) -> List[str]:
        """Return current saved tags."""
        return sorted(self.config.saved_tags)

    def get_start_tags(self) -> List[str]:
        """Return current start tags."""
        return sorted(self.config.start_tags)

    def resolve_start_tag_pool(self, start_tags_input: Optional[str]) -> Dict:
        """Resolve start behavior like the original bot.
        
        Only explicitly provided tags are saved to saved_tags.
        Random/fallback tags are NOT saved.
        """
        if start_tags_input and start_tags_input.strip():
            parsed = self.parse_tag_list(start_tags_input)
            if parsed:
                # ONLY save explicitly provided tags, don't save random fallback tags
                self.config.saved_tags.update(parsed)
                self.config.start_tags.update(parsed)
                self.save_saved_tags()
                return {"mode": "explicit", "tag_pool": parsed, "saved": True}

        if self.config.start_tags:
            # Using saved tags - these were already saved before, don't save again
            return {"mode": "saved", "tag_pool": sorted(self.config.start_tags), "saved": False}

        # Random mode: empty tag_pool, uses fallback tags internally but DOES NOT save them
        return {"mode": "random", "tag_pool": [], "saved": False}

    def _effective_tag_pool(self, tag_pool: List[str]) -> List[str]:
        """Resolve final fetch tags like botUpdated behavior."""
        cleaned = [t.strip() for t in (tag_pool or []) if t and t.strip()]
        if cleaned:
            return [t.replace("+", " ") for t in cleaned if t.strip()]

        return list(self.RANDOM_FALLBACK_TAGS)

    def get_matching_blacklist_tags(self, tags) -> List[str]:
        """Get blacklist tags that match the given tags."""
        if not tags or not self.config.blacklist_tags:
            return []

        if isinstance(tags, str):
            tag_set = {tag.strip().lower() for tag in tags.split() if tag.strip()}
        elif isinstance(tags, list):
            tag_set = {str(tag).strip().lower() for tag in tags if str(tag).strip()}
        else:
            tag_set = {str(tags).strip().lower()}

        blacklist_set = {tag.lower() for tag in self.config.blacklist_tags}
        return sorted(tag for tag in blacklist_set if tag in tag_set)

    def _search_rule34_tags(self, query: str, limit: int = 50) -> Dict[str, int]:
        """Search for tags on Rule34."""
        pages_to_scan = 12

        def fetch_rule34_page(pid):
            page_counts = {}
            params = {
                "page": "dapi",
                "s": "post",
                "q": "index",
                "json": 1,
                "limit": 100,
                "pid": pid,
                "tags": query,
            }
            if self.config.rule34_user_id and self.config.rule34_api_key:
                params["user_id"] = self.config.rule34_user_id
                params["api_key"] = self.config.rule34_api_key

            try:
                response = curi_requests.get(
                    "https://api.rule34.xxx",
                    params=params,
                    headers=self.config.headers,
                    impersonate="chrome110",
                    timeout=10,
                )
                if response.status_code != 200:
                    return page_counts

                body = response.text.strip()
                if not body:
                    return page_counts

                data = response.json()
                if not isinstance(data, list):
                    return page_counts

                for post in data:
                    post_tags = {
                        tag.strip().lower()
                        for tag in str(post.get("tags", "")).split()
                        if tag.strip()
                    }
                    for tag in post_tags:
                        if not self.matches_search_query(tag, query):
                            continue
                        page_counts[tag] = page_counts.get(tag, 0) + 1
            except Exception:
                return page_counts

            return page_counts

        counts = {}
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(fetch_rule34_page, pid) for pid in range(pages_to_scan)]
            for future in as_completed(futures):
                page_counts = future.result()
                for tag, value in page_counts.items():
                    counts[tag] = counts.get(tag, 0) + value

        return counts

    def _search_danbooru_tags(self, query: str, limit: int = 50) -> Dict[str, int]:
        """Search for tags on Danbooru."""
        auth = None
        if self.config.danbooru_username and self.config.danbooru_api_key:
            auth = (self.config.danbooru_username, self.config.danbooru_api_key)

        def fetch_danbooru_page(page):
            page_counts = {}
            params = {
                "tags": query,
                "limit": 200,
                "page": page,
            }
            try:
                response = curi_requests.get(
                    "https://danbooru.donmai.us/posts.json",
                    params=params,
                    auth=auth,
                    impersonate="chrome110",
                    timeout=10,
                )
                if response.status_code != 200:
                    return page_counts

                data = response.json()
                if not isinstance(data, list):
                    return page_counts

                for post in data:
                    post_tags = {
                        tag.strip().lower()
                        for tag in str(post.get("tag_string", "")).split()
                        if tag.strip()
                    }
                    for tag in post_tags:
                        if not self.matches_search_query(tag, query):
                            continue
                        page_counts[tag] = page_counts.get(tag, 0) + 1
            except Exception:
                return page_counts

            return page_counts

        counts = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_danbooru_page, page) for page in range(1, 8)]
            for future in as_completed(futures):
                page_counts = future.result()
                for tag, value in page_counts.items():
                    counts[tag] = counts.get(tag, 0) + value

        return counts

    def _search_danbooru_tag_directory(self, query: str, limit: int = 120) -> Dict[str, int]:
        """Fallback: query Danbooru tag directory directly by name prefix."""
        counts = {}
        auth = None
        if self.config.danbooru_username and self.config.danbooru_api_key:
            auth = (self.config.danbooru_username, self.config.danbooru_api_key)

        params = {
            "search[name_matches]": f"{query}*",
            "search[order]": "count",
            "limit": min(max(limit, 20), 200),
        }
        try:
            response = curi_requests.get(
                "https://danbooru.donmai.us/tags.json",
                params=params,
                auth=auth,
                impersonate="chrome110",
                timeout=15,
            )
            if response.status_code != 200:
                return counts

            data = response.json()
            if not isinstance(data, list):
                return counts

            for entry in data:
                name = str(entry.get("name", "")).strip().lower()
                if not name or not self.matches_search_query(name, query):
                    continue
                counts[name] = max(counts.get(name, 0), self._to_int(entry.get("post_count", 0), 0))
        except Exception:
            return counts

        return counts

    def _search_rule34_wildcard_tags(self, query: str, limit: int = 50) -> Dict[str, int]:
        """Fallback: wildcard-style Rule34 post search to expand matches."""
        counts = {}

        def fetch_page(pid):
            page_counts = {}
            params = {
                "page": "dapi",
                "s": "post",
                "q": "index",
                "json": 1,
                "limit": 100,
                "pid": pid,
                "tags": f"{query}*",
            }
            if self.config.rule34_user_id and self.config.rule34_api_key:
                params["user_id"] = self.config.rule34_user_id
                params["api_key"] = self.config.rule34_api_key

            try:
                response = curi_requests.get(
                    "https://api.rule34.xxx",
                    params=params,
                    headers=self.config.headers,
                    impersonate="chrome110",
                    timeout=12,
                )
                if response.status_code != 200:
                    return page_counts

                data = response.json()
                if not isinstance(data, list):
                    return page_counts

                for post in data:
                    post_tags = {
                        tag.strip().lower()
                        for tag in str(post.get("tags", "")).split()
                        if tag.strip()
                    }
                    for tag in post_tags:
                        if not self.matches_search_query(tag, query):
                            continue
                        page_counts[tag] = page_counts.get(tag, 0) + 1
            except Exception:
                return page_counts

            return page_counts

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(fetch_page, pid) for pid in range(0, 4)]
            for future in as_completed(futures):
                page_counts = future.result()
                for tag, value in page_counts.items():
                    counts[tag] = counts.get(tag, 0) + value

        return counts

    def _get_rule34_association_count(self, base_tag: str, related_tag: str):
        tags = base_tag if base_tag == related_tag else f"{base_tag} {related_tag}"
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "limit": 1,
            "tags": tags,
        }
        if self.config.rule34_user_id and self.config.rule34_api_key:
            params["user_id"] = self.config.rule34_user_id
            params["api_key"] = self.config.rule34_api_key

        try:
            response = curi_requests.get(
                "https://api.rule34.xxx",
                params=params,
                headers=self.config.headers,
                impersonate="chrome110",
                timeout=12,
            )
            if response.status_code != 200:
                return 0

            root = ET.fromstring(response.text)
            if root.tag != "posts":
                return 0
            return self._to_int(root.attrib.get("count", 0), 0)
        except Exception:
            return None

    def _get_danbooru_association_count(self, base_tag: str, related_tag: str):
        tags = base_tag if base_tag == related_tag else f"{base_tag} {related_tag}"
        params = {"tags": tags}
        auth = None
        if self.config.danbooru_username and self.config.danbooru_api_key:
            auth = (self.config.danbooru_username, self.config.danbooru_api_key)

        try:
            response = curi_requests.get(
                "https://danbooru.donmai.us/counts/posts.json",
                params=params,
                auth=auth,
                impersonate="chrome110",
                timeout=12,
            )
            if response.status_code != 200:
                return None

            data = response.json()
            if isinstance(data, dict):
                counts = data.get("counts", {})
                if isinstance(counts, dict):
                    return self._to_int(counts.get("posts", 0), 0)
            return None
        except Exception:
            return None

    def search_tags(self, query: str, limit: int = 50) -> Dict:
        """Search tags across APIs using botUpdated association logic."""
        normalized = query.strip().lower().replace(" ", "_")
        if not normalized:
            return {"query": "", "rule34": {}, "danbooru": {}, "combined": []}

        rule34_tags = self._search_rule34_tags(normalized, limit=limit)
        danbooru_tags = self._search_danbooru_tags(normalized, limit=limit)

        # Reliability fallback for server environments where post endpoints are sparse/rate-limited.
        if len(rule34_tags) < 3:
            wildcard_rule34 = self._search_rule34_wildcard_tags(normalized, limit=limit)
            for name, count in wildcard_rule34.items():
                rule34_tags[name] = max(rule34_tags.get(name, 0), count)

        if len(danbooru_tags) < 3:
            direct_danbooru = self._search_danbooru_tag_directory(normalized, limit=max(limit, 80))
            for name, count in direct_danbooru.items():
                danbooru_tags[name] = max(danbooru_tags.get(name, 0), count)

        sample_sorted = sorted(
            set(rule34_tags.keys()) | set(danbooru_tags.keys()),
            key=lambda name: (-(rule34_tags.get(name, 0) + danbooru_tags.get(name, 0)), name),
        )
        candidate_names = sample_sorted[: min(max(limit, 80), 160)]

        # Exact association lookups only for sampled top candidates.
        exact_lookup_names = set(candidate_names[: min(30, len(candidate_names))])
        if normalized in candidate_names:
            exact_lookup_names.add(normalized)

        exact_counts = {}

        def fetch_exact_counts(tag_name):
            return (
                tag_name,
                self._get_rule34_association_count(normalized, tag_name),
                self._get_danbooru_association_count(normalized, tag_name),
            )

        if exact_lookup_names:
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(fetch_exact_counts, name) for name in exact_lookup_names]
                for future in as_completed(futures):
                    try:
                        name, r34_exact, dan_exact = future.result()
                        exact_counts[name] = (r34_exact, dan_exact)
                    except Exception:
                        continue

        combined_entries = []
        for name in candidate_names:
            r34_exact, dan_exact = exact_counts.get(name, (None, None))
            r34_count = r34_exact if r34_exact is not None else rule34_tags.get(name, 0)
            dan_count = dan_exact if dan_exact is not None else danbooru_tags.get(name, 0)
            combined_entries.append(
                {
                    "name": name,
                    "count": r34_count + dan_count,
                    "rule34_count": r34_count,
                    "danbooru_count": dan_count,
                }
            )

        combined = sorted(combined_entries, key=lambda item: (-item["count"], item["name"]))
        return {
            "query": normalized,
            "rule34": rule34_tags,
            "danbooru": danbooru_tags,
            "combined": combined,
        }

    def _fetch_one_tag(self, tag_param: str, limit: int = 100) -> List[Dict]:
        """Fetch posts for one tag from Rule34 and Danbooru (botUpdated style)."""
        results = []
        query_tag = (tag_param or "").strip()
        use_danbooru = bool(self.config.danbooru_username and self.config.danbooru_api_key)

        # Rule34
        try:
            page_candidates = [random.randint(0, 20), 0, 1, 2]
            seen_rule34_urls = set()
            for pid in page_candidates:
                params = {
                    "page": "dapi",
                    "s": "post",
                    "q": "index",
                    "json": 1,
                    "limit": min(limit, 100),
                    "pid": pid,
                    "tags": query_tag,
                }
                if self.config.rule34_user_id and self.config.rule34_api_key:
                    params["user_id"] = self.config.rule34_user_id
                    params["api_key"] = self.config.rule34_api_key

                response = curi_requests.get(
                    "https://api.rule34.xxx",
                    params=params,
                    headers=self.config.headers,
                    impersonate="chrome110",
                    timeout=15,
                )
                if response.status_code != 200:
                    log_info(f"ImageBot: Rule34 HTTP {response.status_code} for tag='{query_tag}' pid={pid}")
                    continue

                try:
                    data = response.json()
                except Exception as e:
                    log_info(f"ImageBot: Rule34 JSON parse error for tag='{query_tag}': {e}")
                    log_info(f"  Response text: {response.text[:200]}")
                    continue

                if not isinstance(data, list):
                    log_info(f"ImageBot: Rule34 non-list response for tag='{query_tag}': {str(data)[:150]}")
                    continue

                if len(data) == 0:
                    log_verbose(f"ImageBot: Rule34 returned empty list for tag='{query_tag}' pid={pid}")
                    continue

                for post in data:
                    post_tags = post.get("tags", "")
                    if self.get_matching_blacklist_tags(post_tags):
                        continue
                    url = post.get("file_url")
                    if not url or url in seen_rule34_urls:
                        continue
                    seen_rule34_urls.add(url)
                    results.append(
                        {
                            "url": url,
                            "tags": post_tags,
                            "api": "rule34",
                            "query_tag": query_tag or "random",
                        }
                    )

                if results:
                    break
        except Exception as e:
            log_info(f"ImageBot: Rule34 fetch error ({query_tag or 'random'}): {type(e).__name__}: {e}")

        # Danbooru
        if use_danbooru:
            try:
                params = {
                    "tags": query_tag,
                    "limit": min(limit, 100),
                    "random": "true",
                    "login": self.config.danbooru_username,
                    "api_key": self.config.danbooru_api_key,
                }
                response = curi_requests.get(
                    "https://danbooru.donmai.us/posts.json",
                    params=params,
                    impersonate="chrome110",
                    timeout=15,
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        for post in data:
                            post_tags = post.get("tag_string", "")
                            if self.get_matching_blacklist_tags(post_tags):
                                continue
                            url = post.get("file_url") or post.get("large_file_url")
                            if url:
                                results.append(
                                    {
                                        "url": url,
                                        "tags": post_tags,
                                        "api": "danbooru",
                                        "query_tag": query_tag or "random",
                                    }
                                )
            except Exception as e:
                log_verbose(f"Buffer fetch error danbooru ({query_tag or 'random'}): {e}")

        return results

    def _fetch_posts_into_buffer(self, tag_pool: List[str]):
        """Fetch posts for all tags in parallel and push into shared buffer."""
        self._refill_in_progress = True
        try:
            tags = self._effective_tag_pool(tag_pool)
            if not tags:
                tags = ["rating:explicit"]

            new_posts = []
            workers = max(1, min(len(tags), 8))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(self._fetch_one_tag, tag, 100) for tag in tags]
                for future in as_completed(futures):
                    try:
                        new_posts.extend(future.result())
                    except Exception:
                        continue

            # Emergency probe fallback when normal tag fetches return empty.
            if not new_posts:
                for emergency_tag in ["", "1girl", "solo", "original"]:
                    try:
                        new_posts.extend(self._fetch_one_tag(emergency_tag, 80))
                    except Exception:
                        continue
                    if len(new_posts) >= 20:
                        break

            if new_posts:
                random.shuffle(new_posts)
                with self._buffer_lock:
                    self._post_buffer.extend(new_posts)
                log_verbose(
                    f"Buffer refilled: {len(new_posts)} posts from {len(tags)} tag(s) (total: {len(self._post_buffer)})"
                )
            else:
                log_info("ImageBot: buffer refill returned zero posts (including emergency probes)")
        finally:
            self._refill_in_progress = False

    def _trigger_refill(self, tag_pool: List[str]):
        """Start background refill if one is not in progress."""
        if not self._refill_in_progress:
            threading.Thread(target=self._fetch_posts_into_buffer, args=(list(tag_pool),), daemon=True).start()

    def prime_buffer(self, tag_pool: List[str]):
        """Pre-warm post buffer for a stream's tag pool."""
        signature = tuple(sorted(t.strip() for t in tag_pool if t and t.strip()))
        with self._buffer_lock:
            if signature != self._buffer_signature:
                self._post_buffer.clear()
                self._buffer_signature = signature
        self._fetch_posts_into_buffer(tag_pool)

    def fetch_buffered_image(self, tag_pool: List[str]) -> Optional[Dict]:
        """Fetch one non-duplicate image using a buffered pipeline."""
        normalized_pool = self._effective_tag_pool(tag_pool)

        signature = tuple(sorted(normalized_pool))
        with self._buffer_lock:
            if signature != self._buffer_signature:
                self._post_buffer.clear()
                self._buffer_signature = signature

            while self._post_buffer:
                post = self._post_buffer.popleft()
                url = post.get("url")
                if not url or url in self.config.image_history:
                    continue
                if len(self._post_buffer) < self.BUFFER_LOW_MARK:
                    self._trigger_refill(normalized_pool)
                self.config.image_history.append(url)
                if len(self.config.image_history) > self.config.max_history:
                    self.config.image_history.pop(0)
                return post

        # Empty buffer fallback: fetch synchronously once.
        self._fetch_posts_into_buffer(normalized_pool)

        with self._buffer_lock:
            while self._post_buffer:
                post = self._post_buffer.popleft()
                url = post.get("url")
                if not url or url in self.config.image_history:
                    continue
                self.config.image_history.append(url)
                if len(self.config.image_history) > self.config.max_history:
                    self.config.image_history.pop(0)
                return post

        # Final retry with default random pool if a custom pool yielded nothing.
        if normalized_pool:
            self._fetch_posts_into_buffer([])
            with self._buffer_lock:
                while self._post_buffer:
                    post = self._post_buffer.popleft()
                    url = post.get("url")
                    if not url or url in self.config.image_history:
                        continue
                    self.config.image_history.append(url)
                    if len(self.config.image_history) > self.config.max_history:
                        self.config.image_history.pop(0)
                    return post

        return None

    def fetch_images(self, tags: str, limit: int = 10) -> List[Dict]:
        """Fetch images for given tags (endpoint helper)."""
        query_tag = tags.strip() if tags and tags.strip() else "rating:explicit"
        target_limit = max(1, int(limit))

        batch_limit = min(max(target_limit * 8, 20), 100)
        candidate_tags = self._effective_tag_pool([query_tag])
        results = []
        for candidate in candidate_tags:
            results.extend(self._fetch_one_tag(candidate, limit=batch_limit))
            if len(results) >= target_limit * 3:
                break
        random.shuffle(results)

        deduped = []
        seen_urls = set()
        for item in results:
            url = item.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            deduped.append(item)
            if len(deduped) >= target_limit:
                break

        if not deduped:
            log_info(f"ImageBot: no images found for tags='{query_tag}'")

        return deduped

    def add_blacklist_tags(self, tags: str) -> int:
        """Add tags to blacklist."""
        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
        before = len(self.config.blacklist_tags)
        self.config.blacklist_tags.update(tag_list)
        added = len(self.config.blacklist_tags) - before
        self.save_blacklist()
        return added

    def remove_blacklist_tags(self, tags: str) -> int:
        """Remove tags from blacklist."""
        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
        before = len(self.config.blacklist_tags)
        for tag in tag_list:
            self.config.blacklist_tags.discard(tag)
        removed = before - len(self.config.blacklist_tags)
        self.save_blacklist()
        return removed

    def clear_blacklist_tags(self) -> int:
        """Clear all blacklist tags."""
        removed = len(self.config.blacklist_tags)
        self.config.blacklist_tags.clear()
        self.save_blacklist()
        return removed

    def get_blacklist(self) -> List[str]:
        """Get current blacklist."""
        return sorted(tag for tag in self.config.blacklist_tags if tag.strip())


# Global image bot instance
image_bot = ImageBot()
