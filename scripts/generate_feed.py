"""Central feed generator — fetches raw content from Twitter + podcasts + blogs.

Runs on GitHub Actions daily. Outputs raw content (no LLM summarization).
Subscribers pull the feed JSON and use their own LLM to generate digests.

Usage:
    python scripts/generate_feed.py [--twitter-only | --podcasts-only]

Env vars:
    TWITTER_COOKIES — browser cookie string for twscrape auth
"""

import asyncio
import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
FEEDS_DIR = ROOT_DIR / "feeds"
STATE_PATH = FEEDS_DIR / "state-feed.json"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# ── State management ──────────────────────────────────────────────────────────

def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text("utf-8"))
    return {"seen_tweets": {}, "seen_episodes": {}}


def save_state(state):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    for key in ("seen_tweets", "seen_episodes"):
        state[key] = {k: v for k, v in state.get(key, {}).items() if v > cutoff}
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def load_sources():
    with open(ROOT_DIR / "config" / "sources.json", "r", encoding="utf-8") as f:
        return json.load(f)


def log(msg):
    print(msg, file=sys.stderr)


# ── Twitter fetching ──────────────────────────────────────────────────────────

def detect_proxy():
    proxy = os.environ.get("SOCKS_PROXY", "")
    if proxy:
        return proxy
    if sys.platform == "win32":
        try:
            import subprocess
            CF = 0x08000000
            netstat = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                                     timeout=5, encoding="utf-8", errors="replace", creationflags=CF)
            tasklist = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ww-ss-local.exe", "/FO", "CSV", "/NH"],
                                      capture_output=True, text=True, timeout=5,
                                      encoding="utf-8", errors="replace", creationflags=CF)
            pids = set()
            for line in tasklist.stdout.strip().split("\n"):
                parts = line.strip().strip('"').split('","')
                if len(parts) >= 2:
                    try: pids.add(parts[1].strip('"'))
                    except (IndexError, ValueError): pass
            if pids:
                for line in netstat.stdout.split("\n"):
                    if "LISTENING" in line:
                        parts = line.split()
                        if len(parts) >= 5 and parts[4] in pids:
                            port = int(parts[1].rsplit(":", 1)[1])
                            return f"socks5h://127.0.0.1:{port}"
        except Exception:
            pass
        import socket
        for port in [12345, 12346, 12347]:
            try:
                s = socket.create_connection(("127.0.0.1", port), timeout=2)
                s.close()
                return f"socks5h://127.0.0.1:{port}"
            except Exception:
                continue
    return ""


async def fetch_twitter(sources, state):
    twitter_cfg = sources.get("twitter", {})
    accounts = twitter_cfg.get("accounts", [])
    lookback = twitter_cfg.get("lookback_hours", 24)
    max_per_user = twitter_cfg.get("max_tweets_per_user", 5)

    cookies = os.environ.get("TWITTER_COOKIES", "")
    if not cookies:
        log("⚠️ TWITTER_COOKIES not set, skipping Twitter")
        return {"x": [], "errors": ["TWITTER_COOKIES not set"]}

    from twscrape import API, gather
    proxy = detect_proxy()
    if proxy:
        log(f"🌐 Twitter proxy: {proxy}")
        try:
            import twscrape.xclid as _xclid
            from twscrape.http import make_client as _mc
            _xclid._make_client = lambda: _mc(proxy=proxy, headers={"user-agent": "@chrome"})
        except Exception:
            pass

    db_path = str(SCRIPT_DIR / "twitter_accounts.db")
    api = API(db_path, proxy=proxy) if proxy else API(db_path)
    acc = await api.pool.get_account("feed_bot")
    if acc is None:
        await api.pool.add_account_cookies("feed_bot", cookies)
        await api.pool.set_active("feed_bot", True)

    since = datetime.now(timezone.utc) - timedelta(hours=lookback)
    results = []
    errors = []

    for account in accounts:
        handle = account["handle"]
        log(f"📥 @{handle}...")
        try:
            raw = await gather(api.search(f"from:{handle}", limit=max_per_user * 3, kv={"product": "Latest"}))
        except Exception as e:
            log(f"  ⚠️ {e}")
            errors.append(f"@{handle}: {e}")
            continue

        tweets = []
        for t in raw:
            if t.date and t.date.replace(tzinfo=timezone.utc) < since:
                continue
            if t.rawContent.startswith("RT @"):
                continue
            tid = str(t.id)
            if tid in state["seen_tweets"]:
                continue
            state["seen_tweets"][tid] = datetime.now(timezone.utc).isoformat()
            tweets.append({
                "id": tid,
                "text": t.rawContent,
                "created_at": t.date.isoformat() if t.date else "",
                "like_count": t.likeCount or 0,
                "retweet_count": t.retweetCount or 0,
                "reply_count": t.replyCount or 0,
                "url": t.url or "",
            })

        tweets.sort(key=lambda x: x["like_count"] + x["retweet_count"] * 2, reverse=True)
        tweets = tweets[:max_per_user]

        if tweets:
            log(f"  ✅ {len(tweets)} tweets")
        else:
            log(f"  ⏭️ nothing new")

        results.append({
            "handle": handle,
            "name": account["name"],
            "domain": account.get("domain", "ai"),
            "tier": account.get("tier", ""),
            "tweets": tweets,
        })

    return {"x": results, "errors": errors if errors else None}


# ── Podcast fetching ──────────────────────────────────────────────────────────

def parse_rss(xml_text):
    episodes = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return episodes
    ns = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}
    for item in root.iter("item"):
        title = item.findtext("title", "").strip()
        guid = item.findtext("guid", title).strip()
        pub_date_str = item.findtext("pubDate", "")
        link = item.findtext("link", "")
        desc = item.findtext("description", "")
        enc = item.find("enclosure")
        audio = enc.get("url", "") if enc is not None else ""
        dur_el = item.find("itunes:duration", ns)
        duration = dur_el.text.strip() if dur_el is not None and dur_el.text else ""

        parsed_date = None
        for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                    "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
            try:
                parsed_date = datetime.strptime(pub_date_str.strip(), fmt)
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue

        episodes.append({
            "title": title, "guid": guid, "pub_date": parsed_date,
            "link": link, "audio_url": audio, "duration": duration,
            "description": desc[:2000],
        })
    return episodes


def get_youtube_transcript(link):
    if not link:
        return None
    vid = None
    parsed = urlparse(link)
    if "youtube.com" in parsed.netloc:
        m = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", link)
        vid = m.group(1) if m else None
    elif "youtu.be" in parsed.netloc:
        vid = parsed.path.strip("/")[:11]
    if not vid:
        return None
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        tl = YouTubeTranscriptApi.list_transcripts(vid)
        try:
            tr = tl.find_transcript(["en"])
        except Exception:
            tr = tl.find_generated_transcript(["en"])
        segs = tr.fetch()
        text = " ".join(s.text if hasattr(s, "text") else s.get("text", "") for s in segs)
        return text if len(text) > 200 else None
    except Exception:
        return None


def fetch_channel(channel, lookback_hours, state):
    name = channel["name"]
    rss_url = channel["rss_url"]
    since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    log(f"📻 {name}...")

    try:
        resp = httpx.get(rss_url, headers={"User-Agent": UA}, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        episodes = parse_rss(resp.text)
    except Exception as e:
        log(f"  ⚠️ RSS failed: {e}")
        return [], str(e)

    results = []
    for ep in episodes:
        if ep["pub_date"] and ep["pub_date"] < since:
            continue
        if ep["guid"] in state["seen_episodes"]:
            continue
        state["seen_episodes"][ep["guid"]] = datetime.now(timezone.utc).isoformat()

        log(f"  🆕 {ep['title'][:60]}...")

        transcript = get_youtube_transcript(ep["link"])
        if transcript:
            log(f"    ✅ transcript ({len(transcript)} chars)")

        results.append({
            "channel": name,
            "domain": channel.get("domain", "ai"),
            "title": ep["title"],
            "pub_date": ep["pub_date"].isoformat() if ep["pub_date"] else "",
            "link": ep["link"],
            "audio_url": ep["audio_url"],
            "duration": ep["duration"],
            "description": ep["description"],
            "transcript": transcript,
        })

    if not results:
        log(f"  ⏭️ nothing new")
    return results, None


def fetch_podcasts(sources, state):
    podcast_cfg = sources.get("podcasts", {})
    channels = podcast_cfg.get("channels", [])
    lookback = podcast_cfg.get("lookback_hours", 168)

    all_episodes = []
    errors = []

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch_channel, ch, lookback, state): ch for ch in channels}
        for fut in as_completed(futures):
            try:
                eps, err = fut.result()
                all_episodes.extend(eps)
                if err:
                    errors.append(f"{futures[fut]['name']}: {err}")
            except Exception as e:
                errors.append(f"{futures[fut]['name']}: {e}")

    all_episodes.sort(key=lambda x: x.get("pub_date", ""), reverse=True)
    return {"podcasts": all_episodes, "errors": errors if errors else None}


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--twitter-only", action="store_true")
    parser.add_argument("--podcasts-only", action="store_true")
    args = parser.parse_args()

    sources = load_sources()
    state = load_state()
    now = datetime.now(timezone.utc)
    FEEDS_DIR.mkdir(parents=True, exist_ok=True)

    if not args.podcasts_only:
        log("\n━━━ Twitter/X ━━━")
        twitter_feed = await fetch_twitter(sources, state)
        twitter_feed["generated_at"] = now.isoformat()
        (FEEDS_DIR / "feed-x.json").write_text(
            json.dumps(twitter_feed, ensure_ascii=False, indent=2), encoding="utf-8")
        active = sum(1 for a in twitter_feed["x"] if a["tweets"])
        log(f"✅ feed-x.json ({active}/{len(twitter_feed['x'])} accounts with content)")

    if not args.twitter_only:
        log("\n━━━ Podcasts ━━━")
        podcast_feed = fetch_podcasts(sources, state)
        podcast_feed["generated_at"] = now.isoformat()
        (FEEDS_DIR / "feed-podcasts.json").write_text(
            json.dumps(podcast_feed, ensure_ascii=False, indent=2), encoding="utf-8")
        with_transcript = sum(1 for e in podcast_feed["podcasts"] if e.get("transcript"))
        log(f"✅ feed-podcasts.json ({len(podcast_feed['podcasts'])} episodes, {with_transcript} with transcript)")

    save_state(state)
    log("\n🎉 Feed generation complete")


if __name__ == "__main__":
    asyncio.run(main())
