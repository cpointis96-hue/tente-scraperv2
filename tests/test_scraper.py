from unittest.mock import MagicMock
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


def test_get_product_urls_handles_protocol_relative_urls():
    page = _make_page(["//zpacks.com/products/duplex"])
    brand = {"name": "Zpacks", "catalog_url": "https://zpacks.com/collections/tents"}
    urls = get_product_urls(brand, page)
    assert len(urls) == 1
    assert urls[0].startswith("https://")


import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from scraper import expand_all_interactive, scroll_to_load, scrape_product


def test_expand_all_interactive_clicks_collapsed_elements():
    el1 = MagicMock()
    el2 = MagicMock()
    page = MagicMock()

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
