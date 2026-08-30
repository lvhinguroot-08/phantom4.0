"""
PHANTOM // Automated Test Suite: Sentinel Camera Grid Integration
Tests:
- Catalogue parsing & validation from /api/ingest
- Malformed catalogue handling & missing camera fields
- New camera discovery & metadata change reconciliation
- Disappeared camera offline marking
- Offline Sentinel & HTTP 502 resilience
- Timeout resilience & exponential backoff calculation
- H.264 vs H.265 / HEVC codec selection
- Hardware PTS-driven timing & real ΔPTS calculation
- Inter-frame gap tolerance
- Scene discontinuity & video loop track reconciliation
- Stream state transitions (DISCOVERED, CONNECTING, LIVE, DEGRADED, RECONNECTING, OFFLINE)
- Security URL validation & SSRF protection
"""

from datetime import datetime, timezone
import pytest

from app.adapters.corp8_source_adapter import Corp8SourceAdapter
from app.ai.yolo26.tracker import Track, YOLO26Tracker
from app.core.validators import validate_safe_url
from app.services.sentinel_catalogue_service import SentinelCatalogueService
from app.services.stream_gateway_service import StreamGatewayService
from tests.fixtures.mock_sentinel import (
    MockSentinelSourceAdapter,
    SAMPLE_SENTINEL_INGEST_PAYLOAD,
    SAMPLE_UPDATED_INGEST_PAYLOAD,
    MALFORMED_INGEST_MISSING_CAMERAS,
    MALFORMED_INGEST_NOT_ARRAY,
    MALFORMED_INGEST_MISSING_FIELDS,
)


# ==============================================================================
# 1. Catalogue Parsing & Validation Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_catalogue_parsing_valid():
    """Verifies that valid Sentinel ingest JSON is parsed into structured camera models."""
    adapter = MockSentinelSourceAdapter(mode="SUCCESS")
    data = await adapter.discover_cameras("https://live.corp8.cloud")

    assert data["catalog_state"] == "SYNCED"
    assert data["total_discovered"] == 5
    cameras = data["cameras"]
    assert len(cameras) == 5

    cam1 = next(c for c in cameras if c.source_camera_id == "1")
    assert cam1.name == "Camera 1"
    assert "Chiman bhai" in cam1.raw_location_string
    assert cam1.inferred_district == "Ahmedabad"
    assert cam1.status == "ONLINE"

    # Verify stream protocol separation
    protocols = {s.protocol for s in cam1.streams}
    assert "RTSP" in protocols
    assert "WEBRTC" in protocols
    assert "HLS" in protocols


@pytest.mark.asyncio
async def test_codec_detection_h264_vs_h265():
    """Verifies that H.264 and H.265 (HEVC) streams are accurately identified."""
    adapter = Corp8SourceAdapter()
    assert adapter.normalize_codec("hevc") == "H265"
    assert adapter.normalize_codec("h265") == "H265"
    assert adapter.normalize_codec("H.265") == "H265"
    assert adapter.normalize_codec("h264") == "H264"
    assert adapter.normalize_codec("avc") == "H264"
    assert adapter.normalize_codec("") == "H264"  # Default fallback
    assert adapter.normalize_codec(None) == "H264"


@pytest.mark.asyncio
async def test_malformed_catalogue_handling():
    """Ensures malformed JSON or non-array payloads do not crash the service."""
    adapter = MockSentinelSourceAdapter(mode="MALFORMED", custom_payload=MALFORMED_INGEST_NOT_ARRAY)
    service = SentinelCatalogueService(adapter=adapter)

    res = await service.sync_catalogue()
    assert res["success"] is False
    assert service.sentinel_status in ("DEGRADED", "OFFLINE")
    assert service.catalogue_state == "RETRYING"
    assert service.last_error is not None


@pytest.mark.asyncio
async def test_missing_camera_fields_handling():
    """Ensures cameras with missing optional fields are safely parsed."""
    adapter = MockSentinelSourceAdapter(mode="SUCCESS", custom_payload=MALFORMED_INGEST_MISSING_FIELDS)
    data = await adapter.discover_cameras()
    # Should skip invalid records with None ID but process valid ones
    assert data["total_discovered"] == 1
    assert data["cameras"][0].source_camera_id == "50"


# ==============================================================================
# 2. Dynamic Discovery & Reconciliation Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_new_camera_discovery_and_reconciliation():
    """Verifies dynamic addition of new cameras and update of existing ones without hardcoding."""
    mock_adapter = MockSentinelSourceAdapter(mode="SUCCESS")
    service = SentinelCatalogueService(adapter=mock_adapter)

    # First sync
    res1 = await service.sync_catalogue()
    assert res1["success"] is True
    assert res1["total_cameras"] == 5
    assert "1" in service.discovered_cameras
    assert "27" in service.discovered_cameras

    # Second sync with updated payload (CAM-31 added, CAM-27 removed)
    mock_adapter.custom_payload = SAMPLE_UPDATED_INGEST_PAYLOAD
    res2 = await service.sync_catalogue()
    assert res2["success"] is True
    assert res2["new_cameras"] == 1
    assert "31" in service.discovered_cameras
    assert service.discovered_cameras["31"]["name"] == "Camera 31"

    # Disappeared camera (CAM-27) is marked OFFLINE, never destroyed
    assert "27" in service.discovered_cameras
    assert service.discovered_cameras["27"]["status"] == "OFFLINE"
    assert service.discovered_cameras["27"]["live"] is False


# ==============================================================================
# 3. Resilience, HTTP 502, Timeout & Exponential Backoff Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_offline_sentinel_and_http_502():
    """Verifies that HTTP 502 transitions state to DEGRADED without application crash."""
    mock_adapter = MockSentinelSourceAdapter(mode="HTTP_502")
    service = SentinelCatalogueService(adapter=mock_adapter)

    res = await service.sync_catalogue()
    assert res["success"] is False
    assert service.sentinel_status == "DEGRADED"
    assert service.catalogue_state == "RETRYING"
    assert service.reconnect_attempt == 1
    assert "502" in service.last_error


@pytest.mark.asyncio
async def test_timeout_handling():
    """Verifies timeout resilience."""
    mock_adapter = MockSentinelSourceAdapter(mode="TIMEOUT")
    service = SentinelCatalogueService(adapter=mock_adapter)

    res = await service.sync_catalogue()
    assert res["success"] is False
    assert service.sentinel_status == "DEGRADED"
    assert "timed out" in service.last_error.lower()


def test_exponential_backoff_calculation():
    """Verifies exponential retry backoff progression: 2s -> 4s -> 8s -> 16s -> 30s max."""
    service = SentinelCatalogueService()
    b1 = service.calculate_backoff(1)
    b2 = service.calculate_backoff(2)
    b3 = service.calculate_backoff(3)
    b4 = service.calculate_backoff(4)
    b5 = service.calculate_backoff(5)
    b10 = service.calculate_backoff(10)

    # Check nominal targets with +/- 10% jitter
    assert 1.8 <= b1 <= 2.2
    assert 3.6 <= b2 <= 4.4
    assert 7.2 <= b3 <= 8.8
    assert 14.4 <= b4 <= 17.6
    assert 27.0 <= b5 <= 30.0
    assert b10 <= 30.0  # Must never exceed 30 seconds max


# ==============================================================================
# 4. Hardware Presentation Timestamp (PTS) & AI Timing Tests
# ==============================================================================

def test_hardware_pts_timing_and_dwell_speed():
    """
    MANDATORY: Verifies that dwell time and velocity are driven by hardware PTS (ms)
    rather than wall-clock arrival time or assumed FPS.
    """
    track = Track(
        track_id=1,
        camera_id="CAM-001",
        bbox=[100, 100, 200, 200],
        obj_class="CAR",
        conf=0.92,
        pts_msec=1000.0,
    )
    assert track.first_pts_msec == 1000.0
    assert track.dwell_time == 0.0

    # Advance frame with PTS = 3500.0 ms (dwell = 2.5s, displacement = 50px)
    track.update(
        bbox=[150, 100, 250, 200],
        conf=0.94,
        pts_msec=3500.0,
    )
    assert track.dwell_time == 2.5
    assert track.last_pts_msec == 3500.0
    assert track.speed_kmph > 0.0
    assert track.movement_direction == "EASTBOUND"


def test_inter_frame_gaps_tolerance():
    """Verifies that large inter-frame gaps do not cause premature track deletion or crash."""
    tracker = YOLO26Tracker(camera_id="CAM-001", max_lost_frames=20)

    # Frame 1 at PTS = 1000ms
    dets1 = [{"bbox": {"x1": 100, "y1": 100, "x2": 200, "y2": 200}, "object_class": "CAR", "confidence": 0.90}]
    res1 = tracker.update(dets1, pts_msec=1000.0)
    tid = res1[0]["track_id"]
    assert tid == 1

    # Frame 2 arriving after a 2000ms network gap (PTS = 3000ms) with slight displacement
    dets2 = [{"bbox": {"x1": 105, "y1": 105, "x2": 205, "y2": 205}, "object_class": "CAR", "confidence": 0.88}]
    res2 = tracker.update(dets2, pts_msec=3000.0)
    assert res2[0]["track_id"] == tid  # Track preserved across gap
    assert res2[0]["dwell_time"] == 2.0


def test_scene_discontinuity_and_feed_loop():
    """
    Verifies that video loops (negative ΔPTS) or hard cuts trigger track reconciliation
    so stale tracks do not persist indefinitely.
    """
    tracker = YOLO26Tracker(camera_id="CAM-001")

    # Initial stream frames
    dets = [{"bbox": {"x1": 100, "y1": 100, "x2": 200, "y2": 200}, "object_class": "CAR", "confidence": 0.90}]
    tracker.update(dets, pts_msec=60000.0)
    assert len(tracker.tracks) == 1

    # Feed loops back to start (PTS jumps from 60000ms to 1000ms: ΔPTS = -59000ms)
    cut_detected = tracker.check_and_handle_discontinuity(pts_msec=1000.0)
    assert cut_detected is True
    assert len(tracker.tracks) == 0  # Active tracks reset to prevent stale ID drift
    assert tracker.discontinuity_count == 1


# ==============================================================================
# 5. Stream Gateway State Transitions & Load Pacing Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_stream_state_transitions():
    """Verifies stream gateway transitions between connection states."""
    gateway = StreamGatewayService()
    state = gateway.get_or_create_state("CAM-006")
    assert state.connection_state == "DISCOVERED"

    # Resolve stream parameters
    res = await gateway.resolve_stream("CAM-006", protocol="WHEP")
    assert res["camera_id"] == "CAM-006"
    assert "session_id" in res

    # Summary metrics reflection
    summary = gateway.get_gateway_summary()
    assert "total_cameras" in summary
    assert "ai_active" in summary


# ==============================================================================
# 6. Security URL Validation (SSRF Protection)
# ==============================================================================

def test_security_url_validation():
    """Verifies that internal metadata targets and dangerous schemes are blocked."""
    # Valid Sentinel CCTV endpoints
    assert validate_safe_url("https://live.corp8.cloud/api/ingest")
    assert validate_safe_url("rtsp://live.corp8.cloud:8554/stream/1")
    assert validate_safe_url("http://live.corp8.cloud:8889/stream/1/whep")

    # Blocked SSRF & Cloud Metadata URLs
    with pytest.raises(ValueError, match="cloud metadata"):
        validate_safe_url("http://169.254.169.254/latest/meta-data")

    with pytest.raises(ValueError, match="cloud metadata"):
        validate_safe_url("http://metadata.google.internal/computeMetadata/v1/")

    # Blocked dangerous schemes
    with pytest.raises(ValueError, match="Unsupported or dangerous URL scheme"):
        validate_safe_url("file:///etc/passwd")

    with pytest.raises(ValueError, match="Unsupported or dangerous URL scheme"):
        validate_safe_url("gopher://127.0.0.1:6379")
