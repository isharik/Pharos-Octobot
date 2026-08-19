#!/usr/bin/env python3
"""
Pharos Community Data Refresh
=============================
Collects publicly-posted Pharos-related content from X via the Apify
Twitter/X scraper, deduplicates authors, downloads profile pictures,
and writes a local dataset that OctoBot serves instantly.

Usage:
    python refresh_community.py                  # default 100 members
    python refresh_community.py --max 250        # up to 250
    python refresh_community.py --max 500        # up to 500

Requires:
    pip install apify-client requests pillow python-dotenv

Environment:
    APIFY_API_TOKEN  — your Apify API token (in .env or env var)
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO

import requests
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

SCRIPT_DIR = Path(__file__).parent
COMMUNITY_DIR = SCRIPT_DIR / "pharos-community"
DATA_DIR = COMMUNITY_DIR / "data"
IMAGES_DIR = COMMUNITY_DIR / "images"

SEARCH_QUERIES = [
    "Pharos Network",
    '"Pharos Network"',
    "$PROS",
    "@PharosNetwork",
    "#PharosNetwork",
    "#Pharos",
    "Pharos blockchain",
    "Pharos crypto",
]

ACTOR_ID = "apidojo/tweet-scraper"

IMG_SIZE = (256, 256)
IMG_QUALITY = 85
REQUEST_TIMEOUT = 15
APIFY_TIMEOUT_SECS = 300


def get_apify_token() -> str:
    token = os.environ.get("APIFY_API_TOKEN") or os.environ.get("APIFY_TOKEN")
    if not token:
        try:
            import streamlit as st
            token = st.secrets.get("APIFY_API_TOKEN") or st.secrets.get("APIFY_TOKEN")
        except Exception:
            pass
    if not token:
        print("ERROR: APIFY_API_TOKEN not found in .env or environment.")
        print("  Add it to .env:  APIFY_API_TOKEN=apify_api_...")
        sys.exit(1)
    return str(token).strip()


def run_apify_search(token: str, query: str, max_tweets: int = 200) -> list:
    from apify_client import ApifyClient
    client = ApifyClient(token)

    run_input = {
        "searchTerms": [query],
        "maxTweets": max_tweets,
        "sort": "Latest",
        "tweetLanguage": "en",
    }

    print(f"  Searching: {query!r} (max {max_tweets} tweets)...")
    try:
        run = client.actor(ACTOR_ID).call(
            run_input=run_input,
            timeout_secs=APIFY_TIMEOUT_SECS,
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        print(f"    -> {len(items)} tweets returned")
        return items
    except Exception as e:
        print(f"    -> ERROR: {e}")
        return []


def extract_authors(all_tweets: list) -> dict:
    """Deduplicate tweets by author, aggregate Pharos activity."""
    authors = {}

    for tweet in all_tweets:
        author = tweet.get("author") or {}
        user_id = author.get("id") or author.get("userName")
        if not user_id:
            uid = tweet.get("user_id_str") or tweet.get("userId")
            uname = tweet.get("username") or tweet.get("user", {}).get("screen_name")
            if not (uid or uname):
                continue
            user_id = uid or uname
            author = {
                "id": uid,
                "userName": uname,
                "name": tweet.get("user", {}).get("name", uname),
                "profileImageUrl": tweet.get("user", {}).get("profile_image_url_https", ""),
                "description": tweet.get("user", {}).get("description", ""),
                "followers": tweet.get("user", {}).get("followers_count", 0),
                "following": tweet.get("user", {}).get("friends_count", 0),
                "isVerified": tweet.get("user", {}).get("verified", False),
            }

        username = (
            author.get("userName")
            or author.get("username")
            or author.get("screen_name")
            or ""
        )
        if not username:
            continue

        username_lower = username.lower()

        if username_lower in ("pharosnetwork", "pharos_network"):
            continue

        tweet_date = None
        for date_key in ("createdAt", "created_at", "date"):
            raw = tweet.get(date_key)
            if raw:
                try:
                    if isinstance(raw, str):
                        for fmt in ("%a %b %d %H:%M:%S %z %Y", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d"):
                            try:
                                tweet_date = datetime.strptime(raw, fmt)
                                break
                            except ValueError:
                                continue
                    elif isinstance(raw, datetime):
                        tweet_date = raw
                except Exception:
                    pass
                if tweet_date:
                    break

        if username_lower not in authors:
            display_name = (
                author.get("name")
                or author.get("displayName")
                or username
            )
            profile_img = (
                author.get("profileImageUrl")
                or author.get("profile_image_url_https")
                or author.get("profilePicUrl")
                or ""
            )
            if profile_img:
                profile_img = profile_img.replace("_normal.", "_400x400.")

            authors[username_lower] = {
                "user_id": str(author.get("id") or ""),
                "username": username,
                "display_name": display_name,
                "profile_image_url": profile_img,
                "bio": (
                    author.get("description")
                    or author.get("bio")
                    or ""
                )[:280],
                "followers": int(author.get("followers") or author.get("followersCount") or 0),
                "following": int(author.get("following") or author.get("friendsCount") or 0),
                "verified": bool(
                    author.get("isVerified")
                    or author.get("isBlueVerified")
                    or author.get("verified")
                ),
                "pharos_posts": 0,
                "latest_pharos_post": None,
                "tweets_seen": [],
            }

        entry = authors[username_lower]
        entry["pharos_posts"] += 1
        if tweet_date:
            date_str = tweet_date.strftime("%Y-%m-%d")
            if entry["latest_pharos_post"] is None or date_str > entry["latest_pharos_post"]:
                entry["latest_pharos_post"] = date_str


    return authors


def rank_authors(authors: dict, max_members: int) -> list:
    """Rank by pharos_posts desc, then followers desc. Filter low-quality."""
    ranked = []
    for entry in authors.values():
        if entry["pharos_posts"] < 1:
            continue
        ranked.append(entry)

    ranked.sort(key=lambda x: (x["pharos_posts"], x["followers"]), reverse=True)
    return ranked[:max_members]


def download_profile_image(url: str, username: str) -> str | None:
    if not url:
        return None
    dest = IMAGES_DIR / f"{username}.jpg"
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT, stream=True)
        if r.status_code != 200:
            return None
        img = Image.open(BytesIO(r.content))
        img = img.convert("RGB")
        img = img.resize(IMG_SIZE, Image.LANCZOS)
        img.save(str(dest), "JPEG", quality=IMG_QUALITY)
        return f"images/{username}.jpg"
    except Exception as e:
        print(f"    Image failed for @{username}: {e}")
        return None


def generate_fallback_avatar(username: str) -> str:
    dest = IMAGES_DIR / f"{username}.jpg"
    img = Image.new("RGB", IMG_SIZE, color=(60, 70, 120))
    try:
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        letter = username[0].upper() if username else "?"
        try:
            font = ImageFont.truetype("arial.ttf", 100)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), letter, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((256 - w) / 2 - bbox[0], (256 - h) / 2 - bbox[1]), letter, fill=(200, 210, 255), font=font)
    except Exception:
        pass
    img.save(str(dest), "JPEG", quality=IMG_QUALITY)
    return f"images/{username}.jpg"


def load_existing_data() -> dict:
    json_path = DATA_DIR / "community.json"
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {m["username"].lower(): m for m in data}
        except Exception:
            pass
    return {}


def main():
    parser = argparse.ArgumentParser(description="Refresh Pharos Community dataset")
    parser.add_argument("--max", type=int, default=100, choices=[100, 250, 500],
                        help="Maximum community members (100/250/500)")
    parser.add_argument("--tweets-per-query", type=int, default=200,
                        help="Max tweets per search query")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    token = get_apify_token()
    existing = load_existing_data()

    print(f"\n=== Pharos Community Refresh (max {args.max} members) ===\n")

    all_tweets = []
    for query in SEARCH_QUERIES:
        tweets = run_apify_search(token, query, args.tweets_per_query)
        all_tweets.extend(tweets)
        time.sleep(1)

    print(f"\nTotal tweets collected: {len(all_tweets)}")

    authors = extract_authors(all_tweets)
    print(f"Unique authors found: {len(authors)}")

    ranked = rank_authors(authors, args.max)
    print(f"Ranked members (top {args.max}): {len(ranked)}")

    print("\nDownloading profile images...")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    community = []
    for i, member in enumerate(ranked):
        uname = member["username"]
        print(f"  [{i+1}/{len(ranked)}] @{uname}...", end=" ")

        img_path = download_profile_image(member["profile_image_url"], uname.lower())
        if not img_path:
            old = existing.get(uname.lower(), {})
            old_img = old.get("profile_image")
            if old_img and (COMMUNITY_DIR / old_img).exists():
                img_path = old_img
                print("(kept existing)")
            else:
                img_path = generate_fallback_avatar(uname.lower())
                print("(fallback)")
        else:
            print("OK")

        entry = {
            "user_id": member["user_id"],
            "username": uname,
            "display_name": member["display_name"],
            "profile_image": img_path,
            "bio": member["bio"],
            "followers": member["followers"],
            "following": member["following"],
            "verified": member["verified"],
            "pharos_posts": member["pharos_posts"],
            "latest_pharos_post": member["latest_pharos_post"] or now_str,
            "profile_url": f"https://x.com/{uname}",
            "last_updated": now_str,
        }
        community.append(entry)

    json_path = DATA_DIR / "community.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(community, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Wrote {len(community)} members to {json_path}")
    print(f"Images saved to {IMAGES_DIR}")


if __name__ == "__main__":
    main()
