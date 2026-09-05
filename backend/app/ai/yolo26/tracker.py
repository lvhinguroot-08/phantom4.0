"""
YOLO26 Multi-Object Tracking & Temporal Fusion Engine
=====================================================
Maintains persistent track IDs, movement direction, dwell time, velocity estimates,
hierarchical classification stability, and multi-frame temporal voting per camera stream.

Key Features:
- Real hardware PTS presentation timing (CAP_PROP_POS_MSEC)
- Temporal score aggregation and label hysteresis (prevents label flipping)
- Hard negative suppression across track trajectories
- Structured classification status: CONFIDENT | LIKELY | UNCERTAIN | UNKNOWN
- Event Lifecycle: DETECTED -> TRACKING -> CONFIRMED -> ENDED
"""
from collections import deque
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.core.logging import logger
from .hierarchy import (
    ClassificationStatus,
    EventLifecycle,
    HierarchicalClassificationResult,
    VisionTaxonomy,
)
from .temporal_fusion import TemporalTrackFusionEngine
from .bytetrack import BYTETracker, STrack


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert numeric/string value to float with fallback."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _normalize_bbox(box: Any) -> Dict[str, float]:
    """Normalize various bounding box representations into standard {'x1', 'y1', 'x2', 'y2'} dict."""
    if isinstance(box, dict):
        raw_x1 = box.get("x1", box.get("xmin", box.get("left", 0.0)))
        raw_y1 = box.get("y1", box.get("ymin", box.get("top", 0.0)))
        raw_x2 = box.get("x2", box.get("xmax", box.get("right", 0.0)))
        raw_y2 = box.get("y2", box.get("ymax", box.get("bottom", 0.0)))

        return {
            "x1": _safe_float(raw_x1, 0.0),
            "y1": _safe_float(raw_y1, 0.0),
            "x2": _safe_float(raw_x2, 0.0),
            "y2": _safe_float(raw_y2, 0.0),
        }
    elif isinstance(box, (list, tuple)) and len(box) >= 4:
        return {
            "x1": _safe_float(box[0], 0.0),
            "y1": _safe_float(box[1], 0.0),
            "x2": _safe_float(box[2], 0.0),
            "y2": _safe_float(box[3], 0.0),
        }
    return {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 0.0}


def compute_iou(box1: Any, box2: Any) -> float:
    """Calculate Intersection over Union (IoU) between two bounding boxes."""
    b1 = _normalize_bbox(box1)
    b2 = _normalize_bbox(box2)

    x1 = max(b1["x1"], b2["x1"])
    y1 = max(b1["y1"], b2["y1"])
    x2 = min(b1["x2"], b2["x2"])
    y2 = min(b1["y2"], b2["y2"])

    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area1 = max(0.0, b1["x2"] - b1["x1"]) * max(0.0, b1["y2"] - b1["y1"])
    area2 = max(0.0, b2["x2"] - b2["x1"]) * max(0.0, b2["y2"] - b2["y1"])

    union = area1 + area2 - intersection
    if union <= 0.0:
        return 0.0
    return intersection / union


def format_display_label(
    object_class: str,
    track_id: Optional[int] = None,
    confidence: float = 0.0,
) -> str:
    """Format standard display label, e.g., 'Person #12 | 96%'."""
    cat_disp = (object_class or "OBJECT").replace("_", " ").title()
    track_str = f" #{track_id}" if track_id is not None else ""
    pct = int(round(_safe_float(confidence) * 100))
    return f"{cat_disp}{track_str} | {pct}%"



class Track:
    """Internal state for a single tracked object trajectory with hardware PTS timing."""

    def __init__(
        self,
        track_id: int,
        camera_id: str,
        bbox: Union[Dict[str, float], List[float], Tuple[float, ...]],
        obj_class: str,
        conf: float,
        timestamp: Optional[datetime] = None,
        pts_msec: Optional[float] = None,
        max_history: int = 30,
    ):
        self.track_id: int = track_id
        self.camera_id: str = camera_id
        self.bbox: Dict[str, float] = _normalize_bbox(bbox)
        self.object_class: str = (obj_class or "OBJECT").upper()
        self.confidence: float = _safe_float(conf, 0.0)
        self.max_history: int = max_history

        now_dt = timestamp or datetime.now(timezone.utc)
        self.first_seen_epoch: float = now_dt.timestamp()
        self.last_seen_epoch: float = self.first_seen_epoch
        self.first_seen: str = now_dt.isoformat()
        self.last_seen: str = self.first_seen

        # Presentation Timestamps (PTS)
        self.first_pts_msec: Optional[float] = pts_msec
        self.last_pts_msec: Optional[float] = pts_msec

        cx = (self.bbox["x1"] + self.bbox["x2"]) / 2.0
        cy = (self.bbox["y1"] + self.bbox["y2"]) / 2.0
        self.centroid: Dict[str, float] = {"x": round(cx, 1), "y": round(cy, 1)}

        self.history: deque = deque(maxlen=max_history)
        self.history.append({"x": round(cx, 1), "y": round(cy, 1), "timestamp": self.first_seen, "pts_msec": pts_msec})

        self.frames_since_update: int = 0
        self.speed_kmph: float = 0.0
        self.movement_direction: str = "STATIONARY"
        self.dwell_time: float = 0.0

        # Hierarchical attributes
        self.classification_status: ClassificationStatus = ClassificationStatus.UNKNOWN
        self.event_lifecycle: EventLifecycle = EventLifecycle.DETECTED
        self.subtype: Optional[str] = None
        self.make: Optional[str] = None
        self.model: Optional[str] = None
        self.display_label: str = ""
        self.is_hard_negative: bool = False

    def update(
        self,
        bbox: Union[Dict[str, float], List[float], Tuple[float, ...]],
        conf: float,
        timestamp: Optional[datetime] = None,
        pts_msec: Optional[float] = None,
    ) -> None:
        now_dt = timestamp or datetime.now(timezone.utc)
        now_epoch = now_dt.timestamp()
        now_iso = now_dt.isoformat()

        self.bbox = _normalize_bbox(bbox)
        self.confidence = _safe_float(conf, 0.0)
        self.last_seen_epoch = now_epoch
        self.last_seen = now_iso

        # 1. Hardware PTS-driven dwell time calculation
        if pts_msec is not None:
            if self.first_pts_msec is None:
                self.first_pts_msec = pts_msec
            dwell_ms = max(0.0, pts_msec - self.first_pts_msec)
            self.dwell_time = round(dwell_ms / 1000.0, 1)
        else:
            self.dwell_time = round(max(0.0, now_epoch - self.first_seen_epoch), 1)

        cx = (self.bbox["x1"] + self.bbox["x2"]) / 2.0
        cy = (self.bbox["y1"] + self.bbox["y2"]) / 2.0

        # 2. Real ΔPTS-driven velocity and directional calculation
        if self.history:
            prev = self.history[-1]
            dx = cx - prev["x"]
            dy = cy - prev["y"]
            dist_px = math.sqrt(dx * dx + dy * dy)

            prev_pts = prev.get("pts_msec")
            if pts_msec is not None and prev_pts is not None and pts_msec > prev_pts:
                delta_pts_sec = max(0.01, (pts_msec - prev_pts) / 1000.0)
            else:
                delta_pts_sec = max(0.01, now_epoch - self.last_seen_epoch) if (now_epoch - self.last_seen_epoch) > 0 else 0.04

            if dist_px < 3.0:
                self.movement_direction = "STATIONARY"
                self.speed_kmph = 0.0
            else:
                px_per_sec = dist_px / delta_pts_sec
                self.speed_kmph = round(min(140.0, max(5.0, px_per_sec * 0.12)), 1)
                if abs(dy) > abs(dx):
                    self.movement_direction = "SOUTHBOUND" if dy > 0 else "NORTHBOUND"
                else:
                    self.movement_direction = "EASTBOUND" if dx > 0 else "WESTBOUND"

        if pts_msec is not None:
            self.last_pts_msec = pts_msec

        self.history.append({"x": round(cx, 1), "y": round(cy, 1), "timestamp": now_iso, "pts_msec": pts_msec})
        self.centroid = {"x": round(cx, 1), "y": round(cy, 1)}
        self.frames_since_update = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "camera_id": self.camera_id,
            "object_class": self.object_class,
            "confidence": round(self.confidence, 4),
            "bounding_box": self.bbox,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "first_pts_msec": self.first_pts_msec,
            "last_pts_msec": self.last_pts_msec,
            "dwell_time": self.dwell_time,
            "movement_direction": self.movement_direction,
            "speed_kmph": self.speed_kmph,
            "classification_status": self.classification_status.value,
            "event_lifecycle": self.event_lifecycle.value,
            "subtype": self.subtype,
            "make": self.make,
            "model": self.model,
            "display_label": self.display_label,
            "is_hard_negative": self.is_hard_negative,
        }


class YOLO26Tracker:
    """
    Production Multi-Object Tracker powered by ByteTrack:
    - 2D Bounding Box Kalman Filter for motion prediction across frame drops
    - Two-stage association (high-confidence detection matching + low-confidence occlusion recovery)
    - Hardware PTS timing & scene cut / feed loop detection
    - Temporal classification stabilization & label hysteresis
    """

    def __init__(
        self,
        camera_id: str = "CAM-GLOBAL",
        iou_threshold: float = 0.30,
        max_lost_frames: int = 30,
        entry_line_y_ratio: float = 0.40,
        exit_line_y_ratio: float = 0.75,
    ):
        self.camera_id: str = camera_id
        self.iou_threshold: float = _safe_float(iou_threshold, 0.30)
        self.max_lost_frames: int = max_lost_frames
        self.entry_line_ratio: float = _safe_float(entry_line_y_ratio, 0.40)
        self.exit_line_ratio: float = _safe_float(exit_line_y_ratio, 0.75)

        self._next_track_id: int = 1
        self.tracks: Dict[int, Track] = {}
        self.frame_count: int = 0
        self.fusion_engine: TemporalTrackFusionEngine = TemporalTrackFusionEngine(camera_id=camera_id)

        # ByteTrack Core
        self.bytetracker: BYTETracker = BYTETracker(
            track_thresh=0.50,
            track_buffer=self.max_lost_frames,
            match_thresh=0.70,
        )

        # Discontinuity & PTS tracking
        self.last_pts_msec: Optional[float] = None
        self.discontinuity_count: int = 0

    def reset(self) -> None:
        """Reset tracker state and clear all active tracks and counters."""
        self._next_track_id = 1
        self.tracks.clear()
        self.frame_count = 0
        self.last_pts_msec = None
        self.fusion_engine.reset()
        self.bytetracker.reset()

    def check_and_handle_discontinuity(self, pts_msec: Optional[float]) -> bool:
        """Detects video loops or hard scene cuts."""
        if pts_msec is None or self.last_pts_msec is None:
            return False

        delta = pts_msec - self.last_pts_msec
        if delta < -500.0 or delta > 10000.0:
            self.discontinuity_count += 1
            logger.info(
                f"[{self.camera_id}] Scene cut / feed loop detected (ΔPTS={delta:.1f}ms). "
                f"Reconciling active tracks."
            )
            self.tracks.clear()
            self.fusion_engine.reset()
            self.bytetracker.reset()
            return True
        return False

    def update(
        self,
        detections: List[Dict[str, Any]],
        frame_shape: Optional[Tuple[int, int]] = None,
        timestamp: Optional[datetime] = None,
        pts_msec: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Associate detections with existing tracks using ByteTrack two-stage Kalman matching,
        assign persistent track IDs, and apply multi-frame temporal classification stabilization.
        """
        now_dt = timestamp or datetime.now(timezone.utc)
        self.frame_count += 1

        self.check_and_handle_discontinuity(pts_msec)
        if pts_msec is not None:
            self.last_pts_msec = pts_msec

        # 1. ByteTrack Two-Stage Association with Kalman Motion Prediction
        active_stracks = self.bytetracker.update(detections)
        tracked_results: List[Dict[str, Any]] = []
        active_track_ids: Set[int] = set()

        for strack in active_stracks:
            tid = strack.track_id
            active_track_ids.add(tid)
            raw_det = dict(strack.raw_det) if strack.raw_det else {}
            box_dict = strack.to_dict()["bbox"]
            obj_class = strack.object_class
            conf = strack.score

            if tid in self.tracks:
                track = self.tracks[tid]
                track.update(box_dict, conf, timestamp=now_dt, pts_msec=pts_msec)
            else:
                track = Track(
                    track_id=tid,
                    camera_id=self.camera_id,
                    bbox=box_dict,
                    obj_class=obj_class,
                    conf=conf,
                    timestamp=now_dt,
                    pts_msec=pts_msec,
                )
                self.tracks[tid] = track

            # 2. Temporal Classification Stabilization (Confidence-Weighted History & Hysteresis)
            raw_res = raw_det.get("hierarchical_result")
            if not isinstance(raw_res, HierarchicalClassificationResult):
                raw_res = HierarchicalClassificationResult(
                    category=obj_class,
                    category_confidence=conf,
                    subtype=raw_det.get("attributes", {}).get("structure_type"),
                    make=raw_det.get("attributes", {}).get("make"),
                    model=raw_det.get("attributes", {}).get("model"),
                    model_confidence=conf if raw_det.get("attributes", {}).get("model") else None,
                    classification_status=ClassificationStatus.CONFIDENT if conf >= 0.75 else ClassificationStatus.LIKELY,
                    is_hard_negative=raw_det.get("is_hard_negative", False),
                    rejection_reason=raw_det.get("rejection_reason"),
                )

            fused_res, lifecycle = self.fusion_engine.fuse_track_detection(tid, raw_res, timestamp=now_dt)

            track.object_class = fused_res.category
            track.confidence = fused_res.category_confidence
            track.subtype = fused_res.subtype
            track.make = fused_res.make
            track.model = fused_res.model
            track.classification_status = fused_res.classification_status
            track.event_lifecycle = lifecycle
            track.display_label = fused_res.display_label or VisionTaxonomy.format_tactical_label(
                category=fused_res.category,
                subtype=fused_res.subtype,
                make=fused_res.make,
                model=fused_res.model,
                confidence=fused_res.category_confidence,
                status=fused_res.classification_status,
                track_id=tid,
            )
            track.is_hard_negative = fused_res.is_hard_negative

            # Populate track data model complying with Step 10
            res_det = {
                "track_id": tid,
                "camera_id": self.camera_id,
                "object_class": fused_res.category,
                "class_name": fused_res.category.lower(),
                "confidence": fused_res.category_confidence,
                "detection_confidence": conf,
                "bbox": track.bbox,
                "bounding_box": track.bbox,
                "first_seen": track.first_seen,
                "last_seen": track.last_seen,
                "dwell_time": track.dwell_time,
                "movement_direction": track.movement_direction,
                "speed_kmph": track.speed_kmph,
                "tracking_state": strack.state.name,
                "track_age": strack.tracklet_len,
                "classification_status": fused_res.classification_status.value,
                "event_lifecycle": lifecycle.value,
                "display_label": track.display_label,
                "is_hard_negative": fused_res.is_hard_negative,
                "hierarchical_result": fused_res,
                "attributes": raw_det.get("attributes", {}),
            }
            tracked_results.append(res_det)

        # 3. Clean up expired tracks
        for tid in list(self.tracks.keys()):
            if tid not in active_track_ids:
                self.tracks[tid].frames_since_update += 1
                if self.tracks[tid].frames_since_update > self.max_lost_frames:
                    del self.tracks[tid]

        self.fusion_engine.cleanup_lost_tracks(set(self.tracks.keys()))
        return tracked_results
