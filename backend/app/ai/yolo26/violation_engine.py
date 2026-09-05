"""
Traffic Violation Intelligence & Temporal State Machine Engine
Implements:
1. Helmet Violation State Machine (UNKNOWN -> OBSERVING -> SUSPECTED -> CONFIRMED -> RESOLVED)
2. Triple Riding State Machine (NORMAL -> OCCUPANCY_SUSPECTED -> TRIPLE_RIDING_CONFIRMED -> RESOLVED)
3. Duplicate Alert Suppression with Configurable Cooldown
4. Track Lifecycle & Memory Cleanup
"""
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import time
from typing import Any, Deque, Dict, List, Optional, Set, Tuple
import uuid

from .rider_association import VehicleOccupancyRecord
from .schemas import TrafficViolationEvent

logger = logging.getLogger("phantom.ai.yolo26.violation_engine")


class HelmetState:
    UNKNOWN = "UNKNOWN"
    OBSERVING = "OBSERVING"
    SUSPECTED_NO_HELMET = "SUSPECTED_NO_HELMET"
    CONFIRMED_NO_HELMET = "CONFIRMED_NO_HELMET"
    RESOLVED = "RESOLVED"


class OccupancyState:
    NORMAL = "NORMAL"
    OCCUPANCY_SUSPECTED = "OCCUPANCY_SUSPECTED"
    TRIPLE_RIDING_CONFIRMED = "TRIPLE_RIDING_CONFIRMED"
    RESOLVED = "RESOLVED"


@dataclass
class RiderViolationTracker:
    """Temporal tracking state for a specific rider on a two-wheeler."""
    vehicle_track_id: int
    person_track_id: int
    state: str = HelmetState.UNKNOWN
    history: Deque[str] = field(default_factory=lambda: deque(maxlen=15))
    confidence_history: Deque[float] = field(default_factory=lambda: deque(maxlen=15))
    consecutive_no_helmet: int = 0
    track_age: int = 0
    last_updated: float = field(default_factory=time.time)
    confirmed_at: Optional[float] = None


@dataclass
class VehicleTripleRidingTracker:
    """Temporal tracking state for two-wheeler passenger occupancy."""
    vehicle_track_id: int
    state: str = OccupancyState.NORMAL
    occupancy_history: Deque[int] = field(default_factory=lambda: deque(maxlen=15))
    consecutive_over_occupancy: int = 0
    track_age: int = 0
    last_updated: float = field(default_factory=time.time)
    confirmed_at: Optional[float] = None


class TrafficViolationEngine:
    """
    State-machine driven traffic violation intelligence engine.
    Ensures that single-frame anomalies never generate false violation alerts.
    """

    def __init__(
        self,
        camera_id: str = "CAM-GLOBAL",
        min_no_helmet_confirmations: int = 5,
        min_triple_riding_confirmations: int = 5,
        min_track_age: int = 3,
        cooldown_seconds: int = 60,
    ):
        self.camera_id = camera_id
        self.min_no_helmet_conf = min_no_helmet_confirmations
        self.min_triple_riding_conf = min_triple_riding_confirmations
        self.min_track_age = min_track_age
        self.cooldown_seconds = cooldown_seconds

        # Map: (vehicle_track_id, person_track_id) -> RiderViolationTracker
        self.helmet_trackers: Dict[Tuple[int, int], RiderViolationTracker] = {}
        # Map: vehicle_track_id -> VehicleTripleRidingTracker
        self.triple_riding_trackers: Dict[int, VehicleTripleRidingTracker] = {}
        # Cooldown map: (camera_id, vehicle_track_id, violation_type) -> last_alert_time
        self.alert_cooldowns: Dict[Tuple[str, int, str], float] = {}

    def _is_cooling_down(self, vehicle_track_id: int, violation_type: str) -> bool:
        """Checks if a violation alert for this vehicle and type is in cooldown."""
        key = (self.camera_id, vehicle_track_id, violation_type)
        now = time.time()
        last_time = self.alert_cooldowns.get(key, 0.0)
        if (now - last_time) < self.cooldown_seconds:
            return True
        return False

    def _mark_alerted(self, vehicle_track_id: int, violation_type: str) -> None:
        """Records alert emission time for duplicate suppression."""
        key = (self.camera_id, vehicle_track_id, violation_type)
        self.alert_cooldowns[key] = time.time()

    def update_rider_helmet(
        self,
        vehicle_track_id: int,
        person_track_id: int,
        helmet_state: str,
        confidence: float,
    ) -> Tuple[str, bool]:
        """
        Updates helmet state machine for a specific rider.
        Returns: (current_state, is_newly_confirmed)
        """
        key = (vehicle_track_id, person_track_id)
        now = time.time()

        if key not in self.helmet_trackers:
            self.helmet_trackers[key] = RiderViolationTracker(
                vehicle_track_id=vehicle_track_id,
                person_track_id=person_track_id,
            )

        tracker = self.helmet_trackers[key]
        tracker.track_age += 1
        tracker.last_updated = now
        tracker.history.append(helmet_state)
        tracker.confidence_history.append(confidence)

        is_newly_confirmed = False

        if helmet_state == "NO_HELMET":
            tracker.consecutive_no_helmet += 1

            if tracker.state in (HelmetState.UNKNOWN, HelmetState.OBSERVING):
                tracker.state = HelmetState.SUSPECTED_NO_HELMET

            # Check for sustained confirmation
            if (
                tracker.consecutive_no_helmet >= self.min_no_helmet_conf
                and tracker.track_age >= self.min_track_age
                and tracker.state != HelmetState.CONFIRMED_NO_HELMET
            ):
                tracker.state = HelmetState.CONFIRMED_NO_HELMET
                tracker.confirmed_at = now
                is_newly_confirmed = True
                logger.info(
                    f"Helmet Violation CONFIRMED for Rider {person_track_id} on Vehicle {vehicle_track_id} "
                    f"(sustained {tracker.consecutive_no_helmet} frames)."
                )

        elif helmet_state == "HELMET":
            tracker.consecutive_no_helmet = max(0, tracker.consecutive_no_helmet - 1)
            if tracker.state == HelmetState.CONFIRMED_NO_HELMET:
                # Helmet worn after violation -> resolve
                tracker.state = HelmetState.RESOLVED
            elif tracker.state == HelmetState.SUSPECTED_NO_HELMET:
                tracker.state = HelmetState.OBSERVING

        elif helmet_state in ("UNCERTAIN", "TURBAN"):
            # Preserve existing state without escalating suspicion
            pass

        return tracker.state, is_newly_confirmed

    def update_vehicle_occupancy(
        self,
        vehicle_track_id: int,
        occupant_count: int,
        association_confidence: float,
    ) -> Tuple[str, bool]:
        """
        Updates triple-riding state machine for a two-wheeler.
        Returns: (current_state, is_newly_confirmed)
        """
        now = time.time()
        if vehicle_track_id not in self.triple_riding_trackers:
            self.triple_riding_trackers[vehicle_track_id] = VehicleTripleRidingTracker(
                vehicle_track_id=vehicle_track_id,
            )

        tracker = self.triple_riding_trackers[vehicle_track_id]
        tracker.track_age += 1
        tracker.last_updated = now
        tracker.occupancy_history.append(occupant_count)

        is_newly_confirmed = False

        if occupant_count >= 3 and association_confidence >= 0.45:
            tracker.consecutive_over_occupancy += 1

            if tracker.state == OccupancyState.NORMAL:
                tracker.state = OccupancyState.OCCUPANCY_SUSPECTED

            if (
                tracker.consecutive_over_occupancy >= self.min_triple_riding_conf
                and tracker.track_age >= self.min_track_age
                and tracker.state != OccupancyState.TRIPLE_RIDING_CONFIRMED
            ):
                tracker.state = OccupancyState.TRIPLE_RIDING_CONFIRMED
                tracker.confirmed_at = now
                is_newly_confirmed = True
                logger.info(
                    f"Triple Riding Violation CONFIRMED on Vehicle {vehicle_track_id} "
                    f"({occupant_count} occupants sustained for {tracker.consecutive_over_occupancy} frames)."
                )

        elif occupant_count < 3:
            tracker.consecutive_over_occupancy = max(0, tracker.consecutive_over_occupancy - 1)
            if tracker.state == OccupancyState.TRIPLE_RIDING_CONFIRMED:
                tracker.state = OccupancyState.RESOLVED
            elif tracker.state == OccupancyState.OCCUPANCY_SUSPECTED:
                tracker.state = OccupancyState.NORMAL

        return tracker.state, is_newly_confirmed

    def evaluate_frame_violations(
        self,
        occupancy_records: Dict[int, VehicleOccupancyRecord],
        helmet_results: Dict[int, Tuple[str, float]],  # person_track_id -> (state, conf)
    ) -> List[TrafficViolationEvent]:
        """
        Evaluates current frame occupancy and helmet classifications.
        Produces deduplicated TrafficViolationEvent records.
        """
        generated_events: List[TrafficViolationEvent] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for vehicle_track_id, record in occupancy_records.items():
            vehicle_type = record.vehicle_type
            person_tids = record.associated_person_track_ids

            # 1. Evaluate Triple Riding
            occ_state, occ_confirmed = self.update_vehicle_occupancy(
                vehicle_track_id=vehicle_track_id,
                occupant_count=record.occupant_count,
                association_confidence=record.association_confidence,
            )

            if occ_state == OccupancyState.TRIPLE_RIDING_CONFIRMED:
                if not self._is_cooling_down(vehicle_track_id, "TRIPLE_RIDING"):
                    event = TrafficViolationEvent(
                        event_id=str(uuid.uuid4()),
                        violation_type="TRIPLE_RIDING",
                        camera_id=self.camera_id,
                        timestamp=now_iso,
                        vehicle_track_id=vehicle_track_id,
                        vehicle_type=vehicle_type,
                        person_track_ids=person_tids,
                        confidence=record.association_confidence,
                        severity="HIGH",
                        status="CONFIRMED",
                        occupant_count=record.occupant_count,
                        metadata={
                            "consecutive_frames": self.triple_riding_trackers[vehicle_track_id].consecutive_over_occupancy,
                            "occupant_track_ids": person_tids,
                            "association_confidence": record.association_confidence,
                        },
                    )
                    self._mark_alerted(vehicle_track_id, "TRIPLE_RIDING")
                    generated_events.append(event)

            # 2. Evaluate No Helmet for Each Rider
            for rider in record.riders:
                pid = rider.person_track_id
                res = helmet_results.get(pid)
                if not res:
                    continue

                h_state, h_conf = res
                helm_state, helm_confirmed = self.update_rider_helmet(
                    vehicle_track_id=vehicle_track_id,
                    person_track_id=pid,
                    helmet_state=h_state,
                    confidence=h_conf,
                )

                if helm_state == HelmetState.CONFIRMED_NO_HELMET:
                    v_type_key = f"NO_HELMET_RIDER_{pid}"
                    if not self._is_cooling_down(vehicle_track_id, v_type_key):
                        event = TrafficViolationEvent(
                            event_id=str(uuid.uuid4()),
                            violation_type="NO_HELMET",
                            camera_id=self.camera_id,
                            timestamp=now_iso,
                            vehicle_track_id=vehicle_track_id,
                            vehicle_type=vehicle_type,
                            person_track_ids=person_tids,
                            confidence=h_conf,
                            severity="MEDIUM",
                            status="CONFIRMED",
                            rider_track_id=pid,
                            helmet_state=h_state,
                            metadata={
                                "is_primary_rider": rider.is_primary_rider,
                                "rider_track_id": pid,
                                "helmet_confidence": h_conf,
                                "consecutive_frames": self.helmet_trackers[(vehicle_track_id, pid)].consecutive_no_helmet,
                            },
                        )
                        self._mark_alerted(vehicle_track_id, v_type_key)
                        generated_events.append(event)

        return generated_events

    def cleanup_lost_tracks(self, active_track_ids: Set[int]) -> None:
        """
        Safely purges state machines for tracks that have exited the CCTV field of view.
        """
        # Cleanup helmet trackers
        stale_helmet_keys = [
            (v, p) for (v, p) in self.helmet_trackers.keys()
            if v not in active_track_ids and p not in active_track_ids
        ]
        for k in stale_helmet_keys:
            del self.helmet_trackers[k]

        # Cleanup triple riding trackers
        stale_trip_keys = [
            v for v in self.triple_riding_trackers.keys()
            if v not in active_track_ids
        ]
        for k in stale_trip_keys:
            del self.triple_riding_trackers[k]

        # Cleanup expired cooldown entries
        now = time.time()
        self.alert_cooldowns = {
            k: v for k, v in self.alert_cooldowns.items()
            if (now - v) < (self.cooldown_seconds * 2)
        }
