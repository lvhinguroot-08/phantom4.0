"""
Unit Tests for Real-Time Camera-Specific Live AI Detection WebSocket Schema
Validates the 'ai_detection' message envelope, camera_name, tracked objects, and summary breakdown.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.endpoints.live_detection_ws import generate_live_hud_frame


def test_generate_live_hud_frame_schema():
    """Verify live detection payload conforms strictly to required 'ai_detection' schema."""
    frame = generate_live_hud_frame("CAM-AMD-ITX-01", frame_seq=10)

    assert frame["type"] == "ai_detection"
    assert frame["camera_id"] == "CAM-AMD-ITX-01"
    assert "camera_name" in frame
    assert "timestamp" in frame
    assert "objects" in frame
    assert isinstance(frame["objects"], list)
    assert len(frame["objects"]) > 0

    # Validate first tracked object
    obj = frame["objects"][0]
    assert "track_id" in obj
    assert "class_name" in obj
    assert "confidence" in obj
    assert "bbox" in obj
    assert "x1" in obj["bbox"]
    assert "y1" in obj["bbox"]
    assert "x2" in obj["bbox"]
    assert "y2" in obj["bbox"]
    assert "first_seen" in obj
    assert "last_seen" in obj

    # Validate summary
    summary = frame["summary"]
    assert "persons" in summary
    assert "cars" in summary
    assert "total_objects" in summary
    assert summary["total_objects"] == len(frame["objects"])


def test_live_detection_websocket_stream_message():
    """Verify WebSocket stream transmits 'ai_detection' message envelope in real-time."""
    client = TestClient(app)
    with client.websocket_connect("/api/v1/streams/CAM-AMD-ITX-01/detections/ws?fps=10") as ws:
        msg = ws.receive_json()

        assert msg["type"] == "ai_detection"
        assert msg["camera_id"] == "CAM-AMD-ITX-01"
        assert isinstance(msg["objects"], list)
        assert "summary" in msg
        assert "persons" in msg["summary"]
        assert "cars" in msg["summary"]
        assert "total_objects" in msg["summary"]
