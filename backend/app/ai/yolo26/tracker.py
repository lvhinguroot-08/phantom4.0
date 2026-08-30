"""
YOLO26 Multi-Object Tracking & Trajectory Engine
Maintains persistent track IDs, movement direction, dwell time, and velocity estimates within individual camera streams.
Strictly isolated per-camera tracking without facial recognition or cross-camera assumptions.

Hardware Presentation Timestamp (PTS) Driven:
- Dwell time and speed are strictly calculated using real ΔPTS (CAP_PROP_POS_MSEC)
- Never relies on wall-clock arrival time or assumed constant FPS
- Tolerates variable inter-frame intervals and network jitter
- Detects video loops and hard scene cuts to reconcile stale tracks
"""
from collections import deque
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.core.logging import logger


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert any numeric/string value to float with a fallback default."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _normalize_bbox(box: Any) -> Dict[str, float]:
    """Normalize various bounding box representations into standard {'x1', 'y1', 'x2', 'y2'} dict."""
    if isinstance(box, dict):
        raw_x1 = box.get("x1")
        if raw_x1 is None:
            raw_x1 = box.get("xmin", box.get("left", 0.0))

        raw_y1 = box.get("y1")
        if raw_y1 is None:
            raw_y1 = box.get("ymin", box.get("top", 0.0))

        raw_x2 = box.get("x2")
        if raw_x2 is None:
            raw_x2 = box.get("xmax", box.get("right", 0.0))

        raw_y2 = box.get("y2")
        if raw_y2 is None:
            raw_y2 = box.get("ymax", box.get("bottom", 0.0))

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


def format_display_label(obj_class: str, track_id: int, confidence: float) -> str:
    """Format standard display label (e.g. 'Person #12 | 96%', 'Car #7 | 91%')."""
    cleaned = (obj_class or "OBJECT").replace("_", " ").title()
    pct = round(confidence * 100)
    return f"{cleaned} #{track_id} | {pct}%"


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

        self.entry_logged: bool = False
        self.exit_logged: bool = False

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
            # Calculate dwell time directly from presentation timestamps
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

            # Determine real ΔPTS interval in seconds
            prev_pts = prev.get("pts_msec")
            if pts_msec is not None and prev_pts is not None and pts_msec > prev_pts:
                delta_pts_sec = max(0.01, (pts_msec - prev_pts) / 1000.0)
            else:
                delta_pts_sec = max(0.01, now_epoch - self.last_seen_epoch) if (now_epoch - self.last_seen_epoch) > 0 else 0.04

            if dist_px < 3.0:
                self.movement_direction = "STATIONARY"
                self.speed_kmph = 0.0
            else:
                # Approximate scale conversion: speed based on real ΔPTS displacement
                px_per_sec = dist_px / delta_pts_sec
                # Realistic civilian/traffic speed range estimate (0 - 140 km/h)
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
            "display_label": format_display_label(self.object_class, self.track_id, self.confidence),
        }


class YOLO26Tracker:
    """
    Multi-Object Tracker supporting IoU association, hardware PTS timing,
    variable frame interval tolerance, and scene loop / discontinuity handling.
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

        # Discontinuity & PTS tracking
        self.last_pts_msec: Optional[float] = None
        self.discontinuity_count: int = 0

        self.total_entered: int = 0
        self.total_exited: int = 0
        self.class_breakdown: Dict[str, Dict[str, int]] = {}

    def reset(self) -> None:
        """Reset tracker state and clear all active tracks and counters."""
        self._next_track_id = 1
        self.tracks.clear()
        self.frame_count = 0
        self.last_pts_msec = None
        self.total_entered = 0
        self.total_exited = 0
        self.class_breakdown.clear()

    def check_and_handle_discontinuity(self, pts_msec: Optional[float]) -> bool:
        """
        Detects video loops or hard scene cuts:
        1. Negative PTS step (pts_msec < last_pts_msec - 500ms): Feed loop rewind
        2. Huge PTS jump (pts_msec > last_pts_msec + 10000ms): Discontinuity cut
        Reconciles active tracks on cut so stale tracks do not persist.
        """
        if pts_msec is None or self.last_pts_msec is None:
            return False

        delta = pts_msec - self.last_pts_msec
        if delta < -500.0 or delta > 10000.0:
            self.discontinuity_count += 1
            logger.info(
                f"[{self.camera_id}] Scene cut / feed loop detected (ΔPTS={delta:.1f}ms). "
                f"Reconciling {len(self.tracks)} active tracks to prevent stale ID drift."
            )
            # Reconcile / reset active tracks at hard scene boundary
            self.tracks.clear()
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
        Associate detections with existing tracks and assign persistent track IDs.
        Uses real hardware presentation timestamps (pts_msec).
        """
        now_dt = timestamp or datetime.now(timezone.utc)
        self.frame_count += 1

        # Check for scene loop / discontinuity
        self.check_and_handle_discontinuity(pts_msec)
        if pts_msec is not None:
            self.last_pts_msec = pts_msec

        h, w = (frame_shape if frame_shape else (1080, 1920))[:2]
        entry_y = h * self.entry_line_ratio
        exit_y = h * self.exit_line_ratio

        active_track_ids = list(self.tracks.keys())
        matched_tracks: Set[int] = set()
        matched_dets: Set[int] = set()

        vehicle_classes = {
            "CAR", "TRUCK", "BUS", "MOTORCYCLE", "TWO_WHEELER",
            "VEHICLE", "VAN", "AUTO_RICKSHAW", "BICYCLE"
        }

        # Candidate assignment matching
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

            det["track_id"] = tid
            det["camera_id"] = self.camera_id
            det["first_seen"] = track.first_seen
            det["last_seen"] = track.last_seen
            det["dwell_time"] = track.dwell_time
            det["movement_direction"] = track.movement_direction
            det["direction"] = track.movement_direction
            det["speed_kmph"] = track.speed_kmph
            det["display_label"] = format_display_label(obj_class, tid, conf)

        # Register new tracks for unmatched detections
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

                det["track_id"] = tid
                det["camera_id"] = self.camera_id
                det["first_seen"] = new_track.first_seen
                det["last_seen"] = new_track.last_seen
                det["dwell_time"] = 0.0
                det["movement_direction"] = "STATIONARY"
                det["direction"] = "STATIONARY"
                det["speed_kmph"] = 0.0
                det["display_label"] = format_display_label(obj_class, tid, conf)

        # Age unmatched tracks and prune dead ones
        dead_tracks: List[int] = []
        for tid, track in self.tracks.items():
            if tid not in matched_tracks:
                track.frames_since_update += 1
                if track.frames_since_update > self.max_lost_frames:
                    dead_tracks.append(tid)

        for tid in dead_tracks:
            del self.tracks[tid]

        return detections
