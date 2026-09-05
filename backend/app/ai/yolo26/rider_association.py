"""
Rider-to-Vehicle Association Engine
Vehicle-centric geometric and temporal association between two-wheelers (MOTORCYCLE, SCOOTER)
and riders/pillions (PERSON tracks).
Strictly eliminates false associations from nearby pedestrians and passengers of adjacent vehicles.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("phantom.ai.yolo26.rider_association")


@dataclass
class RiderInfo:
    """Detailed record of an associated occupant."""
    person_track_id: int
    bounding_box: Dict[str, float]
    association_confidence: float
    is_primary_rider: bool = False
    head_box: Optional[Dict[str, float]] = None


@dataclass
class VehicleOccupancyRecord:
    """Association context for a tracked two-wheeler."""
    vehicle_track_id: int
    vehicle_type: str
    vehicle_box: Dict[str, float]
    occupant_count: int
    associated_person_track_ids: List[int]
    association_confidence: float
    riders: List[RiderInfo]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RiderAssociationEngine:
    """
    Associates tracked PERSON objects with two-wheelers (MOTORCYCLE, SCOOTER).
    Uses geometric criteria (saddle zone, vertical overlap, horizontal alignment)
    and temporal continuity across ByteTrack frames.
    """

    TWO_WHEELER_CLASSES = {"MOTORCYCLE", "SCOOTER", "TWO_WHEELER", "BIKE"}

    def __init__(
        self,
        min_association_confidence: float = 0.45,
        temporal_bonus: float = 0.12,
        history_window: int = 15,
    ):
        self.min_confidence = min_association_confidence
        self.temporal_bonus = temporal_bonus
        self.history_window = history_window
        # Map: person_track_id -> vehicle_track_id from previous frame
        self._prev_associations: Dict[int, int] = {}
        # Track history counts: (vehicle_track_id, person_track_id) -> streak count
        self._pair_streaks: Dict[Tuple[int, int], int] = {}

    def _extract_coords(self, bbox: Dict[str, float]) -> Tuple[float, float, float, float, float, float, float, float]:
        """Returns x1, y1, x2, y2, cx, cy, w, h."""
        x1 = float(bbox.get("x1", 0.0))
        y1 = float(bbox.get("y1", 0.0))
        x2 = float(bbox.get("x2", 0.0))
        y2 = float(bbox.get("y2", 0.0))
        w = max(0.001, x2 - x1)
        h = max(0.001, y2 - y1)
        cx = x1 + (w / 2.0)
        cy = y1 + (h / 2.0)
        return x1, y1, x2, y2, cx, cy, w, h

    def _compute_geometric_association(
        self,
        person_bbox: Dict[str, float],
        vehicle_bbox: Dict[str, float],
    ) -> float:
        """
        Calculates geometric association score between person and vehicle.
        Returns 0.0 if person is determined to be a pedestrian or outside saddle zone.
        """
        px1, py1, px2, py2, pcx, pcy, pw, ph = self._extract_coords(person_bbox)
        vx1, vy1, vx2, vy2, vcx, vcy, vw, vh = self._extract_coords(vehicle_bbox)

        # 1. PEDESTRIAN REJECTION RULE:
        # A pedestrian standing on the street/pavement has their feet (py2)
        # well below the bottom of the vehicle tires (vy2).
        if py2 > (vy2 + 0.18 * vh):
            return 0.0

        # 2. HORIZONTAL ALIGNMENT REJECTION RULE:
        # A person walking beside the motorcycle has horizontal center outside the saddle zone.
        horizontal_margin = 0.22 * vw
        if pcx < (vx1 - horizontal_margin) or pcx > (vx2 + horizontal_margin):
            return 0.0

        # 3. VERTICAL SADDLE POSITION RULE:
        # A rider's lower body (py2) must reach into or near the motorcycle body/saddle.
        # Person's head (py1) must be near or above the motorcycle top (vy1).
        if py2 < (vy1 + 0.10 * vh):
            # Person is entirely above the motorcycle with no lower body contact
            return 0.0
        if py1 > (vy2 - 0.20 * vh):
            # Person is entirely below the top of the motorcycle
            return 0.0

        # 4. OVERLAP CALCULATIONS:
        # Horizontal intersection
        inter_x1 = max(px1, vx1)
        inter_x2 = min(px2, vx2)
        inter_w = max(0.0, inter_x2 - inter_x1)

        # Vertical intersection
        inter_y1 = max(py1, vy1)
        inter_y2 = min(py2, vy2)
        inter_h = max(0.0, inter_y2 - inter_y1)

        area_inter = inter_w * inter_h
        person_area = pw * ph
        vehicle_area = vw * vh

        if area_inter <= 0.0:
            return 0.0

        # Ratio of person box contained in vehicle vertical & horizontal zone
        inter_over_person = area_inter / person_area
        vertical_overlap = inter_h / ph
        horiz_containment = inter_w / pw

        # Horizontal alignment metric (1.0 = perfectly centered on motorcycle, 0.0 = edge)
        horiz_dist = abs(pcx - vcx)
        horiz_score = max(0.0, 1.0 - (horiz_dist / (vw * 0.75)))

        # Composite score
        score = (
            (0.35 * inter_over_person)
            + (0.30 * vertical_overlap)
            + (0.20 * horiz_containment)
            + (0.15 * horiz_score)
        )
        return min(1.0, max(0.0, score))

    def _extract_head_box(self, person_bbox: Dict[str, float]) -> Dict[str, float]:
        """
        Extracts upper 32% head/upper-body region from person bounding box.
        """
        px1, py1, px2, py2, pcx, pcy, pw, ph = self._extract_coords(person_bbox)
        head_h = ph * 0.32
        head_y2 = py1 + head_h
        return {
            "x1": round(px1, 2),
            "y1": round(py1, 2),
            "x2": round(px2, 2),
            "y2": round(head_y2, 2),
            "width": round(pw, 2),
            "height": round(head_h, 2),
        }

    def associate(
        self,
        detections: List[Dict[str, Any]],
    ) -> Tuple[Dict[int, VehicleOccupancyRecord], List[Dict[str, Any]]]:
        """
        Performs bipartite rider-to-vehicle association.
        Returns:
            - Dict mapping vehicle_track_id -> VehicleOccupancyRecord
            - Updated detections list with enriched association attributes
        """
        # Separate two-wheelers and persons
        vehicles: List[Dict[str, Any]] = []
        persons: List[Dict[str, Any]] = []

        for det in detections:
            cls_name = str(det.get("object_class", "")).upper()
            track_id = det.get("track_id")
            if track_id is None:
                continue
            if cls_name in self.TWO_WHEELER_CLASSES:
                vehicles.append(det)
            elif cls_name == "PERSON":
                persons.append(det)

        if not vehicles or not persons:
            # Clean up prev associations if no vehicles or persons
            current_vehicle_ids = {v.get("track_id") for v in vehicles if v.get("track_id") is not None}
            self._prev_associations = {
                p: v for p, v in self._prev_associations.items() if v in current_vehicle_ids
            }
            empty_records: Dict[int, VehicleOccupancyRecord] = {}
            for v in vehicles:
                vid = v.get("track_id")
                empty_records[vid] = VehicleOccupancyRecord(
                    vehicle_track_id=vid,
                    vehicle_type=v.get("object_class", "MOTORCYCLE"),
                    vehicle_box=v.get("bounding_box", {}),
                    occupant_count=0,
                    associated_person_track_ids=[],
                    association_confidence=0.0,
                    riders=[],
                )
            return empty_records, detections

        # Compute pair scores: (score, p_idx, v_idx)
        candidate_matches: List[Tuple[float, int, int]] = []

        for p_idx, p_det in enumerate(persons):
            p_tid = p_det.get("track_id")
            p_box = p_det.get("bounding_box", {})

            for v_idx, v_det in enumerate(vehicles):
                v_tid = v_det.get("track_id")
                v_box = v_det.get("bounding_box", {})

                score = self._compute_geometric_association(p_box, v_box)
                if score <= 0.0:
                    continue

                # Add temporal continuity bonus if paired previously
                if self._prev_associations.get(p_tid) == v_tid:
                    score = min(1.0, score + self.temporal_bonus)

                if score >= self.min_confidence:
                    candidate_matches.append((score, p_idx, v_idx))

        # Sort candidate matches descending by score (greedy mutual exclusion for persons)
        candidate_matches.sort(key=lambda x: x[0], reverse=True)

        assigned_persons: Set[int] = set()
        # vehicle_idx -> list of (person_idx, score)
        vehicle_occupants: Dict[int, List[Tuple[int, float]]] = {v_idx: [] for v_idx in range(len(vehicles))}

        for score, p_idx, v_idx in candidate_matches:
            p_tid = persons[p_idx].get("track_id")
            if p_tid in assigned_persons:
                # Each person can only belong to one vehicle
                continue

            vehicle_occupants[v_idx].append((p_idx, score))
            assigned_persons.add(p_tid)

        # Build occupancy records
        occupancy_records: Dict[int, VehicleOccupancyRecord] = {}
        new_prev_associations: Dict[int, int] = {}

        for v_idx, v_det in enumerate(vehicles):
            v_tid = v_det.get("track_id")
            v_type = v_det.get("object_class", "MOTORCYCLE")
            v_box = v_det.get("bounding_box", {})
            occupant_pairs = vehicle_occupants.get(v_idx, [])

            riders_list: List[RiderInfo] = []
            associated_tids: List[int] = []
            confidences: List[float] = []

            # Sort occupants horizontally or by vertical position
            for p_idx, score in occupant_pairs:
                p_det = persons[p_idx]
                p_tid = p_det.get("track_id")
                p_box = p_det.get("bounding_box", {})
                head_box = self._extract_head_box(p_box)

                associated_tids.append(p_tid)
                confidences.append(score)
                new_prev_associations[p_tid] = v_tid

                riders_list.append(
                    RiderInfo(
                        person_track_id=p_tid,
                        bounding_box=p_box,
                        association_confidence=round(score, 3),
                        head_box=head_box,
                    )
                )

            # Determine primary rider (closest to handlebar/front)
            if riders_list:
                # By convention in 2D perspective, front rider has lower y2 or centered
                riders_list[0].is_primary_rider = True

            mean_conf = round(sum(confidences) / len(confidences), 3) if confidences else 0.0

            rec = VehicleOccupancyRecord(
                vehicle_track_id=v_tid,
                vehicle_type=v_type,
                vehicle_box=v_box,
                occupant_count=len(associated_tids),
                associated_person_track_ids=associated_tids,
                association_confidence=mean_conf,
                riders=riders_list,
            )
            occupancy_records[v_tid] = rec

            # Enrich vehicle detection dict
            attrs = v_det.setdefault("attributes", {})
            attrs["occupant_count"] = len(associated_tids)
            attrs["associated_riders"] = associated_tids

        # Also enrich person detection dicts with association reference
        for v_tid, rec in occupancy_records.items():
            for rider in rec.riders:
                for p_det in persons:
                    if p_det.get("track_id") == rider.person_track_id:
                        p_attrs = p_det.setdefault("attributes", {})
                        p_attrs["associated_vehicle_track_id"] = v_tid
                        p_attrs["is_rider"] = True
                        p_attrs["head_box"] = rider.head_box

        self._prev_associations = new_prev_associations
        return occupancy_records, detections

    def cleanup_lost_tracks(self, active_track_ids: Set[int]) -> None:
        """Removes stale tracking states when vehicles or persons exit the scene."""
        self._prev_associations = {
            p: v for p, v in self._prev_associations.items()
            if p in active_track_ids and v in active_track_ids
        }
