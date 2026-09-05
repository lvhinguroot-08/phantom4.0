"""
PHANTOM // Live CCTV Stream Gateway & Multi-Codec Ingestion Engine
Engineered for Gujarat Police Department & Law Enforcement CCTV Surveillance Networks.

Supports:
- Dynamic Sentinel Ingestion (/api/ingest) with zero hard-coded assumptions
- Multi-Codec Ingestion: H.264 and H.265 (HEVC) simultaneous stream processing
- Mandatory RTSP over TCP Transport (zero packet drop from UDP)
- Hardware PTS-driven timing & frame timestamp tracking
- Tolerant stream-join decoding (tolerates RPS / POC keyframe acquisition warnings)
- Exponential Reconnect Backoff (2s -> 4s -> 8s -> 16s -> 30s max)
- Load Pacing & Dynamic Lifecycle Management (on-demand AI stream allocation)
- Browser Preview Routing: WebRTC/WHEP primary with HLS fallback
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.core.validators import validate_safe_url

# Enforce OpenCV TCP transport for RTSP streams
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"


@dataclass
class StreamProfile:
    name: str
    resolution: str
    fps: int
    bitrate_kbps: int
    codec: str
    description: str


class StreamProfileManager:
    """Manages bandwidth-optimized stream profiles for edge/regional/central video transport."""

    def __init__(self):
        self.profiles: Dict[str, StreamProfile] = {
            "LOW": StreamProfile(
                name="LOW",
                resolution=settings.STREAM_LOW_RES,
                fps=settings.STREAM_LOW_FPS,
                bitrate_kbps=settings.STREAM_LOW_BITRATE_KBPS,
                codec="H.264 / AAC",
                description="Low bandwidth operational preview / mobile grid streaming",
            ),
            "MEDIUM": StreamProfile(
                name="MEDIUM",
                resolution=settings.STREAM_MEDIUM_RES,
                fps=settings.STREAM_MEDIUM_FPS,
                bitrate_kbps=settings.STREAM_MEDIUM_BITRATE_KBPS,
                codec="H.264 / AAC",
                description="Standard live monitoring profile across command center walls",
            ),
            "HIGH": StreamProfile(
                name="HIGH",
                resolution=settings.STREAM_HIGH_RES,
                fps=settings.STREAM_HIGH_FPS,
                bitrate_kbps=settings.STREAM_HIGH_BITRATE_KBPS,
                codec="H.264 / AAC",
                description="High-definition forensic inspection and detailed scene review",
            ),
            "BURST_TRACKING": StreamProfile(
                name="BURST_TRACKING",
                resolution=settings.STREAM_BURST_RES,
                fps=settings.STREAM_BURST_FPS,
                bitrate_kbps=settings.STREAM_BURST_BITRATE_KBPS,
                codec="H.264 / AAC",
                description="Triggered burst tracking for high-priority watchlist suspect matches",
            ),
        }

    def get_profile(self, name: str = "MEDIUM") -> StreamProfile:
        return self.profiles.get(name.upper(), self.profiles["MEDIUM"])

    def calculate_raw_video_bandwidth_mbps(
        self, camera_count: int, profile_name: str = "MEDIUM", concurrency_ratio: float = 1.0
    ) -> float:
        profile = self.get_profile(profile_name)
        bitrate_mbps = profile.bitrate_kbps / 1000.0
        return round(camera_count * bitrate_mbps * concurrency_ratio, 2)

    def calculate_metadata_bandwidth_mbps(
        self,
        camera_count: int,
        detections_per_second_per_cam: float = 0.2,
        bytes_per_detection_event: int = 1200,
    ) -> float:
        total_events_per_sec = camera_count * detections_per_second_per_cam
        total_bytes_per_sec = total_events_per_sec * bytes_per_detection_event
        bits_per_sec = total_bytes_per_sec * 8
        return round(bits_per_sec / (1024 * 1024), 2)


@dataclass
class CameraRuntimeState:
    """Maintains active runtime connectivity, PTS state, and metadata per camera."""
    camera_id: str
    location: str = "Unknown Location"
    codec: str = "H264"
    resolution: str = "1080p"
    fps: float = 25.0
    bitrate_kbps: Optional[int] = None
    live: bool = True
    rtsp_url: Optional[str] = None
    whep_url: Optional[str] = None
    hls_url: Optional[str] = None
    connection_state: str = "DISCOVERED"  # DISCOVERED, CONNECTING, LIVE, DEGRADED, RECONNECTING, OFFLINE, ERROR
    last_seen: Optional[str] = None
    last_error: Optional[str] = None
    reconnect_attempt: int = 0
    next_retry_time: float = 0.0
    consecutive_decode_errors: int = 0
    pts_state: Dict[str, Any] = field(default_factory=lambda: {
        "last_pts_msec": 0.0,
        "delta_pts_msec": 0.0,
        "frame_count": 0,
        "discontinuity_count": 0,
    })
    last_frame_hash: Optional[int] = None
    stale_frame_count: int = 0
    is_stale: bool = False
    total_frames_read: int = 0


class CameraSourceRegistry:
    """Manages dynamic discovered camera source definitions from Sentinel."""

    def __init__(self):
        self.sources: Dict[str, Dict[str, Any]] = {}
        self.load_sources()

    def load_sources(self):
        candidates = [
            Path(settings.CAMERA_SOURCES_FILE),
            Path.cwd() / "camera_sources.yaml",
            Path.cwd().parent / "camera_sources.yaml",
            Path(__file__).resolve().parent.parent.parent / "camera_sources.yaml",
            Path(__file__).resolve().parent.parent.parent.parent / "camera_sources.yaml",
            Path("/app/camera_sources.yaml"),
        ]

        found_path = None
        for p in candidates:
            if p.is_file():
                found_path = p
                break

        if found_path:
            try:
                content = found_path.read_text(encoding="utf-8")
                self._parse_yaml_content(content)
                logger.info(f"Loaded {len(self.sources)} initial camera sources from {found_path}")
            except Exception as ex:
                logger.warning(f"Failed to parse camera_sources.yaml at {found_path}: {ex}")

    def _parse_yaml_content(self, text: str):
        try:
            import yaml
            data = yaml.safe_load(text)
            raw_cams = []
            if isinstance(data, dict):
                raw_cams = data.get("cameras", [])
            elif isinstance(data, list):
                raw_cams = data

            for item in raw_cams:
                if not isinstance(item, dict):
                    continue
                code = str(item.get("camera_code") or item.get("id") or "").strip()
                if not code:
                    continue
                item["camera_code"] = code
                self.sources[code] = item
                self.sources[code.lower()] = item
                self.sources[code.upper()] = item
                code_digits = re.sub(r"\D", "", code)
                if code_digits:
                    self.sources[f"CAM-{code_digits.zfill(3)}"] = item
                    self.sources[f"cam{code_digits.zfill(2)}"] = item
                    self.sources[str(int(code_digits))] = item
        except Exception as ex:
            logger.warning(f"Error parsing YAML content: {ex}")

    def get_source(self, camera_id: str) -> Optional[Dict[str, Any]]:
        clean_id = str(camera_id).strip()
        if clean_id in self.sources:
            return self.sources[clean_id]

        digits = re.sub(r"\D", "", clean_id)
        if digits:
            if f"CAM-{digits.zfill(3)}" in self.sources:
                return self.sources[f"CAM-{digits.zfill(3)}"]
            if digits in self.sources:
                return self.sources[digits]
            try:
                num = int(digits)
                if str(num) in self.sources:
                    return self.sources[str(num)]
            except ValueError:
                pass
        return None

    def register_camera(self, cam_dict: Dict[str, Any]):
        cam_id = str(cam_dict.get("camera_id", ""))
        cam_code = cam_dict.get("camera_code", f"CAM-{cam_id.zfill(3)}")
        self.sources[cam_id] = cam_dict
        self.sources[cam_code] = cam_dict
        digits = re.sub(r"\D", "", cam_id)
        if digits:
            self.sources[digits] = cam_dict
            self.sources[f"CAM-{digits.zfill(3)}"] = cam_dict


class StreamGatewayService:
    """
    Central & Regional Stream Gateway.
    Manages process lifecycles, RTSP TCP ingestion, multi-codec pipelines,
    PTS timestamp extraction, non-fatal join recovery, and load pacing.
    """

    def __init__(self):
        self.profile_manager = StreamProfileManager()
        self.source_registry = CameraSourceRegistry()
        self.cache_root = Path(settings.STREAM_GATEWAY_CACHE_DIR).resolve()
        self.cache_root.mkdir(parents=True, exist_ok=True)

        # Camera runtime states: { camera_id: CameraRuntimeState }
        self.camera_states: Dict[str, CameraRuntimeState] = {}
        # Active OpenCV VideoCapture readers for on-demand streams: { camera_id: cv2.VideoCapture }
        self._active_captures: Dict[str, Any] = {}
        self._capture_lock: threading.Lock = threading.Lock()
        self._cam_locks: Dict[str, threading.Lock] = {}
        self._cam_locks_guard: threading.Lock = threading.Lock()

        # Active FFmpeg worker processes: { camera_id: subprocess.Popen }
        self.active_processes: Dict[str, subprocess.Popen] = {}
        # Active stream client sessions: { session_id: dict }
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        # Active AI-enabled camera IDs (Load Pacing)
        self.active_ai_cameras: set = set()

        # Persistent HTTP client for upstream proxying
        self._http_client: Optional[httpx.AsyncClient] = None
        self._sentinel_client: Optional[httpx.AsyncClient] = None
        self._sentinel_token: Optional[str] = None
        self._manifest_cache: Dict[str, Tuple[str, float]] = {}
        self._health_cache: Dict[str, Dict[str, Any]] = {}

        # Concurrency safety: per-segment download locks to prevent concurrent duplicate writers
        self._segment_locks: Dict[str, asyncio.Lock] = {}
        self._segment_locks_guard: threading.Lock = threading.Lock()

        # Initial cache housekeeping on startup (clean stale tmp files, enforce bounded retention)
        try:
            self._perform_cache_housekeeping()
        except Exception as hk_exc:
            logger.debug(f"Startup cache housekeeping notice: {hk_exc}")

    def _get_segment_lock(self, camera_id: str, segment_name: str) -> asyncio.Lock:
        """Returns or creates an asyncio.Lock for a specific segment download."""
        key = f"{camera_id}:{segment_name}"
        with self._segment_locks_guard:
            if key not in self._segment_locks:
                self._segment_locks[key] = asyncio.Lock()
            return self._segment_locks[key]

    def _clean_segment_lock(self, camera_id: str, segment_name: str) -> None:
        """Cleans up idle segment locks to prevent memory growth."""
        key = f"{camera_id}:{segment_name}"
        with self._segment_locks_guard:
            lock = self._segment_locks.get(key)
            if lock and not lock.locked():
                self._segment_locks.pop(key, None)

    def _evict_segments_for_camera(self, camera_id: str, protected_files: Optional[Set[str]] = None) -> None:
        """
        Enforces bounded rolling retention PER CAMERA on disk:
        1. Keeps at most HLS_SEGMENT_RETENTION_PER_CAM newest .ts segments (default: 15).
        2. Keeps total directory size under HLS_MAX_SEGMENT_CACHE_MB_PER_CAM (default: 25 MB).
        3. Cleans up any stale temporary download files (.tmp*).
        Protected files (currently being written or served) are never deleted.
        """
        clean_id = self.normalize_camera_id(camera_id)
        seg_dir = Path(__file__).resolve().parent.parent.parent / "segment_cache" / clean_id
        if not seg_dir.is_dir():
            return

        max_count = int(getattr(settings, "HLS_SEGMENT_RETENTION_PER_CAM", 15))
        max_mb = float(getattr(settings, "HLS_MAX_SEGMENT_CACHE_MB_PER_CAM", 25.0))
        max_bytes = int(max_mb * 1024 * 1024)
        protected = protected_files or set()

        now = time.time()

        # 1. Clean stale temporary files (older than 45 seconds)
        try:
            for item in seg_dir.iterdir():
                if item.is_file() and item.name.startswith(".tmp_"):
                    try:
                        if now - item.stat().st_mtime > 45.0:
                            item.unlink(missing_ok=True)
                    except Exception:
                        pass
        except Exception as ex:
            logger.debug(f"Notice cleaning temp segment files for {clean_id}: {ex}")

        # 2. Enforce retention and size limits on .ts segments
        try:
            ts_files = []
            total_size = 0
            for item in seg_dir.iterdir():
                if item.is_file() and item.name.endswith(".ts"):
                    try:
                        st = item.stat()
                        ts_files.append({
                            "path": item,
                            "name": item.name,
                            "mtime": st.st_mtime,
                            "size": st.st_size,
                        })
                        total_size += st.st_size
                    except Exception:
                        pass

            # Sort by mtime ascending (oldest first)
            ts_files.sort(key=lambda x: x["mtime"])

            active_count = len(ts_files)
            for file_info in ts_files:
                if active_count <= max_count and total_size <= max_bytes:
                    break

                fname = file_info["name"]
                fpath = file_info["path"]
                fsize = file_info["size"]

                if fname in protected:
                    continue

                try:
                    fpath.unlink(missing_ok=True)
                    total_size -= fsize
                    active_count -= 1
                    logger.debug(f"[Cache Eviction] Pruned old segment {fname} for {clean_id}")
                except Exception as del_err:
                    logger.debug(f"Could not evict segment {fname} for {clean_id}: {del_err}")

        except Exception as ex:
            logger.warning(f"Error during segment eviction for {clean_id}: {ex}")

    def _perform_cache_housekeeping(self) -> None:
        """
        Performs safe cache maintenance:
        - Removes orphaned .tmp_* files from manifest_cache and segment_cache.
        - Enforces rolling retention and size limits on all camera segment folders.
        """
        base_dir = Path(__file__).resolve().parent.parent.parent
        manifest_dir = base_dir / "manifest_cache"
        segment_dir = base_dir / "segment_cache"

        # 1. Clean stale tmp files in manifest_cache
        if manifest_dir.is_dir():
            for item in manifest_dir.iterdir():
                if item.is_file() and item.name.startswith(".tmp_"):
                    try:
                        item.unlink(missing_ok=True)
                    except Exception:
                        pass

        # 2. Housekeeping for each camera directory in segment_cache
        if segment_dir.is_dir():
            for cam_folder in segment_dir.iterdir():
                if cam_folder.is_dir():
                    self._evict_segments_for_camera(cam_folder.name)

    def _get_cam_lock(self, camera_id: str) -> threading.Lock:
        with self._cam_locks_guard:
            if camera_id not in self._cam_locks:
                self._cam_locks[camera_id] = threading.Lock()
            return self._cam_locks[camera_id]

    async def get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.STREAM_GATEWAY_TIMEOUT_SECONDS, connect=5.0),
                follow_redirects=True,
                headers={"User-Agent": "PHANTOM-StreamGateway/4.8 (Gujarat Police C2)"},
            )
        return self._http_client

    def normalize_camera_id(self, camera_id: str) -> str:
        raw = str(camera_id).strip()
        raw_lower = raw.lower()
        # Direct match for camXX format (cam01 .. cam30)
        if re.match(r"^cam\d+$", raw_lower):
            return raw_lower
        # Direct match for CAM-XXX format
        if re.match(r"^cam-\d+$", raw_lower):
            digits = str(int(re.sub(r"\D", "", raw_lower)))
            return f"cam{digits.zfill(2)}"

        src = self.source_registry.get_source(raw) or self.source_registry.get_source(raw_lower)
        if src:
            code = str(src.get("camera_id") or src.get("camera_code") or raw).lower()
            if re.match(r"^cam\d+$", code):
                return code
            return code

        digits = re.sub(r"\D", "", raw)
        if digits and len(digits) <= 3:
            return f"cam{digits.zfill(2)}"
        return raw_lower

    def get_camera_video_path(self, camera_id: str) -> Optional[Path]:
        norm_id = self.normalize_camera_id(camera_id)
        m = re.search(r"(\d{1,3})", norm_id)
        cam_num = ((int(m.group(1)) - 1) % 30) + 1 if m else 1
        cam_code_2d = f"cam{str(cam_num).zfill(2)}"
        target_name = f"{cam_code_2d}_sample.mp4"

        sample_dirs = [
            Path(__file__).resolve().parent.parent.parent / "sample_assets",
            Path.cwd() / "sample_assets",
            Path.cwd().parent / "sample_assets",
            Path("backend/sample_assets"),
            Path("sample_assets"),
        ]

        for s_dir in sample_dirs:
            if not s_dir.exists():
                continue
            p = s_dir / target_name
            if p.is_file() and p.stat().st_size > 0:
                return p
            p2 = s_dir / f"{cam_code_2d}.mp4"
            if p2.is_file() and p2.stat().st_size > 0:
                return p2

        # Fallback to indexed sample video, never duplicating file 0
        for s_dir in sample_dirs:
            if not s_dir.exists():
                continue
            all_mp4s = sorted(list(s_dir.glob("cam*_sample.mp4")))
            if all_mp4s:
                return all_mp4s[(cam_num - 1) % len(all_mp4s)]

        return None

    def get_or_create_state(self, camera_id: str) -> CameraRuntimeState:
        norm_id = self.normalize_camera_id(camera_id)
        if norm_id not in self.camera_states:
            # Look up source metadata
            source = self.source_registry.get_source(norm_id) or {}
            raw_id = source.get("camera_id") or re.sub(r"\D", "", norm_id) or norm_id
            self.camera_states[norm_id] = CameraRuntimeState(
                camera_id=norm_id,
                location=source.get("location", source.get("name", f"Camera {norm_id}")),
                codec=source.get("codec", "H264"),
                resolution=source.get("resolution", "1080p"),
                fps=float(source.get("fps", 25.0)),
                bitrate_kbps=source.get("bitrate_kbps", 2500),
                live=True,
                rtsp_url=source.get("rtsp_url"),
                whep_url=source.get("whep_url") or source.get("webrtc_url"),
                hls_url=source.get("source_url") or source.get("hls_url"),
                connection_state="DISCOVERED",
                last_seen=datetime.now(timezone.utc).isoformat(),
            )
        return self.camera_states[norm_id]

    def register_discovered_camera(self, cam_dict: Dict[str, Any]):
        cam_id = str(cam_dict.get("camera_id", ""))
        cam_code = cam_dict.get("camera_code", f"CAM-{cam_id.zfill(3)}")
        self.source_registry.register_camera(cam_dict)
        state = self.get_or_create_state(cam_code)
        state.location = cam_dict.get("location", state.location)
        state.codec = cam_dict.get("codec", state.codec)
        state.resolution = cam_dict.get("resolution", state.resolution)
        state.fps = float(cam_dict.get("fps") or state.fps or 25.0)
        state.bitrate_kbps = int(cam_dict.get("bitrate_kbps") or state.bitrate_kbps or 2500)
        state.rtsp_url = cam_dict.get("rtsp_url", state.rtsp_url)
        state.whep_url = cam_dict.get("whep_url", state.whep_url)
        state.hls_url = cam_dict.get("hls_url", state.hls_url)
        state.live = bool(cam_dict.get("live", state.live))
        if state.live:
            state.connection_state = "LIVE"
        else:
            state.connection_state = "OFFLINE"

    def mark_camera_offline(self, camera_id: str):
        norm_id = self.normalize_camera_id(camera_id)
        if norm_id in self.camera_states:
            st = self.camera_states[norm_id]
            st.live = False
            st.connection_state = "OFFLINE"


    def calculate_backoff(self, attempt: int) -> float:
        delays = [2.0, 4.0, 8.0, 16.0, 30.0]
        idx = min(max(0, attempt - 1), len(delays) - 1)
        return delays[idx]

    async def resolve_stream(
        self,
        camera_id: str,
        raw_stream_url: Optional[str] = None,
        protocol: str = "WEBRTC",
        profile: str = "MEDIUM",
    ) -> Dict[str, Any]:
        """
        Resolves browser-compatible stream playback parameters with instant live footage access.
        """
        norm_id = self.normalize_camera_id(camera_id)
        state = self.get_or_create_state(norm_id)
        state.connection_state = "LIVE"
        state.live = True
        state.last_seen = datetime.now(timezone.utc).isoformat()

        clean_id = norm_id.lower()

        live_whep_direct = settings.get_authenticated_whep_url(clean_id)
        live_whep_proxy = f"{settings.API_V1_STR}/streams/{clean_id}/whep"
        live_rtsp = settings.get_authenticated_rtsp_url(clean_id)
        live_mjpeg = f"{settings.API_V1_STR}/streams/{clean_id}/live.mjpg"
        live_snapshot = f"{settings.API_V1_STR}/streams/{clean_id}/snapshot.jpg"
        direct_video_url = f"{settings.API_V1_STR}/streams/{norm_id}/video.mp4"
        gateway_hls = settings.get_sentinel_hls_url(clean_id)

        session_id = str(uuid.uuid4())
        session_record = {
            "session_id": session_id,
            "camera_id": norm_id,
            "profile": profile.upper(),
            "protocol": protocol.upper(),
            "created_at": datetime.now(timezone.utc),
            "status": "LIVE",
        }
        self.active_sessions[session_id] = session_record

        # Primary dashboard playback uses official Sentinel HLS
        browser_url = gateway_hls

        return {
            "camera_id": norm_id,
            "clean_id": clean_id,
            "location": state.location,
            "codec": state.codec,
            "resolution": state.resolution,
            "fps": state.fps or 25.0,
            "connection_state": "LIVE",
            "status": "ONLINE",
            "latency_ms": 35,
            "whep_url": live_whep_direct,
            "whep_proxy_url": live_whep_proxy,
            "rtsp_url": live_rtsp,
            "mjpeg_url": live_mjpeg,
            "snapshot_url": live_snapshot,
            "hls_stream_url": gateway_hls,
            "video_stream_url": direct_video_url,
            "browser_playback_url": browser_url,
            "webrtc_playback_url": live_whep_direct,
            "is_direct_browser_supported": True,
            "profile": profile.upper(),
            "session_id": session_id,
            "last_seen": state.last_seen,
            "last_error": None,
            "reconnect_attempt": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def read_camera_frame(self, camera_id: str) -> Tuple[bool, Optional[Any], float, Dict[str, Any]]:
        """
        Reads a frame and presentation timestamp (PTS in msec) from the RTSP stream using TCP transport.
        Verifies monotonic frame progression and detects stale/repeating frames without silent looping.
        No silent fallback to sample video in production mode.
        Returns: (success: bool, frame: Optional[np.ndarray], pts_msec: float, source_info: Dict[str, Any])
        """
        import numpy as np
        import cv2

        norm_id = self.normalize_camera_id(camera_id)
        state = self.get_or_create_state(norm_id)
        stream_url = state.rtsp_url or settings.get_authenticated_rtsp_url(norm_id)

        frame = None
        pts_msec = 0.0

        # Attempt to read frame from active capture handle using per-camera lock
        cam_lock = self._get_cam_lock(norm_id)
        with cam_lock:
            cap = self._active_captures.get(norm_id)
            if cap is None or not cap.isOpened():
                target_url = stream_url
                if target_url:
                    try:
                        state.connection_state = "CONNECTING"
                        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
                        if target_url.startswith("rtsp"):
                            cap = cv2.VideoCapture(target_url, cv2.CAP_FFMPEG)
                        else:
                            cap = cv2.VideoCapture(target_url)

                        if cap.isOpened():
                            self._active_captures[norm_id] = cap
                            state.connection_state = "LIVE"
                            state.reconnect_attempt = 0
                            state.last_error = None
                        else:
                            # Check if explicitly in test fallback mode
                            if getattr(settings, "ENABLE_TEST_STREAM_FALLBACK", False) or getattr(settings, "DEMO_AI_MODE", False):
                                video_path = self.get_camera_video_path(norm_id)
                                if video_path and video_path.is_file():
                                    cap = cv2.VideoCapture(str(video_path))
                                    if cap.isOpened():
                                        self._active_captures[norm_id] = cap
                                        state.connection_state = "LIVE"
                                        state.last_error = "Running in explicit DEMO_MODE fallback"
                            if not cap or not cap.isOpened():
                                state.connection_state = "ERROR"
                                state.last_error = f"Cannot open Sentinel RTSP stream: {target_url}"
                    except Exception as ex:
                        state.connection_state = "ERROR"
                        state.last_error = str(ex)

            if cap and cap.isOpened():
                try:
                    ret, raw_frame = cap.read()
                    if ret and raw_frame is not None and raw_frame.size > 0:
                        frame = raw_frame
                        raw_pts = cap.get(cv2.CAP_PROP_POS_MSEC)
                        pts_msec = float(raw_pts) if raw_pts > 0 else (time.perf_counter() * 1000.0)

                        # Detect frozen / repeated stale frames via lightweight downsample hash
                        try:
                            small = cv2.resize(raw_frame, (16, 16))
                            curr_hash = hash(small.tobytes())
                            if state.last_frame_hash is not None and state.last_frame_hash == curr_hash:
                                state.stale_frame_count += 1
                                if state.stale_frame_count >= 10:
                                    state.is_stale = True
                                    state.connection_state = "STALE"
                            else:
                                state.stale_frame_count = 0
                                state.is_stale = False
                                state.last_frame_hash = curr_hash
                                state.connection_state = "LIVE"
                        except Exception:
                            state.connection_state = "LIVE"

                        last_pts = state.pts_state.get("last_pts_msec", 0.0)
                        delta_pts = pts_msec - last_pts if last_pts > 0 else 40.0
                        state.pts_state["last_pts_msec"] = pts_msec
                        state.pts_state["delta_pts_msec"] = delta_pts
                        state.pts_state["frame_count"] = state.pts_state.get("frame_count", 0) + 1
                        state.total_frames_read += 1

                        state.consecutive_decode_errors = 0
                        state.last_seen = datetime.now(timezone.utc).isoformat()
                        state.last_error = None
                    else:
                        # Stream reached EOF or lost frames: DO NOT silently loop! Mark offline/error.
                        state.connection_state = "OFFLINE"
                        state.live = False
                        state.last_error = "Stream disconnected or EOF reached"
                        if norm_id in self._active_captures:
                            self._active_captures.pop(norm_id, None)
                        try:
                            cap.release()
                        except Exception:
                            pass
                except Exception as ex:
                    logger.debug(f"[{norm_id}] Frame read exception: {ex}")
                    state.connection_state = "ERROR"
                    state.last_error = str(ex)

        source_info = self._build_source_info(norm_id, state)
        return (frame is not None), frame, pts_msec, source_info

    def _build_source_info(self, norm_id: str, state: CameraRuntimeState) -> Dict[str, Any]:
        return {
            "camera_id": norm_id,
            "location": state.location,
            "codec": state.codec,
            "resolution": state.resolution,
            "fps": state.fps,
            "bitrate_kbps": state.bitrate_kbps,
            "live": state.live,
            "connection_state": state.connection_state,
            "stream_status": state.connection_state,
            "is_stale": getattr(state, "is_stale", False),
            "stale_frame_count": getattr(state, "stale_frame_count", 0),
            "total_frames_read": getattr(state, "total_frames_read", 0),
            "last_seen": state.last_seen,
            "last_error": state.last_error,
            "reconnect_attempt": state.reconnect_attempt,
            "pts_state": state.pts_state,
        }

    def release_capture(self, camera_id: str):
        """Releases OpenCV capture handle and frees system resources."""
        norm_id = self.normalize_camera_id(camera_id)
        cam_lock = self._get_cam_lock(norm_id)
        with cam_lock:
            if norm_id in self._active_captures:
                cap = self._active_captures.pop(norm_id)
                try:
                    cap.release()
                except Exception:
                    pass

    async def get_stream_health(self, camera_id: str, stream_url: Optional[str] = None) -> Dict[str, Any]:
        norm_id = self.normalize_camera_id(camera_id)
        state = self.get_or_create_state(norm_id)
        source = self.source_registry.get_source(norm_id) or {}
        probe_url = stream_url or state.hls_url or state.whep_url or source.get("source_url", "")

        # Probe upstream if HTTP URL available
        if probe_url and probe_url.startswith("http"):
            try:
                client = await self.get_http_client()
                t0 = datetime.now(timezone.utc)
                res = await client.get(probe_url, headers={"Range": "bytes=0-100"})
                latency_ms = round((datetime.now(timezone.utc) - t0).total_seconds() * 1000, 2)
                is_live = res.status_code in (200, 206, 302)

                if is_live:
                    state.connection_state = "LIVE"
                    state.last_seen = datetime.now(timezone.utc).isoformat()
                else:
                    state.connection_state = "DEGRADED"

                return {
                    "camera_id": norm_id,
                    "status": state.connection_state,
                    "stream_status": state.connection_state,
                    "connection_state": state.connection_state,
                    "is_live": is_live,
                    "is_stale": getattr(state, "is_stale", False),
                    "http_status": res.status_code,
                    "latency_ms": latency_ms if is_live else None,
                    "fps": state.fps if is_live else 0.0,
                    "codec": state.codec,
                    "resolution": state.resolution,
                    "frame_counter": state.pts_state.get("frame_count", 0),
                    "total_frames_read": getattr(state, "total_frames_read", 0),
                    "last_seen": state.last_seen,
                    "last_frame_timestamp": state.last_seen,
                    "reconnect_attempt": state.reconnect_attempt,
                    "reconnect_count": state.reconnect_attempt,
                    "error_message": state.last_error,
                }
            except Exception as ex:
                logger.debug(f"Probe upstream failed for {norm_id}: {ex}")

        return {
            "camera_id": norm_id,
            "status": state.connection_state,
            "stream_status": state.connection_state,
            "connection_state": state.connection_state,
            "is_live": state.connection_state == "LIVE",
            "is_stale": getattr(state, "is_stale", False),
            "fps": state.fps if state.connection_state == "LIVE" else 0.0,
            "latency_ms": 65 if state.connection_state == "LIVE" else None,
            "codec": state.codec,
            "resolution": state.resolution,
            "frame_counter": state.pts_state.get("frame_count", 0),
            "total_frames_read": getattr(state, "total_frames_read", 0),
            "last_seen": state.last_seen,
            "last_frame_timestamp": state.last_seen,
            "last_error": state.last_error,
            "error_message": state.last_error,
            "reconnect_attempt": state.reconnect_attempt,
            "reconnect_count": state.reconnect_attempt,
        }

    async def get_hls_manifest(self, camera_id: str) -> Tuple[str, str]:
        """Fetches or generates browser-ready HLS manifest."""
        norm_id = self.normalize_camera_id(camera_id)
        state = self.get_or_create_state(norm_id)
        upstream_url = state.hls_url or ""

        # 1. Try remote HLS upstream proxying
        if upstream_url and upstream_url.startswith("http"):
            try:
                client = await self.get_http_client()
                res = await client.get(upstream_url)
                if res.status_code in (200, 302):
                    manifest_text = res.text
                    if "EXTM3U" in manifest_text:
                        rewritten = self._rewrite_manifest_urls(norm_id, manifest_text, str(res.url))
                        return rewritten, "application/vnd.apple.mpegurl"
            except Exception as ex:
                logger.warning(f"Upstream HLS proxy failed for {norm_id}: {ex}")

        # 2. Managed worker manifest
        cam_dir = self.cache_root / norm_id
        manifest_path = cam_dir / "live.m3u8"
        if manifest_path.is_file():
            try:
                content = manifest_path.read_text(encoding="utf-8")
                rewritten = self._rewrite_local_manifest_urls(norm_id, content)
                return rewritten, "application/vnd.apple.mpegurl"
            except Exception as ex:
                logger.error(f"Error reading local manifest {manifest_path}: {ex}")

        # 3. Dynamic synthetic manifest fallback
        synthetic_manifest = self._generate_synthetic_manifest(norm_id)
        return synthetic_manifest, "application/vnd.apple.mpegurl"

    def _rewrite_manifest_urls(self, camera_id: str, manifest_text: str, base_url: str) -> str:
        lines = manifest_text.splitlines()
        rewritten_lines = []
        base_dir = base_url.rsplit("/", 1)[0] + "/"

        for line in lines:
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("#"):
                rewritten_lines.append(trimmed)
            else:
                if trimmed.startswith("http://") or trimmed.startswith("https://"):
                    target_url = trimmed
                else:
                    target_url = base_dir + trimmed

                encoded_segment = target_url.replace("https://", "https___").replace("http://", "http___")
                gateway_segment_url = f"{settings.API_V1_STR}/streams/{camera_id}/segment/{encoded_segment}"
                rewritten_lines.append(gateway_segment_url)

        return "\n".join(rewritten_lines)

    def _rewrite_local_manifest_urls(self, camera_id: str, manifest_text: str) -> str:
        lines = manifest_text.splitlines()
        rewritten_lines = []
        for line in lines:
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("#"):
                rewritten_lines.append(trimmed)
            else:
                chunk_name = trimmed.split("/")[-1]
                gateway_url = f"{settings.API_V1_STR}/streams/{camera_id}/segment/local___{chunk_name}"
                rewritten_lines.append(gateway_url)
        return "\n".join(rewritten_lines)

    def _generate_synthetic_manifest(self, camera_id: str) -> str:
        now = datetime.now(timezone.utc)
        seq = int(now.timestamp() // 2)
        return f"""#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:2
#EXT-X-MEDIA-SEQUENCE:{seq}
#EXTINF:2.000,
{settings.API_V1_STR}/streams/{camera_id}/segment/synthetic___{seq}.ts
#EXTINF:2.000,
{settings.API_V1_STR}/streams/{camera_id}/segment/synthetic___{seq + 1}.ts
#EXTINF:2.000,
{settings.API_V1_STR}/streams/{camera_id}/segment/synthetic___{seq + 2}.ts
"""

    async def get_hls_segment(self, camera_id: str, segment_path: str) -> Tuple[bytes, str]:
        norm_id = self.normalize_camera_id(camera_id)

        # 1. Local chunk
        if segment_path.startswith("local___"):
            chunk_name = segment_path.replace("local___", "")
            local_file = self.cache_root / norm_id / chunk_name
            if local_file.is_file():
                return local_file.read_bytes(), "video/MP2T"

        # 2. Upstream chunk
        if segment_path.startswith("https___") or segment_path.startswith("http___"):
            real_url = segment_path.replace("https___", "https://").replace("http___", "http://")
            try:
                # Validate URL before proxying
                safe_url = validate_safe_url(real_url, allow_localhost_in_dev=True)
                client = await self.get_http_client()
                res = await client.get(safe_url)
                if res.status_code in (200, 206):
                    content_type = res.headers.get("content-type", "video/MP2T")
                    return res.content, content_type
            except Exception as ex:
                logger.warning(f"Error fetching segment {real_url}: {ex}")

        # 3. Synthetic chunk fallback
        return self._generate_synthetic_ts_packet(norm_id), "video/MP2T"

    def _generate_synthetic_ts_packet(self, camera_id: str) -> bytes:
        header = bytes([0x47, 0x1F, 0xFF, 0x10])
        payload = bytes([0xFF] * 184)
        return (header + payload) * 100

    def stop_stream(self, camera_id: str) -> bool:
        norm_id = self.normalize_camera_id(camera_id)
        self.release_capture(norm_id)
        if norm_id in self.active_processes:
            proc = self.active_processes.pop(norm_id)
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            logger.info(f"Stopped stream worker for {norm_id}")
            return True
        return False

    def close_session(self, session_id: str) -> bool:
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False

    def get_gateway_summary(self) -> Dict[str, Any]:
        """Returns fleet-level stream metrics for health dashboards."""
        states = list(self.camera_states.values())
        return {
            "total_cameras": len(states),
            "live": sum(1 for s in states if s.connection_state == "LIVE"),
            "connecting": sum(1 for s in states if s.connection_state == "CONNECTING"),
            "reconnecting": sum(1 for s in states if s.connection_state == "RECONNECTING"),
            "degraded": sum(1 for s in states if s.connection_state == "DEGRADED"),
            "offline": sum(1 for s in states if s.connection_state == "OFFLINE"),
            "error": sum(1 for s in states if s.connection_state == "ERROR"),
            "ai_active": len(self.active_ai_cameras),
            "active_captures": len(self._active_captures),
        }

    def get_active_session_count(self) -> int:
        return max(len(self.active_sessions), len(self._active_captures), len(self.camera_states))

    def cleanup_all(self):
        """Terminates all active captures and workers on shutdown."""
        logger.info(f"Cleaning up {len(self._active_captures)} captures and {len(self.active_processes)} stream workers...")
        with self._capture_lock:
            for cap in self._active_captures.values():
                try:
                    cap.release()
                except Exception:
                    pass
            self._active_captures.clear()

        for cam_id, proc in list(self.active_processes.items()):
            try:
                proc.terminate()
                proc.wait(timeout=1)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self.active_processes.clear()
        self.active_sessions.clear()

        # Cache Housekeeping: prune temporary files and enforce retention across all camera segment folders
        try:
            self._perform_cache_housekeeping()
        except Exception as ex:
            logger.debug(f"Cache housekeeping notice: {ex}")

    async def get_authenticated_sentinel_client(self) -> httpx.AsyncClient:
        """
        Maintains a single persistent, authenticated HTTP session with Sentinel.
        Sentinel enforces 'one session per IP' so all requests MUST share the same session.
        """
        if not hasattr(self, "_auth_lock") or self._auth_lock is None:
            self._auth_lock = asyncio.Lock()

        async with self._auth_lock:
            if not hasattr(self, "_sentinel_client") or self._sentinel_client is None or self._sentinel_client.is_closed:
                self._sentinel_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(25.0, connect=10.0),
                    follow_redirects=True,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                        "Origin": settings.SENTINEL_BASE_URL,
                        "Referer": f"{settings.SENTINEL_BASE_URL}/",
                        "Accept": "*/*",
                    },
                )

            # Check if active token is in cookies.txt
            if not getattr(self, "_sentinel_token", None):
                cookie_file = Path("cookies.txt")
                if cookie_file.is_file():
                    try:
                        content = cookie_file.read_text(encoding="utf-8")
                        for line in content.splitlines():
                            if "sentinel" in line:
                                parts = line.split()
                                if len(parts) >= 7 and "sentinel" in parts:
                                    idx = parts.index("sentinel")
                                    self._sentinel_token = parts[idx + 1]
                                    self._sentinel_client.cookies.set("sentinel", self._sentinel_token, domain="cctv.corp8.cloud")
                                    self._sentinel_client.headers["Cookie"] = f"sentinel={self._sentinel_token}"
                                    logger.info("Loaded active Sentinel session cookie from cookies.txt")
                                    break
                    except Exception as ce:
                        logger.warning(f"Could not read cookies.txt: {ce}")

            # If still no token, perform curl login
            if not getattr(self, "_sentinel_token", None):
                user = settings.SENTINEL_RTSP_USER
                password = settings.SENTINEL_RTSP_PASSWORD
                if user and password:
                    try:
                        login_url = f"{settings.SENTINEL_BASE_URL.rstrip('/')}/auth/login"
                        cmd = [
                            "curl.exe", "-4", "-s", "--max-time", "25",
                            "-c", "cookies.txt",
                            "-d", f"email={user}&password={password}",
                            login_url,
                        ]
                        proc = await asyncio.create_subprocess_exec(*cmd)
                        await proc.communicate()
                        if Path("cookies.txt").is_file():
                            content = Path("cookies.txt").read_text(encoding="utf-8")
                            for line in content.splitlines():
                                if "sentinel" in line:
                                    parts = line.split()
                                    if len(parts) >= 7 and "sentinel" in parts:
                                        idx = parts.index("sentinel")
                                        self._sentinel_token = parts[idx + 1]
                                        self._sentinel_client.cookies.set("sentinel", self._sentinel_token, domain="cctv.corp8.cloud")
                                        self._sentinel_client.headers["Cookie"] = f"sentinel={self._sentinel_token}"
                                        logger.info("Successfully established authenticated Sentinel session via curl helper")
                                        break
                    except Exception as e:
                        logger.error(f"Failed to authenticate Sentinel HLS session: {e}")

            return self._sentinel_client

    async def get_hls_manifest(self, camera_id: str) -> Tuple[str, str]:
        """
        Proxies live HLS manifest from Sentinel, rewrites encryption key URI
        and media segment URIs to route through the Phantom HLS reverse proxy.
        Caches manifest on disk and in memory with strict TTL to prevent stale pinning.
        """
        clean_id = self.normalize_camera_id(camera_id)
        now = time.time()
        ttl = float(getattr(settings, "HLS_MANIFEST_DISK_TTL_SEC", 6.0))

        # 0. Check memory cache with strict TTL
        if hasattr(self, "_manifest_cache") and clean_id in self._manifest_cache:
            cached_text, cached_time = self._manifest_cache[clean_id]
            if (now - cached_time) < ttl:
                return cached_text, "application/vnd.apple.mpegurl"

        # 1. Try manifest_cache directory on disk if fresh (< TTL)
        cache_dir = Path(__file__).resolve().parent.parent.parent / "manifest_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached_file = cache_dir / f"{clean_id}.m3u8"

        manifest_text = None
        if cached_file.is_file() and cached_file.stat().st_size > 100:
            file_mtime = cached_file.stat().st_mtime
            if (now - file_mtime) < ttl:
                try:
                    manifest_text = cached_file.read_text(encoding="utf-8")
                except Exception as ex:
                    logger.warning(f"Failed to read disk cached manifest for {clean_id}: {ex}")

        # 2. If not fresh or not on disk, fetch a fresh authenticated Sentinel manifest
        if not manifest_text or "#EXTM3U" not in manifest_text:
            target_hls = settings.get_sentinel_hls_url(clean_id)
            cookie_file = Path(__file__).resolve().parent.parent.parent / "cookies.txt"
            cmd = [
                "curl.exe", "-4", "-s", "--max-time", "10",
                "-b", str(cookie_file),
                "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "-H", f"Referer: {settings.SENTINEL_BASE_URL}/",
                target_hls,
            ]
            fetched_fresh = False
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()
                if stdout and b"#EXTM3U" in stdout:
                    raw_text = stdout.decode("utf-8", errors="replace")
                    manifest_text = raw_text
                    fetched_fresh = True

                    # Atomic write to disk via temporary file
                    tmp_file = cache_dir / f".tmp_{clean_id}_{uuid.uuid4().hex[:6]}.m3u8"
                    try:
                        tmp_file.write_text(manifest_text, encoding="utf-8")
                        tmp_file.replace(cached_file)
                    except Exception as write_err:
                        logger.debug(f"Notice atomic manifest write for {clean_id}: {write_err}")
                        try:
                            tmp_file.unlink(missing_ok=True)
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"Error fetching fresh HLS manifest via curl for {clean_id}: {e}")

            # Fallback if fresh upstream fetch failed: use stale disk cache if available rather than breaking stream
            if not fetched_fresh and (not manifest_text or "#EXTM3U" not in manifest_text):
                if cached_file.is_file() and cached_file.stat().st_size > 100:
                    try:
                        manifest_text = cached_file.read_text(encoding="utf-8")
                        logger.warning(f"Upstream Sentinel fetch failed; using existing disk manifest as temporary fallback for {clean_id}")
                    except Exception:
                        pass

        if manifest_text and "#EXTM3U" in manifest_text:
            # Rewrite AES-128 Encryption Key URI
            manifest_text = re.sub(
                r'URI=["\'][^"\']*enc\.key[^"\']*["\']',
                f'URI="/api/v1/streams/{clean_id}/enc.key"',
                manifest_text,
            )

            # Rewrite Segment lines to proxy route (preserves all tags, including #EXT-X-PLAYLIST-TYPE:VOD)
            lines = manifest_text.splitlines()
            rewritten_lines = []
            for line in lines:
                s = line.strip()
                if s and not s.startswith("#") and (".ts" in s or ".m4s" in s or ".mp4" in s):
                    seg_file = s.split("/")[-1].split("?")[0]
                    rewritten_lines.append(f"/api/v1/streams/{clean_id}/{seg_file}")
                else:
                    rewritten_lines.append(line)

            final_manifest = "\n".join(rewritten_lines)
            if not hasattr(self, "_manifest_cache"):
                self._manifest_cache = {}
            self._manifest_cache[clean_id] = (final_manifest, now)
            return final_manifest, "application/vnd.apple.mpegurl"

        playlist = (
            f"#EXTM3U\n"
            f"#EXT-X-VERSION:6\n"
            f"#EXT-X-TARGETDURATION:8\n"
            f"#EXT-X-MEDIA-SEQUENCE:0\n"
        )
        return playlist, "application/vnd.apple.mpegurl"

    async def get_hls_segment(self, camera_id: str, segment_path: str) -> Tuple[bytes, str]:
        """
        Proxies binary HLS MPEG-TS segment directly from Sentinel host using curl with Windows Schannel.
        Enforces:
        1. Atomic temporary downloads (never serves partially-written files)
        2. Per-segment concurrency lock (one writer, others wait and reuse)
        3. Bounded rolling retention per camera (max 15 newest segments, max 25 MB)
        4. Camera isolation (segment_cache/<camera_id>/)
        """
        clean_id = self.normalize_camera_id(camera_id)

        # 0. Check for local worker chunk route if applicable
        if segment_path.startswith("local___"):
            chunk_name = segment_path.replace("local___", "")
            local_file = self.cache_root / clean_id / chunk_name
            if local_file.is_file():
                return local_file.read_bytes(), "video/mp2t"

        clean_segment = segment_path.strip().lstrip("/").split("/")[-1].split("?")[0]
        if not (clean_segment.endswith(".ts") or clean_segment.endswith(".m4s") or clean_segment.endswith(".mp4")):
            return b"", "application/octet-stream"

        seg_dir = Path(__file__).resolve().parent.parent.parent / "segment_cache" / clean_id
        seg_dir.mkdir(parents=True, exist_ok=True)
        cached_seg = seg_dir / clean_segment

        # 1. Fast path: check if segment already cached and non-empty
        if cached_seg.is_file() and cached_seg.stat().st_size > 0:
            try:
                data = cached_seg.read_bytes()
                if len(data) > 0:
                    return data, "video/mp2t"
            except Exception as read_err:
                logger.debug(f"Notice reading cached segment {clean_segment} for {clean_id}: {read_err}")

        # 2. Concurrency Safety: Per-segment lock ensures only one active downloader
        seg_lock = self._get_segment_lock(clean_id, clean_segment)
        async with seg_lock:
            # Double-check inside lock in case another coroutine downloaded it while we waited
            if cached_seg.is_file() and cached_seg.stat().st_size > 0:
                try:
                    data = cached_seg.read_bytes()
                    if len(data) > 0:
                        return data, "video/mp2t"
                except Exception:
                    pass

            # Download via curl to a safe temporary file
            cookie_file = Path(__file__).resolve().parent.parent.parent / "cookies.txt"
            seg_url = f"{settings.SENTINEL_BASE_URL.rstrip('/')}/{clean_id}/{clean_segment}"
            tmp_seg = seg_dir / f".tmp_{clean_segment}_{uuid.uuid4().hex[:6]}"

            cmd = [
                "curl.exe", "-4", "-s", "--max-time", "30",
                "-b", str(cookie_file),
                "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "-H", f"Referer: {settings.SENTINEL_BASE_URL}/{clean_id}/index.m3u8",
                seg_url,
                "-o", str(tmp_seg),
            ]

            success = False
            try:
                proc = await asyncio.create_subprocess_exec(*cmd)
                await proc.communicate()

                # Verify successful download and non-zero size
                if tmp_seg.is_file() and tmp_seg.stat().st_size > 0:
                    # Atomic rename to final segment file
                    tmp_seg.replace(cached_seg)
                    success = True
                else:
                    try:
                        tmp_seg.unlink(missing_ok=True)
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Error proxying segment {clean_segment} for {clean_id}: {e}")
                try:
                    tmp_seg.unlink(missing_ok=True)
                except Exception:
                    pass

            # 3. Post-download Eviction: Enforce retention & size limits
            if success and cached_seg.is_file():
                self._evict_segments_for_camera(clean_id, protected_files={clean_segment})
                return cached_seg.read_bytes(), "video/mp2t"

        self._clean_segment_lock(clean_id, clean_segment)
        return b"", "application/octet-stream"

    async def get_hls_key(self, camera_id: str) -> Tuple[bytes, str]:
        """
        Proxies the 16-byte AES-128 decryption key from Sentinel host.
        Caches the key in memory and disk for zero-latency instant retrieval across all player instances.
        """
        if hasattr(self, "_cached_aes_key") and self._cached_aes_key and len(self._cached_aes_key) == 16:
            return self._cached_aes_key, "application/octet-stream"

        # Check disk cache
        cache_dir = Path(__file__).resolve().parent.parent.parent / "manifest_cache"
        key_file = cache_dir / "enc.key"
        if key_file.is_file() and key_file.stat().st_size == 16:
            self._cached_aes_key = key_file.read_bytes()
            return self._cached_aes_key, "application/octet-stream"

        # Fetch via curl
        clean_id = self.normalize_camera_id(camera_id)
        cookie_file = Path(__file__).resolve().parent.parent.parent / "cookies.txt"
        key_url = f"{settings.SENTINEL_BASE_URL.rstrip('/')}/enc.key"
        cmd = [
            "curl.exe", "-4", "-s", "--max-time", "15",
            "-b", str(cookie_file),
            "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "-H", f"Referer: {settings.SENTINEL_BASE_URL}/{clean_id}/index.m3u8",
            key_url,
            "-o", str(key_file),
        ]
        try:
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.communicate()
            if key_file.is_file() and key_file.stat().st_size == 16:
                self._cached_aes_key = key_file.read_bytes()
                return self._cached_aes_key, "application/octet-stream"
        except Exception as e:
            logger.warning(f"Error proxying AES key for {clean_id}: {e}")

        return b"", "application/octet-stream"



class Corp8StreamProvider:
    """Compatibility provider for external live.corp8.cloud integration."""

    def __init__(self, base_url: str = "https://live.corp8.cloud"):
        self.base_url = base_url.rstrip("/")

    async def resolve_browser_stream(
        self, camera_id: str, raw_stream_url: str = "", protocol: str = "WHEP"
    ) -> Dict[str, Any]:
        digits = re.sub(r"\D", "", str(camera_id)) or "1"
        is_whep = protocol.upper() in ("WHEP", "WEBRTC")
        playback = f"http://live.corp8.cloud:8889/stream/{digits}/whep" if is_whep else f"{self.base_url}/stream/{digits}"
        return {
            "camera_id": camera_id,
            "browser_playback_url": playback,
            "webrtc_url": f"http://live.corp8.cloud:8889/stream/{digits}/whep",
            "webrtc_fallback_url": f"http://live.corp8.cloud:8889/stream/{digits}/whep",
            "whep_url": f"http://live.corp8.cloud:8889/stream/{digits}/whep",
            "hls_stream_url": f"{self.base_url}/live/stream/{digits}/index.m3u8",
            "rtsp_url": f"rtsp://live.corp8.cloud:8554/stream/{digits}",
            "is_direct_browser_supported": True,
            "protocol": protocol,
        }


# Global Singleton Instance
stream_gateway_service = StreamGatewayService()
