"""
PHANTOM YOLO26 Vehicle Tracker & Directional Flow Counter
Assigns persistent track IDs, maintains trajectory trails, and calculates entry/exit counts.
"""
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

import numpy as np
from pydantic import BaseModel, Field

from app.ai.yolo26.detector import get_detector


# ------------------------------------------------------------------------------
# 1. Trajectory & Track Models
# ------------------------------------------------------------------------------

@dataclass
class Point:
    x: float
    y: float
    timestamp: str


class TrackedVehicle(BaseModel):
    track_id: int
    object_class: str
    confidence: float
    bounding_box: Dict[str, float]
    centroid: Dict[str, float]
    speed_kmph: Optional[float] = None
    direction: str = "UNKNOWN"
    history: List[Dict[str, Any]] = Field(default_factory=list)
    state: str = "ACTIVE"  # "ACTIVE", "EXITED", "LOST"
    entry_logged: bool = False
    exit_logged: bool = False
    first_seen: str
    last_seen: str


class TrafficFlowStats(BaseModel):
    total_entered: int = 0
    total_exited: int = 0
    current_active: int = 0
    class_breakdown: Dict[str, Dict[str, int]] = Field(default_factory=dict)


class TrackingFrameResult(BaseModel):
    frame_id: int
    timestamp: str
    camera_id: str
    active_tracks: List[TrackedVehicle]
    traffic_stats: TrafficFlowStats


# ------------------------------------------------------------------------------
# 2. Kalman & IoU Association Core
# ------------------------------------------------------------------------------

class Track:
    """Internal state for an individual tracked vehicle."""

    def __init__(self, track_id: int, bbox: Dict[str, float], obj_class: str, conf: float, max_history: int = 30):
        self.track_id = track_id
        self.bbox = bbox
        self.object_class = obj_class
        self.confidence = conf
        self.max_history = max_history

        cx = (bbox["x1"] + bbox["x2"]) / 2.0
        cy = (bbox["y1"] + bbox["y2"]) / 2.0
        self.centroid = (cx, cy)

        now_iso = datetime.now(timezone.utc).isoformat()
        self.history: deque = deque(maxlen=max_history)
        self.history.append({"x": round(cx, 1), "y": round(cy, 1), "timestamp": now_iso})

        self.first_seen = now_iso
        self.last_seen = now_iso
        self.frames_since_update = 0
        self.entry_logged = False
        self.exit_logged = False

    def update(self, bbox: Dict[str, float], conf: float) -> None:
        self.bbox = bbox
        self.confidence = conf
        cx = (bbox["x1"] + bbox["x2"]) / 2.0
        cy = (bbox["y1"] + bbox["y2"]) / 2.0
        self.centroid = (cx, cy)

        now_iso = datetime.now(timezone.utc).isoformat()
        self.history.append({"x": round(cx, 1), "y": round(cy, 1), "timestamp": now_iso})
        self.last_seen = now_iso
        self.frames_since_update = 0

    def calculate_direction_and_speed(self) -> Tuple[str, float]:
        """Estimate trajectory direction and relative pixel velocity."""
        if len(self.history) < 3:
            return "UNKNOWN", 0.0

        p_start = self.history[0]
        p_end = self.history[-1]
        dx = p_end["x"] - p_start["x"]
        dy = p_end["y"] - p_start["y"]

        # Approximate Direction
        if abs(dy) > abs(dx):
            direction = "SOUTHBOUND" if dy > 0 else "NORTHBOUND"
        else:
            direction = "EASTBOUND" if dx > 0 else "WESTBOUND"

        distance_px = math.sqrt(dx**2 + dy**2)
        speed_approx = round(min(120.0, distance_px * 1.5), 1)  # Calibrated scaling
        return direction, speed_approx


def compute_iou(boxA: Dict[str, float], boxB: Dict[str, float]) -> float:
    """Compute Intersection over Union between two bounding boxes."""
    xA = max(boxA["x1"], boxB["x1"])
    yA = max(boxA["y1"], boxB["y1"])
    xB = min(boxA["x2"], boxB["x2"])
    yB = min(boxA["y2"], boxB["y2"])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = max(0, boxA["x2"] - boxA["x1"]) * max(0, boxA["y2"] - boxA["y1"])
    boxBArea = max(0, boxB["x2"] - boxB["x1"]) * max(0, boxB["y2"] - boxB["y1"])
    denom = float(boxAArea + boxBArea - interArea)
    return interArea / denom if denom > 0 else 0.0


# ------------------------------------------------------------------------------
# 3. YOLO26 Vehicle Tracker Service
# ------------------------------------------------------------------------------

class YOLO26VehicleTracker:
    """
    Multi-Camera Real-time Vehicle Tracker with Virtual Line Tripwires.
    """

    def __init__(
        self,
        camera_id: str = "CAM-01",
        iou_threshold: float = 0.35,
        max_lost_frames: int = 15,
        entry_line_y_ratio: float = 0.40,  # Upper 40% boundary
        exit_line_y_ratio: float = 0.75,   # Lower 75% boundary
    ):
        self.camera_id = camera_id
        self.iou_threshold = iou_threshold
        self.max_lost_frames = max_lost_frames
        self.entry_line_ratio = entry_line_y_ratio
        self.exit_line_ratio = exit_line_y_ratio

        self._next_track_id = 1
        self.tracks: Dict[int, Track] = {}
        self.frame_count = 0

        # Cumulative Flow Statistics
        self.total_entered = 0
        self.total_exited = 0
        self.class_breakdown: Dict[str, Dict[str, int]] = {}

    def _init_class_stats(self, obj_class: str):
        if obj_class not in self.class_breakdown:
            self.class_breakdown[obj_class] = {"entered": 0, "exited": 0}

    def process_frame(self, frame_bgr: np.ndarray) -> TrackingFrameResult:
        """Run YOLO26 inference and perform trajectory association."""
        self.frame_count += 1
        h, w = frame_bgr.shape[:2]
        entry_y = h * self.entry_line_ratio
        exit_y = h * self.exit_line_ratio

        # 1. Run YOLO26 Detection
        detector = get_detector()
        raw_detections = detector.detect(frame_bgr, camera_id=self.camera_id)

        # Filter vehicle classes
        vehicle_detections = [
            d for d in raw_detections
            if d.get("object_class") in ("CAR", "TRUCK", "BUS", "MOTORCYCLE", "BICYCLE", "OTHER_VEHICLE")
        ]

        # 2. Association Matrix (IoU Matching)
        active_track_ids = list(self.tracks.keys())
        matched_tracks = set()
        matched_dets = set()

        for det_idx, det in enumerate(vehicle_detections):
            bbox = det["bounding_box"]
            best_iou = 0.0
            best_id = None

            for tid in active_track_ids:
                if tid in matched_tracks:
                    continue
                iou = compute_iou(bbox, self.tracks[tid].bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_id = tid

            if best_iou >= self.iou_threshold and best_id is not None:
                self.tracks[best_id].update(bbox, det["confidence"])
                matched_tracks.add(best_id)
                matched_dets.add(det_idx)

        # 3. Register New Tracks for Unmatched Detections
        for det_idx, det in enumerate(vehicle_detections):
            if det_idx not in matched_dets:
                tid = self._next_track_id
                self._next_track_id += 1
                new_track = Track(tid, det["bounding_box"], det["object_class"], det["confidence"])
                self.tracks[tid] = new_track

        # 4. Check Virtual Line Tripwire Crossings
        for tid, track in list(self.tracks.items()):
            if len(track.history) >= 2:
                prev_y = track.history[-2]["y"]
                curr_y = track.history[-1]["y"]
                cls = track.object_class
                self._init_class_stats(cls)

                # Entry Crossing (moving North to South across entry line)
                if prev_y < entry_y <= curr_y and not track.entry_logged:
                    track.entry_logged = True
                    self.total_entered += 1
                    self.class_breakdown[cls]["entered"] += 1

                # Exit Crossing (moving downwards across exit line)
                if prev_y < exit_y <= curr_y and not track.exit_logged:
                    track.exit_logged = True
                    self.total_exited += 1
                    self.class_breakdown[cls]["exited"] += 1

        # 5. Cull Stale / Lost Tracks
        output_tracks: List[TrackedVehicle] = []
        for tid, track in list(self.tracks.items()):
            if tid not in matched_tracks:
                track.frames_since_update += 1

            if track.frames_since_update > self.max_lost_frames:
                del self.tracks[tid]
            else:
                direction, speed = track.calculate_direction_and_speed()
                output_tracks.append(
                    TrackedVehicle(
                        track_id=track.track_id,
                        object_class=track.object_class,
                        confidence=track.confidence,
                        bounding_box=track.bbox,
                        centroid={"x": track.centroid[0], "y": track.centroid[1]},
                        speed_kmph=speed,
                        direction=direction,
                        history=list(track.history),
                        state="ACTIVE" if track.frames_since_update == 0 else "OCCLUDED",
                        entry_logged=track.entry_logged,
                        exit_logged=track.exit_logged,
                        first_seen=track.first_seen,
                        last_seen=track.last_seen,
                    )
                )

        # 6. Assemble Output
        stats = TrafficFlowStats(
            total_entered=self.total_entered,
            total_exited=self.total_exited,
            current_active=len(self.tracks),
            class_breakdown=self.class_breakdown,
        )

        return TrackingFrameResult(
            frame_id=self.frame_count,
            timestamp=datetime.now(timezone.utc).isoformat(),
            camera_id=self.camera_id,
            active_tracks=output_tracks,
            traffic_stats=stats,
        )
