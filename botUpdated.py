import discord
from discord.ext import tasks, commands
from curl_cffi import requests as curi_requests
import asyncio
import json
import os
import requests
import random
import sys
import threading
import collections
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- INITIALIZATION ---
TOKEN = 'MTQ2OTAzODg4NDI4MDM0MDYwMw.G_L9fJ.M7p3ANd7P55aGE5Wa5fKsVAs7UqBoQM04B150c' 

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- CONFIGURATION & STATE ---
config = {
    "channel_id": None,
    "tags": [], 
    "interval": 30.0,
    "headers": {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'},
    "history": [],
    "used_tags": set(),
    "start_tags": set(),
    "blacklist_tags": set(),
    # Fill these in with your Danbooru credentials if you want to use Danbooru
    "danbooru_username": "FrostBytte",
    "danbooru_api_key": "b9JmYZAm6a1GMfKdWDNzoFSY",
    # Fill these in with your Rule34 credentials if you want to use Rule34
    "rule34_user_id": "5901111",
    "rule34_api_key": "6a080a028bbeebd598507a18c6ea6f98d3b7ffe3ceef7174f06ebdf919e39ce03a153fbab42833b8b0d3ae5f1ed4053901d8272a1932e66bb46a1209a8ae20c9"
}

BLACKLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blacklist_tags.json")
VERBOSE_LOGS = False


def log_info(message):
    print(message)


def log_verbose(message):
    if VERBOSE_LOGS:
        print(message)


def load_blacklist_tags():
    if not os.path.exists(BLACKLIST_FILE):
        return

    try:
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            config["blacklist_tags"] = {str(tag).strip() for tag in data if str(tag).strip()}
    except Exception as e:
        log_verbose(f"Failed to load blacklist file: {e}")


def save_blacklist_tags():
    try:
        tags = sorted(tag for tag in config["blacklist_tags"] if tag.strip())

        with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(tags, f, ensure_ascii=True, indent=2)
    except Exception as e:
        log_verbose(f"Failed to save blacklist file: {e}")


load_blacklist_tags()

# --- FETCHING LOGIC ---
def format_tags_for_log(tags, max_tags=10):
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


def parse_tag_list(raw_tags):
    return [tag.strip() for tag in raw_tags.split(',') if tag.strip()]


def matches_search_query(tag_name, query):
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


def get_matching_blacklist_tags(tags):
    if not tags or not config["blacklist_tags"]:
        return []

    if isinstance(tags, str):
        tag_set = {tag.strip().lower() for tag in tags.split() if tag.strip()}
    elif isinstance(tags, list):
        tag_set = {str(tag).strip().lower() for tag in tags if str(tag).strip()}
    else:
        tag_set = {str(tags).strip().lower()}

    blacklist_set = {tag.lower() for tag in config["blacklist_tags"]}
    return sorted(tag for tag in blacklist_set if tag in tag_set)


def _to_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _search_rule34_tags(query, limit=50):
    pages_to_scan = 12

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
        if config["rule34_user_id"] and config["rule34_api_key"]:
            params['user_id'] = config["rule34_user_id"]
            params['api_key'] = config["rule34_api_key"]

        try:
            response = requests.get(
                'https://api.rule34.xxx',
                params=params,
                headers=config["headers"],
                timeout=10
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
                post_tags = {tag.strip().lower() for tag in str(post.get("tags", "")).split() if tag.strip()}
                for tag in post_tags:
                    if not matches_search_query(tag, query):
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


def _search_danbooru_tags(query, limit=50):
    auth = None
    if config["danbooru_username"] and config["danbooru_api_key"]:
        auth = (config["danbooru_username"], config["danbooru_api_key"])

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
            if response.status_code != 200:
                return page_counts

            data = response.json()
            if not isinstance(data, list):
                return page_counts

            for post in data:
                post_tags = {tag.strip().lower() for tag in str(post.get("tag_string", "")).split() if tag.strip()}
                for tag in post_tags:
                    if not matches_search_query(tag, query):
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


def _get_rule34_association_count(base_tag, related_tag):
    tags = base_tag if base_tag == related_tag else f"{base_tag} {related_tag}"
    params = {
        'page': 'dapi',
        's': 'post',
        'q': 'index',
        'limit': 1,
        'tags': tags
    }
    if config["rule34_user_id"] and config["rule34_api_key"]:
        params['user_id'] = config["rule34_user_id"]
        params['api_key'] = config["rule34_api_key"]

    try:
        response = requests.get(
            'https://api.rule34.xxx',
            params=params,
            headers=config["headers"],
            timeout=12
        )
        if response.status_code != 200:
            return 0

        root = ET.fromstring(response.text)
        if root.tag != "posts":
            return 0
        return _to_int(root.attrib.get("count", 0), 0)
    except Exception:
        return None


def _get_danbooru_association_count(base_tag, related_tag):
    tags = base_tag if base_tag == related_tag else f"{base_tag} {related_tag}"
    params = {'tags': tags}
    auth = None
    if config["danbooru_username"] and config["danbooru_api_key"]:
        auth = (config["danbooru_username"], config["danbooru_api_key"])

    try:
        response = curi_requests.get(
            'https://danbooru.donmai.us/counts/posts.json',
            params=params,
            auth=auth,
            impersonate="chrome110",
            timeout=12
        )
        if response.status_code != 200:
            return None

        data = response.json()
        if isinstance(data, dict):
            counts = data.get("counts", {})
            if isinstance(counts, dict):
                return _to_int(counts.get("posts", 0), 0)
        return None
    except Exception:
        return None


def search_tags_across_apis(raw_query, limit=50):
    normalized = raw_query.strip().lower().replace(" ", "_")
    if not normalized:
        return {"query": "", "rule34": {}, "danbooru": {}, "combined": []}

    rule34_tags = _search_rule34_tags(normalized, limit=limit)
    danbooru_tags = _search_danbooru_tags(normalized, limit=limit)

    combined_entries = []
    sample_sorted = sorted(
        set(rule34_tags.keys()) | set(danbooru_tags.keys()),
        key=lambda name: (-(rule34_tags.get(name, 0) + danbooru_tags.get(name, 0)), name)
    )
    candidate_names = sample_sorted[:min(max(limit, 80), 160)]

    # Exact per-tag association lookups are expensive; do them only for the top
    # sampled candidates and keep the rest on sampled counts for responsiveness.
    exact_lookup_names = set(candidate_names[:min(30, len(candidate_names))])
    if normalized in candidate_names:
        exact_lookup_names.add(normalized)

    exact_counts = {}

    def fetch_exact_counts(tag_name):
        return (
            tag_name,
            _get_rule34_association_count(normalized, tag_name),
            _get_danbooru_association_count(normalized, tag_name)
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

    for name in candidate_names:
        r34_exact, dan_exact = exact_counts.get(name, (None, None))

        r34_count = r34_exact if r34_exact is not None else rule34_tags.get(name, 0)
        dan_count = dan_exact if dan_exact is not None else danbooru_tags.get(name, 0)
        # Show associated-image totals across both APIs.
        display_count = r34_count + dan_count
        combined_entries.append({
            "name": name,
            "count": display_count,
            "rule34_count": r34_count,
            "danbooru_count": dan_count
        })

    combined = sorted(combined_entries, key=lambda item: (-item["count"], item["name"]))
    return {
        "query": normalized,
        "rule34": rule34_tags,
        "danbooru": danbooru_tags,
        "combined": combined
    }


# --- POST BUFFER ---
# Stores pre-fetched posts so image_stream doesn't wait on HTTP each interval.
_post_buffer = collections.deque()
_buffer_lock = threading.Lock()
_refill_in_progress = False
BUFFER_LOW_MARK = 30


def _fetch_one_tag(tag_param):
    """Fetch up to 100 posts for a single tag from Rule34 and Danbooru."""
    results = []
    use_danbooru = bool(config["danbooru_username"] and config["danbooru_api_key"])

    # Rule34
    try:
        params = {
            'page': 'dapi', 's': 'post', 'q': 'index',
            'json': 1, 'limit': 100, 'pid': random.randint(0, 50),
            'tags': tag_param
        }
        if config["rule34_user_id"] and config["rule34_api_key"]:
            params['user_id'] = config["rule34_user_id"]
            params['api_key'] = config["rule34_api_key"]
        response = requests.get(
            'https://api.rule34.xxx', params=params,
            headers=config["headers"], timeout=15
        )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                for post in data:
                    post_tags = post.get('tags', '')
                    if not get_matching_blacklist_tags(post_tags):
                        url = post.get('file_url')
                        if url:
                            results.append({"url": url, "tags": post_tags, "api": "rule34"})
    except Exception as e:
        log_verbose(f"Buffer fetch error rule34 ({tag_param}): {e}")

    # Danbooru
    if use_danbooru:
        try:
            params = {
                'tags': tag_param, 'limit': 100, 'random': 'true',
                'login': config["danbooru_username"],
                'api_key': config["danbooru_api_key"]
            }
            response = curi_requests.get(
                'https://danbooru.donmai.us/posts.json', params=params,
                impersonate="chrome110", timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    for post in data:
                        post_tags = post.get('tag_string', '')
                        if not get_matching_blacklist_tags(post_tags):
                            url = post.get('file_url') or post.get('large_file_url')
                            if url:
                                results.append({"url": url, "tags": post_tags, "api": "danbooru"})
        except Exception as e:
            log_verbose(f"Buffer fetch error danbooru ({tag_param}): {e}")

    return results


def _fetch_posts_into_buffer():
    """Fetch posts for ALL saved tags in parallel and push everything into the buffer."""
    global _refill_in_progress
    _refill_in_progress = True
    try:
        tags = config["tags"] if config["tags"] else ["rating:explicit"]
        tag_params = [t.strip().replace('+', ' ') for t in tags if t.strip()]

        new_posts = []
        with ThreadPoolExecutor(max_workers=min(len(tag_params), 8)) as executor:
            futures = [executor.submit(_fetch_one_tag, tp) for tp in tag_params]
            for future in as_completed(futures):
                try:
                    new_posts.extend(future.result())
                except Exception:
                    continue

        if new_posts:
            random.shuffle(new_posts)
            with _buffer_lock:
                _post_buffer.extend(new_posts)
            log_verbose(f"Buffer refilled: {len(new_posts)} posts from {len(tag_params)} tag(s) (total: {len(_post_buffer)})")
    finally:
        _refill_in_progress = False


def _trigger_refill():
    """Start a background buffer refill if one isn't already running."""
    global _refill_in_progress
    if not _refill_in_progress:
        threading.Thread(target=_fetch_posts_into_buffer, daemon=True).start()


def fetch_image():
    # Try to serve from the pre-fetched buffer first (near-instant).
    with _buffer_lock:
        while _post_buffer:
            post = _post_buffer.popleft()
            if post["url"] not in config["history"]:
                if len(_post_buffer) < BUFFER_LOW_MARK:
                    _trigger_refill()
                return post

    # Buffer empty — fetch synchronously and fill buffer as a side-effect.
    log_verbose("Post buffer empty, fetching synchronously...")
    _fetch_posts_into_buffer()

    with _buffer_lock:
        while _post_buffer:
            post = _post_buffer.popleft()
            if post["url"] not in config["history"]:
                return post

    return None


# --- BACKGROUND LOOP ---
async def _send_next_image(channel):
    """Pop one post from the buffer and send it. Returns True if sent."""
    image_post = await asyncio.to_thread(fetch_image)
    if not image_post or not image_post.get("url"):
        return False
    if image_post["url"] in config["history"]:
        return False
    config["history"].append(image_post["url"])
    if len(config["history"]) > 200:
        config["history"].pop(0)
    try:
        pretty_tags = format_tags_for_log(image_post.get("tags", ""), max_tags=20)
        await channel.send(f"{image_post['url']}\nTags: {pretty_tags}")
        log_info(f"POSTED [{image_post.get('api', 'unknown')}] Tags: {pretty_tags}")
        return True
    except Exception as e:
        log_verbose(f"Send Error: {e}")
        return False


@tasks.loop(seconds=30.0)
async def image_stream():
    if not config["channel_id"]: return
    channel = bot.get_channel(config["channel_id"])
    if not channel: return
    await _send_next_image(channel)

# --- COMMANDS ---
@bot.command()
async def start(ctx, delay: float, *, tags: str = None):
    config["channel_id"] = ctx.channel.id
    config["interval"] = max(delay, 5.0)
    config["history"] = []
    
    if tags:
        tag_list = parse_tag_list(tags)
        config["tags"] = tag_list
        config["used_tags"].update(tag_list)
        config["start_tags"].update(tag_list)
    else:
        if config["start_tags"]:
            config["tags"] = list(config["start_tags"])
        else:
            config["tags"] = []  # Random NSFW mode (API-specific defaults)
    
    image_stream.change_interval(seconds=config["interval"])
    if not image_stream.is_running():
        image_stream.start()

    # Clear stale buffer and pre-warm with a fresh batch.
    with _buffer_lock:
        _post_buffer.clear()

    tag_display = "Random NSFW" if not config["tags"] else ', '.join(config['tags'])
    await ctx.send(f"🚀 **Stream Active!**\n**Interval:** {config['interval']}s\n**Tag Pool:** `{tag_display}`")

    # Fetch first batch synchronously so the first image sends right away.
    await asyncio.to_thread(_fetch_posts_into_buffer)
    channel = bot.get_channel(config["channel_id"])
    if channel:
        await _send_next_image(channel)


@bot.command(name="addtags")
async def addtags(ctx, *, tags: str):
    tag_list = parse_tag_list(tags)
    if not tag_list:
        await ctx.send("No valid tags provided. Use `!addtags tag1, tag2, tag3`.")
        return

    before = len(config["used_tags"])
    config["used_tags"].update(tag_list)
    config["start_tags"].update(tag_list)
    added_count = len(config["used_tags"]) - before
    await ctx.send(
        f"➕ **Saved Tags Updated**\n"
        f"Added: `{added_count}`\n"
        f"Saved Tag Count: `{len(config['used_tags'])}`"
    )


@bot.command(name="cleartags")
async def cleartags(ctx):
    cleared_count = len(config["used_tags"])
    config["used_tags"].clear()
    config["start_tags"].clear()
    await ctx.send(f"🧹 **Saved Tags Cleared.** Removed `{cleared_count}` saved tags.")


@bot.command(name="addblacklist")
async def addblacklist(ctx, *, tags: str):
    tag_list = parse_tag_list(tags)
    if not tag_list:
        await ctx.send("No valid blacklist tags provided. Use `!addblacklist tag1, tag2`.")
        return

    before = len(config["blacklist_tags"])
    config["blacklist_tags"].update(tag_list)
    save_blacklist_tags()
    added_count = len(config["blacklist_tags"]) - before
    await ctx.send(
        f"🚫 **Blacklist Updated**\n"
        f"Added: `{added_count}`\n"
        f"Blacklist Count: `{len(config['blacklist_tags'])}`"
    )


@bot.command(name="removeblacklist")
async def removeblacklist(ctx, *, tags: str):
    tag_list = parse_tag_list(tags)
    if not tag_list:
        await ctx.send("No valid blacklist tags provided. Use `!removeblacklist tag1, tag2`.")
        return

    removed_count = 0
    blacklist_lookup = {tag.lower(): tag for tag in config["blacklist_tags"]}
    for tag in tag_list:
        stored_tag = blacklist_lookup.get(tag.lower())
        if stored_tag is not None:
            config["blacklist_tags"].remove(stored_tag)
            removed_count += 1

    save_blacklist_tags()

    await ctx.send(
        f"✅ **Blacklist Updated**\n"
        f"Removed: `{removed_count}`\n"
        f"Blacklist Count: `{len(config['blacklist_tags'])}`"
    )


@bot.command(name="blacklist")
async def blacklist(ctx):
    tags = sorted(tag for tag in config["blacklist_tags"] if tag.strip())
    if not tags:
        await ctx.send("Blacklist is empty.")
        return

    body = "\n".join(f"- {tag}" for tag in tags)
    message = f"🚫 **Blacklisted Tags ({len(tags)})**\n{body}"
    if len(message) <= 2000:
        await ctx.send(message)
        return

    await ctx.send(f"🚫 **Blacklisted Tags ({len(tags)})**")
    chunk = ""
    for tag in tags:
        line = f"- {tag}\n"
        if len(chunk) + len(line) > 1900:
            await ctx.send(chunk)
            chunk = line
        else:
            chunk += line
    if chunk:
        await ctx.send(chunk)


@bot.command(name="clearblacklist")
async def clearblacklist(ctx):
    cleared_count = len(config["blacklist_tags"])
    config["blacklist_tags"].clear()
    save_blacklist_tags()
    await ctx.send(f"🧹 **Blacklist Cleared.** Removed `{cleared_count}` blacklisted tags.")

@bot.command()
async def stop(ctx):
    image_stream.stop()
    with _buffer_lock:
        _post_buffer.clear()
    await ctx.send("⏹ **Stream Stopped.**")


@bot.command()
async def pause(ctx):
    if not image_stream.is_running():
        await ctx.send("⏸ Stream is already paused.")
        return

    image_stream.stop()
    await ctx.send("⏸ **Stream Paused.** Use `!resume` to continue with current settings.")


@bot.command()
async def resume(ctx):
    if image_stream.is_running():
        await ctx.send("▶ Stream is already running.")
        return

    if not config["channel_id"]:
        await ctx.send("No active stream config found. Use `!start <delay> [tags]` first.")
        return

    image_stream.change_interval(seconds=config["interval"])
    image_stream.start()
    await ctx.send("▶ **Stream Resumed.** Current settings were preserved.")


@bot.command(name="taglist")
async def taglist(ctx):
    saved_tags = sorted([t for t in config["used_tags"] if t.strip()])
    if not saved_tags:
        await ctx.send("No saved tags yet. Use `!start <delay> <tags>` first.")
        return

    body = "\n".join(f"- {tag}" for tag in saved_tags)
    message = f"📌 **Saved Tags ({len(saved_tags)})**\n{body}"

    # Discord has a 2000-character message limit.
    if len(message) <= 2000:
        await ctx.send(message)
        return

    await ctx.send(f"📌 **Saved Tags ({len(saved_tags)})**")
    chunk = ""
    for tag in saved_tags:
        line = f"- {tag}\n"
        if len(chunk) + len(line) > 1900:
            await ctx.send(chunk)
            chunk = line
        else:
            chunk += line
    if chunk:
        await ctx.send(chunk)


@bot.command(name="searchtags")
async def searchtags(ctx, *, query: str):
    if not query.strip():
        await ctx.send("Provide a search term. Example: `!searchtags laying_down`")
        return

    results = await asyncio.to_thread(search_tags_across_apis, query, 150)
    combined = results["combined"]
    if not combined:
        await ctx.send(f"No tags found for `{results['query']}`.")
        return

    query_tag = results["query"]
    exact_match = next((item for item in combined if item["name"] == query_tag), None)
    exact_count = exact_match["count"] if exact_match else 0

    total_combined_images = sum(item["count"] for item in combined)

    header = (
        f"🔎 **Tag Search:** `{results['query']}`\n"
        f"Total Images (Combined Tags): `{total_combined_images}` | Exact Tag Images: `{exact_count}` | Rule34: `{len(results['rule34'])}` | "
        f"Danbooru: `{len(results['danbooru'])}` | Combined: `{len(combined)}`"
    )
    await ctx.send(header)

    chunk = ""
    for item in combined:
        line = f"- {item['name']} -> images: {item['count']} (r34: {item['rule34_count']}, dan: {item['danbooru_count']})\n"
        if len(chunk) + len(line) > 1900:
            await ctx.send(chunk)
            chunk = line
        else:
            chunk += line
    if chunk:
        await ctx.send(chunk)


@bot.command(name="commands")
async def commands_list(ctx):
    message = (
        "📚 **Bot Commands**\n"
        "- `!start <delay> [tags]` - Start stream (uses saved start tags when no tags given)\n"
        "- `!stop` - Stop stream\n"
        "- `!pause` - Pause stream without clearing settings\n"
        "- `!resume` - Resume paused stream\n"
        "- `!addtags tag1, tag2` - Add tags to saved/start pools\n"
        "- `!taglist` - Show saved tag list\n"
        "- `!cleartags` - Clear saved/start tag pools\n"
        "- `!addblacklist tag1, tag2` - Add blacklist tags\n"
        "- `!removeblacklist tag1, tag2` - Remove blacklist tags\n"
        "- `!blacklist` - Show blacklist tags\n"
        "- `!clearblacklist` - Clear blacklist tags\n"
        "- `!searchtags <query>` - Search tag names across APIs\n"
        "- `!commands` - Show this command list"
    )
    await ctx.send(message)

@bot.event
async def on_ready():
    log_info(f"Logged in as {bot.user.name}")

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        log_info(f"Bot failed to start: {e}")
