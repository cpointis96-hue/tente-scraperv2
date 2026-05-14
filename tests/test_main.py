import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

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


def test_run_pipeline_calls_ensure_schema():
    """Pipeline must call ensure_schema to sync NocoDB before pushing."""
    with patch("main.load_brands", return_value=[]) as mock_lb, \
         patch("main.sync_playwright") as mock_pw, \
         patch("main.extract_all", return_value=[]) as mock_ea, \
         patch("main.NocoDBClient") as mock_nocodb_cls:

        mock_browser = MagicMock()
        mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser

        mock_nocodb = MagicMock()
        mock_nocodb.ensure_schema.return_value = "tbl_abc"
        mock_nocodb_cls.return_value = mock_nocodb

        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                brands_file=Path(tmpdir) / "brands.json",
                html_dir=Path(tmpdir) / "html",
                extracted_dir=Path(tmpdir) / "extracted",
                nocodb_url="http://localhost:8080",
                nocodb_api_key="key",
                nocodb_project_id="proj",
            )

        mock_nocodb.ensure_schema.assert_called_once()


def test_run_pipeline_pushes_extracted_records():
    """Each JSON file produced by extractor must be pushed to NocoDB."""
    mock_data = {
        "brand": "Zpacks",
        "model_name": "Duplex",
        "trail_weight_oz": 19.5,
        "any_extra_fields": {},
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        extracted_dir = Path(tmpdir) / "extracted"
        extracted_dir.mkdir(parents=True)
        json_file = extracted_dir / "zpacks_duplex.json"
        json_file.write_text(json.dumps(mock_data))

        with patch("main.load_brands", return_value=[]), \
             patch("main.sync_playwright") as mock_pw, \
             patch("main.extract_all", return_value=[json_file]), \
             patch("main.NocoDBClient") as mock_nocodb_cls:

            mock_browser = MagicMock()
            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser

            mock_nocodb = MagicMock()
            mock_nocodb.ensure_schema.return_value = "tbl_abc"
            mock_nocodb_cls.return_value = mock_nocodb

            run_pipeline(
                brands_file=Path(tmpdir) / "brands.json",
                html_dir=Path(tmpdir) / "html",
                extracted_dir=extracted_dir,
                nocodb_url="http://localhost:8080",
                nocodb_api_key="key",
                nocodb_project_id="proj",
            )

        # Verify that raw_json field was added to the data
        call_args = mock_nocodb.upsert_tent.call_args
        assert call_args[0][0] == "tbl_abc"
        assert call_args[0][1]["brand"] == "Zpacks"
        assert call_args[0][1]["model_name"] == "Duplex"
        assert call_args[0][1]["trail_weight_oz"] == 19.5
        assert "raw_json" in call_args[0][1]
        assert isinstance(call_args[0][1]["raw_json"], str)


def test_run_pipeline_logs_progress(caplog):
    import logging

    with patch("main.load_brands", return_value=[]), \
         patch("main.sync_playwright") as mock_pw, \
         patch("main.extract_all", return_value=[]), \
         patch("main.NocoDBClient") as mock_nocodb_cls:

        mock_browser = MagicMock()
        mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser

        mock_nocodb = MagicMock()
        mock_nocodb.ensure_schema.return_value = "tbl_abc"
        mock_nocodb_cls.return_value = mock_nocodb

        with caplog.at_level(logging.INFO, logger="main"):
            with tempfile.TemporaryDirectory() as tmpdir:
                run_pipeline(
                    brands_file=Path(tmpdir) / "brands.json",
                    html_dir=Path(tmpdir) / "html",
                    extracted_dir=Path(tmpdir) / "extracted",
                    nocodb_url="http://localhost:8080",
                    nocodb_api_key="key",
                    nocodb_project_id="proj",
                )

    assert len(caplog.records) > 0
