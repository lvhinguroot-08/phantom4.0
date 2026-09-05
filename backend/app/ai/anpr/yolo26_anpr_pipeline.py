"""
PHANTOM Unified YOLO26 + ANPR Pipeline (Phase 3)
Combines YOLO26 vehicle detection/tracking with dedicated license plate detection,
4-point perspective correction, quality filtering, multi-variant preprocessing,
position-specific Indian syntax normalization, multi-frame temporal voting,
and track-aware state management.
"""
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

import cv2
import numpy as np
from pydantic import BaseModel, Field

from app.ai.anpr.anpr_state_machine import ANPRStateMachineManager, ANPRTrackState
from app.ai.anpr.normalize import (
    extract_plate_structure,
    is_gujarat_plate,
    looks_like_indian_plate,
    normalize_plate_text,
    score_plate_format,
)
from app.ai.anpr.ocr import build_ocr_processor, OCRProcessor
from app.ai.anpr.perspective import PlatePerspectiveCorrector, PlateQualityAssessor
from app.ai.anpr.plate_association import PlateAssociationEngine, get_plate_association_engine
from app.ai.anpr.plate_detector import (
    LicensePlateDetector,
    PlateDetectionResult,
    get_license_plate_detector,
)
from app.ai.anpr.preprocessor import PlateImagePreprocessor, get_plate_preprocessor
from app.ai.anpr.temporal_anpr import AggregatedPlateResult, PlateReading
from app.ai.yolo26.config import YOLO26Config
from app.ai.yolo26.detector import YOLO26Detector, get_detector

logger = logging.getLogger("phantom.ai.anpr")


# ------------------------------------------------------------------------------
# 1. Output Schemas
# ------------------------------------------------------------------------------

class PlateDetails(BaseModel):
    raw_text: str = Field(..., description="Raw OCR text output")
    normalized_plate: str = Field(..., description="Cleaned Indian registration number")
    confidence: float = Field(..., description="Composite confidence score (0.0 to 1.0)")
    bounding_box: Optional[Dict[str, float]] = Field(None, description="Plate coordinates")
    rto_jurisdiction: Optional[str] = Field(None, description="Associated RTO or Jurisdiction")
    is_gujarat: bool = Field(False, description="Whether registration is GJ state")
    format: str = Field("STANDARD", description="STANDARD, BHARAT_SERIES, or UNKNOWN")
    is_confirmed: bool = Field(False, description="Whether temporally confirmed across multiple frames")
    confirmations: int = Field(1, description="Number of agreeing frame observations")
    quality_status: str = Field("OK", description="OK, BLURRY, LOW_RES, UNREADABLE")


class VehicleWithPlateDetection(BaseModel):
    detection_id: str
    camera_id: str
    timestamp: str
    vehicle_type: str
    confidence: float
    bounding_box: Dict[str, float]
    track_id: Optional[int] = None
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
# 2. Complete Phase 3 Pipeline Implementation
# ------------------------------------------------------------------------------

class YOLO26ANPRPipeline:
    """
    State-of-the-Art ANPR Pipeline for Indian Traffic Surveillance.
    Integrates dedicated plate localization, perspective rectification, quality filtering,
    adaptive multi-variant preprocessing, and temporal character-level voting.
    """

    def __init__(
        self,
        camera_id: str = "CAM-ANPR-01",
        config: Optional[YOLO26Config] = None,
        prefer_demo_ocr: bool = False,
    ):
        self.camera_id = camera_id
        self.config = config or YOLO26Config()
        self.detector = get_detector(self.config)
        self.ocr_processor: OCRProcessor = build_ocr_processor(prefer_demo=prefer_demo_ocr)

        # Dedicated components
        self.plate_detector: LicensePlateDetector = get_license_plate_detector(
            model_path=self.config.plate_model_path,
        )
        self.association_engine: PlateAssociationEngine = get_plate_association_engine()
        self.quality_assessor = PlateQualityAssessor()
        self.perspective_corrector = PlatePerspectiveCorrector()
        self.preprocessor: PlateImagePreprocessor = get_plate_preprocessor()

        # Track-aware temporal state machine
        self.state_manager = ANPRStateMachineManager(
            temporal_window=self.config.anpr_temporal_window,
            min_confirmations=self.config.anpr_min_confirmations,
            min_confidence=self.config.anpr_min_ocr_confidence,
            duplicate_cooldown_seconds=float(self.config.anpr_cooldown_seconds),
        )

    def process_frame(self, frame_bgr: np.ndarray) -> ANPRInferenceResult:
        """
        Process a single image frame, detect vehicles and plates, rectify perspective,
        and perform temporal ANPR voting.
        """
        start_time = time.perf_counter()
        ts = datetime.now(timezone.utc).isoformat()
        if frame_bgr is None or frame_bgr.size == 0:
            return ANPRInferenceResult(
                frame_id=str(uuid.uuid4())[:8],
                timestamp=ts,
                camera_id=self.camera_id,
                total_vehicles_detected=0,
                total_plates_recognized=0,
                vehicles=[],
            )

        # 1. Detect all objects
        raw_detections = self.detector.detect(frame_bgr, camera_id=self.camera_id)
        vehicle_dets = [
            d for d in raw_detections
            if d.get("object_class") in (
                "CAR", "TRUCK", "BUS", "MOTORCYCLE", "SCOOTER",
                "AUTO_RICKSHAW", "LCV_TEMPO", "OTHER_VEHICLE"
            )
        ]

        # 2. Process plates for detected vehicles
        track_results = self.process_tracked_vehicles(frame_bgr, vehicle_dets)

        # 3. Format structured output
        enriched_vehicles: List[VehicleWithPlateDetection] = []
        recognized_count = 0

        for v in vehicle_dets:
            v_box = v["bounding_box"]
            tid = v.get("track_id")
            plate_details = None

            if tid is not None and tid in track_results:
                res = track_results[tid]
                if res.plate_text and res.plate_text != "UNREADABLE":
                    recognized_count += 1
                    plate_details = PlateDetails(
                        raw_text=res.plate_text,
                        normalized_plate=res.plate_text,
                        confidence=res.confidence,
                        bounding_box=None,
                        rto_jurisdiction=res.structural_info.get("rto_jurisdiction"),
                        is_gujarat=bool(res.structural_info.get("is_gujarat", False)),
                        format=str(res.structural_info.get("format", "STANDARD")),
                        is_confirmed=res.is_confirmed,
                        confirmations=res.confirmations,
                        quality_status="OK",
                    )

            enriched_vehicles.append(
                VehicleWithPlateDetection(
                    detection_id=v.get("detection_id", str(uuid.uuid4())),
                    camera_id=self.camera_id,
                    timestamp=ts,
                    vehicle_type=v.get("object_class", "CAR"),
                    confidence=v.get("confidence", 0.0),
                    bounding_box=v_box,
                    track_id=tid,
                    plate=plate_details,
                    inference_time_ms=round((time.perf_counter() - start_time) * 1000.0, 2),
                )
            )

        return ANPRInferenceResult(
            frame_id=str(uuid.uuid4())[:8],
            timestamp=ts,
            camera_id=self.camera_id,
            total_vehicles_detected=len(enriched_vehicles),
            total_plates_recognized=recognized_count,
            vehicles=enriched_vehicles,
        )

    def process_tracked_vehicles(
        self, frame_bgr: np.ndarray, vehicle_detections: List[Dict[str, Any]]
    ) -> Dict[int, AggregatedPlateResult]:
        """
        Core ANPR processing for active vehicle tracks.
        Returns a dictionary mapping vehicle_track_id -> AggregatedPlateResult.
        """
        results: Dict[int, AggregatedPlateResult] = {}
        if frame_bgr is None or frame_bgr.size == 0 or not vehicle_detections:
            return results

        # 1. Detect candidate plates on vehicle ROIs
        plate_detections: List[PlateDetectionResult] = []
        for v in vehicle_detections:
            v_box = v.get("bounding_box", {})
            v_tid = v.get("track_id")
            v_cls = v.get("object_class", "CAR")
            
            p_res = self.plate_detector.detect_in_vehicle_roi(
                frame_bgr, v_box, vehicle_track_id=v_tid, vehicle_class=v_cls
            )
            if p_res:
                plate_detections.append(p_res)

        # 2. Associate plates with vehicle tracks
        associations = self.association_engine.associate(vehicle_detections, plate_detections)

        # 3. For each association, assess quality, rectify perspective, and run OCR
        active_tids = set()
        for assoc in associations:
            tid = assoc.vehicle_track_id
            v_cls = assoc.vehicle_class
            active_tids.add(tid)

            p_det = assoc.plate_detection
            raw_crop = p_det.plate_crop
            if raw_crop is None or raw_crop.size == 0:
                continue

            # Quality assessment
            quality = self.quality_assessor.assess(raw_crop)
            if quality.status == "UNREADABLE":
                # Do NOT guess fake plates on completely unreadable/blurry crops
                reading = PlateReading(
                    raw_text="",
                    normalized_text="UNREADABLE",
                    ocr_confidence=0.0,
                    detection_confidence=p_det.confidence,
                    quality_score=quality.quality_score,
                    format_validity=0.0,
                    plate_crop=raw_crop,
                )
                agg_res = self.state_manager.update_track(
                    vehicle_track_id=tid,
                    camera_id=self.camera_id,
                    vehicle_type=v_cls,
                    plate_reading=reading,
                    plate_detected=True,
                )
                results[tid] = agg_res
                continue

            # Perspective correction & normalization
            if self.config.enable_perspective_correction:
                rectified_crop = self.perspective_corrector.rectify(raw_crop)
            else:
                rectified_crop = self.perspective_corrector.normalize_resolution(raw_crop)

            # Preprocessing best variant
            preprocessed_crop = self.preprocessor.preprocess_best(rectified_crop)

            # Run OCR
            ocr_res = self.ocr_processor.read_text(preprocessed_crop)
            norm_text = normalize_plate_text(ocr_res.raw_text or ocr_res.normalized_text)
            format_val = score_plate_format(norm_text)

            reading = PlateReading(
                raw_text=ocr_res.raw_text,
                normalized_text=norm_text,
                ocr_confidence=ocr_res.confidence,
                detection_confidence=p_det.confidence,
                quality_score=quality.quality_score,
                format_validity=format_val,
                plate_crop=rectified_crop,
            )

            agg_res = self.state_manager.update_track(
                vehicle_track_id=tid,
                camera_id=self.camera_id,
                vehicle_type=v_cls,
                plate_reading=reading,
                plate_detected=True,
            )
            results[tid] = agg_res

        # Prune exited tracks
        self.state_manager.prune_missing_tracks(active_tids)

        return results

    def get_plate_for_track(self, track_id: int) -> Optional[AggregatedPlateResult]:
        """Query currently active ANPR state for a vehicle track."""
        ctx = self.state_manager.active_tracks.get(track_id)
        if ctx:
            return ctx.aggregator.vote()
        return None
