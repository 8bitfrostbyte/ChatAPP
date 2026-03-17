"""
Integrated Image Bot Service - Adapted from botUpdated.py
Searches and streams images from Rule34 and Danbooru APIs
"""

import requests
from curl_cffi import requests as curi_requests
import asyncio
import json
import os
import random
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
from database import Message, Room


class ImageBotConfig:
    """Configuration for the image bot."""
    
    def __init__(self):
        self.danbooru_username = os.getenv("DANBOORU_USER", "")
        self.danbooru_api_key = os.getenv("DANBOORU_API_KEY", "")
        self.rule34_user_id = os.getenv("RULE34_USER_ID", "")
        self.rule34_api_key = os.getenv("RULE34_API_KEY", "")
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        self.blacklist_tags = set()
        self.saved_tags = set()
        self.start_tags = set()
        self.image_history = []
        self.max_history = 200


class ImageBot:
    """Handles image search and streaming from APIs."""
    
    def __init__(self):
        self.config = ImageBotConfig()
        self.load_blacklist()
        self.load_saved_tags()

    @staticmethod
    def parse_tag_list(tags: str) -> List[str]:
        """Parse comma-separated tags."""
        if not tags:
            return []
        return [t.strip() for t in tags.split(',') if t.strip()]
    
    def load_blacklist(self):
        """Load blacklist from file if it exists."""
        blacklist_file = "blacklist_tags.json"
        if os.path.exists(blacklist_file):
            try:
                with open(blacklist_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.config.blacklist_tags = {str(tag).strip() for tag in data}
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
                "start_tags": sorted(self.config.start_tags)
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
            "start_tags": sorted(self.config.start_tags)
        }

    def remove_tags(self, tags: str) -> Dict:
        """Remove tags from saved and start pools."""
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
            "start_tags": sorted(self.config.start_tags)
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
            "start_tags": []
        }

    def get_saved_tags(self) -> List[str]:
        """Return current saved tags."""
        return sorted(self.config.saved_tags)

    def resolve_start_tag_pool(self, start_tags_input: Optional[str]) -> Dict:
        """Resolve start behavior like Discord bot.

        - If tags were provided on start: use those tags and save them.
        - If no tags were provided and saved start tags exist: use saved start tags.
        - If no tags provided and no saved tags: random mode.
        """
        if start_tags_input and start_tags_input.strip():
            parsed = self.parse_tag_list(start_tags_input)
            if parsed:
                self.config.saved_tags.update(parsed)
                self.config.start_tags.update(parsed)
                self.save_saved_tags()
                return {"mode": "explicit", "tag_pool": parsed, "saved": True}

        if self.config.start_tags:
            return {"mode": "saved", "tag_pool": sorted(self.config.start_tags), "saved": False}

        return {"mode": "random", "tag_pool": ["rating:explicit"], "saved": False}
    
    @staticmethod
    def matches_search_query(tag_name: str, query: str) -> bool:
        """Check if a tag matches the search query."""
        name = str(tag_name or "").strip().lower()
        q = str(query or "").strip().lower()
        if not name or not q:
            return False
        
        if name == q:
            return True
        if name.startswith(f"{q}_"):
            return True
        if name.endswith(f"_{q}"):
            return True
        if f"_{q}_" in name:
            return True
        return name.startswith(q)
    
    def get_matching_blacklist_tags(self, tags: str) -> List[str]:
        """Get blacklist tags that match the given tags."""
        if not tags or not self.config.blacklist_tags:
            return []
        
        tag_set = {tag.strip().lower() for tag in tags.split() if tag.strip()}
        blacklist_set = {tag.lower() for tag in self.config.blacklist_tags}
        return sorted(tag for tag in blacklist_set if tag in tag_set)
    
    def _search_rule34_tags(self, query: str, limit: int = 50) -> Dict[str, int]:
        """Search for tags on Rule34."""
        pages_to_scan = 12
        counts = {}
        
        def fetch_rule34_page(pid):
            page_counts = {}
            params = {
                'page': 'dapi',
                's': 'post',
                'q': 'index',
                'json': 1,
                'limit': 100,
                'pid': pid,
                'tags': query
            }
            if self.config.rule34_user_id and self.config.rule34_api_key:
                params['user_id'] = self.config.rule34_user_id
                params['api_key'] = self.config.rule34_api_key
            
            try:
                response = requests.get(
                    'https://api.rule34.xxx',
                    params=params,
                    headers=self.config.headers,
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        for post in data:
                            post_tags = str(post.get("tags", "")).split()
                            for tag in post_tags:
                                tag_clean = tag.strip().lower()
                                if self.matches_search_query(tag_clean, query):
                                    page_counts[tag_clean] = page_counts.get(tag_clean, 0) + 1
            except Exception:
                pass
            
            return page_counts
        
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(fetch_rule34_page, pid) for pid in range(pages_to_scan)]
            for future in as_completed(futures):
                page_counts = future.result()
                for tag, value in page_counts.items():
                    counts[tag] = counts.get(tag, 0) + value
        
        return counts
    
    def _search_danbooru_tags(self, query: str, limit: int = 50) -> Dict[str, int]:
        """Search for tags on Danbooru."""
        counts = {}
        auth = None
        if self.config.danbooru_username and self.config.danbooru_api_key:
            auth = (self.config.danbooru_username, self.config.danbooru_api_key)
        
        def fetch_danbooru_page(page):
            page_counts = {}
            params = {
                'tags': query,
                'limit': 200,
                'page': page
            }
            try:
                response = curi_requests.get(
                    'https://danbooru.donmai.us/posts.json',
                    params=params,
                    auth=auth,
                    impersonate="chrome110",
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        for post in data:
                            post_tags = str(post.get("tag_string", "")).split()
                            for tag in post_tags:
                                tag_clean = tag.strip().lower()
                                if self.matches_search_query(tag_clean, query):
                                    page_counts[tag_clean] = page_counts.get(tag_clean, 0) + 1
            except Exception:
                pass
            
            return page_counts
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_danbooru_page, page) for page in range(1, 5)]
            for future in as_completed(futures):
                page_counts = future.result()
                for tag, value in page_counts.items():
                    counts[tag] = counts.get(tag, 0) + value
        
        return counts
    
    def search_tags(self, query: str, limit: int = 50) -> Dict:
        """Search tags across both APIs."""
        normalized = query.strip().lower().replace(" ", "_")
        if not normalized:
            return {"query": "", "rule34": {}, "danbooru": {}, "combined": []}
        
        rule34_tags = self._search_rule34_tags(normalized, limit=limit)
        danbooru_tags = self._search_danbooru_tags(normalized, limit=limit)
        
        combined_entries = []
        sample_sorted = sorted(
            set(rule34_tags.keys()) | set(danbooru_tags.keys()),
            key=lambda name: (-(rule34_tags.get(name, 0) + danbooru_tags.get(name, 0)), name)
        )
        
        for name in sample_sorted[:min(limit, len(sample_sorted))]:
            r34_count = rule34_tags.get(name, 0)
            dan_count = danbooru_tags.get(name, 0)
            combined_entries.append({
                "name": name,
                "count": r34_count + dan_count,
                "rule34_count": r34_count,
                "danbooru_count": dan_count
            })
        
        return {
            "query": normalized,
            "rule34": rule34_tags,
            "danbooru": danbooru_tags,
            "combined": combined_entries
        }
    
    def fetch_images(self, tags: str, limit: int = 10) -> List[Dict]:
        """Fetch images for given tags."""
        results = []
        
        # Rule34
        try:
            params = {
                'page': 'dapi',
                's': 'post',
                'q': 'index',
                'json': 1,
                'limit': limit,
                'pid': random.randint(0, 20),
                'tags': tags
            }
            if self.config.rule34_user_id and self.config.rule34_api_key:
                params['user_id'] = self.config.rule34_user_id
                params['api_key'] = self.config.rule34_api_key
            
            response = requests.get(
                'https://api.rule34.xxx',
                params=params,
                headers=self.config.headers,
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    for post in data:
                        post_tags = post.get('tags', '')
                        if not self.get_matching_blacklist_tags(post_tags):
                            url = post.get('file_url')
                            if url:
                                results.append({
                                    "url": url,
                                    "tags": post_tags,
                                    "api": "rule34"
                                })
        except Exception as e:
            print(f"Rule34 fetch error: {e}")
        
        # Danbooru
        if self.config.danbooru_username and self.config.danbooru_api_key:
            try:
                params = {
                    'tags': tags,
                    'limit': limit,
                    'random': 'true'
                }
                response = curi_requests.get(
                    'https://danbooru.donmai.us/posts.json',
                    params=params,
                    auth=(self.config.danbooru_username, self.config.danbooru_api_key),
                    impersonate="chrome110",
                    timeout=15
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        for post in data:
                            post_tags = post.get('tag_string', '')
                            if not self.get_matching_blacklist_tags(post_tags):
                                url = post.get('file_url') or post.get('large_file_url')
                                if url:
                                    results.append({
                                        "url": url,
                                        "tags": post_tags,
                                        "api": "danbooru"
                                    })
            except Exception as e:
                print(f"Danbooru fetch error: {e}")
        
        random.shuffle(results)
        return results
    
    def add_blacklist_tags(self, tags: str) -> int:
        """Add tags to blacklist."""
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        before = len(self.config.blacklist_tags)
        self.config.blacklist_tags.update(tag_list)
        added = len(self.config.blacklist_tags) - before
        self.save_blacklist()
        return added
    
    def remove_blacklist_tags(self, tags: str) -> int:
        """Remove tags from blacklist."""
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        before = len(self.config.blacklist_tags)
        for tag in tag_list:
            self.config.blacklist_tags.discard(tag.lower())
        removed = before - len(self.config.blacklist_tags)
        self.save_blacklist()
        return removed
    
    def get_blacklist(self) -> List[str]:
        """Get current blacklist."""
        return sorted(tag for tag in self.config.blacklist_tags if tag.strip())


# Global image bot instance
image_bot = ImageBot()
