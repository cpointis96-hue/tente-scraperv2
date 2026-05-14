"""NocoDB REST API client: schema auto-create/sync and data upsert."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

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
            headers={
                "xc-auth": api_key,
                "xc-token": api_key,
                "Content-Type": "application/json",
            },
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
                continue  # Skip null fields
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

    def add_dynamic_field(self, table_id: str, field_title: str) -> None:
        """Add a field discovered dynamically during extraction."""
        field_def = {"title": field_title, "uidt": TEXT}
        try:
            self._add_field(table_id, field_def)
            logger.info("Added dynamic field: %s", field_title)
        except httpx.HTTPStatusError as e:
            logger.warning("Could not add dynamic field %s: %s", field_title, e)
