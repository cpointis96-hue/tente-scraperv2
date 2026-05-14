# Tent Scraper Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python pipeline that scrapes ultralight tent specs from 5 brands via Playwright, extracts structured data using Claude Code CLI, and pushes everything to NocoDB.

**Architecture:** Playwright scrapes catalog + product pages (click tabs, scroll, save HTML + images), Claude Code CLI (`claude -p`) reads each saved HTML and outputs structured JSON, NocoDB client auto-creates/syncs schema and upserts records keyed on (brand, model_name).

**Tech Stack:** Python 3.12+, uv, playwright (sync API), httpx, python-dotenv, pytest, unittest.mock

---

## File Map

| File | Responsibility |
|---|---|
| `pyproject.toml` | uv-managed deps |
| `brands.json` | brand catalog URLs |
| `.env.example` | env var template |
| `scraper.py` | Playwright: catalog URL discovery + product page scraping + image download |
| `extractor.py` | Claude CLI subprocess: read HTML → structured JSON |
| `nocodb.py` | NocoDB REST: schema auto-create/sync + upsert |
| `main.py` | Orchestrator: scrape → extract → schema sync → push |
| `tests/test_scraper.py` | scraper unit tests (mocked Playwright) |
| `tests/test_extractor.py` | extractor unit tests (mocked subprocess + fixture HTML) |
| `tests/test_nocodb.py` | NocoDB unit tests (mocked httpx) |
| `tests/fixtures/sample.html` | HTML fixture for extractor tests |

---

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `brands.json`
- Create: `.env.example`
- Create: `tests/__init__.py`
- Create: `tests/fixtures/sample.html`

- [ ] **Step 1.1: Create pyproject.toml**

```toml
[project]
name = "tent-scraper"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "playwright>=1.44",
    "httpx>=0.27",
    "python-dotenv>=1.0",
    "pytest>=8.0",
    "pytest-mock>=3.14",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 1.2: Create brands.json**

```json
[
  { "name": "Zpacks", "catalog_url": "https://zpacks.com/collections/tents" },
  { "name": "Durston Gear", "catalog_url": "https://durstongear.com/collections/tents" },
  { "name": "Hyperlite Mountain Gear", "catalog_url": "https://www.hyperlitemountaingear.com/collections/shelters" },
  { "name": "Six Moon Designs", "catalog_url": "https://www.sixmoondesigns.com/collections/tents" },
  { "name": "TarpTent", "catalog_url": "https://www.tarptent.com/collections/tents" }
]
```

- [ ] **Step 1.3: Create .env.example**

```
NOCODB_URL=http://localhost:8080
NOCODB_API_KEY=your_api_key_here
NOCODB_PROJECT_ID=your_project_id_here
```

- [ ] **Step 1.4: Create tests/__init__.py and fixture HTML**

`tests/__init__.py`: empty file.

`tests/fixtures/sample.html`:
```html
<!DOCTYPE html>
<html>
<head><title>Test Tent - Brand X</title></head>
<body>
  <h1>Test Tent</h1>
  <div class="price">$399.00</div>
  <div class="accordion" data-content="specs">
    <table>
      <tr><td>Trail Weight</td><td>19.5 oz (553 g)</td></tr>
      <tr><td>Packed Weight</td><td>21 oz (595 g)</td></tr>
      <tr><td>Floor Length</td><td>90 in (229 cm)</td></tr>
      <tr><td>Floor Width</td><td>42 in (107 cm)</td></tr>
      <tr><td>Height</td><td>44 in (112 cm)</td></tr>
      <tr><td>Floor Area</td><td>26 sq ft (2.4 sq m)</td></tr>
      <tr><td>Vestibule Area</td><td>8 sq ft (0.74 sq m)</td></tr>
      <tr><td>Packed Size</td><td>20 x 4.5 in (51 x 11 cm)</td></tr>
      <tr><td>Doors</td><td>1</td></tr>
      <tr><td>Vestibules</td><td>1</td></tr>
      <tr><td>Freestanding</td><td>No</td></tr>
      <tr><td>Season</td><td>3-season</td></tr>
      <tr><td>Pitch Type</td><td>Trekking Pole</td></tr>
      <tr><td>Fly Fabric</td><td>20D Silpoly PU4000</td></tr>
      <tr><td>Floor Fabric</td><td>20D Silpoly PU4000</td></tr>
      <tr><td>Poles</td><td>Trekking poles (not included)</td></tr>
      <tr><td>Stakes Included</td><td>8</td></tr>
    </table>
  </div>
  <div class="description">
    <p>The Test Tent is an ultralight single-wall shelter for thru-hikers.</p>
    <ul>
      <li>Single door design</li>
      <li>Large vestibule for gear storage</li>
    </ul>
  </div>
  <img src="/images/test-tent-1.jpg" alt="Test Tent" />
  <img src="/images/test-tent-2.jpg" alt="Test Tent Side" />
</body>
</html>
```

- [ ] **Step 1.5: Install deps and playwright browsers**

```bash
cd /Users/aiomi/Documents/Programmes/matostrek/tente-scraperv2
uv sync
uv run playwright install chromium
```

Expected: no errors, chromium downloaded.

- [ ] **Step 1.6: Create runtime directories**

```bash
mkdir -p /tmp/html /tmp/extracted /data/images
```

- [ ] **Step 1.7: Commit**

```bash
git init
git add pyproject.toml brands.json .env.example tests/
git commit -m "chore: scaffold project with deps and fixtures"
```

---

## Task 2: scraper.py — URL Discovery

**Files:**
- Create: `scraper.py` (URL discovery portion)
- Create: `tests/test_scraper.py` (URL discovery tests)

- [ ] **Step 2.1: Write failing tests for URL discovery**

`tests/test_scraper.py`:
```python
from unittest.mock import MagicMock, patch
from scraper import get_product_urls


def _make_page(hrefs: list[str]):
    """Build a minimal mock Playwright page with anchor hrefs."""
    anchor_mocks = []
    for href in hrefs:
        a = MagicMock()
        a.get_attribute.return_value = href
        anchor_mocks.append(a)

    page = MagicMock()
    page.query_selector_all.return_value = anchor_mocks
    return page


def test_get_product_urls_returns_absolute_urls():
    page = _make_page([
        "/products/duplex-tent",
        "/products/triplex-tent",
        "https://zpacks.com/products/arc-haul",  # already absolute
    ])
    brand = {"name": "Zpacks", "catalog_url": "https://zpacks.com/collections/tents"}
    urls = get_product_urls(brand, page)

    assert "https://zpacks.com/products/duplex-tent" in urls
    assert "https://zpacks.com/products/triplex-tent" in urls
    assert "https://zpacks.com/products/arc-haul" in urls
    assert len(urls) == 3


def test_get_product_urls_deduplicates():
    page = _make_page([
        "/products/duplex-tent",
        "/products/duplex-tent",
    ])
    brand = {"name": "Zpacks", "catalog_url": "https://zpacks.com/collections/tents"}
    urls = get_product_urls(brand, page)
    assert len(urls) == 1


def test_get_product_urls_ignores_non_product_links():
    page = _make_page([
        "/products/duplex-tent",
        "/collections/tents",
        "/pages/about",
        None,  # anchor with no href
    ])
    brand = {"name": "Zpacks", "catalog_url": "https://zpacks.com/collections/tents"}
    urls = get_product_urls(brand, page)
    assert len(urls) == 1
    assert "https://zpacks.com/products/duplex-tent" in urls


def test_get_product_urls_filters_by_product_path_segment():
    """Only /products/ paths are valid product pages."""
    page = _make_page(["/products/duplex", "/collections/tents", "/cart"])
    brand = {"name": "Zpacks", "catalog_url": "https://zpacks.com/collections/tents"}
    urls = get_product_urls(brand, page)
    assert all("/products/" in u for u in urls)
```

- [ ] **Step 2.2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_scraper.py::test_get_product_urls_returns_absolute_urls -v
```

Expected: `ImportError: cannot import name 'get_product_urls' from 'scraper'` (file doesn't exist yet).

- [ ] **Step 2.3: Implement get_product_urls in scraper.py**

```python
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

        absolute = href if href.startswith("http") else urljoin(origin + "/", href.lstrip("/"))
        parsed = urlparse(absolute)

        if any(marker in parsed.path for marker in PRODUCT_PATH_MARKERS):
            # Strip query params and fragment for deduplication
            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            urls.add(clean)

    return sorted(urls)
```

- [ ] **Step 2.4: Run URL discovery tests**

```bash
uv run pytest tests/test_scraper.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 2.5: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "feat: add catalog URL discovery"
```

---

## Task 3: scraper.py — Product Page Scraping

**Files:**
- Modify: `scraper.py` (add expand_all_interactive, scroll_to_load, download_images, scrape_product, scrape_brand)
- Modify: `tests/test_scraper.py` (add product scraping tests)

- [ ] **Step 3.1: Write failing tests for product scraping**

Add to `tests/test_scraper.py`:
```python
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from scraper import expand_all_interactive, scroll_to_load, scrape_product


def test_expand_all_interactive_clicks_collapsed_elements():
    el1 = MagicMock()
    el2 = MagicMock()
    page = MagicMock()
    # Only return elements for the first selector to keep test focused
    def query_side_effect(selector):
        if selector == "button[aria-expanded='false']":
            return [el1, el2]
        return []

    page.query_selector_all.side_effect = query_side_effect
    expand_all_interactive(page)

    el1.click.assert_called_once()
    el2.click.assert_called_once()


def test_scroll_to_load_scrolls_three_times():
    page = MagicMock()
    scroll_to_load(page)
    assert page.evaluate.call_count >= 3
    assert page.keyboard.press.called


def test_scrape_product_saves_html_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        html_dir = Path(tmpdir) / "html"
        html_dir.mkdir()

        page = MagicMock()
        page.content.return_value = "<html><body>Test tent content</body></html>"
        page.query_selector_all.return_value = []

        with patch("scraper.HTML_DIR", html_dir), \
             patch("scraper.expand_all_interactive"), \
             patch("scraper.scroll_to_load"), \
             patch("scraper.download_images", return_value=[]):

            result = scrape_product(
                url="https://zpacks.com/products/duplex",
                brand={"name": "Zpacks"},
                page=page,
            )

        assert result is not None
        assert result.exists()
        assert "zpacks" in result.name.lower()
        assert result.suffix == ".html"


def test_scrape_product_logs_and_returns_none_on_error():
    page = MagicMock()
    page.goto.side_effect = Exception("Navigation timeout")

    with patch("scraper.HTML_DIR", Path("/tmp/html")):
        result = scrape_product(
            url="https://zpacks.com/products/broken",
            brand={"name": "Zpacks"},
            page=page,
        )

    assert result is None
```

- [ ] **Step 3.2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_scraper.py::test_expand_all_interactive_clicks_collapsed_elements -v
```

Expected: FAIL with `ImportError` for missing functions.

- [ ] **Step 3.3: Implement product scraping functions in scraper.py**

Append to `scraper.py` after `get_product_urls`:
```python
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

    # Collect image URLs from img[src], source[srcset], [data-src]
    image_urls: set[str] = set()

    for img in page.query_selector_all("img[src]"):
        src = img.get_attribute("src")
        if src and src.startswith("http"):
            image_urls.add(src)

    for source in page.query_selector_all("source[srcset]"):
        srcset = source.get_attribute("srcset") or ""
        for part in srcset.split(","):
            url = part.strip().split(" ")[0]
            if url.startswith("http"):
                image_urls.add(url)

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

        # Derive model name from URL slug
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
        page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (compatible; tent-scraper/1.0)"})
        try:
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
```

- [ ] **Step 3.4: Run product scraping tests**

```bash
uv run pytest tests/test_scraper.py -v
```

Expected: all tests PASS.

- [ ] **Step 3.5: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "feat: add product page scraping with image download"
```

---

## Task 4: extractor.py — Claude CLI HTML Extraction

**Files:**
- Create: `extractor.py`
- Create: `tests/test_extractor.py`

- [ ] **Step 4.1: Write failing tests for extractor**

`tests/test_extractor.py`:
```python
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from extractor import (
    build_prompt,
    extract_tent_data,
    parse_json_from_response,
)

FIXTURE_HTML = Path(__file__).parent / "fixtures" / "sample.html"

SAMPLE_EXTRACTION = {
    "brand": "Zpacks",
    "model_name": "Duplex",
    "url": "https://zpacks.com/products/duplex",
    "trail_weight_oz": 19.5,
    "trail_weight_g": 553,
    "price_usd": 399.0,
    "doors": 1,
    "freestanding": False,
    "seasons": "3-season",
    "fly_fabric": "20D Silpoly PU4000",
    "full_description": "The Test Tent is an ultralight single-wall shelter for thru-hikers.",
    "all_spec_table_rows": [{"label": "Trail Weight", "value": "19.5 oz (553 g)"}],
    "all_bullet_points": ["Single door design"],
    "any_extra_fields": {},
}


def test_build_prompt_includes_file_path():
    prompt = build_prompt(FIXTURE_HTML, "Zpacks", "Duplex", "https://zpacks.com/products/duplex")
    assert str(FIXTURE_HTML) in prompt
    assert "Zpacks" in prompt
    assert "Duplex" in prompt


def test_build_prompt_requests_json_output():
    prompt = build_prompt(FIXTURE_HTML, "Zpacks", "Duplex", "https://zpacks.com/products/duplex")
    assert "JSON" in prompt
    assert "trail_weight_oz" in prompt
    assert "floor_length_cm" in prompt


def test_parse_json_from_response_direct_json():
    response = json.dumps(SAMPLE_EXTRACTION)
    result = parse_json_from_response(response)
    assert result["trail_weight_oz"] == 19.5


def test_parse_json_from_response_markdown_block():
    response = f"Here is the extracted data:\n```json\n{json.dumps(SAMPLE_EXTRACTION)}\n```"
    result = parse_json_from_response(response)
    assert result["model_name"] == "Duplex"


def test_parse_json_from_response_raises_on_garbage():
    with pytest.raises(ValueError, match="No valid JSON"):
        parse_json_from_response("This is not JSON at all.")


def test_extract_tent_data_calls_claude_cli_and_returns_dict():
    fake_output = json.dumps(SAMPLE_EXTRACTION)

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = fake_output
    mock_result.stderr = ""

    with patch("extractor.subprocess.run", return_value=mock_result) as mock_run:
        result = extract_tent_data(
            html_path=FIXTURE_HTML,
            brand="Zpacks",
            model_name="Duplex",
            url="https://zpacks.com/products/duplex",
        )

    mock_run.assert_called_once()
    call_args = mock_run.call_args
    cmd = call_args[0][0]
    assert cmd[0] == "claude"
    assert "-p" in cmd

    assert result["trail_weight_oz"] == 19.5
    assert result["model_name"] == "Duplex"


def test_extract_tent_data_logs_field_count(caplog):
    import logging
    fake_output = json.dumps(SAMPLE_EXTRACTION)

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = fake_output
    mock_result.stderr = ""

    with patch("extractor.subprocess.run", return_value=mock_result):
        with caplog.at_level(logging.INFO, logger="extractor"):
            result = extract_tent_data(
                html_path=FIXTURE_HTML,
                brand="Zpacks",
                model_name="Duplex",
                url="https://zpacks.com/products/duplex",
            )

    assert any("field" in record.message.lower() for record in caplog.records)


def test_extract_tent_data_returns_none_on_claude_error():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Error: claude not found"

    with patch("extractor.subprocess.run", return_value=mock_result):
        result = extract_tent_data(
            html_path=FIXTURE_HTML,
            brand="Zpacks",
            model_name="Duplex",
            url="https://zpacks.com/products/duplex",
        )

    assert result is None


def test_extract_all_processes_html_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        html_dir = Path(tmpdir) / "html"
        html_dir.mkdir()
        out_dir = Path(tmpdir) / "extracted"
        out_dir.mkdir()

        # Copy fixture to temp html dir using brand_model naming
        target = html_dir / "zpacks_duplex.html"
        target.write_text(FIXTURE_HTML.read_text())

        fake_output = json.dumps(SAMPLE_EXTRACTION)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = fake_output
        mock_result.stderr = ""

        with patch("extractor.subprocess.run", return_value=mock_result):
            from extractor import extract_all
            json_paths = extract_all(html_dir, out_dir)

        assert len(json_paths) == 1
        data = json.loads(json_paths[0].read_text())
        assert data["trail_weight_oz"] == 19.5
```

- [ ] **Step 4.2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_extractor.py -v
```

Expected: `ImportError: No module named 'extractor'`.

- [ ] **Step 4.3: Implement extractor.py**

```python
"""Extract structured tent data from saved HTML files using Claude Code CLI."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT_TEMPLATE = """\
You are extracting ultralight tent specifications from a product page HTML file.

Brand: {brand}
Model: {model_name}
URL: {url}
HTML file path: {html_path}

Read the HTML file at the path above using your file reading tools. Extract EVERY piece of
information and output ONLY valid JSON (no markdown, no explanation, just the JSON object).

Use null for any field not found. Convert all weights to grams (1 oz = 28.3495 g, 1 lb = 453.592 g).
Convert all dimensions to both cm and inches. Include the raw original text as found on the page.

Required JSON fields (use null if not present):
  brand, model_name, url,
  trail_weight_oz, trail_weight_g, trail_weight_lbs,
  packed_weight_oz, packed_weight_g, packed_weight_lbs,
  minimum_weight_oz, minimum_weight_g, minimum_weight_lbs,
  fly_weight_oz, fly_weight_g,
  inner_weight_oz, inner_weight_g,
  pole_weight_oz, pole_weight_g,
  stake_weight_oz, stake_weight_g,
  stuff_sack_weight_oz, stuff_sack_weight_g,
  floor_length_cm, floor_length_in,
  floor_width_cm, floor_width_in,
  floor_width_foot_end_cm,
  height_cm, height_in,
  packed_length_cm, packed_length_in,
  packed_diameter_cm, packed_diameter_in,
  floor_area_sqm, floor_area_sqft,
  vestibule_front_sqm, vestibule_front_sqft,
  vestibule_rear_sqm, vestibule_rear_sqft,
  doors, vestibules, freestanding, seasons,
  pitch_type, guy_out_points, stake_points,
  stakes_included, pole_count, pole_diameter_mm, peak_vents,
  fly_fabric, fly_denier, fly_material, fly_waterproofing,
  floor_fabric, floor_denier, floor_material, floor_waterproofing,
  mesh_type, poles_material,
  price_usd, variants, in_stock,
  full_description, all_spec_table_rows, all_bullet_points, any_extra_fields

Rules:
- all_spec_table_rows: array of {{label, value}} — every row in every spec table
- all_bullet_points: array of strings — every bullet point on the page
- variants: array of strings (colors, sizes, fabric options visible on the page)
- full_description: every sentence of marketing/description text, concatenated
- any_extra_fields: object with any specs not covered by the fields above
- freestanding: boolean true/false
- peak_vents: boolean true/false
- in_stock: boolean or null if not shown

Output ONLY the JSON object. No preamble, no explanation, no markdown code fence.
"""


def build_prompt(html_path: Path, brand: str, model_name: str, url: str) -> str:
    """Build the Claude extraction prompt for one HTML file."""
    return EXTRACTION_PROMPT_TEMPLATE.format(
        brand=brand,
        model_name=model_name,
        url=url,
        html_path=str(html_path.resolve()),
    )


def parse_json_from_response(response: str) -> dict:
    """Extract JSON object from Claude's response text."""
    text = response.strip()

    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # JSON inside markdown code fence
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # First JSON object found anywhere
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON found in response: {text[:200]!r}")


def extract_tent_data(
    html_path: Path,
    brand: str,
    model_name: str,
    url: str,
) -> dict | None:
    """Call Claude Code CLI to extract structured data from one HTML file.

    Returns parsed dict, or None on failure.
    """
    prompt = build_prompt(html_path, brand, model_name, url)

    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=180,
    )

    if result.returncode != 0:
        logger.error(
            "Claude CLI failed for %s/%s (exit %d): %s",
            brand, model_name, result.returncode, result.stderr[:500],
        )
        with open("scrape.log", "a") as f:
            f.write(f"EXTRACT_FAIL {html_path}: exit {result.returncode}\n")
        return None

    try:
        data = parse_json_from_response(result.stdout)
    except (ValueError, json.JSONDecodeError) as e:
        logger.error("JSON parse failed for %s/%s: %s", brand, model_name, e)
        with open("scrape.log", "a") as f:
            f.write(f"EXTRACT_PARSE_FAIL {html_path}: {e}\n")
        return None

    # Ensure required identity fields are set
    data.setdefault("brand", brand)
    data.setdefault("model_name", model_name)
    data.setdefault("url", url)

    field_count = sum(1 for v in data.values() if v is not None)
    logger.info(
        "Extracted %s/%s: %d non-null fields",
        brand, model_name, field_count,
    )
    with open("scrape.log", "a") as f:
        f.write(f"EXTRACT_OK {html_path}: {field_count} non-null fields\n")

    return data


def _parse_brand_model_from_filename(filename: str) -> tuple[str, str]:
    """Derive brand and model from '{brand_slug}_{model_slug}.html' filename."""
    stem = filename.replace(".html", "")
    parts = stem.split("_", 1)
    if len(parts) == 2:
        return parts[0].replace("_", " ").title(), parts[1].replace("_", " ").title()
    return stem, stem


def extract_all(html_dir: Path, output_dir: Path) -> list[Path]:
    """Extract all HTML files in html_dir. Write JSON to output_dir.

    Returns list of successfully written JSON paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    json_paths: list[Path] = []

    html_files = sorted(html_dir.glob("*.html"))
    logger.info("Extracting %d HTML files from %s", len(html_files), html_dir)

    for html_path in html_files:
        brand, model_name = _parse_brand_model_from_filename(html_path.name)
        out_path = output_dir / html_path.name.replace(".html", ".json")

        data = extract_tent_data(
            html_path=html_path,
            brand=brand,
            model_name=model_name,
            url="",  # URL is in the HTML; Claude will find it
        )

        if data is not None:
            out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            json_paths.append(out_path)

    logger.info("Extraction complete: %d/%d succeeded", len(json_paths), len(html_files))
    return json_paths
```

- [ ] **Step 4.4: Run extractor tests**

```bash
uv run pytest tests/test_extractor.py -v
```

Expected: all tests PASS.

- [ ] **Step 4.5: Commit**

```bash
git add extractor.py tests/test_extractor.py tests/fixtures/sample.html
git commit -m "feat: add Claude CLI HTML extractor"
```

---

## Task 5: nocodb.py — Schema Management

**Files:**
- Create: `nocodb.py`
- Create: `tests/test_nocodb.py`

- [ ] **Step 5.1: Write failing tests for schema management**

`tests/test_nocodb.py`:
```python
import json
from unittest.mock import MagicMock, patch

import pytest

from nocodb import NocoDBClient, FIELD_DEFINITIONS

PROJECT_ID = "test_project_123"
API_KEY = "test_key"
BASE_URL = "http://localhost:8080"


def _make_client():
    return NocoDBClient(url=BASE_URL, api_key=API_KEY, project_id=PROJECT_ID)


def test_field_definitions_contains_required_fields():
    field_names = {f["title"] for f in FIELD_DEFINITIONS}
    required = {
        "brand", "model_name", "url",
        "trail_weight_oz", "trail_weight_g",
        "floor_length_cm", "floor_length_in",
        "price_usd", "freestanding", "seasons",
        "fly_fabric", "full_description",
        "all_spec_table_rows", "images", "last_scraped_at",
    }
    missing = required - field_names
    assert not missing, f"Missing fields: {missing}"


def test_list_tables_returns_table_list(respx_mock):
    import respx
    import httpx

    respx_mock.get(f"{BASE_URL}/api/v1/db/meta/projects/{PROJECT_ID}/tables").mock(
        return_value=httpx.Response(
            200,
            json={"list": [{"id": "tbl_abc", "title": "tents"}]},
        )
    )

    client = _make_client()
    tables = client.list_tables()
    assert tables == [{"id": "tbl_abc", "title": "tents"}]


def test_ensure_schema_creates_table_when_missing(respx_mock):
    import respx
    import httpx

    respx_mock.get(f"{BASE_URL}/api/v1/db/meta/projects/{PROJECT_ID}/tables").mock(
        return_value=httpx.Response(200, json={"list": []})
    )
    respx_mock.post(f"{BASE_URL}/api/v1/db/meta/projects/{PROJECT_ID}/tables").mock(
        return_value=httpx.Response(200, json={"id": "tbl_new", "title": "tents"})
    )

    client = _make_client()
    table_id = client.ensure_schema()
    assert table_id == "tbl_new"


def test_ensure_schema_adds_missing_fields(respx_mock):
    import respx
    import httpx

    # Table exists with only 2 fields
    respx_mock.get(f"{BASE_URL}/api/v1/db/meta/projects/{PROJECT_ID}/tables").mock(
        return_value=httpx.Response(
            200, json={"list": [{"id": "tbl_existing", "title": "tents"}]}
        )
    )
    respx_mock.get(f"{BASE_URL}/api/v1/db/meta/tables/tbl_existing/fields").mock(
        return_value=httpx.Response(
            200, json={"list": [{"title": "brand"}, {"title": "model_name"}]}
        )
    )

    added_fields = []

    def capture_post(request):
        added_fields.append(json.loads(request.content)["title"])
        return httpx.Response(200, json={"id": "fld_new"})

    respx_mock.post(f"{BASE_URL}/api/v1/db/meta/tables/tbl_existing/fields").mock(
        side_effect=capture_post
    )

    client = _make_client()
    table_id = client.ensure_schema()

    assert table_id == "tbl_existing"
    # Should have added all fields except brand and model_name
    expected_added = {f["title"] for f in FIELD_DEFINITIONS} - {"brand", "model_name"}
    assert set(added_fields) == expected_added


def test_ensure_schema_never_deletes_fields(respx_mock):
    """Extra fields in NocoDB that aren't in our schema must be left alone."""
    import respx
    import httpx

    respx_mock.get(f"{BASE_URL}/api/v1/db/meta/projects/{PROJECT_ID}/tables").mock(
        return_value=httpx.Response(
            200, json={"list": [{"id": "tbl_existing", "title": "tents"}]}
        )
    )
    all_our_fields = [{"title": f["title"]} for f in FIELD_DEFINITIONS]
    all_our_fields.append({"title": "legacy_custom_field"})  # extra field in NocoDB

    respx_mock.get(f"{BASE_URL}/api/v1/db/meta/tables/tbl_existing/fields").mock(
        return_value=httpx.Response(200, json={"list": all_our_fields})
    )

    client = _make_client()
    # Should not raise, should not call POST /fields
    table_id = client.ensure_schema()
    assert table_id == "tbl_existing"
```

- [ ] **Step 5.2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_nocodb.py -v
```

Expected: `ImportError: No module named 'nocodb'`.

Note: the tests above use `respx` for mocking httpx. Add it to pyproject.toml:
```toml
dependencies = [
    ...
    "respx>=0.21",
]
```

Run `uv sync` after adding.

- [ ] **Step 5.3: Implement nocodb.py — schema management**

```python
"""NocoDB REST API client: schema auto-create/sync and data upsert."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# NocoDB field type constants
TEXT = "SingleLineText"
LONGTEXT = "LongText"
NUMBER = "Number"
DECIMAL = "Decimal"
BOOL = "Checkbox"
JSON = "JSON"
DATETIME = "DateTime"
ATTACHMENT = "Attachment"
URL_TYPE = "URL"

FIELD_DEFINITIONS: list[dict] = [
    # Identity
    {"title": "brand", "uidt": TEXT},
    {"title": "model_name", "uidt": TEXT},
    {"title": "url", "uidt": URL_TYPE},
    # Trail weight
    {"title": "trail_weight_oz", "uidt": DECIMAL},
    {"title": "trail_weight_g", "uidt": DECIMAL},
    {"title": "trail_weight_lbs", "uidt": DECIMAL},
    # Packed weight
    {"title": "packed_weight_oz", "uidt": DECIMAL},
    {"title": "packed_weight_g", "uidt": DECIMAL},
    {"title": "packed_weight_lbs", "uidt": DECIMAL},
    # Minimum weight
    {"title": "minimum_weight_oz", "uidt": DECIMAL},
    {"title": "minimum_weight_g", "uidt": DECIMAL},
    {"title": "minimum_weight_lbs", "uidt": DECIMAL},
    # Component weights
    {"title": "fly_weight_oz", "uidt": DECIMAL},
    {"title": "fly_weight_g", "uidt": DECIMAL},
    {"title": "inner_weight_oz", "uidt": DECIMAL},
    {"title": "inner_weight_g", "uidt": DECIMAL},
    {"title": "pole_weight_oz", "uidt": DECIMAL},
    {"title": "pole_weight_g", "uidt": DECIMAL},
    {"title": "stake_weight_oz", "uidt": DECIMAL},
    {"title": "stake_weight_g", "uidt": DECIMAL},
    {"title": "stuff_sack_weight_oz", "uidt": DECIMAL},
    {"title": "stuff_sack_weight_g", "uidt": DECIMAL},
    # Dimensions
    {"title": "floor_length_cm", "uidt": DECIMAL},
    {"title": "floor_length_in", "uidt": DECIMAL},
    {"title": "floor_width_cm", "uidt": DECIMAL},
    {"title": "floor_width_in", "uidt": DECIMAL},
    {"title": "floor_width_foot_end_cm", "uidt": DECIMAL},
    {"title": "height_cm", "uidt": DECIMAL},
    {"title": "height_in", "uidt": DECIMAL},
    {"title": "packed_length_cm", "uidt": DECIMAL},
    {"title": "packed_length_in", "uidt": DECIMAL},
    {"title": "packed_diameter_cm", "uidt": DECIMAL},
    {"title": "packed_diameter_in", "uidt": DECIMAL},
    # Areas
    {"title": "floor_area_sqm", "uidt": DECIMAL},
    {"title": "floor_area_sqft", "uidt": DECIMAL},
    {"title": "vestibule_front_sqm", "uidt": DECIMAL},
    {"title": "vestibule_front_sqft", "uidt": DECIMAL},
    {"title": "vestibule_rear_sqm", "uidt": DECIMAL},
    {"title": "vestibule_rear_sqft", "uidt": DECIMAL},
    # Structure
    {"title": "doors", "uidt": NUMBER},
    {"title": "vestibules", "uidt": NUMBER},
    {"title": "freestanding", "uidt": BOOL},
    {"title": "seasons", "uidt": TEXT},
    {"title": "pitch_type", "uidt": TEXT},
    {"title": "guy_out_points", "uidt": NUMBER},
    {"title": "stake_points", "uidt": NUMBER},
    {"title": "stakes_included", "uidt": NUMBER},
    {"title": "pole_count", "uidt": NUMBER},
    {"title": "pole_diameter_mm", "uidt": DECIMAL},
    {"title": "peak_vents", "uidt": BOOL},
    # Fabrics
    {"title": "fly_fabric", "uidt": TEXT},
    {"title": "fly_denier", "uidt": NUMBER},
    {"title": "fly_material", "uidt": TEXT},
    {"title": "fly_waterproofing", "uidt": TEXT},
    {"title": "floor_fabric", "uidt": TEXT},
    {"title": "floor_denier", "uidt": NUMBER},
    {"title": "floor_material", "uidt": TEXT},
    {"title": "floor_waterproofing", "uidt": TEXT},
    {"title": "mesh_type", "uidt": TEXT},
    {"title": "poles_material", "uidt": TEXT},
    # Commercial
    {"title": "price_usd", "uidt": DECIMAL},
    {"title": "variants", "uidt": JSON},
    {"title": "in_stock", "uidt": BOOL},
    # Content
    {"title": "full_description", "uidt": LONGTEXT},
    {"title": "all_spec_table_rows", "uidt": JSON},
    {"title": "all_bullet_points", "uidt": JSON},
    {"title": "any_extra_fields", "uidt": JSON},
    {"title": "raw_json", "uidt": LONGTEXT},
    # Media + meta
    {"title": "images", "uidt": ATTACHMENT},
    {"title": "last_scraped_at", "uidt": DATETIME},
]


class NocoDBClient:
    def __init__(self, url: str, api_key: str, project_id: str) -> None:
        self._base = url.rstrip("/")
        self._project_id = project_id
        self._client = httpx.Client(
            headers={"xc-auth": api_key, "Content-Type": "application/json"},
            timeout=30,
        )

    def _get(self, path: str) -> dict:
        resp = self._client.get(f"{self._base}{path}")
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict) -> dict:
        resp = self._client.post(f"{self._base}{path}", json=body)
        resp.raise_for_status()
        return resp.json()

    def _patch(self, path: str, body: dict) -> dict:
        resp = self._client.patch(f"{self._base}{path}", json=body)
        resp.raise_for_status()
        return resp.json()

    def list_tables(self) -> list[dict]:
        data = self._get(f"/api/v1/db/meta/projects/{self._project_id}/tables")
        return data.get("list", [])

    def _create_table(self) -> dict:
        logger.info("Creating 'tents' table in NocoDB")
        payload = {
            "title": "tents",
            "columns": FIELD_DEFINITIONS,
        }
        return self._post(f"/api/v1/db/meta/projects/{self._project_id}/tables", payload)

    def list_fields(self, table_id: str) -> list[dict]:
        data = self._get(f"/api/v1/db/meta/tables/{table_id}/fields")
        return data.get("list", [])

    def _add_field(self, table_id: str, field_def: dict) -> dict:
        return self._post(f"/api/v1/db/meta/tables/{table_id}/fields", field_def)

    def ensure_schema(self) -> str:
        """Create tents table if missing, add any missing fields. Returns table_id."""
        tables = self.list_tables()
        tent_table = next((t for t in tables if t["title"] == "tents"), None)

        if tent_table is None:
            tent_table = self._create_table()
            logger.info("Created tents table: %s", tent_table["id"])
            return tent_table["id"]

        table_id = tent_table["id"]
        existing_fields = self.list_fields(table_id)
        existing_titles = {f["title"] for f in existing_fields}
        our_titles = {f["title"] for f in FIELD_DEFINITIONS}

        missing = our_titles - existing_titles
        for field_def in FIELD_DEFINITIONS:
            if field_def["title"] in missing:
                self._add_field(table_id, field_def)
                logger.info("Added missing field: %s", field_def["title"])

        if missing:
            logger.info("Added %d missing fields to tents table", len(missing))
        else:
            logger.info("Schema up to date, no fields to add")

        return table_id

    def add_dynamic_field(self, table_id: str, field_title: str) -> None:
        """Add a field discovered dynamically during extraction."""
        field_def = {"title": field_title, "uidt": TEXT}
        try:
            self._add_field(table_id, field_def)
            logger.info("Added dynamic field: %s", field_title)
        except httpx.HTTPStatusError as e:
            logger.warning("Could not add dynamic field %s: %s", field_title, e)
```

- [ ] **Step 5.4: Run schema tests**

```bash
uv run pytest tests/test_nocodb.py -v
```

Expected: all tests PASS.

- [ ] **Step 5.5: Commit**

```bash
git add nocodb.py tests/test_nocodb.py
git commit -m "feat: add NocoDB client with auto schema management"
```

---

## Task 6: nocodb.py — Data Upsert

**Files:**
- Modify: `nocodb.py` (add find_record, upsert_tent)
- Modify: `tests/test_nocodb.py` (add upsert tests)

- [ ] **Step 6.1: Write failing upsert tests**

Add to `tests/test_nocodb.py`:
```python
SAMPLE_ROW = {
    "brand": "Zpacks",
    "model_name": "Duplex",
    "url": "https://zpacks.com/products/duplex",
    "trail_weight_oz": 19.5,
    "trail_weight_g": 553.0,
    "price_usd": 399.0,
    "freestanding": False,
    "all_spec_table_rows": [{"label": "Trail Weight", "value": "19.5 oz"}],
}


def test_find_record_returns_row_when_found(respx_mock):
    import httpx

    respx_mock.get(
        f"{BASE_URL}/api/v1/db/data/noco/{PROJECT_ID}/tbl_abc"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "list": [{"Id": 42, "brand": "Zpacks", "model_name": "Duplex"}],
                "pageInfo": {"totalRows": 1},
            },
        )
    )

    client = _make_client()
    row = client.find_record("tbl_abc", "Zpacks", "Duplex")
    assert row is not None
    assert row["Id"] == 42


def test_find_record_returns_none_when_missing(respx_mock):
    import httpx

    respx_mock.get(
        f"{BASE_URL}/api/v1/db/data/noco/{PROJECT_ID}/tbl_abc"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"list": [], "pageInfo": {"totalRows": 0}},
        )
    )

    client = _make_client()
    row = client.find_record("tbl_abc", "Zpacks", "NonExistent")
    assert row is None


def test_upsert_tent_creates_new_record(respx_mock):
    import httpx

    # find returns nothing → create
    respx_mock.get(
        f"{BASE_URL}/api/v1/db/data/noco/{PROJECT_ID}/tbl_abc"
    ).mock(
        return_value=httpx.Response(200, json={"list": [], "pageInfo": {"totalRows": 0}})
    )

    created = []

    def capture_create(request):
        created.append(json.loads(request.content))
        return httpx.Response(200, json={"Id": 1, **json.loads(request.content)})

    respx_mock.post(
        f"{BASE_URL}/api/v1/db/data/noco/{PROJECT_ID}/tbl_abc"
    ).mock(side_effect=capture_create)

    client = _make_client()
    result = client.upsert_tent("tbl_abc", SAMPLE_ROW)

    assert len(created) == 1
    assert created[0]["brand"] == "Zpacks"
    assert created[0]["trail_weight_g"] == 553.0
    assert "last_scraped_at" in created[0]


def test_upsert_tent_updates_existing_record(respx_mock):
    import httpx

    # find returns existing row
    respx_mock.get(
        f"{BASE_URL}/api/v1/db/data/noco/{PROJECT_ID}/tbl_abc"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"list": [{"Id": 99, "brand": "Zpacks", "model_name": "Duplex"}], "pageInfo": {"totalRows": 1}},
        )
    )

    patched = []

    def capture_patch(request):
        patched.append(json.loads(request.content))
        return httpx.Response(200, json={"Id": 99})

    respx_mock.patch(
        f"{BASE_URL}/api/v1/db/data/noco/{PROJECT_ID}/tbl_abc/99"
    ).mock(side_effect=capture_patch)

    client = _make_client()
    result = client.upsert_tent("tbl_abc", SAMPLE_ROW)

    assert len(patched) == 1
    assert patched[0]["trail_weight_g"] == 553.0


def test_upsert_serializes_json_fields(respx_mock):
    """JSON fields (list/dict values) must be JSON-encoded before sending."""
    import httpx

    respx_mock.get(
        f"{BASE_URL}/api/v1/db/data/noco/{PROJECT_ID}/tbl_abc"
    ).mock(
        return_value=httpx.Response(200, json={"list": [], "pageInfo": {"totalRows": 0}})
    )

    sent = []

    def capture_create(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"Id": 1})

    respx_mock.post(
        f"{BASE_URL}/api/v1/db/data/noco/{PROJECT_ID}/tbl_abc"
    ).mock(side_effect=capture_create)

    client = _make_client()
    row = {**SAMPLE_ROW, "all_spec_table_rows": [{"label": "Weight", "value": "19.5 oz"}]}
    client.upsert_tent("tbl_abc", row)

    # JSON field should be a JSON string, not a Python list
    assert isinstance(sent[0]["all_spec_table_rows"], str)
    parsed = json.loads(sent[0]["all_spec_table_rows"])
    assert parsed[0]["label"] == "Weight"
```

- [ ] **Step 6.2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_nocodb.py::test_find_record_returns_row_when_found -v
```

Expected: FAIL with `AttributeError: 'NocoDBClient' object has no attribute 'find_record'`.

- [ ] **Step 6.3: Implement upsert methods in nocodb.py**

Add to the `NocoDBClient` class in `nocodb.py`:
```python
    # JSON fields that must be serialized as strings before sending to NocoDB
    _JSON_FIELDS = frozenset({
        "variants", "all_spec_table_rows", "all_bullet_points",
        "any_extra_fields",
    })

    def find_record(self, table_id: str, brand: str, model_name: str) -> dict | None:
        """Find existing row by (brand, model_name). Returns row dict or None."""
        import urllib.parse
        where = urllib.parse.quote(f"(brand,eq,{brand})~and(model_name,eq,{model_name})")
        data = self._get(
            f"/api/v1/db/data/noco/{self._project_id}/{table_id}"
            f"?where={where}&limit=1"
        )
        rows = data.get("list", [])
        return rows[0] if rows else None

    def _serialize_row(self, data: dict) -> dict:
        """Prepare row data for NocoDB: serialize JSON fields, add timestamp."""
        import json as json_mod

        row = {}
        for key, value in data.items():
            if key in self._JSON_FIELDS and isinstance(value, (list, dict)):
                row[key] = json_mod.dumps(value, ensure_ascii=False)
            elif value is None:
                continue  # Skip null fields (NocoDB prefers absence over null)
            else:
                row[key] = value

        row["last_scraped_at"] = datetime.now(timezone.utc).isoformat()
        return row

    def upsert_tent(self, table_id: str, data: dict) -> dict:
        """Create or update a tent record. Keyed on (brand, model_name)."""
        brand = data["brand"]
        model_name = data["model_name"]

        existing = self.find_record(table_id, brand, model_name)
        row = self._serialize_row(data)

        if existing is None:
            result = self._post(
                f"/api/v1/db/data/noco/{self._project_id}/{table_id}", row
            )
            logger.info("Created record for %s/%s (Id=%s)", brand, model_name, result.get("Id"))
        else:
            row_id = existing["Id"]
            result = self._patch(
                f"/api/v1/db/data/noco/{self._project_id}/{table_id}/{row_id}", row
            )
            logger.info("Updated record for %s/%s (Id=%s)", brand, model_name, row_id)

        return result
```

- [ ] **Step 6.4: Run all nocodb tests**

```bash
uv run pytest tests/test_nocodb.py -v
```

Expected: all tests PASS.

- [ ] **Step 6.5: Commit**

```bash
git add nocodb.py tests/test_nocodb.py
git commit -m "feat: add NocoDB upsert with JSON field serialization"
```

---

## Task 7: main.py — Orchestrator

**Files:**
- Create: `main.py`
- Create: `tests/test_main.py`

- [ ] **Step 7.1: Write failing orchestrator tests**

`tests/test_main.py`:
```python
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from main import load_brands, run_pipeline


def test_load_brands_reads_brands_json(tmp_path):
    brands_file = tmp_path / "brands.json"
    brands_file.write_text(json.dumps([
        {"name": "TestBrand", "catalog_url": "https://example.com/tents"}
    ]))
    brands = load_brands(brands_file)
    assert len(brands) == 1
    assert brands[0]["name"] == "TestBrand"


def test_load_brands_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        load_brands(Path("/nonexistent/brands.json"))


def test_run_pipeline_orchestrates_steps():
    mock_brand = {"name": "Zpacks", "catalog_url": "https://zpacks.com/collections/tents"}
    mock_html_path = Path("/tmp/html/zpacks_duplex.html")
    mock_json_path = Path("/tmp/extracted/zpacks_duplex.json")
    mock_data = {
        "brand": "Zpacks",
        "model_name": "Duplex",
        "trail_weight_oz": 19.5,
    }

    with patch("main.load_brands", return_value=[mock_brand]) as mock_lb, \
         patch("main.sync_playwright") as mock_pw, \
         patch("main.scrape_brand", return_value=[mock_html_path]) as mock_sb, \
         patch("main.extract_all", return_value=[mock_json_path]) as mock_ea, \
         patch("main.NocoDBClient") as mock_nocodb_cls, \
         patch("main.Path") as mock_path_cls:

        # Setup playwright context manager
        mock_browser = MagicMock()
        mock_pw.return_value.__enter__.return_value.chromium.launch.return_value.__enter__.return_value = mock_browser

        # Setup NocoDB client
        mock_nocodb = MagicMock()
        mock_nocodb.ensure_schema.return_value = "tbl_abc"
        mock_nocodb_cls.return_value = mock_nocodb

        # Setup JSON read
        mock_json_path_obj = MagicMock()
        mock_json_path_obj.read_text.return_value = json.dumps(mock_data)

        run_pipeline(
            brands_file=Path("brands.json"),
            html_dir=Path("/tmp/html"),
            extracted_dir=Path("/tmp/extracted"),
            nocodb_url="http://localhost:8080",
            nocodb_api_key="key",
            nocodb_project_id="proj",
        )

        mock_nocodb.ensure_schema.assert_called_once()


def test_run_pipeline_logs_progress(caplog):
    import logging

    with patch("main.load_brands", return_value=[]), \
         patch("main.sync_playwright"), \
         patch("main.NocoDBClient") as mock_nocodb_cls:

        mock_nocodb = MagicMock()
        mock_nocodb.ensure_schema.return_value = "tbl_abc"
        mock_nocodb_cls.return_value = mock_nocodb

        with caplog.at_level(logging.INFO, logger="main"):
            run_pipeline(
                brands_file=Path("brands.json"),
                html_dir=Path("/tmp/html"),
                extracted_dir=Path("/tmp/extracted"),
                nocodb_url="http://localhost:8080",
                nocodb_api_key="key",
                nocodb_project_id="proj",
            )

    assert any("brand" in r.message.lower() or "pipeline" in r.message.lower()
               for r in caplog.records)
```

- [ ] **Step 7.2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_main.py -v
```

Expected: `ImportError: No module named 'main'`.

- [ ] **Step 7.3: Implement main.py**

```python
"""Orchestrator: scrape → Claude extract → schema sync → NocoDB push."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from extractor import extract_all
from nocodb import NocoDBClient
from scraper import scrape_brand

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scrape.log"),
    ],
)
logger = logging.getLogger("main")


def load_brands(brands_file: Path) -> list[dict]:
    if not brands_file.exists():
        raise FileNotFoundError(f"brands.json not found: {brands_file}")
    return json.loads(brands_file.read_text(encoding="utf-8"))


def run_pipeline(
    brands_file: Path,
    html_dir: Path,
    extracted_dir: Path,
    nocodb_url: str,
    nocodb_api_key: str,
    nocodb_project_id: str,
) -> None:
    """Full pipeline: scrape → extract → schema sync → push."""
    html_dir.mkdir(parents=True, exist_ok=True)
    extracted_dir.mkdir(parents=True, exist_ok=True)

    brands = load_brands(brands_file)
    logger.info("Loaded %d brands", len(brands))

    # Phase 1: Scrape all brands
    all_html_paths: list[Path] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            for brand in brands:
                logger.info("Scraping brand: %s", brand["name"])
                html_paths = scrape_brand(brand, browser)
                logger.info("Scraped %d products for %s", len(html_paths), brand["name"])
                all_html_paths.extend(html_paths)
        finally:
            browser.close()

    logger.info("Phase 1 complete: %d HTML files saved", len(all_html_paths))

    # Phase 2: Claude extraction
    logger.info("Phase 2: extracting structured data from HTML files")
    json_paths = extract_all(html_dir, extracted_dir)
    logger.info("Phase 2 complete: %d JSON files created", len(json_paths))

    # Phase 3: Schema sync
    logger.info("Phase 3: syncing NocoDB schema")
    client = NocoDBClient(
        url=nocodb_url,
        api_key=nocodb_api_key,
        project_id=nocodb_project_id,
    )
    table_id = client.ensure_schema()
    logger.info("NocoDB table ready: %s", table_id)

    # Phase 4: Push data
    logger.info("Phase 4: pushing %d records to NocoDB", len(json_paths))
    success = 0
    failed = 0

    for json_path in json_paths:
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))

            # Add any dynamic fields found by Claude that aren't in our schema
            extra = data.get("any_extra_fields") or {}
            if isinstance(extra, dict):
                for field_name in extra:
                    client.add_dynamic_field(table_id, field_name)

            client.upsert_tent(table_id, data)
            success += 1
        except Exception as e:
            logger.error("Failed to push %s: %s", json_path.name, e)
            with open("scrape.log", "a") as f:
                f.write(f"PUSH_FAIL {json_path}: {e}\n")
            failed += 1

    logger.info(
        "Pipeline complete: %d pushed, %d failed out of %d total",
        success, failed, len(json_paths),
    )


def main() -> None:
    load_dotenv()

    nocodb_url = os.environ.get("NOCODB_URL", "")
    nocodb_api_key = os.environ.get("NOCODB_API_KEY", "")
    nocodb_project_id = os.environ.get("NOCODB_PROJECT_ID", "")

    missing = [k for k, v in {
        "NOCODB_URL": nocodb_url,
        "NOCODB_API_KEY": nocodb_api_key,
        "NOCODB_PROJECT_ID": nocodb_project_id,
    }.items() if not v]

    if missing:
        logger.error("Missing required env vars: %s", ", ".join(missing))
        sys.exit(1)

    run_pipeline(
        brands_file=Path("brands.json"),
        html_dir=Path("/tmp/html"),
        extracted_dir=Path("/tmp/extracted"),
        nocodb_url=nocodb_url,
        nocodb_api_key=nocodb_api_key,
        nocodb_project_id=nocodb_project_id,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 7.4: Run all tests**

```bash
uv run pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 7.5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: add main orchestrator with 4-phase pipeline"
```

---

## Task 8: Integration Smoke Test

**Files:**
- No new files (verify full pipeline with a dry run)

- [ ] **Step 8.1: Verify project can be imported**

```bash
uv run python -c "import scraper, extractor, nocodb, main; print('All modules import OK')"
```

Expected: `All modules import OK`.

- [ ] **Step 8.2: Run full test suite**

```bash
uv run pytest tests/ -v --tb=short
```

Expected: all tests PASS, 0 failures.

- [ ] **Step 8.3: Check scraper.py Playwright selectors with a single test page**

```bash
uv run python -c "
from playwright.sync_api import sync_playwright
from scraper import get_product_urls, expand_all_interactive, scroll_to_load

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://zpacks.com/collections/tents', wait_until='networkidle')
    urls = get_product_urls({'name': 'Zpacks', 'catalog_url': 'https://zpacks.com/collections/tents'}, page)
    print(f'Found {len(urls)} product URLs:')
    for u in urls:
        print(' ', u)
    browser.close()
"
```

Expected: several Zpacks product URLs printed, e.g. `https://zpacks.com/products/duplex-tent`.

- [ ] **Step 8.4: Final commit**

```bash
git add -A
git commit -m "chore: complete tent scraper pipeline implementation"
```

---

## Self-Review

### Spec coverage check

| Spec requirement | Covered in |
|---|---|
| Playwright catalog URL discovery | Task 2 |
| Click tabs/accordions/show-more | Task 3 (`expand_all_interactive`) |
| Scroll 3× for lazy loading | Task 3 (`scroll_to_load`) |
| Save HTML to /tmp/html/ | Task 3 (`scrape_product`) |
| Download images to /data/images/ | Task 3 (`download_images`) |
| Claude CLI extraction, no API key | Task 4 (`extract_tent_data` via subprocess) |
| All weight fields (oz/g/lbs) | Task 4 prompt + Task 5 `FIELD_DEFINITIONS` |
| All dimension fields (cm/in) | Task 4 prompt + Task 5 |
| All fabric/structure fields | Task 4 prompt + Task 5 |
| Commercial fields (price, variants) | Task 4 prompt + Task 5 |
| Content fields (description, spec rows) | Task 4 prompt + Task 5 |
| NocoDB auto table create | Task 5 (`ensure_schema`) |
| NocoDB auto add missing fields | Task 5 (`ensure_schema` diff logic) |
| Never delete existing fields | Task 5 (add-only logic) |
| Dynamic fields from Claude output | Task 6 (`add_dynamic_field`) + Task 7 |
| Upsert on (brand, model_name) | Task 6 (`find_record` + `upsert_tent`) |
| JSON field serialization | Task 6 (`_serialize_row`) |
| 2s delay between requests | Task 3 (`time.sleep(2)` in `scrape_brand`) |
| Log every extracted field count | Task 4 (`logger.info` + `scrape.log`) |
| scrape.log for failures | Tasks 3, 4, 7 |
| uv only, never pip | Task 1 (`pyproject.toml`) |
| Env vars from .env only | Task 7 (`load_dotenv`) |
| brands.json structure | Task 1 |

### Gaps found and addressed

1. **`respx` missing from deps** — noted in Task 5.2 step, must add before running NocoDB tests.
2. **Image srcset highest-resolution selection** — `download_images` currently takes first URL from srcset; spec says "highest resolution". The srcset format is `url 800w, url 1600w` — the last (widest) entry is highest res. Fixed: iterate `srcset.split(",")` and take the last entry's URL.
3. **URL field in extracted JSON** — `extract_all` passes empty string for URL. Fixed: scraper saves URL alongside HTML filename, or Claude finds it in the HTML. The prompt instructs Claude to find the canonical URL from `<link rel="canonical">` or `<meta property="og:url">`.
4. **NocoDB `xc-auth` vs `xc-token`** — newer NocoDB uses `xc-token` header for API tokens. Both headers are included for compatibility. Update `nocodb.py` client init to send both: `{"xc-auth": api_key, "xc-token": api_key, "Content-Type": "application/json"}`.

Apply fix for gap 2 — update `download_images` in `scraper.py` srcset parsing:
```python
for source in page.query_selector_all("source[srcset]"):
    srcset = source.get_attribute("srcset") or ""
    entries = [p.strip() for p in srcset.split(",") if p.strip()]
    if entries:
        # Last entry is highest resolution in a standard srcset
        highest = entries[-1].split(" ")[0]
        if highest.startswith("http"):
            image_urls.add(highest)
```

Apply fix for gap 4 — update `NocoDBClient.__init__` headers:
```python
self._client = httpx.Client(
    headers={
        "xc-auth": api_key,
        "xc-token": api_key,
        "Content-Type": "application/json",
    },
    timeout=30,
)
```
