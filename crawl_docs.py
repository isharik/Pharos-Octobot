"""
crawl_docs.py  (UPDATED — Multi-Source Version)
------------------------------------------------
Crawls multiple sources and saves all content into the
same 'raw_docs' folder so OctoBot can answer from all of them.

SOURCES CONFIGURED:
  1. Pharos official docs   -> https://docs.pharos.xyz/        (full site crawl)
  2. CoinMarketCap          -> specific Pharos page(s)         (targeted fetch)
  3. AirdropAlert           -> specific Pharos page(s)         (targeted fetch)
  4. LinkedIn               -> manual paste (see instructions) (no crawling possible)

HOW TO RUN:
    python crawl_docs.py

EXPECTED OUTPUT:
    [Pharos Docs]    Collected (1): /
    [CoinMarketCap]  Fetched: https://coinmarketcap.com/currencies/pharos-network/
    [AirdropAlert]   Fetched: https://airdropalert.com/...
    ...
    Saved 30+ pages to 'raw_docs' folder
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

# ===============================================================
#  SOURCE CONFIGURATION — Edit this section to add/change sources
# ===============================================================

# SOURCE 1: Pharos Official Docs — full recursive crawl
PHAROS_DOCS_CONFIG = {
    "enabled": True,
    "name": "Pharos Docs",
    "base_url": "https://docs.pharos.xyz",
    "delay": 1.0,
    "max_pages": 200,
}

# SOURCE 2: CoinMarketCap — add specific Pharos page URLs
COINMARKETCAP_CONFIG = {
    "enabled": True,
    "name": "CoinMarketCap",
    "urls": [
        "https://coinmarketcap.com/currencies/pharos-network/",
        # Add more CMC URLs here as needed
    ],
    "delay": 2.0,
}

# SOURCE 3: AirdropAlert — add specific Pharos page URLs
AIRDROPALERT_CONFIG = {
    "enabled": True,
    "name": "AirdropAlert",
    "urls": [
        "https://airdropalert.com/airdrops/pharos",
        "https://airdropalert.com/airdrops/pharos-network",
        # Find the exact URL by visiting airdropalert.com and searching "Pharos"
    ],
    "delay": 1.5,
}

# SOURCE 4: LinkedIn — MANUAL PASTE ONLY
# LinkedIn blocks all automated crawlers. Instead:
# 1. Open https://www.linkedin.com/company/pharos-network/about/ in your browser
# 2. Scroll through the page to load all content
# 3. Press Ctrl+A to select all, then Ctrl+C to copy
# 4. Delete the placeholder text below and paste your copied content
# 5. Save this file and re-run: python crawl_docs.py
LINKEDIN_MANUAL_CONTENT = """
PASTE YOUR LINKEDIN CONTENT HERE.

Instructions:
1. Open https://www.linkedin.com/company/pharos-network/about/ in your browser
2. Scroll through the entire page to load all content
3. Press Ctrl+A to select all text, then Ctrl+C to copy
4. Delete these instructions and paste the copied text here
5. Save this file and run: python crawl_docs.py

If you leave this as-is, LinkedIn will simply be skipped.
"""

LINKEDIN_CONFIG = {
    "enabled": True,
    "name": "LinkedIn",
    "source_url": "https://www.linkedin.com/company/pharos-network/about/",
    "title": "Pharos Network — LinkedIn Company Page",
    "content": LINKEDIN_MANUAL_CONTENT,
}

OUTPUT_DIR = "raw_docs"

# ===============================================================
#  SHARED UTILITIES
# ===============================================================

def make_safe_filename(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.replace(".", "_").replace("www_", "")
    path = parsed.path.strip("/")
    if not path:
        path = "index"
    safe_path = re.sub(r"[^\w\-]", "_", path)
    return f"{domain}__{safe_path}.txt"[:200]


def extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["script", "style", "nav", "footer",
                               "header", "aside", "noscript", "svg", "button"]):
        tag.decompose()
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id=re.compile(r"content|main|article", re.I))
        or soup.find("div", class_=re.compile(r"content|main|article|body", re.I))
        or soup.find("body")
    )
    raw = main.get_text(separator="\n", strip=True) if main else soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return "\n".join(lines)


def get_page_title(html: str, fallback: str = "") -> str:
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("title")
    return tag.get_text(strip=True) if tag else fallback


SHARED_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def save_page(url: str, title: str, content: str, filename: str) -> None:
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"SOURCE_URL: {url}\n")
        f.write(f"TITLE: {title}\n")
        f.write("=" * 60 + "\n")
        f.write(content)


# ===============================================================
#  CRAWLER 1 — PHAROS DOCS (full recursive crawl)
# ===============================================================

def get_internal_links(html: str, current_url: str, base_url: str) -> list:
    soup = BeautifulSoup(html, "lxml")
    links = []
    for anchor in soup.find_all("a", href=True):
        full = urljoin(current_url, anchor["href"])
        clean = full.split("#")[0].split("?")[0].rstrip("/")
        if clean.startswith(base_url) and clean not in links:
            links.append(clean)
    return links


def crawl_pharos_docs(config: dict) -> list:
    if not config["enabled"]:
        return []

    base_url = config["base_url"]
    print(f"\n{'='*60}")
    print(f"[{config['name']}] Starting full site crawl of {base_url}")
    print(f"{'='*60}")

    visited = set()
    queue = [base_url]
    pages = []

    while queue and len(pages) < config["max_pages"]:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            resp = requests.get(url, headers=SHARED_HEADERS, timeout=15)
            if "text/html" not in resp.headers.get("content-type", ""):
                continue
            if resp.status_code != 200:
                print(f"  [{config['name']}] Skip {url} (HTTP {resp.status_code})")
                continue

            text = extract_text_from_html(resp.text)
            title = get_page_title(resp.text, fallback=url)
            if len(text) < 50:
                continue

            pages.append({"url": url, "title": title, "content": text})
            path = urlparse(url).path or "/"
            print(f"  [{config['name']}] Collected ({len(pages):>3}): {path}")

            for link in get_internal_links(resp.text, url, base_url):
                if link not in visited:
                    queue.append(link)

            time.sleep(config["delay"])

        except requests.exceptions.RequestException as e:
            print(f"  [{config['name']}] Error: {url} - {e}")

    print(f"  [{config['name']}] Done: {len(pages)} pages collected")
    return pages


# ===============================================================
#  CRAWLER 2 — TARGETED URL FETCHER (CoinMarketCap, AirdropAlert)
# ===============================================================

def fetch_specific_urls(config: dict) -> list:
    if not config["enabled"]:
        return []

    print(f"\n{'='*60}")
    print(f"[{config['name']}] Fetching {len(config['urls'])} URL(s)")
    print(f"{'='*60}")

    pages = []

    for url in config["urls"]:
        try:
            headers = dict(SHARED_HEADERS)
            if "coinmarketcap" in url:
                headers["Referer"] = "https://www.google.com/"

            resp = requests.get(url, headers=headers, timeout=20)

            if resp.status_code == 404:
                print(f"  [{config['name']}] Not found (404): {url}")
                print(f"  [{config['name']}]   The Pharos page may not exist on this site yet.")
                continue

            if resp.status_code == 403:
                print(f"  [{config['name']}] Access denied (403): {url}")
                print(f"  [{config['name']}]   This site blocks automated access.")
                print(f"  [{config['name']}]   Try manual copy-paste instead (see LINKEDIN example).")
                continue

            if resp.status_code != 200:
                print(f"  [{config['name']}] HTTP {resp.status_code}: {url}")
                continue

            if "text/html" not in resp.headers.get("content-type", ""):
                print(f"  [{config['name']}] Not HTML: {url}")
                continue

            text = extract_text_from_html(resp.text)
            title = get_page_title(resp.text, fallback=url)

            if len(text) < 80:
                print(f"  [{config['name']}] Too little content from {url}")
                print(f"  [{config['name']}]   Page may use JavaScript. Try manual paste.")
                continue

            pages.append({"url": url, "title": title, "content": text})
            print(f"  [{config['name']}] Fetched: {url}")
            print(f"  [{config['name']}]   {len(text)} characters extracted")

            time.sleep(config["delay"])

        except requests.exceptions.ConnectionError:
            print(f"  [{config['name']}] Could not connect to {url}")
        except requests.exceptions.Timeout:
            print(f"  [{config['name']}] Timed out: {url}")
        except Exception as e:
            print(f"  [{config['name']}] Unexpected error: {e}")

    print(f"  [{config['name']}] Done: {len(pages)} page(s) saved")
    return pages


# ===============================================================
#  SOURCE 4 — LINKEDIN (manual paste handler)
# ===============================================================

LINKEDIN_PLACEHOLDER = "PASTE YOUR LINKEDIN CONTENT HERE."


def process_linkedin_manual(config: dict) -> list:
    if not config["enabled"]:
        return []

    content = config["content"].strip()

    if LINKEDIN_PLACEHOLDER in content or len(content) < 100:
        print(f"\n{'='*60}")
        print(f"[LinkedIn] Skipped — no content pasted yet.")
        print(f"[LinkedIn] To add LinkedIn:")
        print(f"[LinkedIn]   1. Open: https://www.linkedin.com/company/pharos-network/about/")
        print(f"[LinkedIn]   2. Select all (Ctrl+A), copy (Ctrl+C)")
        print(f"[LinkedIn]   3. In crawl_docs.py, find LINKEDIN_MANUAL_CONTENT")
        print(f"[LinkedIn]   4. Delete the instructions, paste your text")
        print(f"[LinkedIn]   5. Save and re-run: python crawl_docs.py")
        print(f"{'='*60}")
        return []

    print(f"\n{'='*60}")
    print(f"[LinkedIn] Manual content found ({len(content)} characters)")
    print(f"{'='*60}")

    return [{
        "url": config["source_url"],
        "title": config["title"],
        "content": content,
    }]


# ===============================================================
#  SAVE ALL PAGES
# ===============================================================

def save_all_pages(all_pages: list) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
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

    print(f"\n{'='*60}")
    print(f"Saved {len(all_pages)} total pages to '{OUTPUT_DIR}/'")
    print(f"Index written to '{OUTPUT_DIR}/_index.json'")
    print(f"{'='*60}")


# ===============================================================
#  HOW TO ADD MORE SOURCES IN THE FUTURE
#
#  Option A - Specific pages (any public site):
#    1. Create a new config dict like COINMARKETCAP_CONFIG
#    2. Add your URLs to the "urls" list
#    3. Call fetch_specific_urls(your_config) in main below
#    4. Add result to all_pages
#    5. Re-run: python crawl_docs.py  then  python build_vectorstore.py
#
#  Option B - Full site crawl:
#    1. Duplicate PHAROS_DOCS_CONFIG, change base_url
#    2. Call crawl_pharos_docs(your_config) in main below
#    3. Add result to all_pages
#    4. Re-run both scripts
#
#  Option C - Sites that block crawlers:
#    1. Copy page content manually from browser
#    2. Use the LinkedIn manual paste pattern above
# ===============================================================


# ===============================================================
#  MAIN
# ===============================================================

if __name__ == "__main__":
    print("OctoBot Multi-Source Crawler")
    print("=" * 60)
    print("Sources configured:")
    print("  1. Pharos Docs     (full site crawl)")
    print("  2. CoinMarketCap   (targeted pages)")
    print("  3. AirdropAlert    (targeted pages)")
    print("  4. LinkedIn        (manual paste)")
    print()

    all_pages = []

    # 1. Pharos official docs
    pharos_pages = crawl_pharos_docs(PHAROS_DOCS_CONFIG)
    all_pages.extend(pharos_pages)

    # 2. CoinMarketCap
    cmc_pages = fetch_specific_urls(COINMARKETCAP_CONFIG)
    all_pages.extend(cmc_pages)

    # 3. AirdropAlert
    airdrop_pages = fetch_specific_urls(AIRDROPALERT_CONFIG)
    all_pages.extend(airdrop_pages)

    # 4. LinkedIn (manual)
    linkedin_pages = process_linkedin_manual(LINKEDIN_CONFIG)
    all_pages.extend(linkedin_pages)

    # Summary
    print(f"\nCOLLECTION SUMMARY")
    print(f"  Pharos Docs:   {len(pharos_pages)} pages")
    print(f"  CoinMarketCap: {len(cmc_pages)} pages")
    print(f"  AirdropAlert:  {len(airdrop_pages)} pages")
    print(f"  LinkedIn:      {len(linkedin_pages)} pages")
    print(f"  --------------------------")
    print(f"  TOTAL:         {len(all_pages)} pages")

    if not all_pages:
        print("\nNo pages collected. Check your internet connection.")
        exit(1)

    save_all_pages(all_pages)

    print(f"\nCrawling complete!")
    print(f"\nNEXT STEPS:")
    print(f"  1. Run:  python build_vectorstore.py")
    print(f"     (Rebuilds OctoBot knowledge base with all sources)")
    print(f"  2. Then: streamlit run app.py")
    print(f"\nTIP: If CoinMarketCap or AirdropAlert returned 0 pages,")
    print(f"  open the URL in your browser to verify Pharos is listed.")
    print(f"  Copy the exact page URL and update the config in this file.")