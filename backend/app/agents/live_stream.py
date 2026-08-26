"""Live streaming engine for PitwallEar.

Implements a true incremental ingestion loop: it polls the OpenF1 team-radio
endpoint for the active session, diffing against what it has already seen so
only new clips are transcribed and classified. The result is a growing
mood-vs-pace timeline that can be pushed to clients over Server-Sent Events.

OpenF1's *live* REST/MQTT/WebSocket tier is sponsor-gated; the free tier serves
historical data. This engine is live-ready: when live access is available it
streams new clips as they land, and when it is not it degrades to near-real-time
replay of the most recent complete session. The mode is always reported
explicitly so the product never overclaims.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import urllib.request
from datetime import datetime, timezone

from app.agents.emotion import EmotionAgent
from app.agents.radio_timeline import RadioTimelineAgent
from app.agents.transcription import TranscriptionAgent
from app.schemas import MoodPoint

_OPENF1 = "https://api.openf1.org/v1"
_HEADERS = {"User-Agent": "PitwallEar/0.5-live"}


class LiveStreamEngine:
    """Incrementally ingests a driver's radio clips and emits per-lap mood points.

    The engine keeps a seen-set of ``recording_url`` values so a re-poll only
    processes clips that have not yet been analysed. This is the property that
    turns a batch pipeline into a streaming one.
    """

    def __init__(
        self,
        emotion_agent: EmotionAgent | None = None,
        transcription_agent: TranscriptionAgent | None = None,
    ) -> None:
        self._emotion = emotion_agent or EmotionAgent()
        self._transcription = transcription_agent or TranscriptionAgent()
        self._seen: set[str] = set()
        self._timeline: list[MoodPoint] = []
        self._lap_starts: list[tuple[int, datetime]] | None = None
        self._lap_key: tuple[str, str, int] | None = None

    @property
    def timeline(self) -> list[MoodPoint]:
        return list(self._timeline)

    async def poll_once(self, driver: str, gp: str, year: int) -> dict:
        """Poll OpenF1 once and process any new clips.

        Returns a status dict with the number of new clips and the updated
        timeline. Runs synchronously under the hood; the ``async`` signature
        keeps it clean inside an ASGI event loop.
        """
        clips = await asyncio.to_thread(self._fetch_radio_clips, driver, gp, year)
        new = [c for c in clips if c["recording_url"] not in self._seen]

        # Lap starts are fetched once per session, not per clip.
        if self._lap_key != (driver, gp, year):
            self._lap_starts = await asyncio.to_thread(self._fetch_lap_starts, driver, gp, year)
            self._lap_key = (driver, gp, year)

        for clip in new:
            self._seen.add(clip["recording_url"])
            point = await asyncio.to_thread(
                self._process_clip, clip, driver, gp, year
            )
            if point is not None:
                self._timeline.append(point)
                self._timeline.sort(key=lambda p: p.lap)

        return {
            "mode": "live" if self._is_live_window(clips) else "near-real-time-replay",
            "new_clips": len(new),
            "total_clips": len(self._seen),
            "timeline": [p.model_dump() for p in self._timeline],
        }

    # ------------------------------------------------------------------
    # OpenF1 access (mirrors RadioTimelineAgent, but with diffing)
    # ------------------------------------------------------------------

    @staticmethod
    def _get_json(path: str) -> list[dict]:
        req = urllib.request.Request(f"{_OPENF1}{path}", headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    @staticmethod
    def _driver_number(driver: str) -> int:
        return RadioTimelineAgent._driver_number(driver)

    @staticmethod
    def _gp_country(gp: str) -> str:
        return RadioTimelineAgent._gp_country(gp)

    def _fetch_radio_clips(self, driver: str, gp: str, year: int) -> list[dict]:
        sessions = self._get_json(
            f"/sessions?year={year}&country_name={self._gp_country(gp)}&session_name=Race"
        )
        if not sessions:
            return []

        session_key = sessions[0]["session_key"]
        driver_number = self._driver_number(driver)
        clips = self._get_json(
            f"/team_radio?session_key={session_key}&driver_number={driver_number}"
        )
        return [
            {
                "date": c.get("date", ""),
                "recording_url": c.get("recording_url", ""),
            }
            for c in clips
            if c.get("recording_url")
        ]

    @staticmethod
    def _is_live_window(clips: list[dict]) -> bool:
        """Best-effort check: are these clips from an active session?

        A clip within the last ~2 minutes suggests the session is live (OpenF1
        data typically lags reality by ~3 seconds). If no clips have timestamps,
        we conservatively treat the feed as replay.
        """
        now = datetime.now(timezone.utc)
        recent = 0
        for c in clips:
            try:
                dt = datetime.fromisoformat(c["date"])
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if (now - dt).total_seconds() < 120:
                    recent += 1
            except Exception:
                continue
        return recent > 0

    @staticmethod
    def _fetch_lap_starts(driver: str, gp: str, year: int) -> list[tuple[int, datetime]]:
        """Fetch FastF1 lap-start times once per session (empty on failure)."""
        try:
            return RadioTimelineAgent._fetch_lap_starts(driver, gp, year)
        except Exception:
            return []

    def _lap_for_clip(self, clip: dict) -> int | None:
        """Map a clip's timestamp to the lap it was sent on.

        Uses real FastF1 lap starts when available; clips that fall outside
        every lap window map to None and are dropped by the caller.
        """
        if not self._lap_starts:
            return None
        ts = RadioTimelineAgent._parse_ts(clip.get("date", ""))
        if ts is None:
            return None
        return RadioTimelineAgent._lap_for_timestamp(ts, self._lap_starts)

    def _process_clip(
        self, clip: dict, driver: str = "", gp: str = "", year: int = 0
    ) -> MoodPoint | None:
        """Transcribe + classify a single clip, aligning it to a real lap."""
        url = clip["recording_url"]
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                audio_bytes = resp.read()
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            transcription = self._transcription.transcribe(tmp_path)
            os.unlink(tmp_path)

            text = transcription.text.strip()
            if not text:
                return None
            emotion = self._emotion.classify_text(text)

            lap = self._lap_for_clip(clip)
            return MoodPoint(
                lap=lap if lap is not None else 0,
                mood=emotion.mood,
                confidence=emotion.confidence,
                calibrated_confidence=emotion.calibrated_confidence,
                # Unaligned points are labelled so the UI never presents a
                # guessed lap as a real one.
                source="openf1-live" if lap is not None else "openf1-live-unaligned",
                transcript=text,
                clip_url=url,
            )
        except Exception:
            return None
