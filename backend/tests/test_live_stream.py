"""Hermetic tests for the live streaming engine's diffing and alignment."""
from datetime import datetime, timedelta, timezone

from app.agents.live_stream import LiveStreamEngine
from app.schemas import EmotionResult, MoodPoint


def test_engine_starts_empty():
    engine = LiveStreamEngine()
    assert engine.timeline == []
    assert engine._seen == set()


def test_is_live_window_detects_recent_clips():
    recent = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    clips = [{"date": recent, "recording_url": "http://example.com/a.mp3"}]
    assert LiveStreamEngine._is_live_window(clips) is True


def test_is_live_window_rejects_old_clips():
    old = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    clips = [{"date": old, "recording_url": "http://example.com/a.mp3"}]
    assert LiveStreamEngine._is_live_window(clips) is False


def test_is_live_window_empty_clips_is_replay():
    assert LiveStreamEngine._is_live_window([]) is False


class _StubEngine(LiveStreamEngine):
    """Network-free engine: stubs fetch + process at the existing seams."""

    def __init__(self, clips):
        super().__init__(
            emotion_agent=object(), transcription_agent=object()
        )
        self._clips = clips

    def _fetch_radio_clips(self, driver, gp, year):
        return self._clips

    def _process_clip(self, clip, driver="", gp="", year=0):  # noqa: ARG002
        lap = self._lap_for_clip(clip)
        return MoodPoint(
            lap=lap if lap is not None else 0,
            mood="Stressed",
            confidence=0.9,
            source="openf1-live" if lap is not None else "openf1-live-unaligned",
            transcript="stub",
            clip_url=clip["recording_url"],
        )


def test_poll_once_diffs_against_seen_clips():
    import asyncio

    clips = [
        {"date": "2024-06-01T14:00:00+00:00", "recording_url": "http://x/1.mp3"},
        {"date": "2024-06-01T14:01:00+00:00", "recording_url": "http://x/2.mp3"},
    ]
    engine = _StubEngine(clips)

    first = asyncio.run(engine.poll_once("VER", "Spa", 2024))
    assert first["new_clips"] == 2
    assert first["total_clips"] == 2
    assert len(engine.timeline) == 2

    # Second poll sees the same clips: nothing new may be processed.
    second = asyncio.run(engine.poll_once("VER", "Spa", 2024))
    assert second["new_clips"] == 0
    assert second["total_clips"] == 2
    assert len(engine.timeline) == 2


def test_poll_once_aligns_new_clips_to_real_laps():
    import asyncio

    # Lap starts fabricated to match RadioTimelineAgent's contract:
    # lap N runs from its start until lap N+1's start.
    base = datetime(2024, 6, 1, 14, 0, tzinfo=timezone.utc)
    engine = _StubEngine([])
    engine._lap_starts = [(1, base), (2, base + timedelta(seconds=90)), (3, base + timedelta(seconds=180))]
    engine._lap_key = ("VER", "Spa", 2024)

    clip_in_lap_2 = {
        "date": (base + timedelta(seconds=100)).isoformat(),
        "recording_url": "http://x/lap2.mp3",
    }
    engine._clips = [clip_in_lap_2]

    out = asyncio.run(engine.poll_once("VER", "Spa", 2024))
    assert out["timeline"][0]["lap"] == 2
    assert out["timeline"][0]["source"] == "openf1-live"


def test_unalignable_clip_is_labelled_not_faked():
    import asyncio

    engine = _StubEngine([])
    engine._lap_starts = []  # no FastF1 data available
    engine._lap_key = ("VER", "Spa", 2024)
    engine._clips = [
        {"date": "2024-06-01T14:00:00+00:00", "recording_url": "http://x/u.mp3"}
    ]

    out = asyncio.run(engine.poll_once("VER", "Spa", 2024))
    assert out["timeline"][0]["lap"] == 0
    assert out["timeline"][0]["source"] == "openf1-live-unaligned"


def test_fetch_lap_starts_degrades_to_empty(monkeypatch):
    def boom(driver, gp, year):
        raise RuntimeError("fastf1 down")

    monkeypatch.setattr(
        "app.agents.radio_timeline.RadioTimelineAgent._fetch_lap_starts", boom
    )
    assert LiveStreamEngine._fetch_lap_starts("VER", "Spa", 2024) == []
