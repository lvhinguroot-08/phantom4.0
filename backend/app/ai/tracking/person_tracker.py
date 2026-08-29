"""
PHANTOM YOLO26 Person Tracking & Re-Identification (Re-ID) Module
Features persistent IDs, dwell time calculation, compass direction, and tripwire crossing.
"""
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import math
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

import cv2
import numpy as np
from pydantic import BaseModel, Field

from app.ai.yolo26.detector import get_detector


# ------------------------------------------------------------------------------
# 1. Models & Output Schemas
# ------------------------------------------------------------------------------

class ReIDDescriptor(BaseModel):
    """Re-identification embedding signature for cross-camera matching."""
    feature_vector: Optional[List[float]] = Field(None, description="Normalized appearance embedding")
    aspect_ratio: float = Field(..., description="Height-to-width ratio")
    dominant_upper_color: str = Field("UNKNOWN", description="Estimated upper torso color (HEX/name)")
    dominant_lower_color: str = Field("UNKNOWN", description="Estimated lower body color (HEX/name)")
    quality_score: float = Field(..., description="Crop resolution quality score (0-1)")


class TrackedPerson(BaseModel):
    person_id: str
    track_id: int
    confidence: float
    bounding_box: Dict[str, float]
    centroid: Dict[str, float]
    foot_point: Dict[str, float]

    # Motion & Direction
    direction: str = "STATIONARY"
    heading_degrees: Optional[float] = None
    velocity_px_sec: float = 0.0

    # Dwell & Loitering
    first_seen: str
    last_seen: str
    dwell_time_seconds: float = 0.0
    is_loitering: bool = False

    # Tripwire & Crossing
    has_crossed_line: bool = False
    crossing_direction: Optional[str] = None
    crossing_timestamp: Optional[str] = None

    # Trajectory & Re-ID
    reid: ReIDDescriptor
    trajectory: List[Dict[str, float]] = Field(default_factory=list)


class PersonTrackingResult(BaseModel):
    frame_id: int
    timestamp: str
    camera_id: str
    active_persons_count: int
    loitering_count: int
    total_inbound: int
    total_outbound: int
    persons: List[TrackedPerson]


# ------------------------------------------------------------------------------
# 2. Re-ID Feature Extractor
# ------------------------------------------------------------------------------

def extract_person_reid_descriptor(crop_bgr: np.ndarray) -> ReIDDescriptor:
    """Extract color histograms and spatial aspect ratios from person crop."""
    h, w = crop_bgr.shape[:2]
    aspect_ratio = round(float(h) / max(1.0, float(w)), 2)
    quality = min(1.0, round((h * w) / (128 * 64), 2))

    if h < 20 or w < 10:
        return ReIDDescriptor(
            feature_vector=None,
            aspect_ratio=aspect_ratio,
            dominant_upper_color="UNKNOWN",
            dominant_lower_color="UNKNOWN",
            quality_score=0.1,
        )

    upper_torso = crop_bgr[: int(h * 0.5), :]
    lower_body = crop_bgr[int(h * 0.5) :, :]

    def dominant_color(img_patch: np.ndarray) -> str:
        avg_bgr = np.mean(img_patch, axis=(0, 1))
        b, g, r = [int(v) for v in avg_bgr]
        return f"#{r:02x}{g:02x}{b:02x}"

    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [8, 4], [0, 180, 0, 256])
    cv2.normalize(hist, hist)
    feature_vector = [round(float(v), 4) for v in hist.flatten().tolist()]

    return ReIDDescriptor(
        feature_vector=feature_vector,
        aspect_ratio=aspect_ratio,
        dominant_upper_color=dominant_color(upper_torso),
        dominant_lower_color=dominant_color(lower_body),
        quality_score=quality,
    )


def line_crosses_segment(p1: Tuple[float, float], p2: Tuple[float, float], l1: Tuple[float, float], l2: Tuple[float, float]) -> bool:
    """Determine if movement vector (p1 -> p2) intersects with boundary line (l1 -> l2)."""
    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    return (ccw(p1, l1, l2) != ccw(p2, l1, l2)) and (ccw(p1, p2, l1) != ccw(p1, p2, l2))


# ------------------------------------------------------------------------------
# 3. Person Track State
# ------------------------------------------------------------------------------

class PersonTrack:
    crossing_direction: Optional[str]
    crossing_timestamp: Optional[str]

    def __init__(self, track_id: int, bbox: Dict[str, float], conf: float, crop_bgr: np.ndarray):
        self.track_id = track_id
        self.person_id = f"PER-{uuid.uuid4().hex[:8].upper()}"
        self.bbox = bbox
        self.confidence = conf
        self.reid = extract_person_reid_descriptor(crop_bgr)

        self.created_epoch = time.time()
        self.last_seen_epoch = self.created_epoch
        self.first_seen_iso = datetime.now(timezone.utc).isoformat()
        self.last_seen_iso = self.first_seen_iso

        self.frames_unseen = 0
        self.trajectory: deque = deque(maxlen=40)

        cx = (bbox["x1"] + bbox["x2"]) / 2.0
        foot_y = bbox["y2"]

        self.centroid = (cx, (bbox["y1"] + bbox["y2"]) / 2.0)
        self.foot_point = (cx, foot_y)
        self.trajectory.append({"x": round(cx, 1), "y": round(foot_y, 1), "t": self.created_epoch})

        self.has_crossed = False
        self.crossing_direction: Optional[str] = None
        self.crossing_timestamp: Optional[str] = None

    def update(self, bbox: Dict[str, float], conf: float, crop_bgr: np.ndarray):
        self.bbox = bbox
        self.confidence = conf
        self.last_seen_epoch = time.time()
        self.last_seen_iso = datetime.now(timezone.utc).isoformat()
        self.frames_unseen = 0

        cx = (bbox["x1"] + bbox["x2"]) / 2.0
        foot_y = bbox["y2"]
        self.centroid = (cx, (bbox["y1"] + bbox["y2"]) / 2.0)
        self.foot_point = (cx, foot_y)
        self.trajectory.append({"x": round(cx, 1), "y": round(foot_y, 1), "t": self.last_seen_epoch})

        if conf > 0.70:
            self.reid = extract_person_reid_descriptor(crop_bgr)

    def calculate_motion(self) -> Tuple[str, Optional[float], float]:
        if len(self.trajectory) < 4:
            return "STATIONARY", None, 0.0

        p_start = self.trajectory[0]
        p_end = self.trajectory[-1]
        dt = max(0.1, p_end["t"] - p_start["t"])

        dx = p_end["x"] - p_start["x"]
        dy = p_end["y"] - p_start["y"]
        dist = math.sqrt(dx**2 + dy**2)

        if dist < 12.0:
            return "STATIONARY", None, round(dist / dt, 1)

        angle_rad = math.atan2(dy, dx)
        angle_deg = (math.degrees(angle_rad) + 360) % 360

        directions = ["EAST", "SOUTHEAST", "SOUTH", "SOUTHWEST", "WEST", "NORTHWEST", "NORTH", "NORTHEAST"]
        idx = int((angle_deg + 22.5) / 45.0) % 8

        return directions[idx], round(angle_deg, 1), round(dist / dt, 1)


# ------------------------------------------------------------------------------
# 4. YOLO26 Person Tracker Engine
# ------------------------------------------------------------------------------

class YOLO26PersonTracker:
    def __init__(
        self,
        camera_id: str = "CAM-01",
        loitering_threshold_seconds: float = 30.0,
        tripwire_line: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None,
    ):
        self.camera_id = camera_id
        self.loitering_threshold = loitering_threshold_seconds
        self.tripwire_line = tripwire_line
        self.tracks: Dict[int, PersonTrack] = {}
        self._next_id = 1
        self.frame_id = 0

        self.total_inbound = 0
        self.total_outbound = 0

    def process_frame(self, frame_bgr: np.ndarray) -> PersonTrackingResult:
        self.frame_id += 1
        h, w = frame_bgr.shape[:2]
        line = self.tripwire_line or ((0.0, float(h * 0.5)), (float(w), float(h * 0.5)))

        detector = get_detector()
        detections = detector.detect(frame_bgr, camera_id=self.camera_id)
        person_dets = [d for d in detections if d.get("object_class") == "PERSON"]

        matched_tracks = set()
        matched_dets = set()

        for det_idx, det in enumerate(person_dets):
            bbox = det["bounding_box"]
            bx1, by1 = max(0, int(bbox["x1"])), max(0, int(bbox["y1"]))
            bx2, by2 = min(w, int(bbox["x2"])), min(h, int(bbox["y2"]))
            crop = frame_bgr[by1:by2, bx1:bx2] if by2 > by1 and bx2 > bx1 else np.zeros((10, 10, 3), dtype=np.uint8)

            best_match_id = None
            best_dist = 60.0

            cx = (bbox["x1"] + bbox["x2"]) / 2.0
            cy = (bbox["y1"] + bbox["y2"]) / 2.0

            for tid, track in self.tracks.items():
                if tid in matched_tracks:
                    continue
                dist = math.sqrt((cx - track.centroid[0])**2 + (cy - track.centroid[1])**2)
                if dist < best_dist:
                    best_dist = dist
                    best_match_id = tid

            if best_match_id is not None:
                self.tracks[best_match_id].update(bbox, det["confidence"], crop)
                matched_tracks.add(best_match_id)
                matched_dets.add(det_idx)
            else:
                tid = self._next_id
                self._next_id += 1
                self.tracks[tid] = PersonTrack(tid, bbox, det["confidence"], crop)
                matched_dets.add(det_idx)

        now_epoch = time.time()
        output_persons: List[TrackedPerson] = []
        loitering_count = 0

        for tid, track in list(self.tracks.items()):
            if tid not in matched_tracks:
                track.frames_unseen += 1

            if track.frames_unseen > 20:
                del self.tracks[tid]
                continue

            dwell_sec = round(now_epoch - track.created_epoch, 1)
            is_loiter = dwell_sec >= self.loitering_threshold
            if is_loiter:
                loitering_count += 1

            if len(track.trajectory) >= 2 and not track.has_crossed:
                p_prev = (track.trajectory[-2]["x"], track.trajectory[-2]["y"])
                p_curr = (track.trajectory[-1]["x"], track.trajectory[-1]["y"])

                if line_crosses_segment(p_prev, p_curr, line[0], line[1]):
                    track.has_crossed = True
                    track.crossing_timestamp = datetime.now(timezone.utc).isoformat()
                    
                    if p_curr[1] > p_prev[1]:
                        track.crossing_direction = "INBOUND"
                        self.total_inbound += 1
                    else:
                        track.crossing_direction = "OUTBOUND"
                        self.total_outbound += 1

            dir_str, angle, vel = track.calculate_motion()

            output_persons.append(
                TrackedPerson(
                    person_id=track.person_id,
                    track_id=track.track_id,
                    confidence=track.confidence,
                    bounding_box=track.bbox,
                    centroid={"x": track.centroid[0], "y": track.centroid[1]},
                    foot_point={"x": track.foot_point[0], "y": track.foot_point[1]},
                    direction=dir_str,
                    heading_degrees=angle,
                    velocity_px_sec=vel,
                    first_seen=track.first_seen_iso,
                    last_seen=track.last_seen_iso,
                    dwell_time_seconds=dwell_sec,
                    is_loitering=is_loiter,
                    has_crossed_line=track.has_crossed,
                    crossing_direction=track.crossing_direction,
                    crossing_timestamp=track.crossing_timestamp,
                    reid=track.reid,
                    trajectory=[{"x": p["x"], "y": p["y"]} for p in track.trajectory],
                )
            )

        return PersonTrackingResult(
            frame_id=self.frame_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            camera_id=self.camera_id,
            active_persons_count=len(output_persons),
            loitering_count=loitering_count,
            total_inbound=self.total_inbound,
            total_outbound=self.total_outbound,
            persons=output_persons,
        )
