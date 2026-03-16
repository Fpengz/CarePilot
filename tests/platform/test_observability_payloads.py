"""Tests for observability payload logging helpers."""

import json

from care_pilot.platform.observability.payloads import pretty_json_payload


def test_pretty_json_payload_redacts_sensitive_keys() -> None:
    payload = {
        "api_key": "secret",
        "nested": {
            "authorization": "Bearer abc",
            "token": "tok",
        },
    }
    rendered = pretty_json_payload(payload)
    parsed = json.loads(rendered)
    assert parsed["api_key"] == "[redacted]"
    assert parsed["nested"]["authorization"] == "[redacted]"
    assert parsed["nested"]["token"] == "[redacted]"


def test_pretty_json_payload_replaces_bytes() -> None:
    payload = {"data": b"abc"}
    rendered = pretty_json_payload(payload)
    parsed = json.loads(rendered)
    assert parsed["data"] == "<bytes 3>"


def test_pretty_json_payload_truncates_strings() -> None:
    payload = {"text": "a" * 20}
    rendered = pretty_json_payload(payload, max_str_len=10)
    parsed = json.loads(rendered)
    assert parsed["text"] == "aaaaaaaaaa...(truncated, len=20)"
