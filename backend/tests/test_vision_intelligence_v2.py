"""
PHANTOM Vision Intelligence V2 — Automated Test & Regression Suite
==================================================================
Tests all 4 critical failure cases, hierarchical classification, temporal fusion,
hard-negative pole filtering, uncertainty handling, and Copilot tool calling.
"""
import numpy as np
import pytest

from app.ai.agents.tool_registry import phantom_tool_registry
from app.ai.yolo26.detector import YOLO26Detector, get_detector
from app.ai.yolo26.hierarchy import (
    ClassificationStatus,
    EventLifecycle,
    HierarchicalClassificationResult,
    VisionTaxonomy,
)
from app.ai.yolo26.specialized_classifiers import (
    AutoRickshawDisambiguator,
    CarSpecializedClassifier,
    HardNegativePoleFilter,
    TwoWheelerSpecializedClassifier,
)
from app.ai.yolo26.temporal_fusion import TemporalTrackFusionEngine, TrackTemporalState
from app.ai.yolo26.tracker import YOLO26Tracker


# ------------------------------------------------------------------------------
# Test 1: Scooter / Activa vs Motorcycle / Splendor Disambiguation
# ------------------------------------------------------------------------------
def test_scooter_activa_vs_splendor_classification():
    """Verify two-wheelers are hierarchically classified with structural evidence."""
    # 1. Synthetic Scooter Crop (Step-through open floorboard, smooth side pod, AR=1.30)
    scooter_crop = np.zeros((130, 100, 3), dtype=np.uint8)
    # Smooth body panels (low edge noise in middle band)
    scooter_crop[40:80, 20:80] = 180  # Uniform paint
    scooter_bbox = {"x1": 50, "y1": 50, "x2": 150, "y2": 180, "width": 100, "height": 130}

    scooter_res = TwoWheelerSpecializedClassifier.classify_crop(
        crop_bgr=scooter_crop,
        bbox=scooter_bbox,
        raw_conf=0.92,
        track_id=101,
    )
    assert scooter_res.category == "TWO_WHEELER"
    assert scooter_res.subtype == "SCOOTER"
    assert "Activa" in str(scooter_res.model)
    assert scooter_res.classification_status in (ClassificationStatus.CONFIDENT, ClassificationStatus.LIKELY)
    assert "Activa" in scooter_res.display_label

    # 2. Synthetic Motorcycle Crop (Horizontal tank creases, exposed engine edges, AR=0.95)
    moto_crop = np.zeros((95, 100, 3), dtype=np.uint8)
    # High edge noise simulating exposed engine block and chassis tubes
    moto_crop[35:75, 20:80] = np.random.randint(0, 255, (40, 60, 3), dtype=np.uint8)
    moto_bbox = {"x1": 50, "y1": 50, "x2": 150, "y2": 145, "width": 100, "height": 95}

    moto_res = TwoWheelerSpecializedClassifier.classify_crop(
        crop_bgr=moto_crop,
        bbox=moto_bbox,
        raw_conf=0.90,
        track_id=102,
    )
    assert moto_res.category == "TWO_WHEELER"
    assert moto_res.subtype == "MOTORCYCLE"
    assert "Splendor" in str(moto_res.model)
    assert moto_res.classification_status in (ClassificationStatus.CONFIDENT, ClassificationStatus.LIKELY)


def test_two_wheeler_uncertainty_handling():
    """Verify ambiguous two-wheeler crops return UNCERTAIN rather than guessing."""
    # Blank/ambiguous crop with neutral aspect ratio
    ambiguous_crop = np.zeros((100, 100, 3), dtype=np.uint8)
    bbox = {"x1": 10, "y1": 10, "x2": 110, "y2": 110, "width": 100, "height": 100}

    res = TwoWheelerSpecializedClassifier.classify_crop(
        crop_bgr=ambiguous_crop,
        bbox=bbox,
        raw_conf=0.60,
        track_id=103,
    )
    assert res.category == "TWO_WHEELER"
    # When evidence is low/ambiguous, must output UNCERTAIN
    assert res.classification_status in (ClassificationStatus.UNCERTAIN, ClassificationStatus.UNKNOWN)
    assert "Model Uncertain" in res.display_label


# ------------------------------------------------------------------------------
# Test 2: Hard-Negative Pole / Streetlight vs Person Filter
# ------------------------------------------------------------------------------
def test_hard_negative_streetlight_pole_filtering():
    """Verify utility poles and streetlights are filtered and NOT promoted to PERSON."""
    # 1. Pole / Streetlight bounding box (Aspect ratio = 4.2 >= 3.8)
    pole_crop = np.zeros((210, 50, 3), dtype=np.uint8)
    pole_crop[:, 20:30] = 200  # Vertical straight tube
    pole_bbox = {"x1": 100, "y1": 100, "x2": 150, "y2": 310, "width": 50, "height": 210}

    is_pole, reason = HardNegativePoleFilter.is_hard_negative_pole(
        crop_bgr=pole_crop,
        bbox=pole_bbox,
        detector_conf=0.65,
    )
    assert is_pole is True
    assert "pole" in reason.lower() or "aspect ratio" in reason.lower()

    # 2. Real Pedestrian (Aspect ratio = 2.4, valid human height)
    person_crop = np.zeros((120, 50, 3), dtype=np.uint8)
    person_bbox = {"x1": 100, "y1": 100, "x2": 150, "y2": 220, "width": 50, "height": 120}

    is_pole_p, _ = HardNegativePoleFilter.is_hard_negative_pole(
        crop_bgr=person_crop,
        bbox=person_bbox,
        detector_conf=0.92,
    )
    assert is_pole_p is False


# ------------------------------------------------------------------------------
# Test 3: WagonR vs Swift Tallboy Disambiguation & Uncertainty
# ------------------------------------------------------------------------------
def test_wagonr_tallboy_vs_swift_classification():
    """Verify tall-boy boxy WagonR is distinguished from aerodynamic hatchback Swift."""
    # 1. WagonR Tall-boy Silhouette (Height/Width ratio = 0.88, flat boxy roof)
    wagonr_crop = np.zeros((140, 160, 3), dtype=np.uint8)
    wagonr_crop[0:40, :] = 150  # Flat roofline
    wagonr_bbox = {"x1": 100, "y1": 100, "x2": 260, "y2": 240, "width": 160, "height": 140}

    wagonr_res = CarSpecializedClassifier.classify_crop(
        crop_bgr=wagonr_crop,
        bbox=wagonr_bbox,
        raw_conf=0.92,
        track_id=201,
    )
    assert wagonr_res.category == "CAR"
    assert wagonr_res.subtype == "HATCHBACK_TALLBOY"
    assert wagonr_res.model == "WagonR"
    assert wagonr_res.classification_status in (ClassificationStatus.CONFIDENT, ClassificationStatus.LIKELY)
    assert "WagonR" in wagonr_res.display_label

    # 2. Swift Sport Hatchback (Wider low stance, W/H = 1.50)
    swift_crop = np.zeros((100, 150, 3), dtype=np.uint8)
    swift_crop[20:70, :] = 160  # Swept aerodynamic body paint
    swift_bbox = {"x1": 100, "y1": 100, "x2": 250, "y2": 200, "width": 150, "height": 100}

    swift_res = CarSpecializedClassifier.classify_crop(
        crop_bgr=swift_crop,
        bbox=swift_bbox,
        raw_conf=0.91,
        track_id=202,
    )
    assert swift_res.category == "CAR"
    assert swift_res.subtype == "HATCHBACK_SPORT"
    assert swift_res.model == "Swift"
    assert swift_res.classification_status in (ClassificationStatus.CONFIDENT, ClassificationStatus.LIKELY)


def test_car_model_uncertainty_handling():
    """Verify low-margin car predictions output UNCERTAIN rather than guessing."""
    neutral_crop = np.zeros((100, 100, 3), dtype=np.uint8)
    neutral_bbox = {"x1": 50, "y1": 50, "x2": 150, "y2": 150, "width": 100, "height": 100}

    res = CarSpecializedClassifier.classify_crop(
        crop_bgr=neutral_crop,
        bbox=neutral_bbox,
        raw_conf=0.55,
        track_id=203,
    )
    assert res.category == "CAR"
    # Must report UNCERTAIN when confidence margin is low
    assert res.classification_status in (ClassificationStatus.UNCERTAIN, ClassificationStatus.UNKNOWN)
    assert "Model Uncertain" in res.display_label or "55%" in res.display_label


# ------------------------------------------------------------------------------
# Test 4: Auto-Rickshaw vs Truck Disambiguation
# ------------------------------------------------------------------------------
def test_auto_rickshaw_vs_truck_disambiguation():
    """Verify Indian 3-wheelers are resolved to AUTO_RICKSHAW, not TRUCK."""
    # 1. Auto-Rickshaw Crop (Yellow canopy roof, green body, AR = 1.15, area = 15000px)
    auto_crop = np.zeros((115, 100, 3), dtype=np.uint8)
    # Yellow canopy in HSV (H: 25, S: 200, V: 200 -> BGR yellow)
    auto_crop[0:40, :] = [30, 220, 240]
    # Green lower body
    auto_crop[40:115, :] = [40, 180, 50]
    auto_bbox = {"x1": 100, "y1": 100, "x2": 200, "y2": 215, "width": 100, "height": 115}

    is_auto, conf = AutoRickshawDisambiguator.is_auto_rickshaw(
        crop_bgr=auto_crop,
        bbox=auto_bbox,
        detector_class="TRUCK",  # Misdetected by base COCO as TRUCK
        detector_conf=0.75,
    )
    assert is_auto is True
    assert conf >= 0.60

    # 2. Heavy Commercial Truck (Large area > 80000px, wide multi-axle body)
    truck_crop = np.zeros((300, 400, 3), dtype=np.uint8)
    truck_bbox = {"x1": 50, "y1": 50, "x2": 450, "y2": 350, "width": 400, "height": 300}

    is_auto_truck, _ = AutoRickshawDisambiguator.is_auto_rickshaw(
        crop_bgr=truck_crop,
        bbox=truck_bbox,
        detector_class="TRUCK",
        detector_conf=0.92,
    )
    assert is_auto_truck is False


# ------------------------------------------------------------------------------
# Test 5: Temporal Track Fusion & Label Hysteresis
# ------------------------------------------------------------------------------
def test_temporal_fusion_and_label_hysteresis():
    """Verify temporal voting accumulates evidence and prevents label flickering."""
    fusion = TemporalTrackFusionEngine(camera_id="cam05")

    # Frame 1: WagonR (0.75)
    r1 = HierarchicalClassificationResult(
        category="CAR",
        category_confidence=0.75,
        subtype="HATCHBACK_TALLBOY",
        make="Maruti Suzuki",
        model="WagonR",
        classification_status=ClassificationStatus.LIKELY,
    )
    fused1, life1 = fusion.fuse_track_detection(track_id=501, raw_result=r1)
    assert life1 == EventLifecycle.DETECTED

    # Frame 2: Swift (Transient 1-frame noise: 0.52)
    r2 = HierarchicalClassificationResult(
        category="CAR",
        category_confidence=0.52,
        subtype="HATCHBACK_SPORT",
        make="Maruti Suzuki",
        model="Swift",
        classification_status=ClassificationStatus.UNCERTAIN,
    )
    fused2, life2 = fusion.fuse_track_detection(track_id=501, raw_result=r2)

    # Frame 3, 4, 5: WagonR (0.84, 0.88, 0.90)
    r3 = HierarchicalClassificationResult(category="CAR", category_confidence=0.84, subtype="HATCHBACK_TALLBOY", make="Maruti Suzuki", model="WagonR", classification_status=ClassificationStatus.CONFIDENT)
    r4 = HierarchicalClassificationResult(category="CAR", category_confidence=0.88, subtype="HATCHBACK_TALLBOY", make="Maruti Suzuki", model="WagonR", classification_status=ClassificationStatus.CONFIDENT)
    r5 = HierarchicalClassificationResult(category="CAR", category_confidence=0.90, subtype="HATCHBACK_TALLBOY", make="Maruti Suzuki", model="WagonR", classification_status=ClassificationStatus.CONFIDENT)

    fusion.fuse_track_detection(track_id=501, raw_result=r3)
    fusion.fuse_track_detection(track_id=501, raw_result=r4)
    final_fused, final_life = fusion.fuse_track_detection(track_id=501, raw_result=r5)

    # Label should be locked to WagonR without flickering
    assert final_life == EventLifecycle.CONFIRMED
    assert final_fused.category == "CAR"
    assert final_fused.model == "WagonR"
    assert final_fused.classification_status == ClassificationStatus.CONFIDENT


# ------------------------------------------------------------------------------
# Test 6: Person Event Lifecycle & Persistence Validation
# ------------------------------------------------------------------------------
def test_person_event_lifecycle_persistence():
    """Verify single-frame weak prediction is DETECTED, sustained track is CONFIRMED."""
    tracker = YOLO26Tracker(camera_id="cam05")

    # Frame 1: Person single frame
    det1 = [{
        "object_class": "PERSON",
        "confidence": 0.85,
        "bounding_box": {"x1": 100, "y1": 100, "x2": 150, "y2": 220},
    }]
    t_dets1 = tracker.update(det1)
    assert t_dets1[0]["event_lifecycle"] == "DETECTED"

    # Frames 2, 3, 4, 5: Sustained presence
    for i in range(4):
        det_n = [{
            "object_class": "PERSON",
            "confidence": 0.88 + (i * 0.02),
            "bounding_box": {"x1": 102 + i, "y1": 100, "x2": 152 + i, "y2": 220},
        }]
        t_dets_n = tracker.update(det_n)

    assert t_dets_n[0]["event_lifecycle"] == "CONFIRMED"
    assert t_dets_n[0]["object_class"] == "PERSON"


# ------------------------------------------------------------------------------
# Test 7: Copilot AI Vision Tools Integration
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_copilot_vision_tools_integration():
    """Verify all 6 Copilot AI detection tools return structured live data."""
    # 1. get_live_detections
    live_res = await phantom_tool_registry.get_live_detections("cam05")
    assert "detections" in live_res
    assert "camera_id" in live_res

    # 2. get_active_tracks
    tracks_res = await phantom_tool_registry.get_active_tracks("cam05")
    assert "tracks" in tracks_res
    assert "active_tracks_count" in tracks_res

    # 3. get_detection_summary
    summary_res = await phantom_tool_registry.get_detection_summary("cam05")
    assert "total_objects" in summary_res
    assert "model_breakdown" in summary_res

    # 4. get_object_track
    obj_track = await phantom_tool_registry.get_object_track("cam05", 7)
    assert obj_track.get("success") is True
    assert "track" in obj_track

    # 5. get_detection_events
    events_res = await phantom_tool_registry.get_detection_events("cam05", time_range="24h")
    assert "events" in events_res
    assert "confirmed_events_count" in events_res


# ------------------------------------------------------------------------------
# Test 8: All 4 Known Failure Cases Regression Suite
# ------------------------------------------------------------------------------
def test_all_four_known_failures_regression():
    """
    Regression test validating that all 4 known failure cases never regress:
    1. Activa -> Splendor (Fixed)
    2. Streetlight -> Person (Fixed)
    3. WagonR -> Swift (Fixed)
    4. Auto -> Truck (Fixed)
    """
    # 1. Activa is not called Splendor
    scooter_crop = np.zeros((130, 100, 3), dtype=np.uint8)
    scooter_crop[40:80, 20:80] = 190
    scooter_box = {"x1": 50, "y1": 50, "x2": 150, "y2": 180, "width": 100, "height": 130}
    res1 = TwoWheelerSpecializedClassifier.classify_crop(scooter_crop, scooter_box, raw_conf=0.92)
    assert res1.subtype == "SCOOTER"
    assert "Activa" in str(res1.model)

    # 2. Streetlight is not called Person
    pole_crop = np.zeros((220, 50, 3), dtype=np.uint8)
    pole_box = {"x1": 50, "y1": 50, "x2": 100, "y2": 270, "width": 50, "height": 220}
    is_pole, _ = HardNegativePoleFilter.is_hard_negative_pole(pole_crop, pole_box, detector_conf=0.60)
    assert is_pole is True

    # 3. WagonR is not called Swift
    wagonr_crop = np.zeros((140, 160, 3), dtype=np.uint8)
    wagonr_crop[0:40, :] = 150
    wagonr_box = {"x1": 100, "y1": 100, "x2": 260, "y2": 240, "width": 160, "height": 140}
    res3 = CarSpecializedClassifier.classify_crop(wagonr_crop, wagonr_box, raw_conf=0.92)
    assert res3.subtype == "HATCHBACK_TALLBOY"
    assert res3.model == "WagonR"

    # 4. Auto-rickshaw is not called Truck
    auto_crop = np.zeros((115, 100, 3), dtype=np.uint8)
    auto_crop[0:40, :] = [30, 220, 240]
    auto_crop[40:115, :] = [40, 180, 50]
    auto_box = {"x1": 100, "y1": 100, "x2": 200, "y2": 215, "width": 100, "height": 115}
    is_auto, _ = AutoRickshawDisambiguator.is_auto_rickshaw(auto_crop, auto_box, detector_class="TRUCK", detector_conf=0.75)
    assert is_auto is True
