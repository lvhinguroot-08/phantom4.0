"""
Dedicated License Plate Detector
Replaces blind bottom-35% cropping with dedicated license plate localization.
Supports:
1. Pluggable custom deep-learning plate detection models via PLATE_MODEL_PATH.
2. High-precision vehicle ROI morphological band localization fallback.
3. Clean error and uncertainty reporting without fabricating plate bboxes.
"""
from dataclasses import dataclass
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("phantom.ai.anpr.plate_detector")


@dataclass
class PlateDetectionResult:
    """Standardized output of the license plate localization stage."""
    plate_bbox: Dict[str, float]  # Frame pixel coordinates {"x1", "y1", "x2", "y2"}
    confidence: float
    vehicle_track_id: Optional[int]
    detection_source: str  # "MODEL" or "ROI_CONTOUR"
    plate_crop: Optional[np.ndarray] = None


class LicensePlateDetector:
    """
    Dedicated license plate detector operating on vehicle ROIs.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        min_confidence: float = 0.40,
        device: str = "cpu",
    ):
        self.model_path = model_path or os.getenv("PLATE_MODEL_PATH")
        self.min_confidence = min_confidence
        self.device = device
        self.model: Any = None
        self.is_custom_model = False
        self._init_model()

    def _init_model(self) -> None:
        """Loads custom plate detection weights if available on disk."""
        target = self.model_path
        if target and Path(target).is_file():
            try:
                from ultralytics import YOLO
                self.model = YOLO(target)
                self.is_custom_model = True
                logger.info(f"Loaded dedicated license plate detector from: {target}")
                return
            except Exception as exc:
                logger.warning(f"Could not load custom plate weights from {target}: {exc}")

        logger.info(
            "Running LicensePlateDetector in baseline vehicle-ROI morphological mode. "
            "Dedicated plate weights can be supplied via PLATE_MODEL_PATH."
        )

    def _denormalize_vehicle_box(
        self,
        v_box: Dict[str, float],
        fw: int,
        fh: int,
    ) -> Tuple[int, int, int, int]:
        """Converts vehicle bounding box to absolute frame pixel coordinates."""
        x1 = float(v_box.get("x1", 0.0))
        y1 = float(v_box.get("y1", 0.0))
        x2 = float(v_box.get("x2", 0.0))
        y2 = float(v_box.get("y2", 0.0))

        if x2 <= 100.0 and y2 <= 100.0 and (x2 > 1.0 or y2 > 1.0) and (fw > 100 and fh > 100):
            # Percentage coordinates (0-100%)
            px1 = int((x1 / 100.0) * fw)
            py1 = int((y1 / 100.0) * fh)
            px2 = int((x2 / 100.0) * fw)
            py2 = int((y2 / 100.0) * fh)
        elif x2 <= 1.0 and y2 <= 1.0:
            px1 = int(x1 * fw)
            py1 = int(y1 * fh)
            px2 = int(x2 * fw)
            py2 = int(y2 * fh)
        else:
            px1 = int(x1)
            py1 = int(y1)
            px2 = int(x2)
            py2 = int(y2)

        px1 = max(0, min(fw - 1, px1))
        py1 = max(0, min(fh - 1, py1))
        px2 = max(px1 + 1, min(fw, px2))
        py2 = max(py1 + 1, min(fh, py2))
        return px1, py1, px2, py2

    def detect_plate_in_vehicle_roi(
        self,
        frame_bgr: np.ndarray,
        vehicle_box: Dict[str, float],
        vehicle_track_id: Optional[int] = None,
        vehicle_class: Optional[str] = None,
    ) -> Optional[PlateDetectionResult]:
        """
        Locates the license plate within the vehicle's region of interest.
        Returns None if no credible plate band is found.
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return None

        fh, fw = frame_bgr.shape[:2]
        vx1, vy1, vx2, vy2 = self._denormalize_vehicle_box(vehicle_box, fw, fh)
        vw = vx2 - vx1
        vh = vy2 - vy1

        if vw < 30 or vh < 20:
            return None

        vehicle_crop = frame_bgr[vy1:vy2, vx1:vx2]
        if vehicle_crop.size == 0:
            return None

        # 1. Custom Deep Learning Model Branch
        if self.is_custom_model and self.model is not None:
            try:
                results = self.model(vehicle_crop, verbose=False)
                if results and hasattr(results[0], "boxes") and len(results[0].boxes) > 0:
                    best_box = None
                    best_conf = 0.0
                    for box in results[0].boxes:
                        conf = float(box.conf[0])
                        if conf > best_conf and conf >= self.min_confidence:
                            best_conf = conf
                            best_box = box

                    if best_box is not None:
                        bx1, by1, bx2, by2 = [float(v) for v in best_box.xyxy[0]]
                        abs_x1 = vx1 + bx1
                        abs_y1 = vy1 + by1
                        abs_x2 = vx1 + bx2
                        abs_y2 = vy1 + by2

                        crop = frame_bgr[int(abs_y1):int(abs_y2), int(abs_x1):int(abs_x2)]
                        return PlateDetectionResult(
                            plate_bbox={"x1": abs_x1, "y1": abs_y1, "x2": abs_x2, "y2": abs_y2},
                            confidence=round(best_conf, 3),
                            vehicle_track_id=vehicle_track_id,
                            detection_source="MODEL",
                            plate_crop=crop if crop.size > 0 else None,
                        )
            except Exception as err:
                logger.debug(f"Deep learning plate detection failed: {err}; using ROI contour fallback.")

        # 2. High-Precision Vehicle ROI Morphological Band Localization
        # Searches lower 60% of vehicle ROI where Indian registration plates are mounted
        roi_y_start = int(vh * 0.40)
        search_roi = vehicle_crop[roi_y_start:, :]
        if search_roi.size == 0:
            return None

        s_h, s_w = search_roi.shape[:2]
        gray = cv2.cvtColor(search_roi, cv2.COLOR_BGR2GRAY)

        # Sobel vertical edge filter to accentuate vertical plate character strokes
        sobel_x = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
        abs_sobel = cv2.convertScaleAbs(sobel_x)

        # Morphological closing with rectangular kernel to bridge plate characters into a band
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
        closed = cv2.morphologyEx(abs_sobel, cv2.MORPH_CLOSE, kernel)

        # Otsu thresholding
        _, thresh = cv2.threshold(closed, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidate_plates: List[Tuple[float, int, int, int, int]] = []

        total_roi_area = float(s_w * s_h)

        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            area = float(w * h)
            if area < (total_roi_area * 0.003) or area > (total_roi_area * 0.45):
                continue

            aspect_ratio = float(w) / max(1.0, float(h))
            # Standard Indian plates have aspect ratios between 1.8 and 6.0
            if 1.8 <= aspect_ratio <= 6.0:
                # Convex hull represents the outer boundary of the character band
                hull = cv2.convexHull(c)
                hull_area = cv2.contourArea(hull)
                rect_score = hull_area / area if area > 0 else 0.0
                if rect_score >= 0.35:
                    # Centrality bonus
                    cx = x + (w / 2.0)
                    dist_from_center = abs(cx - (s_w / 2.0)) / (s_w / 2.0)
                    score = (rect_score * 0.6) + ((1.0 - dist_from_center) * 0.4)
                    candidate_plates.append((score, x, y, w, h))

        if not candidate_plates:
            return None

        # Sort by candidate quality score
        candidate_plates.sort(key=lambda item: item[0], reverse=True)
        best_score, px, py, pw, ph = candidate_plates[0]

        # Convert back to absolute frame coordinates
        abs_x1 = float(vx1 + px)
        abs_y1 = float(vy1 + roi_y_start + py)
        abs_x2 = float(abs_x1 + pw)
        abs_y2 = float(abs_y1 + ph)

        crop = frame_bgr[int(abs_y1):int(abs_y2), int(abs_x1):int(abs_x2)]

        return PlateDetectionResult(
            plate_bbox={"x1": abs_x1, "y1": abs_y1, "x2": abs_x2, "y2": abs_y2},
            confidence=round(min(0.95, max(0.40, best_score)), 3),
            vehicle_track_id=vehicle_track_id,
            detection_source="ROI_CONTOUR",
            plate_crop=crop if crop.size > 0 else None,
        )

    detect_in_vehicle_roi = detect_plate_in_vehicle_roi


# Global singleton instance
_plate_detector_instance: Optional[LicensePlateDetector] = None


def get_plate_detector(model_path: Optional[str] = None) -> LicensePlateDetector:
    global _plate_detector_instance
    if _plate_detector_instance is None:
        _plate_detector_instance = LicensePlateDetector(model_path=model_path)
    return _plate_detector_instance


get_license_plate_detector = get_plate_detector
