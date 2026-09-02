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
    Multi-Object Tracker with Temporal Fusion, Hardware PTS timing,
    and label hysteresis.
    """

    def __init__(
        self,
        camera_id: str = "CAM-GLOBAL",
        iou_threshold: float = 0.30,
        max_lost_frames: int = 20,
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

    def check_and_handle_discontinuity(self, pts_msec: Optional[float]) -> bool:
        """Detects video loops or hard scene cuts."""
        if pts_msec is None or self.last_pts_msec is None:
            return False

        delta = pts_msec - self.last_pts_msec
        if delta < -500.0 or delta > 10000.0:
            self.discontinuity_count += 1
            logger.info(
                f"[{self.camera_id}] Scene cut / feed loop detected (ΔPTS={delta:.1f}ms). "
                f"Reconciling {len(self.tracks)} active tracks."
            )
            self.tracks.clear()
            self.fusion_engine.reset()
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
        Associate detections with existing tracks, assign persistent track IDs,
        and apply multi-frame temporal classification fusion.
        """
        now_dt = timestamp or datetime.now(timezone.utc)
        self.frame_count += 1

        self.check_and_handle_discontinuity(pts_msec)
        if pts_msec is not None:
            self.last_pts_msec = pts_msec

        active_track_ids = list(self.tracks.keys())
        matched_tracks: Set[int] = set()
        matched_dets: Set[int] = set()

        vehicle_classes = {
            "CAR", "TRUCK", "BUS", "MOTORCYCLE", "TWO_WHEELER",
            "VEHICLE", "VAN", "AUTO_RICKSHAW", "BICYCLE", "OTHER_VEHICLE"
        }

        # Candidate assignment matching based on IoU
        candidates: List[Tuple[float, int, int]] = []
        for det_idx, det in enumerate(detections):
            bbox = det.get("bounding_box") or det.get("bbox") or {}
            obj_class = (det.get("object_class") or det.get("class_name") or "OBJECT").upper()

            for tid in active_track_ids:
                track = self.tracks[tid]
                if track.object_class != obj_class:
                    if not (track.object_class in vehicle_classes and obj_class in vehicle_classes):
                        continue

                iou = compute_iou(bbox, track.bbox)
                if iou >= self.iou_threshold:
                    candidates.append((iou, det_idx, tid))

        candidates.sort(key=lambda x: x[0], reverse=True)

        # 1. Update matched existing tracks
        for iou, det_idx, tid in candidates:
            if det_idx in matched_dets or tid in matched_tracks:
                continue

            det = detections[det_idx]
            bbox = det.get("bounding_box") or det.get("bbox") or {}
            obj_class = (det.get("object_class") or det.get("class_name") or "OBJECT").upper()
            conf = _safe_float(det.get("confidence"), 0.0)

            track = self.tracks[tid]
            track.update(bbox, conf, timestamp=now_dt, pts_msec=pts_msec)

            matched_tracks.add(tid)
            matched_dets.add(det_idx)

            # Temporal classification fusion
            raw_res = det.get("hierarchical_result")
            if not isinstance(raw_res, HierarchicalClassificationResult):
                raw_res = HierarchicalClassificationResult(
                    category=obj_class,
                    category_confidence=conf,
                    subtype=det.get("attributes", {}).get("structure_type"),
                    make=det.get("attributes", {}).get("make"),
                    model=det.get("attributes", {}).get("model"),
                    model_confidence=conf if det.get("attributes", {}).get("model") else None,
                    classification_status=ClassificationStatus.CONFIDENT if conf >= 0.78 else ClassificationStatus.LIKELY,
                    is_hard_negative=det.get("is_hard_negative", False),
                    rejection_reason=det.get("rejection_reason"),
                )

            fused_res, lifecycle = self.fusion_engine.fuse_track_detection(tid, raw_res, timestamp=now_dt)

            # Apply fused properties to track
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

            # Populate detection payload
            det["track_id"] = tid
            det["camera_id"] = self.camera_id
            det["object_class"] = fused_res.category
            det["class_name"] = fused_res.category.lower()
            det["confidence"] = fused_res.category_confidence
            det["first_seen"] = track.first_seen
            det["last_seen"] = track.last_seen
            det["dwell_time"] = track.dwell_time
            det["movement_direction"] = track.movement_direction
            det["speed_kmph"] = track.speed_kmph
            det["classification_status"] = fused_res.classification_status.value
            det["event_lifecycle"] = lifecycle.value
            det["display_label"] = track.display_label
            det["is_hard_negative"] = fused_res.is_hard_negative
            if "attributes" in det and isinstance(det["attributes"], dict):
                if fused_res.make:
                    det["attributes"]["make"] = fused_res.make
                if fused_res.model:
                    det["attributes"]["model"] = fused_res.model
                    det["attributes"]["display_name"] = f"{fused_res.make or ''} {fused_res.model}".strip()
                det["attributes"]["classification_status"] = fused_res.classification_status.value

        # 2. Register new tracks for unmatched detections
        for det_idx, det in enumerate(detections):
            if det_idx not in matched_dets:
                bbox = det.get("bounding_box") or det.get("bbox") or {}
                obj_class = (det.get("object_class") or det.get("class_name") or "OBJECT").upper()
                conf = _safe_float(det.get("confidence"), 0.0)

                tid = self._next_track_id
                self._next_track_id += 1

                new_track = Track(
                    track_id=tid,
                    camera_id=self.camera_id,
                    bbox=bbox,
                    obj_class=obj_class,
                    conf=conf,
                    timestamp=now_dt,
                    pts_msec=pts_msec,
                )
                self.tracks[tid] = new_track

                raw_res = det.get("hierarchical_result")
                if not isinstance(raw_res, HierarchicalClassificationResult):
                    raw_res = HierarchicalClassificationResult(
                        category=obj_class,
                        category_confidence=conf,
                        subtype=det.get("attributes", {}).get("structure_type"),
                        make=det.get("attributes", {}).get("make"),
                        model=det.get("attributes", {}).get("model"),
                        model_confidence=conf if det.get("attributes", {}).get("model") else None,
                        classification_status=ClassificationStatus.CONFIDENT if conf >= 0.78 else ClassificationStatus.LIKELY,
                        is_hard_negative=det.get("is_hard_negative", False),
                        rejection_reason=det.get("rejection_reason"),
                    )

                fused_res, lifecycle = self.fusion_engine.fuse_track_detection(tid, raw_res, timestamp=now_dt)

                new_track.object_class = fused_res.category
                new_track.confidence = fused_res.category_confidence
                new_track.subtype = fused_res.subtype
                new_track.make = fused_res.make
                new_track.model = fused_res.model
                new_track.classification_status = fused_res.classification_status
                new_track.event_lifecycle = lifecycle
                new_track.display_label = fused_res.display_label or VisionTaxonomy.format_tactical_label(
                    category=fused_res.category,
                    subtype=fused_res.subtype,
                    make=fused_res.make,
                    model=fused_res.model,
                    confidence=fused_res.category_confidence,
                    status=fused_res.classification_status,
                    track_id=tid,
                )
                new_track.is_hard_negative = fused_res.is_hard_negative

                det["track_id"] = tid
                det["camera_id"] = self.camera_id
                det["object_class"] = fused_res.category
                det["class_name"] = fused_res.category.lower()
                det["confidence"] = fused_res.category_confidence
                det["first_seen"] = new_track.first_seen
                det["last_seen"] = new_track.last_seen
                det["dwell_time"] = 0.0
                det["movement_direction"] = "STATIONARY"
                det["speed_kmph"] = 0.0
                det["classification_status"] = fused_res.classification_status.value
                det["event_lifecycle"] = lifecycle.value
                det["display_label"] = new_track.display_label
                det["is_hard_negative"] = fused_res.is_hard_negative
                if "attributes" in det and isinstance(det["attributes"], dict):
                    if fused_res.make:
                        det["attributes"]["make"] = fused_res.make
                    if fused_res.model:
                        det["attributes"]["model"] = fused_res.model
                        det["attributes"]["display_name"] = f"{fused_res.make or ''} {fused_res.model}".strip()
                    det["attributes"]["classification_status"] = fused_res.classification_status.value

        # 3. Age unmatched tracks and prune dead ones
        dead_tracks: List[int] = []
        for tid, track in self.tracks.items():
            if tid not in matched_tracks and tid not in [d.get("track_id") for d in detections]:
                track.frames_since_update += 1
                if track.frames_since_update > self.max_lost_frames:
                    dead_tracks.append(tid)

        for tid in dead_tracks:
            del self.tracks[tid]

        self.fusion_engine.cleanup_lost_tracks(set(self.tracks.keys()))
        return detections
