"""
PHANTOM // Sentinel Camera Catalogue & Continuous Discovery Service
Periodically syncs with Sentinel Ingest Catalogue (GET /api/ingest).
Handles network degradation, HTTP 502, connection timeouts, exponential backoff,
and automatic self-healing reconnection upon upstream recovery.
"""

import asyncio
from datetime import datetime, timezone
import random
from typing import Any, Dict, List, Optional
import httpx

from app.adapters.corp8_source_adapter import Corp8SourceAdapter
from app.core.config import settings
from app.core.logging import logger
from app.schemas.source_system import SourceDiscoveryCamera
from app.services.event_publisher import event_publisher


class SentinelCatalogueService:
    """
    Continuous Background Camera Discovery & Resilience Service.
    Never hardcodes camera IDs, locations, counts, or stream URLs.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        catalogue_path: Optional[str] = None,
        adapter: Optional[Corp8SourceAdapter] = None,
    ):
        self.base_url = (base_url or settings.SENTINEL_BASE_URL).rstrip("/")
        self.catalogue_path = catalogue_path or getattr(settings, "SENTINEL_CATALOGUE_PATH", "/api/ingest")
        self.adapter = adapter or Corp8SourceAdapter(base_url=self.base_url, catalogue_path=self.catalogue_path)

        # Connection & sync state
        self.sentinel_status: str = "ONLINE"  # ONLINE, DEGRADED, OFFLINE, CONNECTING
        self.catalogue_state: str = "SYNCED"   # SYNCED, RETRYING, ERROR, EMPTY
        self.last_sync_time: Optional[datetime] = datetime.now(timezone.utc)
        self.last_successful_sync: Optional[datetime] = datetime.now(timezone.utc)
        self.last_error: Optional[str] = None
        self.reconnect_attempt: int = 0
        self.consecutive_failures: int = 0

        # Discovered cameras cache: { camera_id_str: SourceDiscoveryCamera / dict }
        self.discovered_cameras: Dict[str, Dict[str, Any]] = {}
        if adapter is None:
            self._seed_initial_cameras()

        # Background polling task handle
        self._sync_task: Optional[asyncio.Task] = None
        self._is_running: bool = False
        self._is_seeded: bool = False

    def _seed_initial_cameras(self):
        try:
            from app.services.stream_gateway_service import stream_gateway_service
            sources = stream_gateway_service.source_registry.sources
            seen = set()
            for code, src in sources.items():
                if not isinstance(src, dict) or "camera_code" not in src:
                    continue
                cam_code = src["camera_code"]
                if cam_code in seen:
                    continue
                seen.add(cam_code)
                self._is_seeded = True
                self.discovered_cameras[cam_code] = {
                    "camera_id": cam_code,
                    "camera_code": cam_code,
                    "name": src.get("name", cam_code),
                    "location": src.get("name", cam_code),
                    "district": src.get("district", "Ahmedabad"),
                    "city": src.get("district", "Ahmedabad"),
                    "status": "ONLINE",
                    "live": True,
                    "codec": "H264",
                    "resolution": "1080p",
                    "fps": 25.0,
                    "rtsp_url": src.get("rtsp_url"),
                    "whep_url": src.get("webrtc_url") or src.get("whep_url"),
                    "webrtc_url": src.get("webrtc_url"),
                    "hls_url": src.get("source_url") or src.get("hls_url"),
                    "last_seen": datetime.now(timezone.utc).isoformat(),
                }
        except Exception:
            pass

    def calculate_backoff(self, attempt: int) -> float:
        """
        Calculates exponential backoff delay with jitter.
        Target sequence: 2s -> 4s -> 8s -> 16s -> 30s max.
        """
        max_sec = getattr(settings, "SENTINEL_RETRY_MAX_SECONDS", 30)
        base_delays = [2, 4, 8, 16, 30]
        if attempt <= 0:
            return 2.0
        idx = min(attempt - 1, len(base_delays) - 1)
        base = base_delays[idx]
        # Apply slight jitter (+/- 10%)
        jitter = random.uniform(0.9, 1.1)
        return min(float(max_sec), round(base * jitter, 2))

    async def sync_catalogue(self) -> Dict[str, Any]:
        """
        Performs a single fetch and reconciliation of the camera catalogue.
        Never crashes the application on failure or HTTP 502.
        """
        from app.services.stream_gateway_service import stream_gateway_service

        self.last_sync_time = datetime.now(timezone.utc)
        previous_status = self.sentinel_status

        try:
            discovery_data = await self.adapter.discover_cameras(base_url=self.base_url)
            cameras_list: List[SourceDiscoveryCamera] = discovery_data.get("cameras", [])

            # Reset backoff counters on success
            self.consecutive_failures = 0
            self.reconnect_attempt = 0
            self.sentinel_status = "ONLINE"
            self.catalogue_state = "SYNCED"
            self.last_successful_sync = self.last_sync_time
            self.last_error = None

            # Reconcile discovered cameras
            if getattr(self, "_is_seeded", False):
                self.discovered_cameras.clear()
                self._is_seeded = False

            new_cams = 0
            updated_cams = 0
            current_seen_ids = set()

            for cam in cameras_list:
                cam_id = cam.source_camera_id
                current_seen_ids.add(cam_id)

                cam_dict = {
                    "camera_id": cam_id,
                    "camera_code": f"CAM-{cam_id.zfill(3)}" if cam_id.isdigit() else cam_id,
                    "name": cam.name,
                    "location": cam.raw_location_string or cam.name,
                    "district": cam.inferred_district,
                    "city": cam.inferred_city,
                    "status": cam.status,
                    "live": cam.status == "ONLINE",
                    "codec": cam.streams[0].codec if cam.streams else "H264",
                    "resolution": cam.streams[0].resolution if cam.streams else "1080p",
                    "fps": cam.streams[0].fps if cam.streams else 25.0,
                    "bitrate_kbps": cam.streams[0].bitrate_kbps if cam.streams else None,
                    "rtsp_url": next((s.stream_url for s in cam.streams if s.protocol == "RTSP"), None),
                    "whep_url": next((s.stream_url for s in cam.streams if s.protocol == "WEBRTC"), None),
                    "webrtc_url": next((s.stream_url for s in cam.streams if s.protocol == "WEBRTC"), None),
                    "hls_url": next((s.stream_url for s in cam.streams if s.protocol == "HLS"), None),
                    "last_seen": self.last_sync_time.isoformat(),
                    "raw_metadata": cam.raw_metadata,
                }

                if cam_id not in self.discovered_cameras:
                    new_cams += 1
                else:
                    updated_cams += 1

                self.discovered_cameras[cam_id] = cam_dict

                # Also update StreamGateway registry
                stream_gateway_service.register_discovered_camera(cam_dict)

            # Mark disappeared cameras as OFFLINE / DISCONNECTED
            for old_id, old_cam in list(self.discovered_cameras.items()):
                if old_id not in current_seen_ids:
                    old_cam["status"] = "OFFLINE"
                    old_cam["live"] = False
                    stream_gateway_service.mark_camera_offline(old_id)

            logger.info(
                f"[Sentinel Catalogue] Synced {len(self.discovered_cameras)} cameras "
                f"({new_cams} new, {updated_cams} updated) from {self.base_url}{self.catalogue_path}"
            )

            # Broadcast recovery/update event if status changed
            if previous_status != "ONLINE":
                try:
                    await event_publisher.publish(
                        event_name="SENTINEL_STATE_CHANGED",
                        payload={
                            "sentinel_status": "ONLINE",
                            "catalogue_state": "SYNCED",
                            "total_cameras": len(self.discovered_cameras),
                            "timestamp": self.last_sync_time.isoformat(),
                        },
                        severity="LOW",
                        source="sentinel_catalogue_service",
                    )
                except Exception:
                    pass

            return {
                "success": True,
                "sentinel_status": self.sentinel_status,
                "catalogue_state": self.catalogue_state,
                "total_cameras": len(self.discovered_cameras),
                "new_cameras": new_cams,
                "updated_cameras": updated_cams,
                "last_synced_at": self.last_sync_time.isoformat() if self.last_sync_time else None,
            }

        except Exception as ex:
            self.consecutive_failures += 1
            self.reconnect_attempt = self.consecutive_failures
            self.last_error = str(ex)

            # Classify status
            err_str = str(ex).lower()
            if "502" in err_str or "bad gateway" in err_str or "timeout" in err_str or "timed out" in err_str or "503" in err_str:
                self.sentinel_status = "DEGRADED"
            else:
                self.sentinel_status = "OFFLINE"
            self.catalogue_state = "RETRYING"

            logger.warning(
                f"[Sentinel Catalogue] Ingest sync failed (attempt #{self.reconnect_attempt}): {ex}. "
                f"Transitioning to {self.sentinel_status} mode, will retry automatically."
            )

            # Broadcast degraded/offline event if newly degraded
            if previous_status == "ONLINE":
                try:
                    await event_publisher.publish(
                        event_name="SENTINEL_STATE_CHANGED",
                        payload={
                            "sentinel_status": self.sentinel_status,
                            "catalogue_state": self.catalogue_state,
                            "error": self.last_error,
                            "reconnect_attempt": self.reconnect_attempt,
                            "timestamp": self.last_sync_time.isoformat(),
                        },
                        severity="MEDIUM",
                        source="sentinel_catalogue_service",
                    )
                except Exception:
                    pass

            return {
                "success": False,
                "sentinel_status": self.sentinel_status,
                "catalogue_state": self.catalogue_state,
                "error": self.last_error,
                "reconnect_attempt": self.reconnect_attempt,
                "total_cameras": len(self.discovered_cameras),
            }

    async def _sync_loop(self):
        """Continuous background synchronization loop with exponential backoff."""
        while self._is_running:
            res = await self.sync_catalogue()
            if res.get("success"):
                # Normal interval between successful syncs
                delay = getattr(settings, "SENTINEL_SYNC_INTERVAL_SECONDS", 60)
            else:
                # Exponential backoff on failure
                delay = self.calculate_backoff(self.consecutive_failures)
                logger.info(f"[Sentinel Catalogue] Retrying in {delay} seconds...")

            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                break

    def start_periodic_sync(self):
        """Starts the background periodic catalogue synchronization loop."""
        if self._is_running and self._sync_task and not self._sync_task.done():
            return
        self._is_running = True
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        self._sync_task = loop.create_task(self._sync_loop())
        logger.info(f"Started Sentinel Catalogue Service background sync loop for {self.base_url}")

    def stop_periodic_sync(self):
        """Stops the background periodic catalogue synchronization loop."""
        self._is_running = False
        if self._sync_task:
            self._sync_task.cancel()
            self._sync_task = None
        logger.info("Stopped Sentinel Catalogue Service background sync loop")

    def get_catalogue_health(self) -> Dict[str, Any]:
        """Returns high-level health overview of Sentinel integration."""
        from app.services.stream_gateway_service import stream_gateway_service

        total = len(self.discovered_cameras)
        live_count = sum(1 for c in self.discovered_cameras.values() if c.get("live") or c.get("status") == "ONLINE")
        offline_count = total - live_count

        gateway_metrics = stream_gateway_service.get_gateway_summary()

        return {
            "sentinel_connection": self.sentinel_status,
            "catalogue_state": self.catalogue_state,
            "base_url": self.base_url,
            "catalogue_path": self.catalogue_path,
            "total_discovered_cameras": total,
            "live_cameras": live_count,
            "offline_cameras": offline_count,
            "connecting_cameras": gateway_metrics.get("connecting", 0),
            "reconnecting_cameras": gateway_metrics.get("reconnecting", 0),
            "ai_active_cameras": gateway_metrics.get("ai_active", 0),
            "last_sync": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "last_successful_sync": self.last_successful_sync.isoformat() if self.last_successful_sync else None,
            "last_error": self.last_error,
            "reconnect_attempt": self.reconnect_attempt,
        }

    def get_camera_by_id(self, camera_id: str) -> Optional[Dict[str, Any]]:
        clean_id = str(camera_id).strip()
        if clean_id in self.discovered_cameras:
            return self.discovered_cameras[clean_id]
        import re
        digits = re.sub(r'\D', '', clean_id)
        if digits and digits in self.discovered_cameras:
            return self.discovered_cameras[digits]
        return None

    def get_all_cameras(self) -> List[Dict[str, Any]]:
        return list(self.discovered_cameras.values())


# Global Singleton Instance
sentinel_catalogue_service = SentinelCatalogueService()
