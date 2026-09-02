"""
YOLO26 Object Detector Implementation
=====================================
Production singleton inference service with automatic GPU/CPU routing for PHANTOM.
Employs 3-tier hierarchical classification, specialized secondary feature extractors,
hard-negative pole filtering, and strict uncertainty handling.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import logging
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional, Union
import uuid

import numpy as np

from .config import YOLO26Config
from .hierarchy import (
    ClassificationStatus,
    EventLifecycle,
    HierarchicalClassificationResult,
    VisionTaxonomy,
)
from .model_loader import YOLO26ModelLoader, get_model_loader
from .specialized_classifiers import (
    AutoRickshawDisambiguator,
    CarSpecializedClassifier,
    HardNegativePoleFilter,
    TwoWheelerSpecializedClassifier,
)
from .utils import format_bounding_box, normalize_class_name, preprocess_image
from .vehicle_attributes import VehicleAttributeExtractor

logger = logging.getLogger("phantom.ai.yolo26")


class YOLO26Detector:
    """
    Thread-safe Singleton YOLO26 Object Detection Engine.
    Loads model weights once and handles concurrent inference safely.
    """

    _instance: Optional["YOLO26Detector"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, config: Optional[YOLO26Config] = None) -> "YOLO26Detector":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(YOLO26Detector, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: Optional[YOLO26Config] = None) -> None:
        if getattr(self, "_initialized", False):
            return

        with self._lock:
            if getattr(self, "_initialized", False):
                return

            self.config = config or YOLO26Config()
            self.loader = get_model_loader(self.config)
            self._initialized = True

    @property
    def model(self) -> Optional[Any]:
        return self.loader.model

    @property
    def device(self) -> str:
        return self.loader.device

    @property
    def is_loaded(self) -> bool:
        return self.loader.is_loaded

    def detect_frame(
        self,
        frame: Any,
        confidence_threshold: Optional[float] = None,
        classes: Optional[List[str]] = None,
        track_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Reusable inference method for OpenCV/NumPy image frames.
        Executes primary object detection + secondary hierarchical classification.
        """
        # 1. Invalid Frame Handling
        if frame is None or not isinstance(frame, np.ndarray):
            logger.warning("detect_frame received invalid non-numpy frame input.")
            return []

        if frame.size == 0 or len(frame.shape) < 2:
            logger.warning("detect_frame received empty frame.")
            return []

        if len(frame.shape) == 2:  # Grayscale conversion if 2D
            import cv2
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        h, w = frame.shape[:2]
        if h <= 0 or w <= 0:
            return []

        # 2. Configure Thresholds and Target Classes
        conf_thresh = (
            float(confidence_threshold)
            if confidence_threshold is not None and 0.0 <= confidence_threshold <= 1.0
            else self.config.confidence_threshold
        )

        allowed_classes_lower = (
            {c.strip().lower() for c in classes if c.strip()}
            if classes is not None
            else {c.lower() for c in self.config.target_classes}
        )

        raw_results_list: List[Dict[str, Any]] = []

        # 3. Model Inference Execution
        if self.is_loaded and self.model is not None:
            try:
                predict_kwargs: Dict[str, Any] = {
                    "source": frame,
                    "conf": conf_thresh,
                    "iou": self.config.iou_threshold,
                    "device": self.device,
                    "imgsz": min(640, max(320, getattr(self.config, "input_size", 640))),
                    "verbose": False,
                }
                if self.device.startswith("cuda") and self.config.half_precision:
                    predict_kwargs["half"] = True

                results = self.model.predict(**predict_kwargs)

                for result in results:
                    boxes = result.boxes
                    if boxes is None:
                        continue

                    names = result.names or {}
                    for box in boxes:
                        conf = float(box.conf[0])
                        if conf < conf_thresh:
                            continue

                        cls_id = int(box.cls[0])
                        raw_name = names.get(cls_id, str(cls_id))
                        clean_name = str(raw_name).strip().lower()

                        if allowed_classes_lower and clean_name not in allowed_classes_lower:
                            canon_name = normalize_class_name(raw_name).lower()
                            if canon_name not in allowed_classes_lower:
                                continue

                        xyxy = box.xyxy[0].tolist()
                        x1 = max(0, min(w, int(round(xyxy[0]))))
                        y1 = max(0, min(h, int(round(xyxy[1]))))
                        x2 = max(0, min(w, int(round(xyxy[2]))))
                        y2 = max(0, min(h, int(round(xyxy[3]))))
                        bw = x2 - x1
                        bh = y2 - y1

                        if bw < 14 or bh < 14:
                            continue

                        aspect_ratio = bh / float(bw) if bw > 0 else 1.0
                        if aspect_ratio > 4.8 or aspect_ratio < 0.25:
                            continue

                        raw_results_list.append({
                            "class_id": cls_id,
                            "class_name": clean_name,
                            "confidence": round(conf, 4),
                            "bbox": {
                                "x1": x1,
                                "y1": y1,
                                "x2": x2,
                                "y2": y2,
                                "width": bw,
                                "height": bh,
                            },
                        })
            except Exception as inference_err:
                logger.error(f"Inference error in detect_frame: {inference_err}")

        # 4. Secondary Hierarchical Classification & Hard-Negative Filtering
        processed_list: List[Dict[str, Any]] = []
        suppressed_indices = set()

        for i, det in enumerate(raw_results_list):
            if i in suppressed_indices:
                continue

            cname = det["class_name"].lower()
            canon = normalize_class_name(cname)
            bx = det["bbox"]
            bw = bx["width"]
            bh = bx["height"]
            conf = det["confidence"]

            # Extract image crop with contextual padding
            pad_x = int(bw * 0.08)
            pad_y = int(bh * 0.08)
            cx1 = max(0, bx["x1"] - pad_x)
            cy1 = max(0, bx["y1"] - pad_y)
            cx2 = min(w, bx["x2"] + pad_x)
            cy2 = min(h, bx["y2"] + pad_y)
            crop = frame[cy1:cy2, cx1:cx2] if (cx2 > cx1 + 4 and cy2 > cy1 + 4) else None

            # --- HARD NEGATIVE PERSON / POLE FILTERING ---
            if canon == "PERSON":
                # Check for motorcycle rider fusion
                has_moto_overlap = False
                for j, other in enumerate(raw_results_list):
                    if i != j and j not in suppressed_indices:
                        if normalize_class_name(other["class_name"]) in ("MOTORCYCLE", "TWO_WHEELER", "SCOOTER", "BICYCLE"):
                            obx = other["bbox"]
                            ix1 = max(bx["x1"], obx["x1"])
                            iy1 = max(bx["y1"], obx["y1"])
                            ix2 = min(bx["x2"], obx["x2"])
                            iy2 = min(bx["y2"], obx["y2"])
                            if ix2 > ix1 and iy2 > iy1:
                                inter_area = (ix2 - ix1) * (iy2 - iy1)
                                o_area = max(1, obx["width"] * obx["height"])
                                if inter_area / float(o_area) > 0.22 or inter_area / float(bw * bh) > 0.22:
                                    has_moto_overlap = True
                                    break
                if has_moto_overlap:
                    suppressed_indices.add(i)
                    continue

                # Run Hard-Negative Pole / Streetlight Filter
                is_pole, reason = HardNegativePoleFilter.is_hard_negative_pole(crop, bx, detector_conf=conf)
                if is_pole:
                    # Filter out pole false-positives
                    logger.debug(f"Hard-negative pole filtered: {reason}")
                    continue

                h_res = HierarchicalClassificationResult(
                    category="PERSON",
                    category_confidence=conf,
                    subtype="PEDESTRIAN",
                    subtype_confidence=conf,
                    classification_status=ClassificationStatus.CONFIDENT if conf >= 0.75 else ClassificationStatus.LIKELY,
                    display_label=VisionTaxonomy.format_tactical_label("PERSON", confidence=conf, status=ClassificationStatus.CONFIDENT),
                )
                det["object_class"] = "PERSON"
                det["hierarchical_result"] = h_res
                processed_list.append(det)

            # --- TWO-WHEELER CLASSIFIER (SCOOTER vs MOTORCYCLE) ---
            elif canon in ("TWO_WHEELER", "MOTORCYCLE", "SCOOTER"):
                h_res = TwoWheelerSpecializedClassifier.classify_crop(
                    crop_bgr=crop,
                    bbox=bx,
                    raw_conf=conf,
                    track_id=track_id,
                )
                det["object_class"] = h_res.category
                det["hierarchical_result"] = h_res
                processed_list.append(det)

            # --- CAR / HATCHBACK / WAGONR vs SWIFT CLASSIFIER ---
            elif canon in ("CAR", "HATCHBACK", "SEDAN", "SUV"):
                # Check for 3-wheeler auto-rickshaw misclassification
                is_auto, auto_conf = AutoRickshawDisambiguator.is_auto_rickshaw(crop, bx, canon, conf)
                if is_auto:
                    h_res = HierarchicalClassificationResult(
                        category="AUTO_RICKSHAW",
                        category_confidence=auto_conf,
                        subtype="AUTO_RICKSHAW",
                        make="Bajaj",
                        model="Compact Auto",
                        model_confidence=auto_conf,
                        classification_status=ClassificationStatus.CONFIDENT if auto_conf >= 0.75 else ClassificationStatus.LIKELY,
                        display_label=VisionTaxonomy.format_tactical_label("AUTO_RICKSHAW", make="Bajaj", model="Compact Auto", confidence=auto_conf, status=ClassificationStatus.CONFIDENT),
                    )
                    det["object_class"] = "AUTO_RICKSHAW"
                else:
                    h_res = CarSpecializedClassifier.classify_crop(
                        crop_bgr=crop,
                        bbox=bx,
                        raw_conf=conf,
                        track_id=track_id,
                    )
                    det["object_class"] = "CAR"

                det["hierarchical_result"] = h_res
                processed_list.append(det)

            # --- TRUCK / AUTO-RICKSHAW DISAMBIGUATION ---
            elif canon in ("TRUCK", "VAN", "BUS", "OTHER_VEHICLE"):
                is_auto, auto_conf = AutoRickshawDisambiguator.is_auto_rickshaw(crop, bx, canon, conf)
                if is_auto:
                    h_res = HierarchicalClassificationResult(
                        category="AUTO_RICKSHAW",
                        category_confidence=auto_conf,
                        subtype="AUTO_RICKSHAW",
                        make="Bajaj",
                        model="Compact Auto",
                        model_confidence=auto_conf,
                        classification_status=ClassificationStatus.CONFIDENT if auto_conf >= 0.75 else ClassificationStatus.LIKELY,
                        display_label=VisionTaxonomy.format_tactical_label("AUTO_RICKSHAW", make="Bajaj", model="Compact Auto", confidence=auto_conf, status=ClassificationStatus.CONFIDENT),
                    )
                    det["object_class"] = "AUTO_RICKSHAW"
                else:
                    h_res = HierarchicalClassificationResult(
                        category=canon,
                        category_confidence=conf,
                        subtype=canon,
                        classification_status=ClassificationStatus.CONFIDENT if conf >= 0.78 else ClassificationStatus.LIKELY,
                        display_label=VisionTaxonomy.format_tactical_label(canon, confidence=conf, status=ClassificationStatus.CONFIDENT),
                    )
                    det["object_class"] = canon

                det["hierarchical_result"] = h_res
                processed_list.append(det)

            else:
                h_res = HierarchicalClassificationResult(
                    category=canon,
                    category_confidence=conf,
                    classification_status=ClassificationStatus.CONFIDENT if conf >= 0.78 else ClassificationStatus.LIKELY,
                    display_label=VisionTaxonomy.format_tactical_label(canon, confidence=conf, status=ClassificationStatus.CONFIDENT),
                )
                det["object_class"] = canon
                det["hierarchical_result"] = h_res
                processed_list.append(det)

        return processed_list

    def detect(
        self,
        image: Any,
        camera_id: Optional[Union[str, uuid.UUID]] = None,
        timestamp: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Comprehensive detection pipeline returning enriched vehicle attributes,
        hierarchical classification metadata, and tracking compatibility.
        """
        ts = timestamp or datetime.now(timezone.utc)
        cam_id = str(camera_id or uuid.uuid4())
        started_time = time.perf_counter()

        try:
            frame_np = preprocess_image(image)
        except Exception as prep_err:
            logger.error(f"Image preprocessing failure: {prep_err}")
            return []

        if frame_np is None:
            return []

        standard_dets = self.detect_frame(frame_np)
        detections: List[Dict[str, Any]] = []

        for d in standard_dets:
            canon_class = d.get("object_class") or normalize_class_name(d["class_name"])
            bx = d["bbox"]
            det_id = str(uuid.uuid4())
            h_res = d.get("hierarchical_result")

            det_item = {
                "detection_id": det_id,
                "camera_id": cam_id,
                "timestamp": ts.isoformat(),
                "object_class": canon_class,
                "confidence": d["confidence"],
                "bounding_box": {
                    "x1": bx["x1"],
                    "y1": bx["y1"],
                    "x2": bx["x2"],
                    "y2": bx["y2"],
                    "width": abs(bx["x2"] - bx["x1"]),
                    "height": abs(bx["y2"] - bx["y1"]),
                },
                "model_name": self.config.model_name,
                "model_version": self.config.model_version,
                "device": self.device,
                "is_demo": not self.is_loaded,
                "raw_class": d.get("class_name", canon_class),
                "hierarchical_result": h_res,
                "classification_status": h_res.classification_status.value if h_res else ClassificationStatus.UNKNOWN.value,
                "display_label": h_res.display_label if h_res else "",
            }
            # Enrich with vehicle attributes
            det_item = VehicleAttributeExtractor.enrich_detection(det_item, frame_np, cam_id)
            detections.append(det_item)

        elapsed_ms = round((time.perf_counter() - started_time) * 1000.0, 2)
        for item in detections:
            item["inference_time_ms"] = elapsed_ms

        return detections


def get_detector(config: Optional[YOLO26Config] = None) -> YOLO26Detector:
    return YOLO26Detector(config=config)
