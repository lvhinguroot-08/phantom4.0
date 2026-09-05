"""
Track-Aware Vehicle-to-Plate Association Engine
Associates license plate detections with specific vehicle tracks.
Handles multi-vehicle overlap and enforces spatial containment and temporal continuity.
"""
from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from app.ai.anpr.plate_detector import PlateDetectionResult

logger = logging.getLogger("phantom.ai.anpr.plate_association")


@dataclass
class AssociatedPlate:
    """Record of a plate bound to a vehicle track."""
    vehicle_track_id: int
    plate_bbox: Dict[str, float]
    confidence: float
    association_score: float
    detection_source: str


@dataclass
class AssociatedPlateRecord:
    """High-level association pairing a vehicle track to a plate detection."""
    vehicle_track_id: int
    vehicle_class: str
    plate_detection: PlateDetectionResult
    association_score: float


class PlateAssociationEngine:
    """
    Associates detected license plates with vehicle tracks.
    """

    def __init__(self, min_association_score: float = 0.40):
        self.min_association_score = min_association_score

    def _extract_center(self, bbox: Dict[str, float]) -> Tuple[float, float, float, float]:
        x1 = float(bbox.get("x1", 0.0))
        y1 = float(bbox.get("y1", 0.0))
        x2 = float(bbox.get("x2", 0.0))
        y2 = float(bbox.get("y2", 0.0))
        w = max(0.001, x2 - x1)
        h = max(0.001, y2 - y1)
        return x1 + (w / 2.0), y1 + (h / 2.0), w, h

    def compute_association_score(
        self,
        plate_box: Dict[str, float],
        vehicle_box: Dict[str, float],
    ) -> float:
        """
        Calculates spatial association score between plate and vehicle.
        Returns 0.0 if plate center is outside the vehicle bounding box.
        """
        px1 = float(plate_box.get("x1", 0.0))
        py1 = float(plate_box.get("y1", 0.0))
        px2 = float(plate_box.get("x2", 0.0))
        py2 = float(plate_box.get("y2", 0.0))
        pcx, pcy, pw, ph = self._extract_center(plate_box)

        vx1 = float(vehicle_box.get("x1", 0.0))
        vy1 = float(vehicle_box.get("y1", 0.0))
        vx2 = float(vehicle_box.get("x2", 0.0))
        vy2 = float(vehicle_box.get("y2", 0.0))
        vcx, vcy, vw, vh = self._extract_center(vehicle_box)

        # 1. Plate center containment rule (with small 5% margin)
        margin_x = vw * 0.05
        margin_y = vh * 0.05
        if pcx < (vx1 - margin_x) or pcx > (vx2 + margin_x):
            return 0.0
        if pcy < (vy1 - margin_y) or pcy > (vy2 + margin_y):
            return 0.0

        # 2. Overlap calculation
        inter_x1 = max(px1, vx1)
        inter_y1 = max(py1, vy1)
        inter_x2 = min(px2, vx2)
        inter_y2 = min(py2, vy2)
        inter_area = max(0.0, inter_x2 - inter_x1) * max(0.0, inter_y2 - inter_y1)
        plate_area = pw * ph

        if plate_area <= 0.0 or inter_area <= 0.0:
            return 0.0

        containment_ratio = inter_area / plate_area

        # 3. Horizontal centrality: plates are usually mounted horizontally centered
        horiz_offset = abs(pcx - vcx) / (vw * 0.5)
        centrality_score = max(0.0, 1.0 - min(1.0, horiz_offset))

        score = (0.70 * containment_ratio) + (0.30 * centrality_score)
        return min(1.0, max(0.0, score))

    def associate(
        self,
        vehicle_detections: List[Dict[str, Any]],
        plate_detections: List[PlateDetectionResult],
    ) -> List[AssociatedPlateRecord]:
        """
        Matches detected PlateDetectionResults to vehicle tracks.
        """
        if not plate_detections or not vehicle_detections:
            return []

        candidates: List[Tuple[float, int, int]] = []

        for p_idx, p_res in enumerate(plate_detections):
            # If the plate detection already carries a vehicle_track_id from ROI extraction, score it directly
            if p_res.vehicle_track_id is not None:
                for v_idx, vehicle in enumerate(vehicle_detections):
                    if vehicle.get("track_id") == p_res.vehicle_track_id:
                        candidates.append((1.0, p_idx, v_idx))
                continue

            p_box = p_res.plate_bbox
            for v_idx, vehicle in enumerate(vehicle_detections):
                v_box = vehicle.get("bounding_box", {})
                score = self.compute_association_score(p_box, v_box)
                if score >= self.min_association_score:
                    candidates.append((score, p_idx, v_idx))

        candidates.sort(key=lambda item: item[0], reverse=True)

        assigned_plates: Set[int] = set()
        assigned_vehicles: Set[int] = set()
        associations: List[AssociatedPlateRecord] = []

        for score, p_idx, v_idx in candidates:
            if p_idx in assigned_plates or v_idx in assigned_vehicles:
                continue

            p_res = plate_detections[p_idx]
            vehicle = vehicle_detections[v_idx]
            v_tid = vehicle.get("track_id")
            if v_tid is None:
                v_tid = hash(vehicle.get("detection_id", str(p_idx))) % 100000
            v_cls = vehicle.get("object_class", "CAR")

            associations.append(
                AssociatedPlateRecord(
                    vehicle_track_id=v_tid,
                    vehicle_class=v_cls,
                    plate_detection=p_res,
                    association_score=round(score, 3),
                )
            )

            assigned_plates.add(p_idx)
            assigned_vehicles.add(v_idx)

        return associations

    def associate_plates_to_vehicles(
        self,
        plate_detections: List[Dict[str, Any]],
        vehicle_detections: List[Dict[str, Any]],
    ) -> Dict[int, AssociatedPlate]:
        """
        Legacy dictionary-based matcher.
        """
        if not plate_detections or not vehicle_detections:
            return {}

        candidates: List[Tuple[float, int, int]] = []

        for p_idx, plate in enumerate(plate_detections):
            p_box = plate.get("bounding_box") or plate.get("plate_bbox", {})
            for v_idx, vehicle in enumerate(vehicle_detections):
                v_tid = vehicle.get("track_id")
                if v_tid is None:
                    continue
                v_box = vehicle.get("bounding_box", {})
                score = self.compute_association_score(p_box, v_box)
                if score >= self.min_association_score:
                    candidates.append((score, p_idx, v_idx))

        candidates.sort(key=lambda item: item[0], reverse=True)

        assigned_plates: Set[int] = set()
        assigned_vehicles: Set[int] = set()
        matched: Dict[int, AssociatedPlate] = {}

        for score, p_idx, v_idx in candidates:
            if p_idx in assigned_plates or v_idx in assigned_vehicles:
                continue

            plate = plate_detections[p_idx]
            vehicle = vehicle_detections[v_idx]
            v_tid = vehicle.get("track_id")
            p_box = plate.get("bounding_box") or plate.get("plate_bbox", {})

            matched[v_tid] = AssociatedPlate(
                vehicle_track_id=v_tid,
                plate_bbox=p_box,
                confidence=float(plate.get("confidence", 0.0)),
                association_score=round(score, 3),
                detection_source=str(plate.get("detection_source", "MODEL")),
            )

            assigned_plates.add(p_idx)
            assigned_vehicles.add(v_idx)

        return matched


_association_engine_instance: Optional[PlateAssociationEngine] = None


def get_plate_association_engine() -> PlateAssociationEngine:
    global _association_engine_instance
    if _association_engine_instance is None:
        _association_engine_instance = PlateAssociationEngine()
    return _association_engine_instance
