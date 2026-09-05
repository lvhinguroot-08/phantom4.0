"""
YOLO26 Stream Processor
High-level pipeline orchestrator linking frame ingestion, detector inference, trajectory tracking, and HUD generation.
"""
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

import numpy as np

from .config import YOLO26Config
from .detector import YOLO26Detector, get_detector
from .helmet_classifier import DeepLearningHelmetClassifier, get_helmet_classifier
from .rider_association import RiderAssociationEngine, VehicleOccupancyRecord
from .schemas import (
    BoundingBox,
    DetectedObject,
    DetectionBatchResult,
    DetectionSummary,
    TrafficViolationEvent,
    VehicleAttributes,
)
from .tracker import YOLO26Tracker
from .utils import preprocess_image
from .violation_engine import TrafficViolationEngine
from .violation_evidence import ViolationEvidenceService, get_evidence_service
from app.ai.anpr.yolo26_anpr_pipeline import YOLO26ANPRPipeline

logger = logging.getLogger("phantom.ai.yolo26.processor")


class YOLO26StreamProcessor:
    """
    Unified frame processor for single images, video clips, and continuous CCTV streams.
    Orchestrates detection, tracking, rider association, helmet analysis, and violation detection.
    """

    def __init__(self, camera_id: str = "CAM-GLOBAL", config: Optional[YOLO26Config] = None):
        self.camera_id = camera_id
        self.config = config or YOLO26Config()
        self.detector = get_detector(self.config)
        self.tracker = YOLO26Tracker(camera_id=camera_id) if self.config.enable_tracking else None
        self.rider_association = RiderAssociationEngine(
            min_association_confidence=self.config.min_association_confidence,
        )
        self.helmet_classifier = get_helmet_classifier(
            model_path=self.config.helmet_model_path,
            min_confidence=self.config.helmet_min_confidence,
        )
        self.violation_engine = TrafficViolationEngine(
            camera_id=camera_id,
            min_no_helmet_confirmations=self.config.no_helmet_confirmation_window,
            min_triple_riding_confirmations=self.config.triple_riding_confirmation_window,
            min_track_age=self.config.track_min_age,
            cooldown_seconds=self.config.violation_cooldown_seconds,
        )
        self.evidence_service = get_evidence_service()
        self.anpr_pipeline = YOLO26ANPRPipeline(camera_id=camera_id, config=self.config)
        self.latest_violations: List[TrafficViolationEvent] = []
        self.frame_seq = 0


    def process_frame(
        self,
        image_input: Any,
        timestamp: Optional[datetime] = None,
        normalize_coordinates: bool = True,
    ) -> DetectionBatchResult:
        """
        Process a single video or image frame and return a structured DetectionBatchResult.
        """
        self.frame_seq += 1
        now_dt = timestamp or datetime.now(timezone.utc)
        start_time = time.perf_counter()

        frame_bgr = preprocess_image(image_input)
        if frame_bgr is None:
            return DetectionBatchResult(
                camera_id=self.camera_id,
                frame_seq=self.frame_seq,
                timestamp=now_dt.isoformat(),
                latency_ms=0.0,
            )

        h, w = frame_bgr.shape[:2]

        # 1. Execute Object Detection & Attribute Enrichment
        raw_detections = self.detector.detect(frame_bgr, camera_id=self.camera_id, timestamp=now_dt)

        # 2. Execute Multi-Object Tracking if enabled
        if self.tracker:
            raw_detections = self.tracker.update(raw_detections, frame_shape=(h, w))

        # 3. Rider <-> Two-Wheeler Association
        occupancy_records, raw_detections = self.rider_association.associate(raw_detections)

        # 4. Helmet Analysis on Associated Two-Wheeler Riders
        helmet_results: Dict[int, Tuple[str, float]] = {}
        for v_tid, occ in occupancy_records.items():
            for rider in occ.riders:
                if rider.head_box:
                    head_crop, _ = self.helmet_classifier.extract_head_crop(frame_bgr, rider.head_box)
                    if head_crop is not None:
                        res = self.helmet_classifier.classify_crop(head_crop)
                        helmet_results[rider.person_track_id] = (res.state, res.confidence)
                    else:
                        helmet_results[rider.person_track_id] = ("UNCERTAIN", 0.0)

        # 5. Execute ANPR on Tracked Vehicles
        vehicle_dets = [
            d for d in raw_detections
            if (d.get("attributes") and d["attributes"].get("is_vehicle"))
            or d.get("object_class") in (
                "CAR", "TRUCK", "BUS", "MOTORCYCLE", "SCOOTER",
                "AUTO_RICKSHAW", "LCV_TEMPO", "OTHER_VEHICLE"
            )
        ]
        plate_results = self.anpr_pipeline.process_tracked_vehicles(frame_bgr, vehicle_dets)

        # 6. Temporal Violation State Machine Evaluation
        confirmed_violations = self.violation_engine.evaluate_frame_violations(
            occupancy_records=occupancy_records,
            helmet_results=helmet_results,
        )

        # 7. Link Recognized Plates to Confirmed Violations & Capture Visual Evidence
        for viol in confirmed_violations:
            occ_rec = occupancy_records.get(viol.vehicle_track_id)
            if viol.vehicle_track_id in plate_results:
                p_res = plate_results[viol.vehicle_track_id]
                if p_res.plate_text and p_res.plate_text != "UNREADABLE":
                    viol.vehicle_plate = p_res.plate_text
                    viol.plate_confidence = p_res.confidence
                    viol.metadata["plate_confirmed"] = p_res.is_confirmed
                    viol.metadata["plate_confirmations"] = p_res.confirmations
            self.evidence_service.capture_evidence(frame_bgr, viol, occ_rec)

        self.latest_violations = confirmed_violations

        # 8. Cleanup Stale Tracking States
        active_track_ids = {d.get("track_id") for d in raw_detections if d.get("track_id") is not None}
        self.rider_association.cleanup_lost_tracks(active_track_ids)
        self.violation_engine.cleanup_lost_tracks(active_track_ids)

        # 9. Format Structured Output & Coordinate Normalization
        formatted_objects: List[DetectedObject] = []
        vehicles_count = 0
        persons_count = 0
        plates_count = 0
        critical_alerts = 0

        # Map vehicle track id -> active violation types
        vehicle_violations: Dict[int, List[str]] = {}
        for viol in confirmed_violations:
            vehicle_violations.setdefault(viol.vehicle_track_id, []).append(viol.violation_type)

        for d in raw_detections:
            raw_bbox = d.get("bounding_box", {})
            bx1 = raw_bbox.get("x1", 0.0)
            by1 = raw_bbox.get("y1", 0.0)
            bx2 = raw_bbox.get("x2", 0.0)
            by2 = raw_bbox.get("y2", 0.0)

            if normalize_coordinates:
                if bx2 > 1.0 or by2 > 1.0:
                    nx1 = round((bx1 / max(1, w)) * 100, 2)
                    ny1 = round((by1 / max(1, h)) * 100, 2)
                    nx2 = round((bx2 / max(1, w)) * 100, 2)
                    ny2 = round((by2 / max(1, h)) * 100, 2)
                else:
                    nx1 = round(bx1 * 100, 2)
                    ny1 = round(by1 * 100, 2)
                    nx2 = round(bx2 * 100, 2)
                    ny2 = round(by2 * 100, 2)
            else:
                nx1, ny1, nx2, ny2 = bx1, by1, bx2, by2

            bbox_obj = BoundingBox(
                x1=nx1,
                y1=ny1,
                x2=nx2,
                y2=ny2,
                width=round(abs(nx2 - nx1), 2),
                height=round(abs(ny2 - ny1), 2),
            )

            attrs_dict = d.get("attributes")
            attrs_obj = VehicleAttributes(**attrs_dict) if attrs_dict else None

            tid = d.get("track_id")
            if tid is not None and attrs_obj:
                if tid in vehicle_violations:
                    attrs_obj.active_violations = vehicle_violations[tid]
                if tid in plate_results:
                    p_res = plate_results[tid]
                    if p_res.plate_text and p_res.plate_text != "UNREADABLE":
                        attrs_obj.license_plate = p_res.plate_text
                        attrs_obj.plate_confidence = p_res.confidence
                        attrs_obj.anpr_confirmed = p_res.is_confirmed

            cls_name = d.get("object_class", "OBJECT")
            if attrs_obj and attrs_obj.is_vehicle:
                vehicles_count += 1
            if cls_name == "PERSON":
                persons_count += 1
            if attrs_obj and attrs_obj.license_plate:
                plates_count += 1
            if d.get("is_watchlist_match") or (tid is not None and tid in vehicle_violations):
                critical_alerts += 1

            threat = "NORMAL"
            if tid is not None and tid in vehicle_violations:
                threat = "CRITICAL" if "TRIPLE_RIDING" in vehicle_violations[tid] else "ELEVATED"
            elif d.get("is_watchlist_match"):
                threat = "CRITICAL"


            det_obj = DetectedObject(
                detection_id=d.get("detection_id", str(uuid.uuid4())),
                camera_id=self.camera_id,
                timestamp=now_dt.isoformat(),
                object_class=cls_name,
                confidence=d.get("confidence", 0.0),
                bounding_box=bbox_obj,
                attributes=attrs_obj,
                track_id=d.get("track_id"),
                speed_kmph=d.get("speed_kmph"),
                direction=d.get("direction"),
                model_name=self.config.model_name,
                model_version=self.config.model_version,
                device=self.detector.device,
                inference_time_ms=d.get("inference_time_ms", 0.0),
                is_demo=d.get("is_demo", False),
                is_watchlist_match=d.get("is_watchlist_match", False),
                threat_level=threat,
                raw_class=d.get("raw_class"),
            )
            formatted_objects.append(det_obj)

        latency = round((time.perf_counter() - start_time) * 1000.0, 2)

        summary = DetectionSummary(
            total_objects=len(formatted_objects),
            vehicles_count=vehicles_count,
            persons_count=persons_count,
            plates_count=plates_count,
            critical_alerts=critical_alerts,
        )

        return DetectionBatchResult(
            type="LIVE_DETECTION_OVERLAY",
            camera_id=self.camera_id,
            frame_seq=self.frame_seq,
            timestamp=now_dt.isoformat(),
            ai_fps=round(1000.0 / max(1.0, latency), 1),
            latency_ms=latency,
            summary=summary,
            detections=formatted_objects,
        )
