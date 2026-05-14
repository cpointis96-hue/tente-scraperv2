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
            raw = json_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            data["raw_json"] = raw

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
