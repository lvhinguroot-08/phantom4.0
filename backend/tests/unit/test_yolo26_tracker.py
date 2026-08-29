"""
Unit Tests for YOLO26 Multi-Object Tracking Engine
Validates track_id persistence, dwell_time, movement_direction, and display labels.
"""
from datetime import datetime, timezone, timedelta
import pytest
from app.ai.yolo26.tracker import YOLO26Tracker, Track, format_display_label, compute_iou


def test_format_display_label():
    """Verify display label format: 'Person #12 | 96%', 'Car #7 | 91%'."""
    assert format_display_label("PERSON", 12, 0.96) == "Person #12 | 96%"
    assert format_display_label("CAR", 7, 0.91) == "Car #7 | 91%"
    assert format_display_label("MOTORCYCLE", 3, 0.92) == "Motorcycle #3 | 92%"
    assert format_display_label("BUS", 1, 0.88) == "Bus #1 | 88%"
    assert format_display_label("TRUCK", 5, 0.95) == "Truck #5 | 95%"


def test_yolo26_tracker_persistent_id_and_motion():
    """Verify persistent track_id assignment, dwell time calculation, and direction."""
    tracker = YOLO26Tracker(camera_id="CAM-TEST-01", iou_threshold=0.25)
    t0 = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)

    # Frame 1: Initial detection of a car and a person
    frame1_dets = [
        {
            "object_class": "CAR",
            "confidence": 0.94,
            "bounding_box": {"x1": 100, "y1": 200, "x2": 300, "y2": 400},
        },
        {
            "object_class": "PERSON",
            "confidence": 0.89,
            "bounding_box": {"x1": 600, "y1": 150, "x2": 680, "y2": 350},
        },
    ]
    res1 = tracker.update(frame1_dets, frame_shape=(720, 1280), timestamp=t0)
    assert len(res1) == 2
    car_tid = res1[0]["track_id"]
    ped_tid = res1[1]["track_id"]
    assert car_tid is not None
    assert ped_tid is not None
    assert car_tid != ped_tid
    assert res1[0]["display_label"] == f"Car #{car_tid} | 94%"
    assert res1[1]["display_label"] == f"Person #{ped_tid} | 89%"

    # Frame 2: Objects moved slightly (1.5 seconds later)
    t1 = t0 + timedelta(seconds=1.5)
    frame2_dets = [
        {
            "object_class": "CAR",
            "confidence": 0.95,
            "bounding_box": {"x1": 130, "y1": 200, "x2": 330, "y2": 400},  # Moved East
        },
        {
            "object_class": "PERSON",
            "confidence": 0.91,
            "bounding_box": {"x1": 600, "y1": 190, "x2": 680, "y2": 390},  # Moved South
        },
    ]
    res2 = tracker.update(frame2_dets, frame_shape=(720, 1280), timestamp=t1)
    assert len(res2) == 2
    assert res2[0]["track_id"] == car_tid, "Track ID for CAR must persist across frames"
    assert res2[1]["track_id"] == ped_tid, "Track ID for PERSON must persist across frames"
    assert res2[0]["dwell_time"] == 1.5
    assert res2[1]["dwell_time"] == 1.5
    assert res2[0]["movement_direction"] == "EASTBOUND"
    assert res2[1]["movement_direction"] == "SOUTHBOUND"


def test_yolo26_tracker_stale_track_culling():
    """Verify tracks are removed after max_lost_frames without updates."""
    tracker = YOLO26Tracker(camera_id="CAM-TEST-01", max_lost_frames=3)
    t0 = datetime.now(timezone.utc)

    # Add 1 track
    tracker.update([{"object_class": "CAR", "confidence": 0.9, "bounding_box": {"x1": 10, "y1": 10, "x2": 50, "y2": 50}}], timestamp=t0)
    assert len(tracker.tracks) == 1

    # Send 4 empty frames
    for _ in range(4):
        tracker.update([], timestamp=t0)

    # Track must be culled
    assert len(tracker.tracks) == 0


def test_normalize_bbox_with_none_and_edge_cases():
    """Verify _normalize_bbox handles None values, malformed inputs, and alternative key schemas gracefully."""
    from app.ai.yolo26.tracker import _normalize_bbox

    # Dict with None values
    bbox_none = {"x1": None, "y1": None, "x2": None, "y2": None}
    res = _normalize_bbox(bbox_none)
    assert res == {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 0.0}

    # Dict with mixed/alternative keys and None fallbacks
    bbox_alt = {"xmin": 10.5, "ymin": 20.0, "xmax": 100.0, "ymax": 200.0}
    assert _normalize_bbox(bbox_alt) == {"x1": 10.5, "y1": 20.0, "x2": 100.0, "y2": 200.0}

    bbox_left_top = {"left": 5, "top": 15, "right": 50, "bottom": 75}
    assert _normalize_bbox(bbox_left_top) == {"x1": 5.0, "y1": 15.0, "x2": 50.0, "y2": 75.0}

    # List / tuple formats
    assert _normalize_bbox([10, 20, 30, 40]) == {"x1": 10.0, "y1": 20.0, "x2": 30.0, "y2": 40.0}
    assert _normalize_bbox((10, 20, 30, 40)) == {"x1": 10.0, "y1": 20.0, "x2": 30.0, "y2": 40.0}

    # None and empty
    assert _normalize_bbox(None) == {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 0.0}
    assert _normalize_bbox({}) == {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 0.0}

