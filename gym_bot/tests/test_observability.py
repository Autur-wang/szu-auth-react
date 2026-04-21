"""Tests for observability.py structured events."""

import json

import observability


def test_emit_event_writes_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(observability, "LOG_DIR", tmp_path)
    monkeypatch.setattr(observability, "_LOGGING_INITIALIZED", False)

    observability.emit_event("unit.test", foo="bar")
    files = list(tmp_path.glob("events-*.jsonl"))
    assert len(files) == 1
    row = json.loads(files[0].read_text().strip())
    assert row["event"] == "unit.test"
    assert row["foo"] == "bar"


def test_read_recent_events_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(observability, "LOG_DIR", tmp_path)
    day = "20260421"
    path = tmp_path / f"events-{day}.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"event": "a", "n": 1}),
                json.dumps({"event": "b", "n": 2}),
                json.dumps({"event": "c", "n": 3}),
            ]
        )
        + "\n"
    )

    events = observability.read_recent_events(limit=2)
    assert len(events) == 2
    assert events[0]["event"] == "b"
    assert events[1]["event"] == "c"


def test_request_context_propagates_to_event(tmp_path, monkeypatch):
    monkeypatch.setattr(observability, "LOG_DIR", tmp_path)
    token = observability.set_request_context("req-test-1")
    try:
        observability.emit_event("ctx.test")
    finally:
        observability.reset_context(token)

    files = list(tmp_path.glob("events-*.jsonl"))
    assert files
    row = json.loads(files[0].read_text().strip())
    assert row["request_id"] == "req-test-1"
