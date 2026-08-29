"""
YOLO26 Multi-Object Tracking & Trajectory Engine
Maintains persistent track IDs, movement direction, dwell time, and velocity estimates within individual camera streams.
Strictly isolated per-camera tracking without facial recognition or cross-camera assumptions.
"""
from collections import deque
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union


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
    """
    Format standard display label as requested:
    e.g. 'Person #12 | 96%', 'Car #7 | 91%'
    """
    cleaned = (obj_class or "OBJECT").replace("_", " ").title()
    pct = round(confidence * 100)
    return f"{cleaned} #{track_id} | {pct}%"


class Track:
    """Internal state for a single tracked object trajectory."""

    def __init__(
        self,
        track_id: int,
        camera_id: str,
        bbox: Union[Dict[str, float], List[float], Tuple[float, ...]],
        obj_class: str,
        conf: float,
        timestamp: Optional[datetime] = None,
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

        cx = (self.bbox["x1"] + self.bbox["x2"]) / 2.0
        cy = (self.bbox["y1"] + self.bbox["y2"]) / 2.0
        self.centroid: Dict[str, float] = {"x": round(cx, 1), "y": round(cy, 1)}

        self.history: deque[Dict[str, Any]] = deque(maxlen=max_history)
        self.history.append({"x": round(cx, 1), "y": round(cy, 1), "timestamp": self.first_seen})

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
    ) -> None:
        now_dt = timestamp or datetime.now(timezone.utc)
        now_epoch = now_dt.timestamp()
        now_iso = now_dt.isoformat()

        self.bbox = _normalize_bbox(bbox)
        self.confidence = _safe_float(conf, 0.0)
        self.last_seen_epoch = now_epoch
        self.last_seen = now_iso
        self.dwell_time = round(max(0.0, now_epoch - self.first_seen_epoch), 1)

        cx = (self.bbox["x1"] + self.bbox["x2"]) / 2.0
        cy = (self.bbox["y1"] + self.bbox["y2"]) / 2.0

        if self.history:
            prev = self.history[-1]
            dx = cx - prev["x"]
            dy = cy - prev["y"]
            dist_px = math.sqrt(dx * dx + dy * dy)

            # Determine movement direction and speed
            if dist_px < 3.0:
                self.movement_direction = "STATIONARY"
                self.speed_kmph = 0.0
            else:
                self.speed_kmph = round(min(120.0, max(5.0, dist_px * 2.2)), 1)
                if abs(dy) > abs(dx):
                    self.movement_direction = "SOUTHBOUND" if dy > 0 else "NORTHBOUND"
                else:
                    self.movement_direction = "EASTBOUND" if dx > 0 else "WESTBOUND"

        self.history.append({"x": round(cx, 1), "y": round(cy, 1), "timestamp": now_iso})
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
            "dwell_time": self.dwell_time,
            "movement_direction": self.movement_direction,
            "speed_kmph": self.speed_kmph,
            "display_label": format_display_label(self.object_class, self.track_id, self.confidence),
        }


class YOLO26Tracker:
    """
    Multi-Object Tracker supporting IoU association, dwell time tracking, and directional motion analysis.
    """

    def __init__(
        self,
        camera_id: str = "CAM-GLOBAL",
        iou_threshold: float = 0.30,
        max_lost_frames: int = 15,
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

        self.total_entered: int = 0
        self.total_exited: int = 0
        self.class_breakdown: Dict[str, Dict[str, int]] = {}

    def reset(self) -> None:
        """Reset tracker state and clear all active tracks and counters."""
        self._next_track_id = 1
        self.tracks.clear()
        self.frame_count = 0
        self.total_entered = 0
        self.total_exited = 0
        self.class_breakdown.clear()

    def update(
        self,
        detections: List[Dict[str, Any]],
        frame_shape: Optional[Tuple[int, int]] = None,
        timestamp: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Associate detections with existing tracks and assign persistent track IDs.
        Attaches track_id, first_seen, last_seen, dwell_time, movement_direction, and display_label.
        """
        now_dt = timestamp or datetime.now(timezone.utc)
        self.frame_count += 1
        h, w = (frame_shape if frame_shape else (1080, 1920))[:2]
        entry_y = h * self.entry_line_ratio
        exit_y = h * self.exit_line_ratio

        active_track_ids = list(self.tracks.keys())
        matched_tracks: Set[int] = set()
        matched_dets: Set[int] = set()

        vehicle_classes = {
            "CAR",
            "TRUCK",
            "BUS",
            "MOTORCYCLE",
            "TWO_WHEELER",
            "VEHICLE",
            "VAN",
            "AUTO_RICKSHAW",
        }

        # Build candidate match list (iou, det_idx, track_id)
        candidates: List[Tuple[float, int, int]] = []
        for det_idx, det in enumerate(detections):
            bbox = det.get("bounding_box") or det.get("bbox") or {}
            obj_class = (det.get("object_class") or det.get("class_name") or "OBJECT").upper()

            for tid in active_track_ids:
                track = self.tracks[tid]

                # Ensure class consistency (prevent track id hopping across classes)
                if track.object_class != obj_class:
                    # Allow vehicle subtype flexibility (e.g. CAR/TRUCK/BUS)
                    if not (track.object_class in vehicle_classes and obj_class in vehicle_classes):
                        continue

                iou = compute_iou(bbox, track.bbox)
                if iou >= self.iou_threshold:
                    candidates.append((iou, det_idx, tid))

        # Sort candidate matches by highest IoU first for optimal greedy assignment
        candidates.sort(key=lambda x: x[0], reverse=True)

        for iou, det_idx, tid in candidates:
            if det_idx in matched_dets or tid in matched_tracks:
                continue

            det = detections[det_idx]
            bbox = det.get("bounding_box") or det.get("bbox") or {}
            obj_class = (det.get("object_class") or det.get("class_name") or "OBJECT").upper()
            conf = _safe_float(det.get("confidence"), 0.0)

            track = self.tracks[tid]
            track.update(bbox, conf, timestamp=now_dt)

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
                tid = self._next_track_id
                self._next_track_id += 1
                obj_class = (det.get("object_class") or det.get("class_name") or "OBJECT").upper()
                conf = _safe_float(det.get("confidence"), 0.0)
                bbox = det.get("bounding_box") or det.get("bbox") or {}

                new_track = Track(
                    track_id=tid,
                    camera_id=self.camera_id,
                    bbox=bbox,
                    obj_class=obj_class,
                    conf=conf,
                    timestamp=now_dt,
                )
                self.tracks[tid] = new_track

                det["track_id"] = tid
                det["camera_id"] = self.camera_id
                det["first_seen"] = new_track.first_seen
                det["last_seen"] = new_track.last_seen
                det["dwell_time"] = 0.0
                det["movement_direction"] = "STATIONARY"
                det["direction"] = "STATIONARY"
                det["speed_kmph"] = new_track.speed_kmph
                det["display_label"] = format_display_label(obj_class, tid, conf)

        # Check tripwire flow
        for tid, track in list(self.tracks.items()):
            if len(track.history) >= 2:
                prev_y = track.history[-2]["y"]
                curr_y = track.history[-1]["y"]
                cls = track.object_class
                if cls not in self.class_breakdown:
                    self.class_breakdown[cls] = {"entered": 0, "exited": 0}

                if prev_y < entry_y <= curr_y and not track.entry_logged:
                    track.entry_logged = True
                    self.total_entered += 1
                    self.class_breakdown[cls]["entered"] += 1

                if prev_y < exit_y <= curr_y and not track.exit_logged:
                    track.exit_logged = True
                    self.total_exited += 1
                    self.class_breakdown[cls]["exited"] += 1

        # Cull stale tracks
        for tid in list(self.tracks.keys()):
            if tid not in matched_tracks:
                self.tracks[tid].frames_since_update += 1
                if self.tracks[tid].frames_since_update > self.max_lost_frames:
                    del self.tracks[tid]

        return detections

    def get_stats(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "total_entered": self.total_entered,
            "total_exited": self.total_exited,
            "active_tracks_count": len(self.tracks),
            "class_breakdown": self.class_breakdown,
        }

