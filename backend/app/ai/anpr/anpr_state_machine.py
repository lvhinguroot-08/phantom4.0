from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional, Set
import numpy as np

from app.ai.anpr.temporal_anpr import (
    TemporalANPRAggregator,
    PlateReading,
    AggregatedPlateResult,
)


class ANPRTrackState(str, Enum):
    NO_PLATE = "NO_PLATE"
    PLATE_DETECTED = "PLATE_DETECTED"
    OCR_OBSERVING = "OCR_OBSERVING"
    PLATE_HYPOTHESIS = "PLATE_HYPOTHESIS"
    PLATE_CONFIRMED = "PLATE_CONFIRMED"
    TRACK_EXITED = "TRACK_EXITED"


@dataclass
class TrackANPRContext:
    """Per-vehicle track state and temporal aggregation buffer."""
    vehicle_track_id: int
    camera_id: str
    vehicle_type: str
    state: ANPRTrackState = ANPRTrackState.NO_PLATE
    aggregator: TemporalANPRAggregator = field(default_factory=TemporalANPRAggregator)
    confirmed_plate: Optional[str] = None
    confirmed_confidence: float = 0.0
    confirmed_crop: Optional[np.ndarray] = None
    last_updated: float = field(default_factory=time.time)
    consecutive_missing_frames: int = 0
    plate_published: bool = False


class ANPRStateMachineManager:
    """
    Manages track-aware ANPR state machines across multiple vehicles and cameras.
    Enforces hysteresis, cooldown periods, duplicate suppression, and memory eviction.
    """

    def __init__(
        self,
        temporal_window: int = 8,
        min_confirmations: int = 3,
        min_confidence: float = 0.55,
        duplicate_cooldown_seconds: float = 60.0,
        max_missing_frames: int = 30,
    ):
        self.temporal_window = temporal_window
        self.min_confirmations = min_confirmations
        self.min_confidence = min_confidence
        self.duplicate_cooldown_seconds = duplicate_cooldown_seconds
        self.max_missing_frames = max_missing_frames

        # Active tracks: track_id -> TrackANPRContext
        self.active_tracks: Dict[int, TrackANPRContext] = {}

        # Cooldown record: (camera_id, plate_text) -> timestamp
        self._published_plate_timestamps: Dict[str, float] = {}

    def get_or_create_context(
        self, vehicle_track_id: int, camera_id: str, vehicle_type: str
    ) -> TrackANPRContext:
        if vehicle_track_id not in self.active_tracks:
            ctx = TrackANPRContext(
                vehicle_track_id=vehicle_track_id,
                camera_id=camera_id,
                vehicle_type=vehicle_type,
                aggregator=TemporalANPRAggregator(
                    window_size=self.temporal_window,
                    min_confirmations=self.min_confirmations,
                    min_confidence=self.min_confidence,
                ),
            )
            self.active_tracks[vehicle_track_id] = ctx
        return self.active_tracks[vehicle_track_id]

    def update_track(
        self,
        vehicle_track_id: int,
        camera_id: str,
        vehicle_type: str,
        plate_reading: Optional[PlateReading],
        plate_detected: bool,
    ) -> AggregatedPlateResult:
        """
        Advance state machine for vehicle track with frame's observation.
        """
        ctx = self.get_or_create_context(vehicle_track_id, camera_id, vehicle_type)
        ctx.last_updated = time.time()
        ctx.consecutive_missing_frames = 0

        # If already confirmed, we keep the confirmed plate locked
        if ctx.state == ANPRTrackState.PLATE_CONFIRMED:
            if plate_reading and plate_reading.normalized_text == ctx.confirmed_plate:
                ctx.aggregator.add_reading(plate_reading)
            return AggregatedPlateResult(
                plate_text=ctx.confirmed_plate or "",
                confidence=ctx.confirmed_confidence,
                confirmations=ctx.aggregator.count(),
                temporal_consistency=1.0,
                format_validity=1.0,
                best_crop=ctx.confirmed_crop,
                is_confirmed=True,
            )

        if not plate_detected:
            # No plate found on this frame
            if ctx.state == ANPRTrackState.NO_PLATE:
                return AggregatedPlateResult(plate_text="", confidence=0.0, confirmations=0, temporal_consistency=0.0, format_validity=0.0)

        if plate_detected and (not plate_reading or plate_reading.normalized_text == "UNREADABLE"):
            if ctx.state == ANPRTrackState.NO_PLATE:
                ctx.state = ANPRTrackState.PLATE_DETECTED

        if plate_reading and plate_reading.normalized_text and plate_reading.normalized_text != "UNREADABLE":
            ctx.aggregator.add_reading(plate_reading)
            count = ctx.aggregator.count()
            if ctx.state in (ANPRTrackState.NO_PLATE, ANPRTrackState.PLATE_DETECTED):
                ctx.state = ANPRTrackState.OCR_OBSERVING
            elif ctx.state == ANPRTrackState.OCR_OBSERVING and count >= 2:
                ctx.state = ANPRTrackState.PLATE_HYPOTHESIS

        # Perform temporal voting
        result = ctx.aggregator.vote()

        if result.is_confirmed:
            ctx.state = ANPRTrackState.PLATE_CONFIRMED
            ctx.confirmed_plate = result.plate_text
            ctx.confirmed_confidence = result.confidence
            ctx.confirmed_crop = result.best_crop

        return result

    def should_publish_event(self, camera_id: str, plate_text: str) -> bool:
        """
        Checks if an ANPR recognition event should be published or suppressed by cooldown.
        """
        if not plate_text or plate_text == "UNREADABLE":
            return False

        key = f"{camera_id}:{plate_text}"
        now = time.time()
        last_time = self._published_plate_timestamps.get(key, 0.0)

        if (now - last_time) >= self.duplicate_cooldown_seconds:
            self._published_plate_timestamps[key] = now
            return True
        return False

    def mark_published(self, vehicle_track_id: int) -> None:
        if vehicle_track_id in self.active_tracks:
            self.active_tracks[vehicle_track_id].plate_published = True

    def is_published(self, vehicle_track_id: int) -> bool:
        if vehicle_track_id in self.active_tracks:
            return self.active_tracks[vehicle_track_id].plate_published
        return False

    def prune_missing_tracks(self, current_active_track_ids: Set[int]) -> List[int]:
        """
        Increment missing frame count and remove stale tracks from memory.
        Returns list of pruned track IDs.
        """
        pruned = []
        for track_id, ctx in list(self.active_tracks.items()):
            if track_id not in current_active_track_ids:
                ctx.consecutive_missing_frames += 1
                if ctx.consecutive_missing_frames > self.max_missing_frames:
                    ctx.state = ANPRTrackState.TRACK_EXITED
                    pruned.append(track_id)
                    del self.active_tracks[track_id]
            else:
                ctx.consecutive_missing_frames = 0
        return pruned
