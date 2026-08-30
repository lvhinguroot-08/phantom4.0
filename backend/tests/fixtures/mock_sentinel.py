"""
PHANTOM // Mock Sentinel Camera Grid Test Fixtures & Adapters
Provides isolated testing fixtures for Sentinel Ingest Catalogue (GET /api/ingest),
HTTP 502 simulations, timeouts, malformed payloads, and multi-codec stream tests.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from app.adapters.base_source_adapter import BaseSourceAdapter
from app.schemas.source_system import DiscoveredStream, SourceDiscoveryCamera

# Standard sample Sentinel Ingest payload containing both H.264 and H.265 cameras
SAMPLE_SENTINEL_INGEST_PAYLOAD = {
    "cameras": [
        {
            "id": "1",
            "number": 1,
            "name": "Camera 1",
            "location": "01 Chiman bhai Bridge",
            "codec": "",
            "live": True,
            "width": 1920,
            "height": 1080,
            "fps": 25.0,
            "bitrate_kbps": 2000,
            "bits_per_pixel": 0.0,
            "rtsp_url": "rtsp://live.corp8.cloud:8554/stream/1",
            "webrtc_url": "http://live.corp8.cloud:8889/stream/1/whep",
            "hls_live_url": "/live/stream/1/index.m3u8"
        },
        {
            "id": "6",
            "number": 6,
            "name": "Camera 6",
            "location": "06 Timbavadi gate-Junagadh",
            "codec": "hevc",
            "live": True,
            "width": 1920,
            "height": 1080,
            "fps": 25.0,
            "bitrate_kbps": 2500,
            "bits_per_pixel": 0.0,
            "rtsp_url": "rtsp://live.corp8.cloud:8554/stream/6",
            "webrtc_url": "http://live.corp8.cloud:8889/stream/6/whep",
            "hls_live_url": "/live/stream/6/index.m3u8"
        },
        {
            "id": "13",
            "number": 13,
            "name": "Camera 13",
            "location": "13 CN Vidhyalaya",
            "codec": "h264",
            "live": True,
            "width": 1280,
            "height": 720,
            "fps": 30.0,
            "bitrate_kbps": 1500,
            "bits_per_pixel": 0.0,
            "rtsp_url": "rtsp://live.corp8.cloud:8554/stream/13",
            "webrtc_url": "http://live.corp8.cloud:8889/stream/13/whep",
            "hls_live_url": "/live/stream/13/index.m3u8"
        },
        {
            "id": "17",
            "number": 17,
            "name": "Camera 17",
            "location": "17 Rajkot Bus Port CCTV",
            "codec": "hevc",
            "live": True,
            "width": 1920,
            "height": 1080,
            "fps": 25.0,
            "bitrate_kbps": 3000,
            "bits_per_pixel": 0.0,
            "rtsp_url": "rtsp://live.corp8.cloud:8554/stream/17",
            "webrtc_url": "http://live.corp8.cloud:8889/stream/17/whep",
            "hls_live_url": "/live/stream/17/index.m3u8"
        },
        {
            "id": "27",
            "number": 27,
            "name": "Camera 27",
            "location": "36 bilimora",
            "codec": "h264",
            "live": False,
            "width": 1920,
            "height": 1080,
            "fps": 25.0,
            "bitrate_kbps": 2000,
            "bits_per_pixel": 0.0,
            "rtsp_url": "rtsp://live.corp8.cloud:8554/stream/27",
            "webrtc_url": "http://live.corp8.cloud:8889/stream/27/whep",
            "hls_live_url": "/live/stream/27/index.m3u8"
        }
    ]
}

# Updated catalogue state with newly added CAM-31 and removed CAM-27
SAMPLE_UPDATED_INGEST_PAYLOAD = {
    "cameras": [
        SAMPLE_SENTINEL_INGEST_PAYLOAD["cameras"][0],
        SAMPLE_SENTINEL_INGEST_PAYLOAD["cameras"][1],
        SAMPLE_SENTINEL_INGEST_PAYLOAD["cameras"][2],
        SAMPLE_SENTINEL_INGEST_PAYLOAD["cameras"][3],
        {
            "id": "31",
            "number": 31,
            "name": "Camera 31",
            "location": "31 Surat Diamond Bourse",
            "codec": "h264",
            "live": True,
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
            "bitrate_kbps": 2200,
            "bits_per_pixel": 0.0,
            "rtsp_url": "rtsp://live.corp8.cloud:8554/stream/31",
            "webrtc_url": "http://live.corp8.cloud:8889/stream/31/whep",
            "hls_live_url": "/live/stream/31/index.m3u8"
        }
    ]
}

# Malformed catalogue payloads
MALFORMED_INGEST_MISSING_CAMERAS = {"status": "ok", "message": "no camera array"}
MALFORMED_INGEST_NOT_ARRAY = {"cameras": "not-a-list"}
MALFORMED_INGEST_MISSING_FIELDS = {
    "cameras": [
        {"id": None, "name": "Broken Camera"},
        {"number": 99, "location": "No ID Camera"},
        {"id": "50", "location": "Valid Location with no URLs"},
    ]
}


class MockSentinelSourceAdapter(BaseSourceAdapter):
    """
    Mock Adapter for offline testing and continuous integration.
    Configurable to simulate normal responses, 502 errors, timeouts, or malformed data.
    """

    def __init__(
        self,
        mode: str = "SUCCESS",  # SUCCESS, HTTP_502, TIMEOUT, MALFORMED, UPDATED
        custom_payload: Optional[Dict[str, Any]] = None
    ):
        self.mode = mode
        self.custom_payload = custom_payload
        self.call_count: int = 0

    async def probe(self, base_url: str = "https://live.corp8.cloud", auth_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.call_count += 1
        if self.mode == "HTTP_502":
            return {"accessible": False, "status_code": 502, "error": "HTTP 502 Bad Gateway", "catalog_state": "DEGRADED"}
        elif self.mode == "TIMEOUT":
            return {"accessible": False, "error": "Connection timeout", "catalog_state": "DEGRADED"}
        elif self.mode == "MALFORMED":
            return {"accessible": False, "error": "Malformed JSON payload", "catalog_state": "DEGRADED"}

        payload = self.custom_payload or SAMPLE_SENTINEL_INGEST_PAYLOAD
        cams = payload.get("cameras", [])
        return {
            "accessible": True,
            "status_code": 200,
            "catalog_state": "SYNCED",
            "total_cameras": len(cams),
            "latency_ms": 42.5,
        }

    async def discover_cameras(self, base_url: str = "https://live.corp8.cloud", auth_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.call_count += 1
        if self.mode == "HTTP_502":
            raise RuntimeError("Sentinel host returned HTTP 502 Bad Gateway")
        elif self.mode == "TIMEOUT":
            raise httpx.TimeoutException("Connection timed out after 5.0s")
        elif self.mode == "MALFORMED":
            payload = self.custom_payload or MALFORMED_INGEST_NOT_ARRAY
            if not isinstance(payload.get("cameras"), list):
                raise ValueError("Expected 'cameras' list in catalogue payload")

        payload = self.custom_payload or (SAMPLE_UPDATED_INGEST_PAYLOAD if self.mode == "UPDATED" else SAMPLE_SENTINEL_INGEST_PAYLOAD)
        raw_cameras = payload.get("cameras", [])

        from app.adapters.corp8_source_adapter import Corp8SourceAdapter
        real_adapter = Corp8SourceAdapter()

        discovered: List[SourceDiscoveryCamera] = []
        for raw in raw_cameras:
            raw_id = raw.get("id")
            if raw_id is None:
                continue
            cam_id = str(raw_id).strip()
            cam_name = str(raw.get("name") or f"Camera {cam_id}")
            raw_loc = raw.get("location")
            district, city = real_adapter._infer_district_and_city(raw_loc)
            codec = real_adapter.normalize_codec(raw.get("codec"))
            is_live = bool(raw.get("live", True))

            streams: List[DiscoveredStream] = []
            if raw.get("rtsp_url"):
                streams.append(DiscoveredStream(protocol="RTSP", stream_url=raw["rtsp_url"], codec=codec, is_primary=True))
            if raw.get("webrtc_url"):
                streams.append(DiscoveredStream(protocol="WEBRTC", stream_url=raw["webrtc_url"], codec=codec))
            if raw.get("hls_live_url"):
                hls = raw["hls_live_url"]
                hls_url = f"https://live.corp8.cloud{hls}" if hls.startswith("/") else hls
                streams.append(DiscoveredStream(protocol="HLS", stream_url=hls_url, codec=codec))

            discovered.append(
                SourceDiscoveryCamera(
                    source_camera_id=cam_id,
                    number=raw.get("number"),
                    name=cam_name,
                    raw_location_string=raw_loc,
                    inferred_district=district,
                    inferred_city=city,
                    status="ONLINE" if is_live else "OFFLINE",
                    delivery="RTSP",
                    streams=streams,
                    raw_metadata=raw,
                )
            )

        return {
            "catalog_state": "SYNCED",
            "scanned_at": datetime.now(timezone.utc),
            "total_discovered": len(discovered),
            "cameras": discovered,
        }
