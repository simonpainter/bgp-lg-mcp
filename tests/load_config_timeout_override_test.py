import json

import bgp_lg


def test_load_config_env_timeout_override_does_not_pollute_server_dict(monkeypatch, tmp_path):
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
    bgp_lg._env_timeout_override_servers.clear()

    config = bgp_lg.load_config()

    no_timeout_server = config["servers"][0]
    has_timeout_server = config["servers"][1]

    assert no_timeout_server["timeout"] == 20
    assert "_env_timeout_override" not in no_timeout_server
    assert has_timeout_server["timeout"] == 5
    assert "_env_timeout_override" not in has_timeout_server
