"""
crawl_docs.py  (UPDATED — 5 Verified Sources)
----------------------------------------------
Crawls 5 confirmed-accessible sources about Pharos Network.

SOURCES:
  1. docs.pharos.xyz        -> Full recursive crawl (official docs)
  2. buildonpharos.com      -> Full recursive crawl (developer hub)
  3. github.com/PharosNetwork-> Targeted README pages (code + audit docs)
  4. Medium articles        -> 6 confirmed Pharos articles (targeted fetch)
  5. web3.bitget.com        -> Pharos academy/explainer page (targeted fetch)

NOTE on pharos.xyz/blog and pharos.xyz/resources:
  These are React apps that require JavaScript to render.
  A basic requests crawler gets an empty page from them.
  They are NOT included — they would produce 0 content.
  If you want them, see the MANUAL PASTE section at the bottom.

HOW TO RUN:
    python crawl_docs.py

AFTER THIS COMPLETES:
    python build_vectorstore.py
    streamlit run app.py
"""

import os
import re
import time
import json
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = "raw_docs"

# ===============================================================
#  SOURCE CONFIGURATIONS
# ===============================================================

# ── SOURCE 1: Pharos Official Docs ──────────────────────────────
# Full recursive crawl — follows every internal link
SOURCE_1_PHAROS_DOCS = {
    "enabled": True,
    "name": "Pharos Docs",
    "type": "full_crawl",
    "base_url": "https://docs.pharos.xyz",
    "delay": 1.0,
    "max_pages": 200,
}

# ── SOURCE 2: Build on Pharos ────────────────────────────────────
# Developer hub — hackathons, grants, builder programs
# Confirmed accessible in pre-flight check
SOURCE_2_BUILDONPHAROS = {
    "enabled": True,
    "name": "Build on Pharos",
    "type": "full_crawl",
    "base_url": "https://www.buildonpharos.com",
    "delay": 1.0,
    "max_pages": 50,
}

# ── SOURCE 3: Pharos GitHub READMEs ─────────────────────────────
# Fetch specific GitHub repository pages.
# GitHub renders README content in HTML — we extract it cleanly.
# These are the most useful public repos from github.com/PharosNetwork
SOURCE_3_GITHUB = {
    "enabled": True,
    "name": "Pharos GitHub",
    "type": "targeted",
    "delay": 1.5,
    "urls": [
        # Main org page
        "https://github.com/PharosNetwork",
        # Key repositories — add/remove as needed
        "https://github.com/PharosNetwork/pharos-audit",
        "https://github.com/PharosNetwork/contracts",
        "https://github.com/PharosNetwork/examples",
        "https://github.com/PharosNetwork/resources",
        "https://github.com/PharosNetwork/ops",
    ],
}

# ── SOURCE 4: Medium Articles ────────────────────────────────────
# Confirmed Medium articles about Pharos Network.
# Medium serves static HTML for articles — extractable without JS.
# All URLs verified in search results above.
SOURCE_4_MEDIUM = {
    "enabled": True,
    "name": "Medium",
    "type": "targeted",
    "delay": 2.0,  # Medium rate-limits — be patient
    "urls": [
        # Technical deep-dives
        "https://lithiumdigital.medium.com/pharos-network-bridging-traditional-finance-and-web3-with-deep-parallel-performance-5339ad373749",
        "https://medium.com/@alphatalks/pharos-network-pioneering-the-future-of-blockchain-with-special-processing-networks-spns-62e089c48795",
        "https://medium.com/@mwaqasamin1987/pharos-network-the-layer-1-blockchain-redefining-defi-and-tradfi-integration-c60e2adc0599",
        # Analysis and overviews
        "https://medium.com/@makarcorex/pharos-network-real-rwa-contender-or-just-another-vc-l1-6ff5f46f284a",
        "https://medium.com/@PujiAnggraini/exploring-pharos-network-a-beacon-for-real-world-finance-in-blockchain-7c874206a0ab",
        "https://medium.com/gti-sonu-mehta/unveiling-pharos-network-a-deep-dive-into-its-technology-earning-opportunities-and-airdrop-55538938d869",
        "https://medium.com/@thecryptect/exploring-the-pharos-network-and-its-exciting-airdrop-opportunity-5167ff69b90b",
    ],
}

# ── SOURCE 5: Bitget Academy ────────────────────────────────────
# Pharos explainer page — covers token, SPNs, architecture
# Confirmed in search results as a clean crawlable page
SOURCE_5_BITGET = {
    "enabled": True,
    "name": "Bitget Academy",
    "type": "targeted",
    "delay": 1.5,
    "urls": [
        "https://web3.bitget.com/en/academy/what-is-pharos-network-pharos-a-high-throughput-evm-layer-1-for-real-world-asset-tokenization-and-defi-lLending",
        "https://web3.bitget.com/en/dapp/pharos-network-30127",
    ],
}

# ── MANUAL PASTE: pharos.xyz blog/resources ─────────────────────
# These pages use React and cannot be auto-crawled.
# To add them:
#   1. Open https://www.pharos.xyz/blog in Chrome
#   2. Wait for page to fully load, scroll to bottom
#   3. Ctrl+A, Ctrl+C to copy all text
#   4. Replace the placeholder below with your pasted text
#   5. Do the same for https://www.pharos.xyz/resources
#   6. Re-run: python crawl_docs.py
MANUAL_PHAROS_BLOG = {
    "enabled": True,
    "name": "Pharos Blog",
    "source_url": "https://www.pharos.xyz/blog",
    "title": "Pharos Network — Official Blog",
    "content": "PASTE_PHAROS_BLOG_CONTENT_HERE",
}

MANUAL_PHAROS_RESOURCES = {
    "enabled": True,
    "name": "Pharos Resources",
    "source_url": "https://www.pharos.xyz/resources",
    "title": "Pharos Network — Resources & Research",
    "content": "PASTE_PHAROS_RESOURCES_CONTENT_HERE",
}


# ===============================================================
#  SHARED UTILITIES
# ===============================================================

SHARED_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def make_safe_filename(url: str) -> str:
    """Turn a URL into a safe .txt filename, including the domain."""
    parsed = urlparse(url)
    domain = re.sub(r"[^\w]", "_", parsed.netloc)
    path = parsed.path.strip("/")
    if not path:
        path = "index"
    safe = re.sub(r"[^\w\-]", "_", path)
    return f"{domain}__{safe}.txt"[:200]


def extract_text(html: str) -> str:
    """Strip HTML noise and return clean readable text."""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup.find_all([
        "script", "style", "nav", "footer", "header",
        "aside", "noscript", "svg", "button", "form",
        "meta", "link",
    ]):
        tag.decompose()

    # Prefer semantic content containers
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id=re.compile(r"content|main|article|readme", re.I))
        or soup.find("div", class_=re.compile(r"content|article|post|readme|markdown", re.I))
        or soup.find("body")
    )

    raw = main.get_text(separator="\n", strip=True) if main else ""
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    return "\n".join(lines)


def get_title(html: str, fallback: str = "") -> str:
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("title")
    return tag.get_text(strip=True) if tag else fallback


def get_internal_links(html: str, current_url: str, base_url: str) -> list:
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        full = urljoin(current_url, a["href"])
        clean = full.split("#")[0].split("?")[0].rstrip("/")
        if clean.startswith(base_url) and clean not in links:
            links.append(clean)
    return links


def save_page(url: str, title: str, content: str, filename: str) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"SOURCE_URL: {url}\n")
        f.write(f"TITLE: {title}\n")
        f.write("=" * 60 + "\n")
        f.write(content)


def fetch_url(url: str, source_name: str, extra_headers: dict = None) -> tuple:
    """
    Fetch a single URL. Returns (html, status_code) or (None, error_code).
    Handles the most common failure modes with clear messages.
    """
    headers = dict(SHARED_HEADERS)
    if extra_headers:
        headers.update(extra_headers)

    try:
        resp = requests.get(url, headers=headers, timeout=20)

        if resp.status_code == 200:
            ct = resp.headers.get("content-type", "")
            if "text/html" not in ct:
                print(f"  [{source_name}] Skipped (not HTML): {url}")
                return None, "not_html"
            return resp.text, 200

        elif resp.status_code == 404:
            print(f"  [{source_name}] Not found (404): {url}")
            return None, 404

        elif resp.status_code == 403:
            print(f"  [{source_name}] Blocked (403): {url}")
            print(f"  [{source_name}]   Try manual paste for this page.")
            return None, 403

        elif resp.status_code == 429:
            print(f"  [{source_name}] Rate limited (429): {url} — waiting 10s...")
            time.sleep(10)
            return fetch_url(url, source_name, extra_headers)  # retry once

        else:
            print(f"  [{source_name}] HTTP {resp.status_code}: {url}")
            return None, resp.status_code

    except requests.exceptions.ConnectionError:
        print(f"  [{source_name}] Connection error: {url}")
        return None, "connection_error"
    except requests.exceptions.Timeout:
        print(f"  [{source_name}] Timeout: {url}")
        return None, "timeout"
    except Exception as e:
        print(f"  [{source_name}] Unexpected error: {e}")
        return None, "unknown"


# ===============================================================
#  CRAWLER TYPE A — FULL RECURSIVE CRAWL
#  Used for: Pharos Docs, Build on Pharos
# ===============================================================

def full_crawl(config: dict) -> list:
    if not config["enabled"]:
        return []

    base_url = config["base_url"]
    name = config["name"]

    print(f"\n{'='*60}")
    print(f"SOURCE: {name}")
    print(f"TYPE:   Full recursive crawl")
    print(f"URL:    {base_url}")
    print(f"{'='*60}")

    visited = set()
    queue = [base_url]
    pages = []

    while queue and len(pages) < config["max_pages"]:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        html, status = fetch_url(url, name)
        if not html:
            continue

        text = extract_text(html)
        title = get_title(html, fallback=url)

        if len(text) < 80:
            continue

        pages.append({"url": url, "title": title, "content": text})
        path = urlparse(url).path or "/"
        print(f"  [{name}] Collected ({len(pages):>3}): {path}")

        for link in get_internal_links(html, url, base_url):
            if link not in visited:
                queue.append(link)

        time.sleep(config["delay"])

    print(f"  [{name}] Done — {len(pages)} pages collected")
    return pages


# ===============================================================
#  CRAWLER TYPE B — TARGETED URL LIST
#  Used for: GitHub, Medium, Bitget
# ===============================================================

def targeted_fetch(config: dict) -> list:
    if not config["enabled"]:
        return []

    name = config["name"]
    urls = config["urls"]

    print(f"\n{'='*60}")
    print(f"SOURCE: {name}")
    print(f"TYPE:   Targeted fetch ({len(urls)} URL(s))")
    print(f"{'='*60}")

    pages = []

    for url in urls:
        # GitHub needs a Referer to avoid some redirects
        extra = {}
        if "github.com" in url:
            extra = {"Referer": "https://github.com"}
        elif "medium.com" in url:
            extra = {"Referer": "https://www.google.com/"}

        html, status = fetch_url(url, name, extra)
        if not html:
            continue

        text = extract_text(html)
        title = get_title(html, fallback=url)

        if len(text) < 80:
            print(f"  [{name}] Too little content (may be JS-rendered): {url}")
            print(f"  [{name}]   Characters extracted: {len(text)}")
            continue

        pages.append({"url": url, "title": title, "content": text})
        print(f"  [{name}] Fetched: {title[:60]}")
        print(f"  [{name}]   {len(text):,} characters — {url}")

        time.sleep(config["delay"])

    print(f"  [{name}] Done — {len(pages)} page(s) saved")
    return pages


# ===============================================================
#  CRAWLER TYPE C — MANUAL PASTE
#  Used for: pharos.xyz/blog, pharos.xyz/resources (JS-rendered)
# ===============================================================

PLACEHOLDER_MARKERS = [
    "PASTE_PHAROS_BLOG_CONTENT_HERE",
    "PASTE_PHAROS_RESOURCES_CONTENT_HERE",
    "PASTE YOUR LINKEDIN CONTENT HERE",
]

def manual_paste(config: dict) -> list:
    if not config["enabled"]:
        return []

    name = config["name"]
    content = config["content"].strip()

    is_placeholder = any(marker in content for marker in PLACEHOLDER_MARKERS)

    if is_placeholder or len(content) < 100:
        print(f"\n[{name}] Skipped — placeholder text detected.")
        print(f"[{name}]   To add this source:")
        print(f"[{name}]   1. Open {config['source_url']} in Chrome")
        print(f"[{name}]   2. Wait for page to fully load, scroll to bottom")
        print(f"[{name}]   3. Press Ctrl+A then Ctrl+C")
        print(f"[{name}]   4. In crawl_docs.py, find the content field for '{name}'")
        print(f"[{name}]   5. Delete the placeholder and paste your text")
        print(f"[{name}]   6. Save and re-run: python crawl_docs.py")
        return []

    print(f"\n[{name}] Manual content found ({len(content):,} characters)")
    return [{
        "url": config["source_url"],
        "title": config["title"],
        "content": content,
    }]


# ===============================================================
#  SAVE INDEX
# ===============================================================

def save_index(all_pages: list) -> None:
    index = []
    for page in all_pages:
        filename = make_safe_filename(page["url"])
        save_page(page["url"], page["title"], page["content"], filename)
        index.append({
            "url": page["url"],
            "title": page["title"],
            "filename": filename,
        })

    index_path = os.path.join(OUTPUT_DIR, "_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    print(f"\n  Index written: {index_path}")


# ===============================================================
#  MAIN
# ===============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  OctoBot Multi-Source Crawler — 5 Sources")
    print("=" * 60)
    print()
    print("  Source 1: Pharos Docs         (docs.pharos.xyz)")
    print("  Source 2: Build on Pharos     (buildonpharos.com)")
    print("  Source 3: Pharos GitHub       (github.com/PharosNetwork)")
    print("  Source 4: Medium Articles     (7 confirmed articles)")
    print("  Source 5: Bitget Academy      (web3.bitget.com)")
    print()
    print("  + Manual paste slots for pharos.xyz/blog and /resources")
    print()

    results = {}

    # ── 1. Pharos Docs ────────────────────────────────────────────
    results["Pharos Docs"] = full_crawl(SOURCE_1_PHAROS_DOCS)

    # ── 2. Build on Pharos ────────────────────────────────────────
    results["Build on Pharos"] = full_crawl(SOURCE_2_BUILDONPHAROS)

    # ── 3. GitHub ─────────────────────────────────────────────────
    results["GitHub"] = targeted_fetch(SOURCE_3_GITHUB)

    # ── 4. Medium ─────────────────────────────────────────────────
    results["Medium"] = targeted_fetch(SOURCE_4_MEDIUM)

    # ── 5. Bitget Academy ─────────────────────────────────────────
    results["Bitget"] = targeted_fetch(SOURCE_5_BITGET)

    # ── Manual paste sources (skipped until you fill them in) ─────
    results["Pharos Blog"] = manual_paste(MANUAL_PHAROS_BLOG)
    results["Pharos Resources"] = manual_paste(MANUAL_PHAROS_RESOURCES)

    # ── Combine and save ─────────────────────────────────────────
    all_pages = []
    for pages in results.values():
        all_pages.extend(pages)

    if not all_pages:
        print("\nNo pages collected. Check your internet connection.")
        exit(1)

    print(f"\n{'='*60}")
    print(f"  SAVING {len(all_pages)} PAGES TO '{OUTPUT_DIR}/'")
    print(f"{'='*60}")
    save_index(all_pages)

    # ── Final summary ─────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  COLLECTION SUMMARY")
    print(f"{'='*60}")
    total = 0
    for source, pages in results.items():
        count = len(pages)
        total += count
        status = f"{count} pages" if count > 0 else "0 pages (skipped or blocked)"
        print(f"  {source:<22} {status}")
    print(f"  {'─'*38}")
    print(f"  {'TOTAL':<22} {total} pages")
    print(f"{'='*60}")

    print(f"""
  Crawling complete!

  NEXT STEPS:
  ──────────────────────────────────────────
  Step 1 — Rebuild the knowledge base:
      python build_vectorstore.py

  Step 2 — Launch OctoBot:
      streamlit run app.py

  OPTIONAL — Add more content later:
  - Open pharos.xyz/blog in Chrome
  - Copy all text (Ctrl+A, Ctrl+C)
  - Paste into MANUAL_PHAROS_BLOG content field
  - Re-run both scripts above
  ──────────────────────────────────────────
""")