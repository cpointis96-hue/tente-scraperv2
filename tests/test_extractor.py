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
