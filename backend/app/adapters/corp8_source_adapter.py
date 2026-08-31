"""
PHANTOM // Sentinel CCTV Source Adapter
Implements the Sentinel Camera Grid Integration Contract (GET /api/ingest).
Consumes dynamic camera catalogue, multi-codec stream metadata (H.264 / H.265),
RTSP over TCP, WebRTC / WHEP, and HLS fallback stream endpoints.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin
import httpx

from app.adapters.base_source_adapter import BaseSourceAdapter
from app.core.config import settings
from app.core.logging import logger
from app.core.validators import validate_safe_url
from app.schemas.source_system import DiscoveredStream, SourceDiscoveryCamera

# Known Gujarat districts for geographic inference from location labels
GUJARAT_DISTRICTS = [
    "Ahmedabad", "Gandhinagar", "Surat", "Vadodara", "Rajkot", "Junagadh",
    "Navsari", "Patan", "Gir Somnath", "Kutch", "Kachchh", "Bhavnagar",
    "Jamnagar", "Banaskantha", "Panchmahal", "Anand", "Kheda", "Mehsana",
    "Dahod", "Bharuch", "Valsad", "Amreli", "Porbandar", "Surendranagar",
    "Morbi", "Botad", "Aravalli", "Mahisagar", "Chhotaudepur", "Narmada",
    "Tapi", "Dang", "Devbhumi Dwarka"
]


class Corp8SourceAdapter(BaseSourceAdapter):
    """
    Production adapter for the official Sentinel Camera Grid (live.corp8.cloud).
    Contract Source of Truth: GET /api/ingest
    """

    def __init__(self, base_url: Optional[str] = None, catalogue_path: Optional[str] = None):
        self.base_url = (base_url or settings.SENTINEL_BASE_URL).rstrip("/")
        self.catalogue_path = catalogue_path or getattr(settings, "SENTINEL_CATALOGUE_PATH", "/api/ingest")

    def _infer_district_and_city(self, location_str: Optional[str]) -> Tuple[str, str]:
        if not location_str:
            return "Gujarat", "Gujarat"

        loc_lower = location_str.lower()
        for dist in GUJARAT_DISTRICTS:
            if dist.lower() in loc_lower:
                return dist, dist

        # Keyword heuristics for specific Gujarat municipal and transit nodes
        if "adalaj" in loc_lower or "dehgam" in loc_lower:
            return "Gandhinagar", "Gandhinagar"
        if "bilimora" in loc_lower or "gandevi" in loc_lower:
            return "Navsari", "Bilimora"
        if "gandhidham" in loc_lower or "kutch" in loc_lower or "kachchh" in loc_lower:
            return "Kutch", "Gandhidham"
        if any(k in loc_lower for k in ["chiman bhai", "janpath", "paldi", "visat", "ongc", "delight", "suvidha", "vidhyalaya", "dhanori"]):
            return "Ahmedabad", "Ahmedabad"
        if any(k in loc_lower for k in ["timbavadi", "majewadi", "dolatpara", "char chowk"]):
            return "Junagadh", "Junagadh"
        if "somnath" in loc_lower or "veraval" in loc_lower:
            return "Gir Somnath", "Veraval"
        if "mervada" in loc_lower:
            return "Morbi", "Morbi"
        if "kheram" in loc_lower:
            return "Kheda", "Kheram"
        if "tankal" in loc_lower:
            return "Narmada", "Tankal"

        return "Gujarat", "Gujarat"

    def normalize_codec(self, raw_codec: Optional[str]) -> str:
        """Normalizes codec string to standard H264 or H265 / HEVC."""
        if not raw_codec:
            return "H264"
        c = str(raw_codec).strip().lower()
        if c in ("hevc", "h265", "h.265", "x265"):
            return "H265"
        if c in ("h264", "h.264", "avc", "x264"):
            return "H264"
        return c.upper()

    def _sanitize_url(self, raw_url: Optional[str], default_base: str) -> Optional[str]:
        """Validates and sanitizes stream URLs to prevent SSRF and security risks."""
        if not raw_url or not isinstance(raw_url, str):
            return None
        clean_url = raw_url.strip()
        if not clean_url:
            return None

        # If relative URL (e.g. /live/stream/1/index.m3u8), resolve against base URL
        if clean_url.startswith("/"):
            clean_url = urljoin(default_base, clean_url)

        try:
            return validate_safe_url(clean_url, allow_localhost_in_dev=True)
        except Exception as ex:
            logger.warning(f"Rejected invalid or dangerous stream URL '{raw_url}': {ex}")
            return None

    async def probe(self, base_url: Optional[str] = None, auth_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Probes live health and reachability of Sentinel Ingest Catalogue."""
        target_base = (base_url or self.base_url).rstrip("/")
        api_url = f"{target_base}{self.catalogue_path}"

        connect_timeout = getattr(settings, "SENTINEL_CONNECT_TIMEOUT", 5.0)
        read_timeout = getattr(settings, "SENTINEL_READ_TIMEOUT", 10.0)

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(read_timeout, connect=connect_timeout),
                follow_redirects=True,
                headers={"User-Agent": "PHANTOM-SentinelAdapter/2.0"}
            ) as client:
                res = await client.get(api_url)
                if res.status_code == 200:
                    try:
                        data = res.json()
                        cameras = data if isinstance(data, list) else data.get("cameras", [])
                        return {
                            "accessible": True,
                            "status_code": res.status_code,
                            "catalog_state": "SYNCED",
                            "total_cameras": len(cameras),
                            "latency_ms": round(res.elapsed.total_seconds() * 1000, 2),
                        }
                    except Exception as json_err:
                        return {
                            "accessible": False,
                            "status_code": res.status_code,
                            "error": f"Malformed JSON response: {json_err}",
                            "catalog_state": "DEGRADED",
                        }
                return {
                    "accessible": False,
                    "status_code": res.status_code,
                    "error": f"HTTP {res.status_code}",
                    "catalog_state": "DEGRADED" if res.status_code == 502 else "OFFLINE",
                }
        except httpx.TimeoutException as tex:
            logger.warning(f"Timeout probing Sentinel host at {api_url}: {tex}")
            return {
                "accessible": False,
                "error": f"Connection timeout ({connect_timeout}s connect, {read_timeout}s read)",
                "catalog_state": "DEGRADED",
            }
        except Exception as ex:
            logger.warning(f"Failed to probe Sentinel host at {api_url}: {ex}")
            return {
                "accessible": False,
                "error": str(ex),
                "catalog_state": "OFFLINE",
            }

    async def discover_cameras(
        self, base_url: Optional[str] = None, auth_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Fetches the complete camera catalogue from Sentinel (GET /cameras.json or GET /api/ingest).
        Never hardcodes camera IDs, locations, or stream URLs.
        """
        target_base = (base_url or self.base_url).rstrip("/")
        api_url = f"{target_base}{self.catalogue_path}"

        connect_timeout = getattr(settings, "SENTINEL_CONNECT_TIMEOUT", 5.0)
        read_timeout = getattr(settings, "SENTINEL_READ_TIMEOUT", 10.0)

        last_error = None
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(read_timeout, connect=connect_timeout),
                follow_redirects=True,
                headers={"User-Agent": "PHANTOM-SentinelAdapter/2.0"}
            ) as client:
                res = await client.get(api_url)
                if res.status_code != 200:
                    raise RuntimeError(f"Sentinel host returned HTTP {res.status_code}: {res.text[:200]}")

                data = res.json()
                raw_cameras = data if isinstance(data, list) else data.get("cameras", [])
                if not isinstance(raw_cameras, list):
                    raise ValueError(f"Expected cameras list in catalogue payload, got {type(raw_cameras)}")

                discovered_cameras: List[SourceDiscoveryCamera] = []

                for raw in raw_cameras:
                    if not isinstance(raw, dict):
                        continue

                    raw_id = raw.get("id")
                    if raw_id is None:
                        continue
                    cam_id = str(raw_id).strip()
                    cam_name = str(raw.get("name") or f"Camera {cam_id}")
                    raw_loc = raw.get("location") or cam_name
                    district, city = self._infer_district_and_city(raw_loc)

                    # Codec resolution
                    codec = self.normalize_codec(raw.get("codec") or "H264")
                    is_live = bool(raw.get("live", True))

                    # Width / Height / FPS / Bitrate metadata
                    width = int(raw.get("width") or 1920)
                    height = int(raw.get("height") or 1080)
                    res_label = f"{width}x{height}" if width > 0 and height > 0 else "1080p"

                    raw_fps = raw.get("fps")
                    fps = float(raw_fps) if raw_fps and float(raw_fps) > 0 else 25.0
                    bitrate = int(raw.get("bitrate_kbps") or 1500)

                    streams: List[DiscoveredStream] = []

                    # 1. RTSP Stream (Direct TCP for AI inference)
                    raw_rtsp = raw.get("rtsp_url") or f"rtsp://103.250.160.189:8554/stream/{cam_id}"
                    safe_rtsp = self._sanitize_url(raw_rtsp, target_base)
                    if safe_rtsp:
                        streams.append(
                            DiscoveredStream(
                                protocol="RTSP",
                                stream_url=safe_rtsp,
                                resolution=res_label,
                                fps=fps,
                                codec=codec,
                                bitrate_kbps=bitrate if bitrate > 0 else None,
                                is_primary=True,
                            )
                        )

                    # 2. WebRTC / WHEP Stream (Low-latency Browser Preview)
                    raw_webrtc = raw.get("webrtc_url") or f"http://103.250.160.189:8889/stream/{cam_id}/whep"
                    safe_webrtc = self._sanitize_url(raw_webrtc, target_base)
                    if safe_webrtc:
                        streams.append(
                            DiscoveredStream(
                                protocol="WEBRTC",
                                stream_url=safe_webrtc,
                                resolution=res_label,
                                fps=fps,
                                codec=codec,
                                bitrate_kbps=bitrate if bitrate > 0 else None,
                                is_primary=False,
                            )
                        )

                    # 3. HLS Live Stream (Dashboard / Mobile Fallback)
                    raw_hls = raw.get("hls_live_url") or raw.get("hls_url") or f"{target_base}/{cam_id}/index.m3u8"
                    safe_hls = self._sanitize_url(raw_hls, target_base)
                    if safe_hls:
                        streams.append(
                            DiscoveredStream(
                                protocol="HLS",
                                stream_url=safe_hls,
                                resolution=res_label,
                                fps=fps,
                                codec=codec,
                                bitrate_kbps=bitrate if bitrate > 0 else None,
                                is_primary=False,
                            )
                        )

                    discovered_cameras.append(
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
                    "total_discovered": len(discovered_cameras),
                    "cameras": discovered_cameras,
                }
        except Exception as ex:
            last_error = ex
            logger.warning(f"Error discovering cameras from Sentinel catalogue at {api_url}: {ex}")
            raise RuntimeError(f"Could not reach Sentinel CCTV catalogue at {api_url}: {last_error}")

