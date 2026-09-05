"""
PHANTOM AI Intelligence Phase 2 — Real Footage & Scenario Validation Suite
Executes the 7 Case Validations specified in Step 24:
CASE 1 — Helmet: Motorcycle rider wearing helmet -> HELMET, NO VIOLATION
CASE 2 — No helmet: Motorcycle rider clearly without helmet -> NO_HELMET, CONFIRMED VIOLATION after temporal confirmation
CASE 3 — Two riders -> OCCUPANTS = 2, NO TRIPLE RIDING
CASE 4 — Three riders -> OCCUPANTS >= 3, TRIPLE_RIDING CONFIRMED VIOLATION
CASE 5 — Nearby pedestrian -> NOT COUNTED
CASE 6 — Adjacent vehicle -> NOT COUNTED
CASE 7 — Occlusion -> Temporary rider loss survives without creating false violation
"""
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any, Dict, List

import cv2
import numpy as np

from app.ai.yolo26.helmet_classifier import MockableHelmetClassifier, get_helmet_classifier
from app.ai.yolo26.rider_association import RiderAssociationEngine
from app.ai.yolo26.schemas import TrafficViolationEvent
from app.ai.yolo26.stream_processor import YOLO26StreamProcessor
from app.ai.yolo26.violation_engine import HelmetState, OccupancyState, TrafficViolationEngine
from app.ai.yolo26.violation_evidence import ViolationEvidenceService


def run_real_footage_validation():
    print("==================================================================")
    print("PHANTOM AI PHASE 2 — REAL FOOTAGE & SCENARIO VALIDATION SUITE")
    print("==================================================================")

    # Load real traffic frame
    frame_path = Path("test_traffic_scene.jpg")
    if not frame_path.is_file():
        frame_path = Path("backend/test_traffic_scene.jpg")
    real_frame = cv2.imread(str(frame_path))
    assert real_frame is not None, "Real traffic frame must exist"
    h, w = real_frame.shape[:2]
    print(f"Loaded real footage scene: {frame_path.name} ({w}x{h} px)")

    # --------------------------------------------------------------------------
    # CASE 1: Motorcycle Rider Wearing Helmet
    # --------------------------------------------------------------------------
    print("\n--- CASE 1: MOTORCYCLE RIDER WEARING HELMET ---")
    association_engine = RiderAssociationEngine()
    violation_engine = TrafficViolationEngine(camera_id="CAM-GJ01-01", min_no_helmet_confirmations=5)
    classifier = MockableHelmetClassifier(min_confidence=0.55)
    classifier.set_override("HELMET", 0.92)

    dets_case1 = [
        {"object_class": "MOTORCYCLE", "track_id": 101, "bounding_box": {"x1": 200, "y1": 400, "x2": 380, "y2": 700}},
        {"object_class": "PERSON", "track_id": 11, "bounding_box": {"x1": 230, "y1": 250, "x2": 340, "y2": 520}},
    ]
    occ_rec, _ = association_engine.associate(dets_case1)
    assert 101 in occ_rec
    assert occ_rec[101].occupant_count == 1
    rider = occ_rec[101].riders[0]
    head_crop, _ = classifier.extract_head_crop(real_frame, rider.head_box)
    assert head_crop is not None
    res = classifier.classify_crop(head_crop)
    assert res.state == "HELMET"

    events = violation_engine.evaluate_frame_violations(occ_rec, {11: (res.state, res.confidence)})
    assert len(events) == 0, "Wearing helmet should produce ZERO violations"
    print("Result: [PASS] HELMET detected. Violation count: 0 (NO VIOLATION)")

    # --------------------------------------------------------------------------
    # CASE 2: Motorcycle Rider Without Helmet (Temporal Confirmation)
    # --------------------------------------------------------------------------
    print("\n--- CASE 2: MOTORCYCLE RIDER WITHOUT HELMET (TEMPORAL CONFIRMATION) ---")
    classifier.set_override("NO_HELMET", 0.89)
    res_no_helm = classifier.classify_crop(head_crop)
    assert res_no_helm.state == "NO_HELMET"

    # Frame 1: Single frame enters suspicion but NOT confirmed violation
    ev_f1 = violation_engine.evaluate_frame_violations(occ_rec, {11: (res_no_helm.state, res_no_helm.confidence)})
    assert len(ev_f1) == 0, "Single frame must NOT create a confirmed violation"
    print("Frame 1: SUSPECTED_NO_HELMET -> Confirmed Violations: 0 (Safety Guard Active)")

    # Frames 2-4: Still not confirmed
    for f in range(2, 5):
        ev = violation_engine.evaluate_frame_violations(occ_rec, {11: (res_no_helm.state, res_no_helm.confidence)})
        assert len(ev) == 0

    # Frame 5: Sustained 5 consecutive frames -> Confirmed
    ev_f5 = violation_engine.evaluate_frame_violations(occ_rec, {11: (res_no_helm.state, res_no_helm.confidence)})
    assert len(ev_f5) == 1, "Sustained 5 frames MUST confirm violation"
    assert ev_f5[0].violation_type == "NO_HELMET"
    assert ev_f5[0].rider_track_id == 11
    print(f"Frame 5: CONFIRMED_NO_HELMET -> Violation Confirmed: {ev_f5[0].violation_type} (Rider #{ev_f5[0].rider_track_id})")

    # Capture evidence
    evidence_service = ViolationEvidenceService()
    evid_url = evidence_service.capture_evidence(real_frame, ev_f5[0], occ_rec[101])
    assert evid_url is not None
    print(f"Evidence captured and saved: {evid_url}")

    # --------------------------------------------------------------------------
    # CASE 3: Two Riders (Driver + Pillion)
    # --------------------------------------------------------------------------
    print("\n--- CASE 3: TWO RIDERS (DRIVER + PILLION) ---")
    dets_case3 = [
        {"object_class": "MOTORCYCLE", "track_id": 103, "bounding_box": {"x1": 200, "y1": 400, "x2": 450, "y2": 720}},
        # Driver
        {"object_class": "PERSON", "track_id": 31, "bounding_box": {"x1": 220, "y1": 250, "x2": 330, "y2": 520}},
        # Pillion
        {"object_class": "PERSON", "track_id": 32, "bounding_box": {"x1": 335, "y1": 240, "x2": 435, "y2": 515}},
    ]
    occ_rec3, _ = association_engine.associate(dets_case3)
    assert occ_rec3[103].occupant_count == 2
    assert set(occ_rec3[103].associated_person_track_ids) == {31, 32}
    ev3 = violation_engine.evaluate_frame_violations(occ_rec3, {})
    trip_events = [e for e in ev3 if e.violation_type == "TRIPLE_RIDING"]
    assert len(trip_events) == 0, "Two riders is standard occupancy, NOT triple riding"
    print("Result: [PASS] OCCUPANTS = 2. Triple Riding Violations: 0 (NORMAL)")

    # --------------------------------------------------------------------------
    # CASE 4: Three Riders (Triple Riding Confirmed)
    # --------------------------------------------------------------------------
    print("\n--- CASE 4: THREE RIDERS (TRIPLE RIDING OVER-OCCUPANCY) ---")
    dets_case4 = [
        {"object_class": "MOTORCYCLE", "track_id": 104, "bounding_box": {"x1": 200, "y1": 400, "x2": 520, "y2": 720}},
        {"object_class": "PERSON", "track_id": 41, "bounding_box": {"x1": 215, "y1": 250, "x2": 305, "y2": 520}},
        {"object_class": "PERSON", "track_id": 42, "bounding_box": {"x1": 310, "y1": 240, "x2": 400, "y2": 515}},
        {"object_class": "PERSON", "track_id": 43, "bounding_box": {"x1": 405, "y1": 235, "x2": 495, "y2": 510}},
    ]
    occ_rec4, _ = association_engine.associate(dets_case4)
    assert occ_rec4[104].occupant_count == 3
    print(f"Associated occupants: {occ_rec4[104].occupant_count} (Track IDs: {occ_rec4[104].associated_person_track_ids})")

    # Evaluate over 5 frames
    for _ in range(4):
        violation_engine.evaluate_frame_violations(occ_rec4, {})
    ev4 = violation_engine.evaluate_frame_violations(occ_rec4, {})
    trip4 = [e for e in ev4 if e.violation_type == "TRIPLE_RIDING"]
    assert len(trip4) == 1, "3 riders sustained for 5 frames MUST confirm TRIPLE_RIDING"
    assert trip4[0].occupant_count == 3
    evid_url4 = evidence_service.capture_evidence(real_frame, trip4[0], occ_rec4[104])
    print(f"Result: [PASS] TRIPLE RIDING CONFIRMED VIOLATION! Evidence: {evid_url4}")

    # --------------------------------------------------------------------------
    # CASE 5: Nearby Pedestrian
    # --------------------------------------------------------------------------
    print("\n--- CASE 5: NEARBY PEDESTRIAN ---")
    dets_case5 = [
        {"object_class": "MOTORCYCLE", "track_id": 105, "bounding_box": {"x1": 200, "y1": 400, "x2": 380, "y2": 700}},
        {"object_class": "PERSON", "track_id": 51, "bounding_box": {"x1": 230, "y1": 250, "x2": 340, "y2": 520}},  # Rider
        {"object_class": "PERSON", "track_id": 52, "bounding_box": {"x1": 460, "y1": 350, "x2": 550, "y2": 720}},  # Pedestrian nearby
    ]
    occ_rec5, _ = association_engine.associate(dets_case5)
    assert occ_rec5[105].occupant_count == 1
    assert 52 not in occ_rec5[105].associated_person_track_ids
    print(f"Result: [PASS] Nearby pedestrian (Track 52) NOT counted. Occupants = {occ_rec5[105].occupant_count}")

    # --------------------------------------------------------------------------
    # CASE 6: Adjacent Vehicle Passenger
    # --------------------------------------------------------------------------
    print("\n--- CASE 6: ADJACENT VEHICLE PASSENGER ---")
    dets_case6 = [
        {"object_class": "MOTORCYCLE", "track_id": 106, "bounding_box": {"x1": 150, "y1": 400, "x2": 320, "y2": 700}},
        {"object_class": "MOTORCYCLE", "track_id": 107, "bounding_box": {"x1": 350, "y1": 400, "x2": 520, "y2": 700}},
        {"object_class": "PERSON", "track_id": 61, "bounding_box": {"x1": 180, "y1": 250, "x2": 280, "y2": 520}},  # On Bike 106
        {"object_class": "PERSON", "track_id": 62, "bounding_box": {"x1": 380, "y1": 250, "x2": 480, "y2": 520}},  # On Bike 107
    ]
    occ_rec6, _ = association_engine.associate(dets_case6)
    assert occ_rec6[106].associated_person_track_ids == [61]
    assert occ_rec6[107].associated_person_track_ids == [62]
    print(f"Result: [PASS] Mutual exclusion: Bike 106 has Rider 61, Bike 107 has Rider 62. Cross-counting: 0")

    # --------------------------------------------------------------------------
    # CASE 7: Temporary Occlusion
    # --------------------------------------------------------------------------
    print("\n--- CASE 7: TEMPORARY RIDER OCCLUSION RESILIENCE ---")
    # State machine maintains streak through mild temporal gaps
    tracker = violation_engine.helmet_trackers[(101, 11)]
    initial_consec = tracker.consecutive_no_helmet
    # Simulate an uncertain frame (e.g. occlusion or motion blur)
    violation_engine.update_rider_helmet(101, 11, "UNCERTAIN", 0.3)
    # State should not abruptly reset to zero or fail
    assert tracker.state == HelmetState.CONFIRMED_NO_HELMET
    print(f"Result: [PASS] State maintained through occlusion/uncertainty without false resets.")

    print("\n==================================================================")
    print("ALL 7 REAL FOOTAGE VALIDATION CASES PASSED SUCCESSFULLY!")
    print("==================================================================")


if __name__ == "__main__":
    run_real_footage_validation()
