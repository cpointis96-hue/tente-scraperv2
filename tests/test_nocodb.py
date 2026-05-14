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
    import httpx

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
    expected_added = {f["title"] for f in FIELD_DEFINITIONS} - {"brand", "model_name"}
    assert set(added_fields) == expected_added


def test_ensure_schema_never_deletes_fields(respx_mock):
    """Extra fields in NocoDB that are not in our schema must be left alone."""
    import httpx

    respx_mock.get(f"{BASE_URL}/api/v1/db/meta/projects/{PROJECT_ID}/tables").mock(
        return_value=httpx.Response(
            200, json={"list": [{"id": "tbl_existing", "title": "tents"}]}
        )
    )
    all_our_fields = [{"title": f["title"]} for f in FIELD_DEFINITIONS]
    all_our_fields.append({"title": "legacy_custom_field"})

    respx_mock.get(f"{BASE_URL}/api/v1/db/meta/tables/tbl_existing/fields").mock(
        return_value=httpx.Response(200, json={"list": all_our_fields})
    )

    client = _make_client()
    table_id = client.ensure_schema()
    assert table_id == "tbl_existing"


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

    assert isinstance(sent[0]["all_spec_table_rows"], str)
    parsed = json.loads(sent[0]["all_spec_table_rows"])
    assert parsed[0]["label"] == "Weight"
