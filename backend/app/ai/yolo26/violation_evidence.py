"""
Violation Evidence Capture Service
Saves annotated visual evidence snapshots for confirmed traffic violations.
Annotates vehicle bounding boxes, rider crops, and violation tags.
"""
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

import cv2
import numpy as np

from .rider_association import VehicleOccupancyRecord
from .schemas import TrafficViolationEvent

logger = logging.getLogger("phantom.ai.yolo26.violation_evidence")


class ViolationEvidenceService:
    """
    Renders tactical evidence overlays on camera frames and persists them to disk.
    """

    def __init__(self, output_dir: str = "static/evidence", base_url: str = "/static/evidence"):
        # Resolve path relative to backend root
        backend_root = Path(__file__).resolve().parent.parent.parent.parent
        self.output_dir = backend_root / output_dir
        self.base_url = base_url.rstrip("/")
        self._ensure_output_dir()

    def _ensure_output_dir(self) -> None:
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as err:
            logger.warning(f"Could not create evidence directory {self.output_dir}: {err}")

    def _denormalize_box(self, bbox: Dict[str, float], w: int, h: int) -> List[int]:
        """Converts box coordinates to absolute frame pixel coordinates [x1, y1, x2, y2]."""
        x1 = float(bbox.get("x1", 0.0))
        y1 = float(bbox.get("y1", 0.0))
        x2 = float(bbox.get("x2", 0.0))
        y2 = float(bbox.get("y2", 0.0))

        if x2 <= 100.0 and y2 <= 100.0 and (x2 > 1.0 or y2 > 1.0) and (w > 100 and h > 100):
            # Percentage coordinates (0-100%)
            px1 = int((x1 / 100.0) * w)
            py1 = int((y1 / 100.0) * h)
            px2 = int((x2 / 100.0) * w)
            py2 = int((y2 / 100.0) * h)
        elif x2 <= 1.0 and y2 <= 1.0:
            px1 = int(x1 * w)
            py1 = int(y1 * h)
            px2 = int(x2 * w)
            py2 = int(y2 * h)
        else:
            px1 = int(x1)
            py1 = int(y1)
            px2 = int(x2)
            py2 = int(y2)

        px1 = max(0, min(w - 1, px1))
        py1 = max(0, min(h - 1, py1))
        px2 = max(px1 + 1, min(w, px2))
        py2 = max(py1 + 1, min(h, py2))
        return [px1, py1, px2, py2]

    def capture_evidence(
        self,
        frame: np.ndarray,
        violation: TrafficViolationEvent,
        occupancy_record: Optional[VehicleOccupancyRecord] = None,
    ) -> Optional[str]:
        """
        Renders tactical annotations onto frame and saves JPEG snapshot.
        Returns relative evidence URL if successful.
        """
        if frame is None or frame.size == 0:
            return None

        h, w = frame.shape[:2]
        annotated = frame.copy()

        # Colors (BGR)
        COLOR_VEHICLE = (0, 0, 230)      # Bright Red
        COLOR_RIDER = (200, 50, 180)     # Magenta / Purple
        COLOR_HEAD = (0, 220, 255)       # Gold / Yellow
        COLOR_TEXT = (255, 255, 255)
        COLOR_BG = (10, 10, 20)

        # Draw Header Banner
        header_text = f"PHANTOM AI EVIDENCE // {violation.violation_type} // CAM: {violation.camera_id}"
        cv2.rectangle(annotated, (0, 0), (w, 38), COLOR_BG, -1)
        cv2.putText(
            annotated,
            header_text,
            (14, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )

        # Timestamp on right
        time_text = violation.timestamp
        cv2.putText(
            annotated,
            time_text,
            (w - 240, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (180, 180, 180),
            1,
            cv2.LINE_AA,
        )

        # Draw vehicle box if available
        if occupancy_record and occupancy_record.vehicle_box:
            vx1, vy1, vx2, vy2 = self._denormalize_box(occupancy_record.vehicle_box, w, h)
            cv2.rectangle(annotated, (vx1, vy1), (vx2, vy2), COLOR_VEHICLE, 2)
            v_label = f"{violation.vehicle_type} #{violation.vehicle_track_id} (Occ: {occupancy_record.occupant_count})"
            cv2.putText(
                annotated,
                v_label,
                (vx1, max(15, vy1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                COLOR_VEHICLE,
                2,
                cv2.LINE_AA,
            )

            # Draw rider boxes
            for rider in occupancy_record.riders:
                rx1, ry1, rx2, ry2 = self._denormalize_box(rider.bounding_box, w, h)
                cv2.rectangle(annotated, (rx1, ry1), (rx2, ry2), COLOR_RIDER, 2)
                r_label = f"Rider #{rider.person_track_id}"
                cv2.putText(
                    annotated,
                    r_label,
                    (rx1, max(15, ry1 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    COLOR_RIDER,
                    1,
                    cv2.LINE_AA,
                )

                if rider.head_box:
                    hx1, hy1, hx2, hy2 = self._denormalize_box(rider.head_box, w, h)
                    cv2.rectangle(annotated, (hx1, hy1), (hx2, hy2), COLOR_HEAD, 2)
                    if violation.violation_type == "NO_HELMET" and rider.person_track_id == violation.rider_track_id:
                        cv2.putText(
                            annotated,
                            "NO HELMET",
                            (hx1, max(12, hy1 - 4)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.45,
                            (0, 0, 255),
                            2,
                            cv2.LINE_AA,
                        )

        # Draw linked license plate if recognized
        if violation.vehicle_plate:
            plate_str = f"REG: {violation.vehicle_plate}"
            if violation.plate_confidence:
                plate_str += f" ({round(violation.plate_confidence * 100)}%)"
            cv2.rectangle(annotated, (10, h - 38), (320, h - 8), COLOR_BG, -1)
            cv2.rectangle(annotated, (10, h - 38), (320, h - 8), (0, 255, 0), 1)
            cv2.putText(
                annotated,
                plate_str,
                (18, h - 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

        # Save to disk
        timestamp_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        uid_slug = uuid.uuid4().hex[:6]
        vtype_slug = violation.violation_type.lower()
        cam_slug = violation.camera_id.replace("/", "_").replace("\\", "_")
        filename = f"evid_{vtype_slug}_{cam_slug}_v{violation.vehicle_track_id}_{timestamp_slug}_{uid_slug}.jpg"

        file_path = self.output_dir / filename
        try:
            cv2.imwrite(str(file_path), annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
            evidence_url = f"{self.base_url}/{filename}"
            violation.evidence_reference = evidence_url
            logger.info(f"Captured violation evidence: {file_path}")
            return evidence_url
        except Exception as err:
            logger.warning(f"Failed to write evidence snapshot to {file_path}: {err}")
            return None


# Global singleton instance
_evidence_service_instance: Optional[ViolationEvidenceService] = None


def get_evidence_service() -> ViolationEvidenceService:
    global _evidence_service_instance
    if _evidence_service_instance is None:
        _evidence_service_instance = ViolationEvidenceService()
    return _evidence_service_instance
