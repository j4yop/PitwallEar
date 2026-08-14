"""Hermetic tests for the live streaming engine's diffing and helpers."""
from app.agents.live_stream import LiveStreamEngine


def test_engine_starts_empty():
    engine = LiveStreamEngine()
    assert engine.timeline == []
    assert engine._seen == set()


def test_is_live_window_detects_recent_clips():
    from datetime import datetime, timedelta, timezone

    recent = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    clips = [{"date": recent, "recording_url": "http://example.com/a.mp3"}]
    assert LiveStreamEngine._is_live_window(clips) is True


def test_is_live_window_rejects_old_clips():
    from datetime import datetime, timedelta, timezone

    old = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    clips = [{"date": old, "recording_url": "http://example.com/a.mp3"}]
    assert LiveStreamEngine._is_live_window(clips) is False


def test_is_live_window_empty_clips_is_replay():
    assert LiveStreamEngine._is_live_window([]) is False


def test_lap_for_stream_is_zero_placeholder():
    assert LiveStreamEngine._lap_for_stream({}) == 0
