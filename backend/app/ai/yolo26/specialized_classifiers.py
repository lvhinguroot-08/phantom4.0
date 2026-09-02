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
        If True, this detection should NEVER be promoted to a high-confidence PERSON.
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

        # 1. Extreme tall vertical strip test (Poles/Streetlights are typically AR > 3.8)
        if aspect_ratio >= 3.8:
            return True, f"Extreme aspect ratio ({aspect_ratio:.2f} >= 3.8) characteristic of vertical utility pole"

        # 2. Minimum physical pedestrian pixel height test
        if h < 22:
            return True, f"Sub-threshold height ({h:.1f}px < 22px) insufficient for pedestrian resolution"

        if crop_bgr is None or crop_bgr.size == 0:
            if aspect_ratio > 3.2 and detector_conf < 0.65:
                return True, "Ambiguous narrow vertical shape with low detector confidence"
            return False, None

        try:
            ch, cw = crop_bgr.shape[:2]
            if ch < 15 or cw < 8:
                return False, None

            gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)

            # 3. Horizontal symmetry & vertical uniformity test
            # Utility poles have uniform horizontal width along the entire vertical axis.
            # Real humans have distinct head, wider shoulders/torso, waist taper, and leg stride.
            head_zone = gray[0:int(ch * 0.25), :]
            torso_zone = gray[int(ch * 0.25):int(ch * 0.65), :]
            legs_zone = gray[int(ch * 0.65):ch, :]

            head_w = float(np.sum(head_zone > 30)) / max(1, head_zone.size)
            torso_w = float(np.sum(torso_zone > 30)) / max(1, torso_zone.size)
            legs_w = float(np.sum(legs_zone > 30)) / max(1, legs_zone.size)

            # Check for straight parallel vertical edges along entire height
            edges = cv2.Canny(gray, 50, 150)
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))
            vert_edges = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
            vert_edge_density = float(np.sum(vert_edges > 0)) / float(edges.size)

            # If strictly vertical parallel edges dominate with high aspect ratio
            if aspect_ratio >= 3.0 and vert_edge_density > 0.18 and detector_conf < 0.70:
                return True, f"Parallel straight vertical edges ({vert_edge_density:.2f}) matching pole fixture"

            # Check if bottom half is completely stationary straight line without leg opening
            if aspect_ratio >= 2.8 and abs(torso_w - legs_w) < 0.04 and detector_conf < 0.65:
                return True, "Uniform cylindrical profile lacking human anatomical variation"

        except Exception as err:
            logger.debug(f"Pole filter error: {err}")

        return False, None


class TwoWheelerSpecializedClassifier:
    """
    Distinguishes SCOOTER (Honda Activa, Suzuki Access, TVS Jupiter) from
    MOTORCYCLE (Hero Splendor, Bajaj Pulsar, Royal Enfield Classic 350).
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
        Extracts structural features to classify two-wheeler subtype and specific model.
        Outputs UNCERTAIN / UNKNOWN if visual evidence is low.
        """
        w = bbox.get("width", 1.0)
        h = max(0.1, bbox.get("height", 1.0))
        if "x1" in bbox and "x2" in bbox and (w <= 1.0 or h <= 1.0):
            w = max(1.0, abs(bbox["x2"] - bbox["x1"]))
            h = max(1.0, abs(bbox["y2"] - bbox["y1"]))

        aspect_ratio = h / float(w)

        # Baseline scores
        scooter_score = 0.50
        motorcycle_score = 0.50

        if crop_bgr is not None and crop_bgr.size > 0:
            try:
                ch, cw = crop_bgr.shape[:2]
                gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)

                # 1. Step-Through Floorboard vs Fuel Tank Analysis
                # Scooters: Open step-through floorboard (lower edge density & open gap in center)
                # Motorcycles: Straddled horizontal fuel tank and exposed engine block (high edge density)
                mid_roi = gray[int(ch * 0.35):int(ch * 0.65), int(cw * 0.25):int(cw * 0.75)]
                if mid_roi.size > 0:
                    edges = cv2.Canny(mid_roi, 40, 140)
                    edge_density = float(np.sum(edges > 0)) / float(mid_roi.size)

                    if edge_density < 0.12:
                        scooter_score += 0.28
                        motorcycle_score -= 0.28
                    elif edge_density > 0.22:
                        motorcycle_score += 0.28
                        scooter_score -= 0.28

                # 2. Aspect Ratio Evidence
                # Scooters are slightly more compact/boxy (AR 1.05 to 1.45)
                # Commuter bikes (Splendor) are longer (AR 0.80 to 1.20)
                if 1.15 <= aspect_ratio <= 1.55:
                    scooter_score += 0.15
                elif 0.75 <= aspect_ratio <= 1.10:
                    motorcycle_score += 0.15

                # 3. Rear Body Pod Cladding (Smooth plastic body on Activa vs open spoked wheel)
                lower_rear = gray[int(ch * 0.55):ch, 0:int(cw * 0.40)]
                if lower_rear.size > 0:
                    rear_std = float(np.std(lower_rear))
                    if rear_std < 40.0:
                        scooter_score += 0.18
                    elif rear_std > 58.0:
                        motorcycle_score += 0.18

            except Exception as err:
                logger.debug(f"Two-wheeler feature extraction error: {err}")

        # Normalization
        total = max(0.001, scooter_score + motorcycle_score)
        scooter_conf = round(scooter_score / total, 3)
        moto_conf = round(motorcycle_score / total, 3)
        margin = abs(scooter_conf - moto_conf)
        candidate_scores = {
            "SCOOTER": scooter_conf,
            "MOTORCYCLE": moto_conf,
        }

        # Grounded Uncertainty Check: low raw confidence or empty crop -> UNCERTAIN
        is_blank_crop = (crop_bgr is None or crop_bgr.size == 0 or np.all(crop_bgr == 0))
        if raw_conf < 0.68 or is_blank_crop or margin < 0.22 or max(scooter_conf, moto_conf) < 0.60:
            label = VisionTaxonomy.format_tactical_label(
                category="TWO_WHEELER",
                confidence=raw_conf,
                status=ClassificationStatus.UNCERTAIN,
                track_id=track_id,
            )
            return HierarchicalClassificationResult(
                category="TWO_WHEELER",
                category_confidence=raw_conf,
                subtype=None,
                subtype_confidence=None,
                make=None,
                model=None,
                model_confidence=None,
                classification_status=ClassificationStatus.UNCERTAIN,
                display_label=label,
                candidate_scores=candidate_scores,
            )

        if scooter_conf > moto_conf:
            subtype = "SCOOTER"
            sub_conf = scooter_conf
            # Scooter model candidates (Honda Activa is dominant in Gujarat)
            if sub_conf >= 0.75:
                make = "Honda"
                model = "Activa 6G"
                status = ClassificationStatus.CONFIDENT
                model_conf = min(0.95, round(sub_conf * raw_conf, 3))
            else:
                make = "Honda"
                model = "Activa"
                status = ClassificationStatus.LIKELY
                model_conf = min(0.85, round(sub_conf * raw_conf, 3))
        else:
            subtype = "MOTORCYCLE"
            sub_conf = moto_conf
            # Motorcycle model candidates (Hero Splendor is dominant commuter)
            if sub_conf >= 0.75:
                make = "Hero"
                model = "Splendor+"
                status = ClassificationStatus.CONFIDENT
                model_conf = min(0.95, round(sub_conf * raw_conf, 3))
            else:
                make = "Hero"
                model = "Splendor"
                status = ClassificationStatus.LIKELY
                model_conf = min(0.85, round(sub_conf * raw_conf, 3))

        label = VisionTaxonomy.format_tactical_label(
            category="TWO_WHEELER",
            subtype=subtype,
            make=make,
            model=model,
            confidence=model_conf,
            status=status,
            track_id=track_id,
        )

        return HierarchicalClassificationResult(
            category="TWO_WHEELER",
            category_confidence=raw_conf,
            subtype=subtype,
            subtype_confidence=sub_conf,
            make=make,
            model=model,
            model_confidence=model_conf,
            classification_status=status,
            display_label=label,
            candidate_scores=candidate_scores,
        )


class CarSpecializedClassifier:
    """
    Distinguishes Car Subtypes and Models:
    - HATCHBACK_TALLBOY (Maruti Suzuki WagonR)
    - HATCHBACK_SPORT (Maruti Suzuki Swift, Baleno, i20)
    - SEDAN (Dzire, City, Verna)
    - SUV (Creta, Nexon, Scorpio)
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
        Analyzes vehicle height-to-width ratio, roofline curvature, and glasshouse proportions
        to distinguish WagonR (tall-boy) from Swift (sloping sport hatchback), Sedan, and SUV.
        """
        w = bbox.get("width", 1.0)
        h = max(0.1, bbox.get("height", 1.0))
        if "x1" in bbox and "x2" in bbox and (w <= 1.0 or h <= 1.0):
            w = max(1.0, abs(bbox["x2"] - bbox["x1"]))
            h = max(1.0, abs(bbox["y2"] - bbox["y1"]))

        aspect_ratio_w_h = float(w) / float(h)
        height_ratio = float(h) / float(w)

        # Baseline hypothesis distribution
        scores = {
            "WagonR": 0.25,
            "Swift": 0.25,
            "Sedan": 0.25,
            "SUV": 0.25,
        }

        # 1. Structural Aspect Ratio Rules:
        # Sedan: Elongated 3-box profile (W/H >= 1.65)
        if aspect_ratio_w_h >= 1.68:
            scores["Sedan"] += 0.40
            scores["SUV"] -= 0.10
            scores["WagonR"] -= 0.20
            scores["Swift"] -= 0.10
        # Tallboy WagonR: High vertical silhouette (H/W >= 0.82 or W/H <= 1.25)
        elif height_ratio >= 0.82 or aspect_ratio_w_h <= 1.25:
            scores["WagonR"] += 0.45
            scores["Swift"] -= 0.25
            scores["Sedan"] -= 0.20
        # Sport Hatchback Swift: Low, wide, sporty stance (W/H between 1.30 and 1.65)
        elif 1.30 <= aspect_ratio_w_h <= 1.65:
            scores["Swift"] += 0.45
            scores["WagonR"] -= 0.25
            scores["SUV"] -= 0.10
            scores["Sedan"] -= 0.10

        # 2. Roofline & Pillar Analysis on Image ROI
        if crop_bgr is not None and crop_bgr.size > 0:
            try:
                ch, cw = crop_bgr.shape[:2]
                gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)

                # Upper 40% represents the roofline and window glasshouse
                roof_roi = gray[0:int(ch * 0.40), :]
                if roof_roi.size > 0:
                    edges = cv2.Canny(roof_roi, 50, 150)
                    # WagonR has a flat horizontal roof with nearly vertical C-pillar
                    # Swift has a swept aerodynamic sloping roofline curving downward towards the rear
                    upper_left = edges[:, 0:int(cw * 0.30)]
                    upper_right = edges[:, int(cw * 0.70):cw]

                    ul_density = float(np.sum(upper_left > 0)) / max(1, upper_left.size)
                    ur_density = float(np.sum(upper_right > 0)) / max(1, upper_right.size)

                    # Flat boxy roofline (WagonR) has symmetric edge heights
                    if abs(ul_density - ur_density) < 0.05 and height_ratio >= 0.78:
                        scores["WagonR"] += 0.25
                        scores["Swift"] -= 0.20
                    elif abs(ul_density - ur_density) >= 0.10:
                        scores["Swift"] += 0.20
                        scores["WagonR"] -= 0.15

            except Exception as err:
                logger.debug(f"Car feature extraction notice: {err}")

        # Normalize scores
        total_s = max(0.001, sum(max(0.01, v) for v in scores.values()))
        norm_scores = {k: round(max(0.01, v) / total_s, 3) for k, v in scores.items()}

        sorted_candidates = sorted(norm_scores.items(), key=lambda x: x[1], reverse=True)
        top_name, top_score = sorted_candidates[0]
        runner_up_name, runner_up_score = sorted_candidates[1]

        margin = top_score - runner_up_score
        is_blank_crop = (crop_bgr is None or crop_bgr.size == 0 or np.all(crop_bgr == 0))

        # If low margin, low raw confidence, or blank crop -> Output UNCERTAIN
        if raw_conf < 0.68 or is_blank_crop or top_score < 0.44 or margin < 0.12:
            label = VisionTaxonomy.format_tactical_label(
                category="CAR",
                confidence=raw_conf,
                status=ClassificationStatus.UNCERTAIN,
                track_id=track_id,
            )
            return HierarchicalClassificationResult(
                category="CAR",
                category_confidence=raw_conf,
                subtype=None,
                subtype_confidence=None,
                make=None,
                model=None,
                model_confidence=None,
                classification_status=ClassificationStatus.UNCERTAIN,
                display_label=label,
                candidate_scores=norm_scores,
            )

        # Confident / Likely Mapping
        if top_name == "WagonR":
            subtype = "HATCHBACK_TALLBOY"
            make = "Maruti Suzuki"
            model = "WagonR"
            status = ClassificationStatus.CONFIDENT if top_score >= 0.65 else ClassificationStatus.LIKELY
        elif top_name == "Swift":
            subtype = "HATCHBACK_SPORT"
            make = "Maruti Suzuki"
            model = "Swift"
            status = ClassificationStatus.CONFIDENT if top_score >= 0.65 else ClassificationStatus.LIKELY
        elif top_name == "Sedan":
            subtype = "SEDAN"
            make = "Maruti Suzuki"
            model = "Dzire"
            status = ClassificationStatus.CONFIDENT if top_score >= 0.65 else ClassificationStatus.LIKELY
        else:
            subtype = "SUV"
            make = "Hyundai"
            model = "Creta"
            status = ClassificationStatus.CONFIDENT if top_score >= 0.65 else ClassificationStatus.LIKELY

        model_conf = min(0.98, round(top_score * raw_conf, 3))
        label = VisionTaxonomy.format_tactical_label(
            category="CAR",
            subtype=subtype,
            make=make,
            model=model,
            confidence=model_conf,
            status=status,
            track_id=track_id,
        )

        return HierarchicalClassificationResult(
            category="CAR",
            category_confidence=raw_conf,
            subtype=subtype,
            subtype_confidence=top_score,
            make=make,
            model=model,
            model_confidence=model_conf,
            classification_status=status,
            display_label=label,
            candidate_scores=norm_scores,
        )


class AutoRickshawDisambiguator:
    """
    Disambiguates Indian Three-Wheelers (Auto-Rickshaws) from Commercial Trucks and Cars.
    Eliminates COCO class-index mismatch errors where three-wheelers are mislabeled as Truck.
    """

    @staticmethod
    def is_auto_rickshaw(
        crop_bgr: Optional[np.ndarray],
        bbox: Dict[str, float],
        detector_class: str,
        detector_conf: float = 0.85,
    ) -> Tuple[bool, float]:
        """
        Returns (is_auto_rickshaw, confidence).
        Evaluates 3-wheeler triangular cab geometry, open sides, and green/yellow or black/yellow livery.
        """
        w = bbox.get("width", 1.0)
        h = max(0.1, bbox.get("height", 1.0))
        if "x1" in bbox and "x2" in bbox and (w <= 1.0 or h <= 1.0):
            w = max(1.0, abs(bbox["x2"] - bbox["x1"]))
            h = max(1.0, abs(bbox["y2"] - bbox["y1"]))

        aspect_ratio = float(h) / float(w)
        area = w * h
        cname = detector_class.upper()

        auto_score = 0.30

        # Auto-rickshaws have distinct aspect ratio (nearly square to slightly tall: 0.85 <= AR <= 1.35)
        if 0.85 <= aspect_ratio <= 1.35:
            auto_score += 0.30

        # Physical size in CCTV stream: Heavy trucks are large, autos are compact
        if 1200 <= area <= 32000:
            auto_score += 0.20

        # Color and Canopy Check
        if crop_bgr is not None and crop_bgr.size > 0:
            try:
                hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
                # Yellow canopy / roof (H: 20-35, S > 70, V > 70)
                yellow_mask = cv2.inRange(hsv, np.array([18, 60, 60]), np.array([36, 255, 255]))
                # Green lower body (Gujarat CNG Auto Rickshaw Livery) (H: 36-85)
                green_mask = cv2.inRange(hsv, np.array([36, 50, 50]), np.array([85, 255, 255]))

                y_pct = float(cv2.countNonZero(yellow_mask)) / float(crop_bgr.shape[0] * crop_bgr.shape[1])
                g_pct = float(cv2.countNonZero(green_mask)) / float(crop_bgr.shape[0] * crop_bgr.shape[1])

                if y_pct > 0.08 or (y_pct > 0.04 and g_pct > 0.05):
                    auto_score += 0.35
            except Exception:
                pass

        if cname == "AUTO_RICKSHAW":
            auto_score += 0.40
        elif cname == "TRUCK" and area < 15000 and 0.88 <= aspect_ratio <= 1.30:
            # High probability of COCO truck mismatch on auto-rickshaw
            auto_score += 0.25

        conf = min(0.98, max(0.10, auto_score))
        return (conf >= 0.60), conf
