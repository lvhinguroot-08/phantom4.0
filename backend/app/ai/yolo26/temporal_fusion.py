"""
PHANTOM Vision Intelligence V2 — Temporal Track Fusion & Hysteresis Engine
==========================================================================
Maintains multi-frame classification evidence, exponential moving average score
aggregation, and label stabilization across object trajectories.

Core Principles:
1. Never rely on a single video frame for incident confirmation or fine make/model.
2. Temporal Voting: Aggregates candidate scores across track history.
3. Label Hysteresis: Prevents rapid frame-to-frame label flickering.
4. Event Lifecycle: Separates RAW DETECTIONS from CONFIRMED SURVEILLANCE EVENTS.
"""
from collections import defaultdict, deque
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

from .hierarchy import (
    ClassificationStatus,
    EventLifecycle,
    HierarchicalClassificationResult,
    VisionTaxonomy,
)

logger = logging.getLogger("phantom.ai.temporal_fusion")


class TrackTemporalState:
    """Temporal classification state buffer for a single object track."""

    def __init__(self, track_id: int, camera_id: str, max_history: int = 15):
        self.track_id: int = track_id
        self.camera_id: str = camera_id
        self.max_history: int = max_history

        self.frames_seen: int = 0
        self.first_seen: str = datetime.now(timezone.utc).isoformat()
        self.last_seen: str = self.first_seen

        # History queues
        self.category_history: deque = deque(maxlen=max_history)
        self.subtype_history: deque = deque(maxlen=max_history)
        self.model_history: deque = deque(maxlen=max_history)
        self.conf_history: deque = deque(maxlen=max_history)

        # Stable locked states (Hysteresis)
        self.stable_category: str = "OBJECT"
        self.stable_subtype: Optional[str] = None
        self.stable_make: Optional[str] = None
        self.stable_model: Optional[str] = None
        self.stable_confidence: float = 0.0
        self.stable_status: ClassificationStatus = ClassificationStatus.UNKNOWN
        self.lifecycle: EventLifecycle = EventLifecycle.DETECTED

        self.is_hard_negative: bool = False
        self.rejection_reason: Optional[str] = None

    def update(
        self,
        hierarchical_result: HierarchicalClassificationResult,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Accumulates evidence from the current frame and applies temporal fusion."""
        now_dt = timestamp or datetime.now(timezone.utc)
        self.last_seen = now_dt.isoformat()
        self.frames_seen += 1

        res = hierarchical_result
        self.is_hard_negative = res.is_hard_negative
        self.rejection_reason = res.rejection_reason

        # Append to history
        self.category_history.append(res.category)
        if res.subtype:
            self.subtype_history.append(res.subtype)
        if res.model:
            self.model_history.append((res.make, res.model))
        self.conf_history.append(res.category_confidence)

        # 1. Update Event Lifecycle
        if self.is_hard_negative:
            self.lifecycle = EventLifecycle.DETECTED
        elif self.frames_seen < 3:
            self.lifecycle = EventLifecycle.DETECTED
        elif self.frames_seen < 5:
            self.lifecycle = EventLifecycle.TRACKING
        else:
            self.lifecycle = EventLifecycle.CONFIRMED

        # 2. Temporal Category Voting with Confidence Weighting & Hysteresis
        cat_counts: Dict[str, float] = defaultdict(float)
        for idx, (cat, c_conf) in enumerate(zip(self.category_history, self.conf_history)):
            # Recency weight multiplied by detection confidence
            weight = (1.0 + (idx / float(len(self.category_history)))) * max(0.1, float(c_conf))
            cat_counts[cat] += weight

        total_cat_weight = sum(cat_counts.values())
        sorted_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
        top_cat, top_cat_weight = sorted_cats[0]

        # Hysteresis: An established stable track requires >= 65% weighted consensus to switch classes
        if self.stable_category != "OBJECT" and len(self.category_history) >= 3:
            if top_cat != self.stable_category:
                if total_cat_weight > 0 and (top_cat_weight / total_cat_weight) >= 0.65:
                    self.stable_category = top_cat
            else:
                self.stable_category = top_cat
        else:
            self.stable_category = top_cat

        self.stable_confidence = round(float(sum(self.conf_history)) / max(1, len(self.conf_history)), 3)

        # 3. Temporal Subtype Voting & Hysteresis
        if self.subtype_history:
            sub_counts: Dict[str, float] = defaultdict(float)
            for idx, sub in enumerate(self.subtype_history):
                weight = 1.0 + (idx / float(len(self.subtype_history)))
                sub_counts[sub] += weight
            best_sub = max(sub_counts.items(), key=lambda x: x[1])[0]
            sub_ratio = sub_counts[best_sub] / sum(sub_counts.values())

            if sub_ratio >= 0.60 or self.frames_seen >= 4:
                self.stable_subtype = best_sub

        # 4. Temporal Model Voting & Hysteresis (Prevent label flipping)
        if self.model_history:
            model_counts: Dict[Tuple[Optional[str], Optional[str]], float] = defaultdict(float)
            for idx, mm in enumerate(self.model_history):
                weight = 1.0 + (idx / float(len(self.model_history)))
                model_counts[mm] += weight

            sorted_models = sorted(model_counts.items(), key=lambda x: x[1], reverse=True)
            top_mm, top_count = sorted_models[0]
            total_model_votes = sum(model_counts.values())
            top_ratio = top_count / total_model_votes

            # If there is strong consistent evidence across consecutive frames
            if top_ratio >= 0.65 and len(self.model_history) >= 3:
                self.stable_make, self.stable_model = top_mm
                self.stable_status = (
                    ClassificationStatus.CONFIDENT
                    if (top_ratio >= 0.75 and self.stable_confidence >= 0.72)
                    else ClassificationStatus.LIKELY
                )
            elif top_ratio < 0.55:
                # Contested models (e.g. WagonR 50% vs Swift 50%) -> Lock to UNCERTAIN
                self.stable_make = None
                self.stable_model = None
                self.stable_status = ClassificationStatus.UNCERTAIN
            else:
                self.stable_status = res.classification_status
        else:
            self.stable_status = res.classification_status

    def get_fused_result(self) -> HierarchicalClassificationResult:
        """Returns the stabilized, temporally fused classification result."""
        disp_label = VisionTaxonomy.format_tactical_label(
            category=self.stable_category,
            subtype=self.stable_subtype,
            make=self.stable_make,
            model=self.stable_model,
            confidence=self.stable_confidence,
            status=self.stable_status,
            track_id=self.track_id,
        )

        return HierarchicalClassificationResult(
            category=self.stable_category,
            category_confidence=self.stable_confidence,
            subtype=self.stable_subtype,
            make=self.stable_make,
            model=self.stable_model,
            model_confidence=self.stable_confidence if self.stable_model else None,
            classification_status=self.stable_status,
            display_label=disp_label,
            is_hard_negative=self.is_hard_negative,
            rejection_reason=self.rejection_reason,
        )


class TemporalTrackFusionEngine:
    """
    Registry and manager of temporal track states per camera.
    Provides persistent cross-frame voting, label hysteresis, and lifecycle management.
    """

    def __init__(self, camera_id: str):
        self.camera_id: str = camera_id
        self._states: Dict[int, TrackTemporalState] = {}

    def get_or_create_state(self, track_id: int) -> TrackTemporalState:
        if track_id not in self._states:
            self._states[track_id] = TrackTemporalState(track_id=track_id, camera_id=self.camera_id)
        return self._states[track_id]

    def fuse_track_detection(
        self,
        track_id: int,
        raw_result: HierarchicalClassificationResult,
        timestamp: Optional[datetime] = None,
    ) -> Tuple[HierarchicalClassificationResult, EventLifecycle]:
        """
        Updates temporal state for track_id and returns (fused_result, event_lifecycle).
        """
        state = self.get_or_create_state(track_id)
        state.update(raw_result, timestamp=timestamp)
        return state.get_fused_result(), state.lifecycle

    def cleanup_lost_tracks(self, active_track_ids: set) -> None:
        """Removes states for tracks that have ended/exited."""
        expired = [tid for tid in self._states if tid not in active_track_ids]
        for tid in expired:
            del self._states[tid]

    def reset(self) -> None:
        """Clears all track states."""
        self._states.clear()
