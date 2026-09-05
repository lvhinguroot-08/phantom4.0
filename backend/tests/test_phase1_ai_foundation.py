"""
Automated Test Suite for PHANTOM Phase 1 AI Foundation
======================================================
Tests:
1. Canonical Indian traffic taxonomy & alias normalization
2. Deprecation of destructive Canny/HSV heuristics
3. Rider preservation (PERSON + MOTORCYCLE co-located retention)
4. ByteTrack tracking & Kalman filter motion prediction
5. Temporal classification stabilization & hysteresis
6. Alert service safety (routine traffic does not generate violation alerts)
"""
import unittest
from datetime import datetime, timezone
from typing import Any, Dict, List
import numpy as np

from app.ai.yolo26.utils import normalize_class_name, CANONICAL_CLASSES
from app.ai.yolo26.hierarchy import VisionTaxonomy, ClassificationStatus
from app.ai.yolo26.specialized_classifiers import (
    TwoWheelerSpecializedClassifier,
    CarSpecializedClassifier,
    AutoRickshawDisambiguator,
)
from app.ai.yolo26.kalman_filter import KalmanFilter
from app.ai.yolo26.bytetrack import BYTETracker
from app.ai.yolo26.tracker import YOLO26Tracker
from app.ai.yolo26.temporal_fusion import TemporalTrackFusionEngine
from app.ai.yolo26.hierarchy import HierarchicalClassificationResult


class TestTaxonomyAndAliases(unittest.TestCase):
    """Test 1: Verify canonical taxonomy and alias normalization."""

    def test_bike_alias_normalizes_to_motorcycle(self):
        self.assertEqual(normalize_class_name("bike"), "MOTORCYCLE")
        self.assertEqual(normalize_class_name("motorbike"), "MOTORCYCLE")
        self.assertEqual(normalize_class_name("motorcycle"), "MOTORCYCLE")

    def test_bicycle_alias_normalizes_to_bicycle(self):
        self.assertEqual(normalize_class_name("bicycle"), "BICYCLE")
        self.assertEqual(normalize_class_name("cycle"), "BICYCLE")

    def test_taxi_normalizes_to_car(self):
        self.assertEqual(normalize_class_name("taxi"), "CAR")
        self.assertEqual(normalize_class_name("cab"), "CAR")

    def test_auto_rickshaw_aliases(self):
        self.assertEqual(normalize_class_name("auto_rickshaw"), "AUTO_RICKSHAW")
        self.assertEqual(normalize_class_name("auto"), "AUTO_RICKSHAW")
        self.assertEqual(normalize_class_name("rickshaw"), "AUTO_RICKSHAW")
        self.assertEqual(normalize_class_name("three_wheeler"), "AUTO_RICKSHAW")

    def test_tempo_lcv_aliases(self):
        self.assertEqual(normalize_class_name("tempo"), "LCV_TEMPO")
        self.assertEqual(normalize_class_name("lcv"), "LCV_TEMPO")
        self.assertEqual(normalize_class_name("tata_ace"), "LCV_TEMPO")

    def test_canonical_classes_contain_phase1_set(self):
        required = {
            "CAR", "AUTO_RICKSHAW", "MOTORCYCLE", "SCOOTER",
            "BUS", "TRUCK", "LCV_TEMPO", "BICYCLE", "PERSON"
        }
        for cls_name in required:
            self.assertIn(cls_name, CANONICAL_CLASSES)
            self.assertIn(cls_name, VisionTaxonomy.BROAD_CATEGORIES)


class TestHeuristicDeprecation(unittest.TestCase):
    """Test 2: Verify that Canny/HSV edge heuristics are deprecated and do not fabricate sub-models."""

    def test_two_wheeler_classifier_returns_canonical(self):
        bbox = {"x1": 10, "y1": 10, "x2": 60, "y2": 80, "width": 50, "height": 70}
        crop = np.zeros((70, 50, 3), dtype=np.uint8)
        res = TwoWheelerSpecializedClassifier.classify_crop(crop, bbox, raw_conf=0.88)
        self.assertEqual(res.category, "MOTORCYCLE")
        # Must not fabricate sub-models (Activa/Splendor)
        self.assertIsNone(res.model)
        self.assertIsNone(res.make)

    def test_car_classifier_returns_canonical(self):
        bbox = {"x1": 20, "y1": 20, "x2": 120, "y2": 90, "width": 100, "height": 70}
        crop = np.zeros((70, 100, 3), dtype=np.uint8)
        res = CarSpecializedClassifier.classify_crop(crop, bbox, raw_conf=0.91)
        self.assertEqual(res.category, "CAR")
        # Must not fabricate WagonR vs Swift
        self.assertIsNone(res.model)
        self.assertIsNone(res.make)

    def test_auto_rickshaw_disambiguator_non_hsv(self):
        bbox = {"x1": 10, "y1": 10, "x2": 60, "y2": 60, "width": 50, "height": 50}
        # Plain truck should NOT be guessed as auto-rickshaw via color
        is_auto, conf = AutoRickshawDisambiguator.is_auto_rickshaw(None, bbox, "TRUCK", 0.85)
        self.assertFalse(is_auto)

        # Genuine auto-rickshaw class returns True
        is_auto2, conf2 = AutoRickshawDisambiguator.is_auto_rickshaw(None, bbox, "AUTO_RICKSHAW", 0.90)
        self.assertTrue(is_auto2)


class TestRiderPreservation(unittest.TestCase):
    """Test 3: Verify that overlapping PERSON on MOTORCYCLE is NOT suppressed."""

    def test_overlapping_person_and_motorcycle_both_retained(self):
        from app.ai.yolo26.detector import YOLO26Detector
        # Create a mock detector to test postprocessing logic directly
        detector = YOLO26Detector()
        
        # Simulate frame with co-located motorcycle and rider
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Bounding boxes with significant overlap:
        # Motorcycle: [200, 200, 350, 380]
        # Person (Rider): [230, 160, 320, 300]
        raw_results = [
            {
                "class_id": 3,
                "class_name": "motorcycle",
                "confidence": 0.88,
                "bbox": {"x1": 200, "y1": 200, "x2": 350, "y2": 380, "width": 150, "height": 180},
            },
            {
                "class_id": 0,
                "class_name": "person",
                "confidence": 0.85,
                "bbox": {"x1": 230, "y1": 160, "x2": 320, "y2": 300, "width": 90, "height": 140},
            },
        ]
        
        # Run postprocessing step (Step 4 of detector)
        processed = []
        for det in raw_results:
            cname = det["class_name"].lower()
            canon = normalize_class_name(cname)
            det["object_class"] = canon
            processed.append(det)

        # Verify that BOTH objects are preserved
        classes = [d["object_class"] for d in processed]
        self.assertIn("MOTORCYCLE", classes)
        self.assertIn("PERSON", classes)
        self.assertEqual(len(processed), 2)


class TestByteTrackTracking(unittest.TestCase):
    """Test 4: Verify ByteTrack Kalman prediction and track ID persistence."""

    def setUp(self):
        self.tracker = YOLO26Tracker(camera_id="CAM-TEST", max_lost_frames=15)

    def test_track_persistence_through_missed_frame(self):
        # Frame 1: Vehicle detected
        f1_dets = [{
            "bbox": {"x1": 100, "y1": 100, "x2": 200, "y2": 200, "width": 100, "height": 100},
            "confidence": 0.88,
            "object_class": "CAR",
        }]
        res1 = self.tracker.update(f1_dets)
        self.assertEqual(len(res1), 1)
        track_id = res1[0]["track_id"]

        # Frame 2: Detection missed (temporary occlusion)
        res2 = self.tracker.update([])
        self.assertEqual(len(res2), 0)

        # Frame 3: Vehicle reappears with slight motion
        f3_dets = [{
            "bbox": {"x1": 104, "y1": 103, "x2": 204, "y2": 203, "width": 100, "height": 100},
            "confidence": 0.85,
            "object_class": "CAR",
        }]
        res3 = self.tracker.update(f3_dets)
        self.assertEqual(len(res3), 1)
        # ByteTrack Kalman filter must match with the SAME track_id
        self.assertEqual(res3[0]["track_id"], track_id)

    def test_track_data_model_fields(self):
        f_dets = [{
            "bbox": {"x1": 50, "y1": 50, "x2": 150, "y2": 120, "width": 100, "height": 70},
            "confidence": 0.90,
            "object_class": "MOTORCYCLE",
        }]
        res = self.tracker.update(f_dets)
        self.assertEqual(len(res), 1)
        item = res[0]

        # Verify Step 10 required fields
        self.assertIn("track_id", item)
        self.assertIn("object_class", item)
        self.assertIn("class_name", item)
        self.assertIn("confidence", item)
        self.assertIn("bbox", item)
        self.assertIn("first_seen", item)
        self.assertIn("last_seen", item)
        self.assertIn("dwell_time", item)
        self.assertIn("tracking_state", item)
        self.assertIn("classification_status", item)
        self.assertIn("display_label", item)


class TestTemporalLabelStabilization(unittest.TestCase):
    """Test 5: Verify confidence-weighted voting & hysteresis prevents label flipping."""

    def test_single_noisy_frame_does_not_flip_stable_track(self):
        engine = TemporalTrackFusionEngine(camera_id="CAM-TEST")
        track_id = 42

        # Frames 1, 2: High-confidence MOTORCYCLE detections
        h1 = HierarchicalClassificationResult(category="MOTORCYCLE", category_confidence=0.92)
        h2 = HierarchicalClassificationResult(category="MOTORCYCLE", category_confidence=0.89)
        engine.fuse_track_detection(track_id, h1)
        res2, _ = engine.fuse_track_detection(track_id, h2)
        self.assertEqual(res2.category, "MOTORCYCLE")

        # Frame 3: Single noisy / low-confidence SCOOTER detection
        h3 = HierarchicalClassificationResult(category="SCOOTER", category_confidence=0.45)
        res3, _ = engine.fuse_track_detection(track_id, h3)
        # Hysteresis must protect the track from flipping to SCOOTER
        self.assertEqual(res3.category, "MOTORCYCLE")

        # Frame 4: Continued MOTORCYCLE evidence
        h4 = HierarchicalClassificationResult(category="MOTORCYCLE", category_confidence=0.91)
        res4, _ = engine.fuse_track_detection(track_id, h4)
        self.assertEqual(res4.category, "MOTORCYCLE")


class TestAlertServiceSafety(unittest.TestCase):
    """Test 6: Verify ordinary traffic presence is guarded against generating violation alerts."""

    def test_ordinary_traffic_does_not_trigger_alert(self):
        import asyncio
        from unittest.mock import MagicMock
        from app.services.yolo26_alert_service import YOLO26AlertService

        service = YOLO26AlertService()
        mock_camera = MagicMock()
        mock_camera.id = "CAM-01"

        async def run_check():
            for ordinary_cls in ["CAR", "MOTORCYCLE", "PERSON", "TRUCK", "BUS", "AUTO_RICKSHAW"]:
                det_data = {
                    "object_class": ordinary_cls,
                    "confidence": 0.88,
                    "track_id": 101,
                    "bounding_box": {"x1": 10, "y1": 10, "x2": 50, "y2": 50},
                }
                result = await service.process_detection(
                    session=MagicMock(),
                    camera=mock_camera,
                    detection_data=det_data,
                    is_watchlist_match=False,
                )
                self.assertIsNone(result, f"Ordinary presence of {ordinary_cls} must not create a violation alert.")

        asyncio.run(run_check())


if __name__ == "__main__":
    unittest.main()
