"""
PHANTOM Unified YOLO26 + ANPR Pipeline
Combines YOLO26 vehicle detection with existing OCR processors and Gujarat RTO normalization.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

import cv2
import numpy as np
from pydantic import BaseModel, Field

from app.ai.anpr.normalize import (
    extract_plate_structure,
    is_gujarat_plate,
    looks_like_indian_plate,
    normalize_plate_text,
)
from app.ai.anpr.ocr import build_ocr_processor
from app.ai.yolo26.detector import get_detector

logger = logging.getLogger("phantom.ai.anpr")


# ------------------------------------------------------------------------------
# 1. Output Schemas
# ------------------------------------------------------------------------------

class PlateDetails(BaseModel):
    raw_text: str = Field(..., description="Raw unprocessed OCR text output")
    normalized_plate: str = Field(..., description="Cleaned Gujarat/Indian registration number")
    confidence: float = Field(..., description="OCR read confidence score (0.0 to 1.0)")
    bounding_box: Optional[Dict[str, float]] = Field(None, description="Plate crop coordinates")
    rto_jurisdiction: Optional[str] = Field(None, description="Associated RTO (e.g., Surat, Ahmedabad)")
    is_gujarat: bool = Field(False, description="Whether registration is GJ state")
    format: str = Field("STANDARD", description="STANDARD, BHARAT_SERIES, or UNKNOWN")


class VehicleWithPlateDetection(BaseModel):
    detection_id: str
    camera_id: str
    timestamp: str
    vehicle_type: str
    confidence: float
    bounding_box: Dict[str, float]
    plate: Optional[PlateDetails] = None
    inference_time_ms: float = 0.0


class ANPRInferenceResult(BaseModel):
    frame_id: str
    timestamp: str
    camera_id: str
    total_vehicles_detected: int
    total_plates_recognized: int
    vehicles: List[VehicleWithPlateDetection]


# ------------------------------------------------------------------------------
# 2. Pipeline Implementation
# ------------------------------------------------------------------------------

class YOLO26ANPRPipeline:
    """
    End-to-End Vehicle & Number Plate Recognition Pipeline.
    Reuses existing OCR and normalization services.
    """

    def __init__(self, camera_id: str = "CAM-ANPR-01", prefer_demo_ocr: bool = False):
        self.camera_id = camera_id
        self.detector = get_detector()
        self.ocr_processor = build_ocr_processor(prefer_demo=prefer_demo_ocr)

    def _crop_plate_roi(self, frame_bgr: np.ndarray, vehicle_box: Dict[str, float], plate_box: Optional[Dict[str, float]]) -> Optional[np.ndarray]:
        """Extract high-resolution plate region from frame."""
        h, w = frame_bgr.shape[:2]

        if plate_box:
            x1 = max(0, int(plate_box["x1"]))
            y1 = max(0, int(plate_box["y1"]))
            x2 = min(w, int(plate_box["x2"]))
            y2 = min(h, int(plate_box["y2"]))
        else:
            vx1 = int(vehicle_box["x1"])
            vy1 = int(vehicle_box["y1"])
            vx2 = int(vehicle_box["x2"])
            vy2 = int(vehicle_box["y2"])
            vh = vy2 - vy1
            vw = vx2 - vx1

            x1 = max(0, int(vx1 + vw * 0.20))
            y1 = max(0, int(vy1 + vh * 0.65))
            x2 = min(w, int(vx2 - vw * 0.20))
            y2 = min(h, vy2)

        if y2 > y1 and x2 > x1:
            return frame_bgr[y1:y2, x1:x2]
        return None

    def process_frame(self, frame_bgr: np.ndarray) -> ANPRInferenceResult:
        ts = datetime.now(timezone.utc).isoformat()
        raw_detections = self.detector.detect(frame_bgr, camera_id=self.camera_id)

        vehicle_dets = [d for d in raw_detections if d.get("object_class") in ("CAR", "TRUCK", "BUS", "MOTORCYCLE", "OTHER_VEHICLE")]
        plate_dets = [d for d in raw_detections if d.get("object_class") == "LICENSE_PLATE"]

        enriched_vehicles: List[VehicleWithPlateDetection] = []
        plates_count = 0

        for v in vehicle_dets:
            v_box = v["bounding_box"]
            matched_plate_box = None

            for p in plate_dets:
                p_box = p["bounding_box"]
                if (
                    p_box["x1"] >= v_box["x1"] - 10
                    and p_box["y1"] >= v_box["y1"] - 10
                    and p_box["x2"] <= v_box["x2"] + 10
                    and p_box["y2"] <= v_box["y2"] + 10
                ):
                    matched_plate_box = p_box
                    break

            plate_crop = self._crop_plate_roi(frame_bgr, v_box, matched_plate_box)
            plate_details = None

            if plate_crop is not None:
                ocr_result = self.ocr_processor.read_text(plate_crop)
                norm_text = normalize_plate_text(ocr_result.raw_text or ocr_result.normalized_text)

                if norm_text:
                    struct = extract_plate_structure(norm_text)
                    plates_count += 1

                    plate_details = PlateDetails(
                        raw_text=ocr_result.raw_text or norm_text,
                        normalized_plate=norm_text,
                        confidence=round(ocr_result.confidence or 0.90, 4),
                        bounding_box=matched_plate_box,
                        rto_jurisdiction=struct.get("rto_jurisdiction"),
                        is_gujarat=bool(struct.get("is_gujarat", False)),
                        format=str(struct.get("format", "STANDARD")),
                    )

            enriched_vehicles.append(
                VehicleWithPlateDetection(
                    detection_id=v.get("detection_id", str(uuid.uuid4())),
                    camera_id=self.camera_id,
                    timestamp=ts,
                    vehicle_type=v.get("object_class", "CAR"),
                    confidence=v.get("confidence", 0.0),
                    bounding_box=v_box,
                    plate=plate_details,
                    inference_time_ms=v.get("inference_time_ms", 0.0),
                )
            )

        return ANPRInferenceResult(
            frame_id=str(uuid.uuid4())[:8],
            timestamp=ts,
            camera_id=self.camera_id,
            total_vehicles_detected=len(enriched_vehicles),
            total_plates_recognized=plates_count,
            vehicles=enriched_vehicles,
        )
