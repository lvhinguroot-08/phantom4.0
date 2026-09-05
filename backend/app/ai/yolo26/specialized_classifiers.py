"""
PHANTOM Vision Intelligence V2 — Specialized Classifiers & Hard-Negative Filtering
=================================================================================
High-precision secondary feature extractors operating on detected bounding box crops:
1. HardNegativePoleFilter: Rejects streetlights, utility poles, signposts from PERSON
2. TwoWheelerSpecializedClassifier: Distinguishes SCOOTER (Activa) vs MOTORCYCLE (Splendor)
3. CarSpecializedClassifier: Distinguishes TALLBOY (WagonR) vs SPORT (Swift) vs SEDAN vs SUV
4. AutoRickshawDisambiguator: Resolves 3-wheelers vs Trucks vs Cars
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from .hierarchy import (
    ClassificationStatus,
    HierarchicalClassificationResult,
    VisionTaxonomy,
)

logger = logging.getLogger("phantom.ai.specialized_classifiers")


class HardNegativePoleFilter:
    """
    Filters out static inanimate vertical structures (streetlights, utility poles,
    traffic signal poles, banners) that false-trigger generic person detectors.
    """

    @staticmethod
    def is_hard_negative_pole(
        crop_bgr: Optional[np.ndarray],
        bbox: Dict[str, float],
        detector_conf: float = 0.5,
    ) -> Tuple[bool, Optional[str]]:
        """
        Returns (is_hard_negative, reason).
        If True, this detection should NEVER be classified or promoted as a PERSON.
        """
        w = bbox.get("width", 0.0)
        h = bbox.get("height", 0.0)
        if w <= 0 or h <= 0:
            if "x1" in bbox and "x2" in bbox:
                w = abs(bbox["x2"] - bbox["x1"])
                h = abs(bbox["y2"] - bbox["y1"])

        if w <= 0 or h <= 0:
            return False, None

        aspect_ratio = float(h) / float(w)

        # 1. Tall vertical strip test (Streetlights/utility poles typically have AR > 3.2)
        if aspect_ratio >= 3.2:
            return True, f"High aspect ratio ({aspect_ratio:.2f} >= 3.2) characteristic of vertical streetlight / pole"

        # 2. Minimum physical pedestrian pixel width/height test
        if w < 16 or h < 26:
            return True, f"Sub-threshold dimensions ({w:.1f}x{h:.1f}px) characteristic of slender pole or noise"

        if crop_bgr is None or crop_bgr.size == 0:
            if aspect_ratio > 2.8:
                return True, "Narrow vertical shape with unresolvable crop"
            return False, None

        try:
            ch, cw = crop_bgr.shape[:2]
            if ch < 15 or cw < 8:
                return False, None

            gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)

            # 3. Straight parallel vertical edge detection along full height
            edges = cv2.Canny(gray, 40, 140)
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))
            vert_edges = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
            vert_edge_density = float(np.sum(vert_edges > 0)) / max(1.0, float(edges.size))

            # Utility poles have continuous parallel vertical edges without human taper
            if aspect_ratio >= 2.6 and vert_edge_density > 0.12:
                return True, f"Parallel vertical edges ({vert_edge_density:.2f}) characteristic of utility pole/post"

            # Check for lack of anatomical profile variance (shoulders, waist, legs)
            head_zone = gray[0:int(ch * 0.25), :]
            torso_zone = gray[int(ch * 0.25):int(ch * 0.65), :]
            legs_zone = gray[int(ch * 0.65):ch, :]

            head_w = float(np.sum(head_zone > 25)) / max(1, head_zone.size)
            torso_w = float(np.sum(torso_zone > 25)) / max(1, torso_zone.size)
            legs_w = float(np.sum(legs_zone > 25)) / max(1, legs_zone.size)

            if aspect_ratio >= 2.6 and abs(torso_w - legs_w) < 0.05 and abs(head_w - torso_w) < 0.05:
                return True, "Uniform columnar geometry lacking human anatomical variance"

        except Exception as err:
            logger.debug(f"Pole filter error: {err}")

        return False, None


class TwoWheelerSpecializedClassifier:
    """
    [DEPRECATED in Phase 1]
    Previously attempted to distinguish SCOOTER vs MOTORCYCLE using Canny edge heuristics.
    Retained solely as a backward-compatible wrapper. Authoritative classification is
    performed directly by the primary model detector and temporal track stabilization.
    """

    @classmethod
    def classify_crop(
        cls,
        crop_bgr: Optional[np.ndarray],
        bbox: Dict[str, float],
        raw_conf: float = 0.85,
        track_id: Optional[int] = None,
    ) -> HierarchicalClassificationResult:
        """
        Deprecated compatibility wrapper. Returns canonical two-wheeler classification
        without relying on edge-density or color heuristics.
        """
        # Default canonical category is MOTORCYCLE unless high-confidence model evidence exists
        category = "MOTORCYCLE"
        conf = round(float(raw_conf), 3)
        status = ClassificationStatus.CONFIDENT if conf >= 0.75 else ClassificationStatus.LIKELY

        display_label = VisionTaxonomy.format_tactical_label(
            category=category,
            confidence=conf,
            status=status,
            track_id=track_id,
        )

        return HierarchicalClassificationResult(
            category=category,
            category_confidence=conf,
            subtype=None,
            subtype_confidence=None,
            make=None,
            model=None,
            model_confidence=None,
            classification_status=status,
            display_label=display_label,
            candidate_scores={"MOTORCYCLE": conf, "SCOOTER": round(1.0 - conf, 3)},
        )


class CarSpecializedClassifier:
    """
    [DEPRECATED in Phase 1]
    Previously attempted to distinguish car models (WagonR vs Swift) using aspect ratio & roofline heuristics.
    Retained solely as a backward-compatible wrapper. Authoritative classification is
    performed directly by the primary model detector and temporal track stabilization.
    """

    @classmethod
    def classify_crop(
        cls,
        crop_bgr: Optional[np.ndarray],
        bbox: Dict[str, float],
        raw_conf: float = 0.90,
        track_id: Optional[int] = None,
    ) -> HierarchicalClassificationResult:
        """
        Deprecated compatibility wrapper. Returns canonical CAR classification.
        """
        category = "CAR"
        conf = round(float(raw_conf), 3)
        status = ClassificationStatus.CONFIDENT if conf >= 0.75 else ClassificationStatus.LIKELY

        display_label = VisionTaxonomy.format_tactical_label(
            category=category,
            confidence=conf,
            status=status,
            track_id=track_id,
        )

        return HierarchicalClassificationResult(
            category=category,
            category_confidence=conf,
            subtype=None,
            subtype_confidence=None,
            make=None,
            model=None,
            model_confidence=None,
            classification_status=status,
            display_label=display_label,
            candidate_scores={"CAR": conf},
        )


class AutoRickshawDisambiguator:
    """
    [DEPRECATED in Phase 1]
    Previously used HSV yellow/green thresholds to guess whether a vehicle was an Auto-Rickshaw.
    Model predictions and canonical taxonomy are now the single source of truth.
    """

    @staticmethod
    def is_auto_rickshaw(
        crop_bgr: Optional[np.ndarray],
        bbox: Dict[str, float],
        detector_class: str,
        detector_conf: float = 0.85,
    ) -> Tuple[bool, float]:
        """
        Deprecated compatibility wrapper.
        Returns True only if the detector natively classified the object as AUTO_RICKSHAW.
        """
        cname = str(detector_class).upper().strip()
        if cname in ("AUTO_RICKSHAW", "AUTORICKSHAW", "AUTO", "RICKSHAW", "TUK_TUK", "THREE_WHEELER"):
            return True, float(detector_conf)
        return False, 0.0
