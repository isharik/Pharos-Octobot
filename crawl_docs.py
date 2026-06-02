"""
crawl_docs.py
-------------
Phase 2: Crawl the entire Pharos documentation site and save
all pages as text files in the 'raw_docs' folder.

Why we crawl first and save locally:
- We don't want to hit the website every time we test our chatbot
- Local files are much faster to process
- We can inspect what was collected

How to run:
    python crawl_docs.py

Expected output:
    🕷️  Starting to crawl https://docs.pharos.xyz/
    ✅ Collected: /introduction
    ✅ Collected: /core-technologies/...
    ...
    💾 Saved 25 pages to 'raw_docs' folder.
    🎉 Crawling complete!
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

# ─────────────────────────────────────────────
# CONFIGURATION — adjust these if needed
# ─────────────────────────────────────────────
BASE_URL = "https://docs.pharos.xyz"
OUTPUT_DIR = "raw_docs"
DELAY_BETWEEN_REQUESTS = 1.0  # seconds — be polite to the server
MAX_PAGES = 200  # safety limit so we don't run forever

# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def make_safe_filename(url: str) -> str:
    """Convert a URL path into a safe filename."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        path = "index"
    # Replace slashes and special chars with underscores
    safe = re.sub(r"[^\w\-]", "_", path)
    return safe + ".txt"


def extract_text_from_html(html: str) -> str:
    """Extract clean readable text from HTML, removing nav/footer noise."""
    soup = BeautifulSoup(html, "lxml")

    # Remove elements that aren't part of the main content
    for tag in soup.find_all(["script", "style", "nav", "footer",
                               "header", "aside", "noscript"]):
        tag.decompose()

    # Try to find the main content area
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", class_=re.compile(r"content|main|docs|page", re.I))
        or soup.find("body")
    )

    if main:
        text = main.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)

    # Clean up excessive blank lines
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def get_all_links(html: str, current_url: str) -> list[str]:
    """Find all internal links on a page that belong to the same domain."""
    soup = BeautifulSoup(html, "lxml")
    links = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        full_url = urljoin(current_url, href)

        # Only keep links that are on docs.pharos.xyz
        if full_url.startswith(BASE_URL):
            # Remove URL fragments (#section) and query strings
            clean = full_url.split("#")[0].split("?")[0].rstrip("/")
            if clean and clean not in links:
                links.append(clean)
    return links


def crawl_site() -> list[dict]:
    """
    BFS (breadth-first search) crawler.
    Visits every page once, collects text content.
    Returns a list of dicts: [{url, title, content}, ...]
    """
    visited = set()
    queue = [BASE_URL]
    collected_pages = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; OctoBot-crawler/1.0; "
            "+https://docs.pharos.xyz)"
        )
    }

    print(f"🕷️  Starting to crawl {BASE_URL}")
    print(f"📁 Saving text files to '{OUTPUT_DIR}' folder\n")

    while queue and len(collected_pages) < MAX_PAGES:
        url = queue.pop(0)

        if url in visited:
            continue
        visited.add(url)

        try:
            resp = requests.get(url, headers=headers, timeout=15)

            # Skip non-HTML responses (PDFs, images, etc.)
            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type:
                continue

            if resp.status_code != 200:
                print(f"⚠️  Skipped {url} (status {resp.status_code})")
                continue

            html = resp.text
            text = extract_text_from_html(html)

            # Extract the page title
            soup = BeautifulSoup(html, "lxml")
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else url

            if len(text) < 50:
                print(f"⚠️  Skipped {url} (too little content)")
                continue

            page_data = {
                "url": url,
                "title": title,
                "content": text
            }
            collected_pages.append(page_data)

            path = urlparse(url).path or "/"
            print(f"✅ Collected ({len(collected_pages):>3}): {path}")

            # Add newly discovered links to the queue
            new_links = get_all_links(html, url)
            for link in new_links:
                if link not in visited:
                    queue.append(link)

            # Be polite — don't hammer the server
            time.sleep(DELAY_BETWEEN_REQUESTS)

        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching {url}: {e}")

    return collected_pages


def save_pages(pages: list[dict]) -> None:
    """Save each page as a .txt file and a metadata JSON index."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    index = []  # We'll save an index.json for reference

    for page in pages:
        filename = make_safe_filename(page["url"])
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            # Write metadata header at the top of each file
            f.write(f"SOURCE_URL: {page['url']}\n")
            f.write(f"TITLE: {page['title']}\n")
            f.write("=" * 60 + "\n")
            f.write(page["content"])

        index.append({
            "url": page["url"],
            "title": page["title"],
            "filename": filename
        })

    # Save the index
    index_path = os.path.join(OUTPUT_DIR, "_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    print(f"\n💾 Saved {len(pages)} pages to '{OUTPUT_DIR}/' folder")
    print(f"📋 Index saved to '{OUTPUT_DIR}/_index.json'")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    pages = crawl_site()

    if not pages:
        print("\n❌ No pages were collected. Check your internet connection.")
    else:
        save_pages(pages)
        print(f"\n🎉 Crawling complete! Collected {len(pages)} pages.")
        print(f"\nNext step: Run  python build_vectorstore.py")