"""Tests for the settings email-templates commands."""

import json

import httpx
import respx
import yaml
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"
URL = f"{BASE_URL}/api/settings/email-templates"

DOCUMENT = {
    "templates": {
        "invitation": {
            "enabled": True,
            "canBeDisabled": False,
            "variables": [{"name": "invitationUrl", "optional": False}],
            "languages": {
                "en": {"subject": "Invitation", "body": "{{invitationUrl}}", "customized": False},
                "de": {"subject": "Einladung", "body": "{{invitationUrl}}", "customized": True},
            },
        },
        "access-rejected": {
            "enabled": False,
            "canBeDisabled": True,
            "variables": [{"name": "reason", "optional": True}],
            "languages": {
                "en": {"subject": "Rejected", "body": "Sorry.", "customized": False},
                "de": {"subject": "Abgelehnt", "body": "Leider nicht.", "customized": False},
            },
        },
    }
}


def _setup(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


@respx.mock
def test_get_table_marks_disabled_types_and_customized_languages(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    respx.get(URL).mock(return_value=httpx.Response(200, json=DOCUMENT))
    result = runner.invoke(app, ["settings", "email-templates", "get"])
    assert result.exit_code == 0, result.output
    lines = {line.split("│")[1].strip(): line for line in result.output.splitlines() if line.startswith("│")}
    assert "yes" in lines["invitation"] and "de" in lines["invitation"]
    assert "no" in lines["access-rejected"] and "-" in lines["access-rejected"]


@respx.mock
def test_get_yaml_prints_the_document(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    respx.get(URL).mock(return_value=httpx.Response(200, json=DOCUMENT))
    result = runner.invoke(app, ["settings", "email-templates", "get", "--output", "yaml"])
    assert result.exit_code == 0, result.output
    assert yaml.safe_load(result.output) == DOCUMENT


@respx.mock
def test_put_sends_the_file_as_json_and_reports_counts(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    body = {
        "templates": {
            "access-rejected": {"enabled": False, "languages": {"en": {"subject": "Rejected", "body": "Sorry."}}}
        }
    }
    body_file = tmp_path / "email-templates.yaml"
    body_file.write_text(yaml.safe_dump(body))

    captured = {}

    def _capture(request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=DOCUMENT)

    respx.put(URL).mock(side_effect=_capture)
    result = runner.invoke(app, ["settings", "email-templates", "put", "--file", str(body_file)])
    assert result.exit_code == 0, result.output
    assert captured["body"] == body
    assert "1 customized, 1 disabled" in result.output


@respx.mock
def test_put_validation_error_surfaces_detail(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    body_file = tmp_path / "email-templates.json"
    body_file.write_text(json.dumps({"templates": {"invitation": {"enabled": False}}}))
    respx.put(URL).mock(
        return_value=httpx.Response(400, json={"status": 400, "detail": "Email type 'invitation' cannot be disabled"})
    )
    result = runner.invoke(app, ["settings", "email-templates", "put", "--file", str(body_file)])
    assert result.exit_code != 0
    assert "cannot be disabled" in result.output
