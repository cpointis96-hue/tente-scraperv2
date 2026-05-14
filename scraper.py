"""Playwright-based scraper for ultralight tent data."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

# CSS selectors to click when expanding interactive elements
EXPAND_SELECTORS = [
    "button[aria-expanded='false']",
    ".accordion:not(.active)",
    ".tab:not(.active)",
    "[data-toggle='collapse']",
    "summary",
    "[aria-controls]",
    ".show-more",
    ".read-more",
]

# Selectors that identify product links in catalog pages
PRODUCT_PATH_MARKERS = ["/products/", "/product/", "/shop/"]


def get_product_urls(brand: dict, page) -> list[str]:
    """Return deduplicated absolute product URLs from a catalog page.

    Filters to links whose path contains a product marker.
    """
    base = brand["catalog_url"]
    origin = "{scheme}://{netloc}".format(
        scheme=urlparse(base).scheme,
        netloc=urlparse(base).netloc,
    )

    anchors = page.query_selector_all("a[href]")
    urls: set[str] = set()

    for a in anchors:
        href = a.get_attribute("href")
        if not href:
            continue

        absolute = urljoin(origin + "/", href)
        parsed = urlparse(absolute)

        if any(marker in parsed.path for marker in PRODUCT_PATH_MARKERS):
            # Strip query params and fragment for deduplication
            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            urls.add(clean)

    return sorted(urls)


HTML_DIR = Path("/tmp/html")
IMAGE_BASE_DIR = Path("/data/images")


def _slug(text: str) -> str:
    """Convert text to filesystem-safe slug."""
    import re
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def expand_all_interactive(page) -> None:
    """Click every collapsed accordion, tab, and show-more button."""
    for selector in EXPAND_SELECTORS:
        elements = page.query_selector_all(selector)
        for el in elements:
            try:
                el.click()
                time.sleep(0.3)
            except Exception:
                pass


def scroll_to_load(page) -> None:
    """Scroll to bottom 3 times to trigger lazy loading."""
    page.keyboard.press("End")
    time.sleep(2)
    for _ in range(3):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)


def download_images(page, brand_name: str, model_name: str, dest_dir: Path) -> list[Path]:
    """Download all product images found in DOM. Returns list of saved paths."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []

    image_urls: set[str] = set()

    for img in page.query_selector_all("img[src]"):
        src = img.get_attribute("src")
        if src and src.startswith("http"):
            image_urls.add(src)

    for source in page.query_selector_all("source[srcset]"):
        srcset = source.get_attribute("srcset") or ""
        entries = [p.strip() for p in srcset.split(",") if p.strip()]
        if entries:
            # Last entry is highest resolution in a standard srcset
            highest = entries[-1].split(" ")[0]
            if highest.startswith("http"):
                image_urls.add(highest)

    for el in page.query_selector_all("[data-src]"):
        src = el.get_attribute("data-src")
        if src and src.startswith("http"):
            image_urls.add(src)

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for i, url in enumerate(sorted(image_urls)):
            try:
                resp = client.get(url)
                resp.raise_for_status()
                ext = url.split(".")[-1].split("?")[0][:4] or "jpg"
                out_path = dest_dir / f"{i:03d}.{ext}"
                out_path.write_bytes(resp.content)
                saved.append(out_path)
                logger.info("Downloaded image: %s → %s", url, out_path)
            except Exception as e:
                logger.warning("Image download failed %s: %s", url, e)

    return saved


def scrape_product(url: str, brand: dict, page) -> Path | None:
    """Scrape one product page: expand + scroll + save HTML + download images.

    Returns path to saved HTML, or None on failure.
    """
    brand_slug = _slug(brand["name"])

    try:
        page.goto(url, wait_until="networkidle")
    except Exception as e:
        logger.error("Navigation failed %s: %s", url, e)
        with open("scrape.log", "a") as f:
            f.write(f"FAIL navigate {url}: {e}\n")
        return None

    try:
        expand_all_interactive(page)
        scroll_to_load(page)

        model_slug = _slug(url.rstrip("/").split("/")[-1])

        html_content = page.content()
        html_path = HTML_DIR / f"{brand_slug}_{model_slug}.html"
        HTML_DIR.mkdir(parents=True, exist_ok=True)
        html_path.write_text(html_content, encoding="utf-8")
        logger.info("Saved HTML: %s", html_path)

        img_dir = IMAGE_BASE_DIR / brand_slug / model_slug
        saved_images = download_images(page, brand_slug, model_slug, img_dir)
        logger.info("Downloaded %d images for %s/%s", len(saved_images), brand_slug, model_slug)

        with open("scrape.log", "a") as f:
            f.write(f"OK {url} → {html_path} ({len(saved_images)} images)\n")

        return html_path

    except Exception as e:
        logger.error("Scrape failed %s: %s", url, e)
        with open("scrape.log", "a") as f:
            f.write(f"FAIL scrape {url}: {e}\n")
        return None


def scrape_brand(brand: dict, browser) -> list[Path]:
    """Scrape all products for one brand. Returns list of saved HTML paths."""
    html_paths: list[Path] = []

    with browser.new_page() as page:
        try:
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (compatible; tent-scraper/1.0)"})
            page.goto(brand["catalog_url"], wait_until="networkidle")
        except Exception as e:
            logger.error("Catalog page failed for %s: %s", brand["name"], e)
            return []

        urls = get_product_urls(brand, page)
        logger.info("Found %d products for %s", len(urls), brand["name"])

    for url in urls:
        with browser.new_page() as product_page:
            product_page.set_extra_http_headers(
                {"User-Agent": "Mozilla/5.0 (compatible; tent-scraper/1.0)"}
            )
            html_path = scrape_product(url, brand, product_page)
            if html_path:
                html_paths.append(html_path)
        time.sleep(2)

    return html_paths
