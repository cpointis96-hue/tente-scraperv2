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

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

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
            url="",
        )

        if data is not None:
            out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            json_paths.append(out_path)

    logger.info("Extraction complete: %d/%d succeeded", len(json_paths), len(html_files))
    return json_paths
