"""
Automated Test Suite for PHANTOM AI Intelligence Phase 2
Covers:
1. Rider <-> Two-Wheeler Association (geometry, saddle zone, pedestrian rejection, adjacent vehicle exclusion)
2. Helmet Intelligence (HELMET, NO_HELMET, UNCERTAIN, TURBAN, low resolution handling, zero fake heuristics)
3. Triple Riding (1 person solo, 2 pillion, 3+ triple riding, pedestrian rejection)
4. Temporal Confirmation State Machines (single-frame safety, sustained confirmation, resolution)
5. Alert Deduplication & Cooldown (suppression of duplicate alert floods)
6. StreamProcessor & End-to-End Pipeline Integration
"""
from datetime import datetime, timezone
import os
from typing import Any, Dict, List
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import numpy as np
import pytest

from app.ai.yolo26.config import YOLO26Config
from app.ai.yolo26.helmet_classifier import (
    DeepLearningHelmetClassifier,
    HelmetClassificationResult,
    MockableHelmetClassifier,
    get_helmet_classifier,
)
from app.ai.yolo26.rider_association import RiderAssociationEngine, VehicleOccupancyRecord
from app.ai.yolo26.schemas import (
    BoundingBox,
    DetectedObject,
    TrafficViolationEvent,
    VehicleAttributes,
)
from app.ai.yolo26.stream_processor import YOLO26StreamProcessor
from app.ai.yolo26.violation_engine import (
    HelmetState,
    OccupancyState,
    TrafficViolationEngine,
)
from app.models.camera import Camera
from app.services.yolo26_alert_service import YOLO26AlertService


# ------------------------------------------------------------------------------
# 1. Rider Association Unit Tests
# ------------------------------------------------------------------------------
class TestRiderAssociation:

    def setup_method(self):
        self.engine = RiderAssociationEngine(min_association_confidence=0.45)

    def test_motorcycle_with_single_rider_associated(self):
        """A person positioned in motorcycle saddle is successfully associated as solo rider."""
        # Motorcycle box: [x1=100, y1=200, x2=250, y2=400] (w=150, h=200, cx=175)
        # Rider box: [x1=120, y1=100, x2=200, y2=280] (w=80, h=180, cx=160, py2 inside motorcycle)
        detections = [
            {
                "object_class": "MOTORCYCLE",
                "track_id": 101,
                "bounding_box": {"x1": 100.0, "y1": 200.0, "x2": 250.0, "y2": 400.0},
            },
            {
                "object_class": "PERSON",
                "track_id": 1,
                "bounding_box": {"x1": 120.0, "y1": 100.0, "x2": 200.0, "y2": 280.0},
            },
        ]
        records, enriched = self.engine.associate(detections)

        assert 101 in records
        rec = records[101]
        assert rec.occupant_count == 1
        assert rec.associated_person_track_ids == [1]
        assert rec.riders[0].is_primary_rider is True
        assert rec.riders[0].head_box is not None
        assert rec.riders[0].head_box["y1"] == 100.0

    def test_pedestrian_beside_motorcycle_rejected(self):
        """A pedestrian standing beside the motorcycle is NOT associated as an occupant."""
        # Motorcycle box: [x1=100, y1=200, x2=250, y2=400]
        # Pedestrian standing to the right: [x1=300, y1=150, x2=360, y2=410] (cx=330, outside margin)
        detections = [
            {
                "object_class": "MOTORCYCLE",
                "track_id": 102,
                "bounding_box": {"x1": 100.0, "y1": 200.0, "x2": 250.0, "y2": 400.0},
            },
            {
                "object_class": "PERSON",
                "track_id": 2,
                "bounding_box": {"x1": 300.0, "y1": 150.0, "x2": 360.0, "y2": 410.0},
            },
        ]
        records, _ = self.engine.associate(detections)
        assert records[102].occupant_count == 0
        assert records[102].associated_person_track_ids == []

    def test_pedestrian_with_ground_contact_below_wheels_rejected(self):
        """A person whose feet extend far below the motorcycle wheels is rejected as a pedestrian."""
        # Motorcycle box: [x1=100, y1=200, x2=250, y2=400] (vy2=400, vh=200)
        # Person walking in foreground: py2=480 (feet touch ground below tires)
        detections = [
            {
                "object_class": "MOTORCYCLE",
                "track_id": 103,
                "bounding_box": {"x1": 100.0, "y1": 200.0, "x2": 250.0, "y2": 400.0},
            },
            {
                "object_class": "PERSON",
                "track_id": 3,
                "bounding_box": {"x1": 120.0, "y1": 250.0, "x2": 200.0, "y2": 480.0},
            },
        ]
        records, _ = self.engine.associate(detections)
        assert records[103].occupant_count == 0

    def test_adjacent_motorcycles_mutual_exclusion(self):
        """When two motorcycles are adjacent, one person cannot be assigned to both."""
        # Motorcycle A: [100, 200, 250, 400] (center cx=175)
        # Motorcycle B: [260, 200, 410, 400] (center cx=335)
        # Rider on Bike A: [110, 100, 190, 280] (center cx=150)
        detections = [
            {
                "object_class": "MOTORCYCLE",
                "track_id": 201,
                "bounding_box": {"x1": 100.0, "y1": 200.0, "x2": 250.0, "y2": 400.0},
            },
            {
                "object_class": "MOTORCYCLE",
                "track_id": 202,
                "bounding_box": {"x1": 260.0, "y1": 200.0, "x2": 410.0, "y2": 400.0},
            },
            {
                "object_class": "PERSON",
                "track_id": 10,
                "bounding_box": {"x1": 110.0, "y1": 100.0, "x2": 190.0, "y2": 280.0},
            },
        ]
        records, _ = self.engine.associate(detections)
        assert records[201].occupant_count == 1
        assert records[201].associated_person_track_ids == [10]
        assert records[202].occupant_count == 0
        assert records[202].associated_person_track_ids == []

    def test_scooter_pillion_passenger_associated(self):
        """A scooter with two riders (driver + pillion) counts 2 occupants."""
        detections = [
            {
                "object_class": "SCOOTER",
                "track_id": 301,
                "bounding_box": {"x1": 100.0, "y1": 200.0, "x2": 280.0, "y2": 420.0},
            },
            # Front driver
            {
                "object_class": "PERSON",
                "track_id": 21,
                "bounding_box": {"x1": 115.0, "y1": 100.0, "x2": 190.0, "y2": 300.0},
            },
            # Rear pillion passenger
            {
                "object_class": "PERSON",
                "track_id": 22,
                "bounding_box": {"x1": 190.0, "y1": 95.0, "x2": 265.0, "y2": 295.0},
            },
        ]
        records, _ = self.engine.associate(detections)
        assert records[301].occupant_count == 2
        assert set(records[301].associated_person_track_ids) == {21, 22}


# ------------------------------------------------------------------------------
# 2. Helmet Classification Unit Tests
# ------------------------------------------------------------------------------
class TestHelmetIntelligence:

    def setup_method(self):
        self.classifier = DeepLearningHelmetClassifier(min_confidence=0.55)

    def test_empty_or_degenerate_crop_returns_uncertain(self):
        """Empty or degenerate crops return UNCERTAIN with crop_valid=False."""
        res = self.classifier.classify_crop(np.zeros((0, 0, 3), dtype=np.uint8))
        assert res.state == "UNCERTAIN"
        assert res.is_violation_candidate is False
        assert res.crop_valid is False

    def test_low_resolution_crop_returns_uncertain(self):
        """Tiny crops smaller than 16x16 px return UNCERTAIN to prevent false violations."""
        tiny_crop = np.zeros((10, 12, 3), dtype=np.uint8)
        res = self.classifier.classify_crop(tiny_crop)
        assert res.state == "UNCERTAIN"
        assert res.is_violation_candidate is False
        assert "LOW_RESOLUTION" in str(res.uncertain_reason)

    def test_mockable_classifier_injected_states(self):
        """Test mockable classifier supports HELMET, NO_HELMET, UNCERTAIN, TURBAN."""
        mock_cls = MockableHelmetClassifier(min_confidence=0.55)
        dummy_crop = np.full((50, 50, 3), 128, dtype=np.uint8)

        # Helmet
        mock_cls.set_override("HELMET", 0.90)
        res_helmet = mock_cls.classify_crop(dummy_crop)
        assert res_helmet.state == "HELMET"
        assert res_helmet.is_violation_candidate is False

        # No Helmet
        mock_cls.set_override("NO_HELMET", 0.88)
        res_no_helmet = mock_cls.classify_crop(dummy_crop)
        assert res_no_helmet.state == "NO_HELMET"
        assert res_no_helmet.is_violation_candidate is True

        # Turban (Does NOT cause violation candidate!)
        mock_cls.set_override("TURBAN", 0.85)
        res_turban = mock_cls.classify_crop(dummy_crop)
        assert res_turban.state == "TURBAN"
        assert res_turban.is_violation_candidate is False

        # Uncertain
        mock_cls.set_override("UNCERTAIN", 0.40)
        res_unc = mock_cls.classify_crop(dummy_crop)
        assert res_unc.state == "UNCERTAIN"
        assert res_unc.is_violation_candidate is False


# ------------------------------------------------------------------------------
# 3. Triple Riding & Occupancy Counting Unit Tests
# ------------------------------------------------------------------------------
class TestTripleRidingDetection:

    def setup_method(self):
        self.engine = RiderAssociationEngine(min_association_confidence=0.45)

    def test_three_associated_occupants_detected(self):
        """Three riders on a single motorcycle produces occupant_count = 3."""
        detections = [
            {
                "object_class": "MOTORCYCLE",
                "track_id": 401,
                "bounding_box": {"x1": 100.0, "y1": 200.0, "x2": 320.0, "y2": 420.0},
            },
            # Rider 1
            {"object_class": "PERSON", "track_id": 1, "bounding_box": {"x1": 110.0, "y1": 90.0, "x2": 170.0, "y2": 290.0}},
            # Rider 2
            {"object_class": "PERSON", "track_id": 2, "bounding_box": {"x1": 175.0, "y1": 85.0, "x2": 235.0, "y2": 285.0}},
            # Rider 3
            {"object_class": "PERSON", "track_id": 3, "bounding_box": {"x1": 240.0, "y1": 80.0, "x2": 305.0, "y2": 280.0}},
        ]
        records, _ = self.engine.associate(detections)
        assert records[401].occupant_count == 3
        assert len(records[401].associated_person_track_ids) == 3

    def test_four_associated_occupants_detected(self):
        """Four riders on a motorcycle produces occupant_count = 4."""
        detections = [
            {
                "object_class": "MOTORCYCLE",
                "track_id": 402,
                "bounding_box": {"x1": 100.0, "y1": 200.0, "x2": 350.0, "y2": 420.0},
            },
            {"object_class": "PERSON", "track_id": 1, "bounding_box": {"x1": 105.0, "y1": 90.0, "x2": 155.0, "y2": 290.0}},
            {"object_class": "PERSON", "track_id": 2, "bounding_box": {"x1": 160.0, "y1": 85.0, "x2": 210.0, "y2": 285.0}},
            {"object_class": "PERSON", "track_id": 3, "bounding_box": {"x1": 215.0, "y1": 80.0, "x2": 265.0, "y2": 280.0}},
            {"object_class": "PERSON", "track_id": 4, "bounding_box": {"x1": 270.0, "y1": 75.0, "x2": 325.0, "y2": 275.0}},
        ]
        records, _ = self.engine.associate(detections)
        assert records[402].occupant_count == 4


# ------------------------------------------------------------------------------
# 4. Temporal State Machine & Duplicate Suppression Unit Tests
# ------------------------------------------------------------------------------
class TestTemporalViolationEngine:

    def setup_method(self):
        self.v_engine = TrafficViolationEngine(
            camera_id="CAM-TEST-01",
            min_no_helmet_confirmations=5,
            min_triple_riding_confirmations=5,
            min_track_age=3,
            cooldown_seconds=60,
        )

    def test_single_no_helmet_frame_does_not_confirm_violation(self):
        """A single frame of NO_HELMET enters SUSPECTED state but does NOT generate confirmed alert."""
        state, is_confirmed = self.v_engine.update_rider_helmet(
            vehicle_track_id=10,
            person_track_id=1,
            helmet_state="NO_HELMET",
            confidence=0.85,
        )
        assert state == HelmetState.SUSPECTED_NO_HELMET
        assert is_confirmed is False

    def test_sustained_no_helmet_confirms_violation(self):
        """Five consecutive frames of NO_HELMET transitions to CONFIRMED_NO_HELMET."""
        for frame_idx in range(4):
            state, is_conf = self.v_engine.update_rider_helmet(10, 1, "NO_HELMET", 0.85)
            assert is_conf is False

        # Frame 5 (meets threshold of 5 confirmations and track age >= 3)
        state, is_conf = self.v_engine.update_rider_helmet(10, 1, "NO_HELMET", 0.85)
        assert state == HelmetState.CONFIRMED_NO_HELMET
        assert is_conf is True

    def test_helmet_wearing_resolves_violation(self):
        """If a rider is observed wearing a helmet after violation, state resolves."""
        # Confirm violation
        for _ in range(5):
            self.v_engine.update_rider_helmet(10, 1, "NO_HELMET", 0.85)

        # Rider puts on helmet
        state, _ = self.v_engine.update_rider_helmet(10, 1, "HELMET", 0.90)
        assert state == HelmetState.RESOLVED

    def test_triple_riding_temporal_confirmation_and_deduplication(self):
        """Triple riding requires sustained occupancy and does not flood duplicate alerts."""
        occ_rec = VehicleOccupancyRecord(
            vehicle_track_id=50,
            vehicle_type="MOTORCYCLE",
            vehicle_box={"x1": 100, "y1": 200, "x2": 300, "y2": 400},
            occupant_count=3,
            associated_person_track_ids=[1, 2, 3],
            association_confidence=0.82,
            riders=[],
        )

        # Frames 1-4: no alert
        for _ in range(4):
            events = self.v_engine.evaluate_frame_violations({50: occ_rec}, {})
            assert len(events) == 0

        # Frame 5: Sustained triple riding confirmed -> exactly 1 event generated
        events = self.v_engine.evaluate_frame_violations({50: occ_rec}, {})
        assert len(events) == 1
        assert events[0].violation_type == "TRIPLE_RIDING"
        assert events[0].occupant_count == 3

        # Frame 6 (immediate next frame): Cooldown deduplication suppresses repeat alert
        events_next = self.v_engine.evaluate_frame_violations({50: occ_rec}, {})
        assert len(events_next) == 0

    def test_track_loss_cleans_up_memory(self):
        """Tracks exiting the frame are cleanly purged from state machines."""
        for _ in range(3):
            self.v_engine.update_rider_helmet(99, 5, "NO_HELMET", 0.80)
            self.v_engine.update_vehicle_occupancy(99, 3, 0.80)

        assert (99, 5) in self.v_engine.helmet_trackers
        assert 99 in self.v_engine.triple_riding_trackers

        # Active tracks no longer contain 99
        self.v_engine.cleanup_lost_tracks(active_track_ids={101, 102})
        assert (99, 5) not in self.v_engine.helmet_trackers
        assert 99 not in self.v_engine.triple_riding_trackers


# ------------------------------------------------------------------------------
# 5. Alert Service & Database Integration Unit Tests
# ------------------------------------------------------------------------------
class TestViolationAlertService:

    @pytest.mark.asyncio
    async def test_alert_service_processes_no_helmet_violation(self):
        """YOLO26AlertService records NO_HELMET violation and publishes event."""
        service = YOLO26AlertService()
        mock_session = AsyncMock()
        mock_camera = MagicMock(spec=Camera)
        mock_camera.id = uuid.uuid4()
        mock_camera.name = "SG-HIGHWAY-CAM-01"

        violation = TrafficViolationEvent(
            violation_type="NO_HELMET",
            camera_id=str(mock_camera.id),
            vehicle_track_id=15,
            vehicle_type="MOTORCYCLE",
            person_track_ids=[105],
            rider_track_id=105,
            helmet_state="NO_HELMET",
            confidence=0.88,
            severity="MEDIUM",
            status="CONFIRMED",
            evidence_reference="/static/evidence/evid_no_helmet_15.jpg",
        )

        with patch("app.services.yolo26_alert_service.event_publisher.publish", new_callable=AsyncMock) as mock_pub:
            alert = await service.process_violation_event(
                session=mock_session,
                camera=mock_camera,
                violation=violation,
            )

            assert alert is not None
            assert alert.alert_type == "NO_HELMET"
            assert alert.severity == "MEDIUM"
            assert "Helmet Rule Non-Compliance" in alert.title
            assert alert.metadata_["vehicle_track_id"] == 15
            assert alert.metadata_["evidence_reference"] == "/static/evidence/evid_no_helmet_15.jpg"
            mock_session.add.assert_called_once()
            assert mock_pub.call_count >= 1

    @pytest.mark.asyncio
    async def test_alert_service_processes_triple_riding_violation(self):
        """YOLO26AlertService records TRIPLE_RIDING violation with HIGH severity."""
        service = YOLO26AlertService()
        mock_session = AsyncMock()
        mock_camera = MagicMock(spec=Camera)
        mock_camera.id = uuid.uuid4()
        mock_camera.name = "PALDI-CROSSROAD-CAM-03"

        violation = TrafficViolationEvent(
            violation_type="TRIPLE_RIDING",
            camera_id=str(mock_camera.id),
            vehicle_track_id=25,
            vehicle_type="MOTORCYCLE",
            person_track_ids=[1, 2, 3],
            occupant_count=3,
            confidence=0.82,
            severity="HIGH",
            status="CONFIRMED",
            evidence_reference="/static/evidence/evid_triple_riding_25.jpg",
        )

        with patch("app.services.yolo26_alert_service.event_publisher.publish", new_callable=AsyncMock) as mock_pub:
            alert = await service.process_violation_event(
                session=mock_session,
                camera=mock_camera,
                violation=violation,
            )

            assert alert is not None
            assert alert.alert_type == "TRIPLE_RIDING"
            assert alert.severity == "HIGH"
            assert "Triple Riding" in alert.title
            assert alert.metadata_["occupant_count"] == 3
            mock_session.add.assert_called_once()


# ------------------------------------------------------------------------------
# 6. Stream Processor End-to-End Execution
# ------------------------------------------------------------------------------
class TestStreamProcessorPhase2:

    def test_stream_processor_execution_pipeline(self):
        """Verify YOLO26StreamProcessor executes Phase 2 components without runtime errors."""
        processor = YOLO26StreamProcessor(camera_id="CAM-TEST-STREAM")
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Run 2 consecutive frames
        res1 = processor.process_frame(dummy_frame)
        res2 = processor.process_frame(dummy_frame)

        assert res1.camera_id == "CAM-TEST-STREAM"
        assert res1.frame_seq == 1
        assert res2.frame_seq == 2
        assert isinstance(res1.detections, list)
        assert hasattr(processor, "latest_violations")
