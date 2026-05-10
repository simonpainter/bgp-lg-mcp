import json

import bgp_lg
import pytest


def test_env_timeout_override_no_sentinel_pollution(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "servers": [
                    {"name": "No Timeout", "host": "example.org"},
                    {"name": "Has Timeout", "host": "example.net", "timeout": 5},
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("CONFIG_PATH", str(config_path))
    monkeypatch.setenv("BGP_SERVER_TIMEOUT", "20")
    monkeypatch.setattr(bgp_lg, "_config", None)
    monkeypatch.setattr(bgp_lg, "_config_path", None)

    config = bgp_lg.load_config()

    no_timeout_server = config["servers"][0]
    has_timeout_server = config["servers"][1]

    assert no_timeout_server["timeout"] == 20
    assert "_env_timeout_override" not in no_timeout_server
    assert has_timeout_server["timeout"] == 5
    assert "_env_timeout_override" not in has_timeout_server


def test_load_config_missing_file_has_helpful_error(monkeypatch, tmp_path):
    missing_path = tmp_path / "does-not-exist.json"

    monkeypatch.setenv("CONFIG_PATH", str(missing_path))
    monkeypatch.setattr(bgp_lg, "_config", None)
    monkeypatch.setattr(bgp_lg, "_config_path", None)

    with pytest.raises(FileNotFoundError, match=f"Config file not found at {missing_path}"):
        bgp_lg.load_config()


def test_load_config_invalid_json_has_helpful_error(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("{invalid-json", encoding="utf-8")

    monkeypatch.setenv("CONFIG_PATH", str(config_path))
    monkeypatch.setattr(bgp_lg, "_config", None)
    monkeypatch.setattr(bgp_lg, "_config_path", None)

    with pytest.raises(ValueError, match=f"Invalid JSON in config file {config_path}:"):
        bgp_lg.load_config()
