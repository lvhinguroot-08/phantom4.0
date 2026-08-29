"""
PHANTOM AI Alert System for YOLO26
Evaluates detections, persists alerts in PostgreSQL, and pushes real-time WebSocket events.
"""
from datetime import datetime, timezone
import threading
from typing import Any, Dict, Optional, Tuple, Union
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.alert import Alert
from app.models.camera import Camera
from app.repositories.alert import AlertRepository
from app.schemas.events import EventType
from app.services.event_publisher import event_publisher


class YOLO26AlertService:
    """
    Evaluates YOLO26 & ANPR outputs, stores alerts in DB, and broadcasts live events.
    Features TTL-bounded deduplication cache and safe async ORM access.
    """

    def __init__(self, deduplication_cooldown_seconds: int = 60, max_cache_size: int = 10000):
        self.alert_repo = AlertRepository()
        self.cooldown_seconds = deduplication_cooldown_seconds
        self.max_cache_size = max_cache_size
        self._cooldown_cache: Dict[Tuple[str, str], float] = {}
        self._lock = threading.Lock()

    def _determine_alert_type_and_severity(
        self, object_class: str, confidence: float, is_watchlist_match: bool = False
    ) -> Tuple[str, str, str]:
        if is_watchlist_match:
            return "WATCHLIST_PLATE_MATCH", "CRITICAL", "🚨 CRITICAL WATCHLIST HIT: Wanted Vehicle Match"

        cls = (object_class or "UNKNOWN").upper().strip()
        if cls == "PERSON":
            sev = "HIGH" if confidence > 0.85 else "MEDIUM"
            return "PERSON_DETECTED", sev, "👤 Pedestrian / Person Sighting Detected"

        elif cls == "CAR":
            return "CAR_DETECTED", "LOW", "🚗 Motor Vehicle (Car) Observed"

        elif cls in ("MOTORCYCLE", "BICYCLE", "TWO_WHEELER", "BIKE"):
            return "TWO_WHEELER_DETECTED", "LOW", "🏍️ Two-Wheeler / Motorcycle Observed"

        elif cls == "TRUCK":
            return "HEAVY_VEHICLE_TRUCK", "MEDIUM", "🚛 Heavy Transport Truck Detected"

        elif cls == "BUS":
            return "PUBLIC_TRANSPORT_BUS", "MEDIUM", "🚌 Public Transport Bus Sighting"

        elif cls in ("LICENSE_PLATE", "PLATE"):
            return "NUMBER_PLATE_OBSERVED", "INFO", "🔢 Vehicle License Plate Scanned"

        else:
            return "UNKNOWN_ANOMALOUS_OBJECT", "HIGH", "⚠️ Unclassified Object / Anomaly Detected"

    def _is_rate_limited(self, camera_id: Union[str, uuid.UUID], alert_key: str) -> bool:
        """
        Thread-safe cooldown checker with automatic TTL eviction to prevent memory leaks.
        """
        now_epoch = datetime.now(timezone.utc).timestamp()
        key = (str(camera_id), alert_key)

        with self._lock:
            # Periodic cleanup if cache grows large
            if len(self._cooldown_cache) > self.max_cache_size:
                cutoff = now_epoch - (self.cooldown_seconds * 2)
                self._cooldown_cache = {k: v for k, v in self._cooldown_cache.items() if v > cutoff}

            last_time = self._cooldown_cache.get(key, 0.0)
            if (now_epoch - last_time) < self.cooldown_seconds:
                return True

            self._cooldown_cache[key] = now_epoch
            return False

    async def process_detection(
        self,
        session: AsyncSession,
        *,
        camera: Camera,
        detection_data: Dict[str, Any],
        plate_number: Optional[str] = None,
        is_watchlist_match: bool = False,
        watchlist_details: Optional[Dict[str, Any]] = None,
    ) -> Optional[Alert]:
        obj_class = str(detection_data.get("object_class", "UNKNOWN"))
        confidence = float(detection_data.get("confidence", 0.0))
        bbox = detection_data.get("bounding_box", {})
        track_id = detection_data.get("track_id")

        alert_type, severity, title_prefix = self._determine_alert_type_and_severity(
            obj_class, confidence, is_watchlist_match=is_watchlist_match
        )

        # Granular alert key prevents dropping separate vehicles / tracks
        if plate_number:
            alert_key = f"PLATE:{plate_number.strip().upper()}"
        elif track_id is not None:
            alert_key = f"TRACK:{obj_class}:{track_id}"
        elif is_watchlist_match:
            alert_key = f"WATCHLIST:{uuid.uuid4().hex[:8]}"
        else:
            # For untracked generic objects, use class with short temporal window
            alert_key = f"OBJ:{obj_class}"

        if self._is_rate_limited(camera.id, alert_key):
            logger.debug(f"Suppressed duplicate alert for key '{alert_key}' on camera {camera.id}")
            return None

        now_dt = datetime.now(timezone.utc)
        alert_code = f"ALT-{now_dt.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        cam_name = getattr(camera, "name", None) or getattr(camera, "camera_code", None) or "SURVEILLANCE-CAM"
        
        # Safely obtain district without triggering un-awaited async lazy loading
        district_name = "Gujarat"
        if hasattr(camera, "__dict__") and "location" in camera.__dict__ and camera.__dict__["location"]:
            loc = camera.__dict__["location"]
            district_name = getattr(loc, "district", "Gujarat") or "Gujarat"
        elif hasattr(camera, "metadata_") and isinstance(camera.metadata_, dict):
            district_name = camera.metadata_.get("district", "Gujarat")

        if is_watchlist_match:
            title = f"CRITICAL WATCHLIST HIT: {plate_number}"
            message = (
                f"Vehicle with plate [{plate_number}] matched against active hotlist at {cam_name} "
                f"({district_name}) with {confidence*100:.1f}% confidence."
            )
        else:
            title = f"{title_prefix} [{cam_name}]"
            message = (
                f"{obj_class} detected at {cam_name} ({district_name}) "
                f"with {confidence*100:.1f}% confidence score."
            )

        metadata = {
            "origin": "YOLO26_AI_ENGINE",
            "camera_id": str(camera.id),
            "camera_code": getattr(camera, "camera_code", None),
            "district": district_name,
            "object_class": obj_class,
            "confidence": confidence,
            "bounding_box": bbox,
            "track_id": track_id,
            "plate_number": plate_number,
            "is_watchlist_match": is_watchlist_match,
            "watchlist_info": watchlist_details,
            "detected_at": now_dt.isoformat(),
        }

        # Ensure camera_id is proper UUID
        resolved_cam_uuid = camera.id if isinstance(camera.id, uuid.UUID) else uuid.UUID(str(camera.id))

        alert_record = Alert(
            id=uuid.uuid4(),
            alert_code=alert_code,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            status="NEW",
            camera_id=resolved_cam_uuid,
            metadata_=metadata,
            created_at=now_dt,
            updated_at=now_dt,
        )

        session.add(alert_record)
        await session.flush()

        logger.info(f"Generated AI Alert [{alert_code}] {alert_type} ({severity}) on camera {resolved_cam_uuid}")

        # Broadcast via standard EventType + custom event name for maximum compatibility
        event_type_enum = EventType.WATCHLIST_MATCH if is_watchlist_match else EventType.ALERT_CREATED
        event_payload = {
            "alert_id": str(alert_record.id),
            "alert_code": alert_code,
            "event_id": str(uuid.uuid4()),
            "title": title,
            "message": message,
            "severity": severity,
            "alert_type": alert_type,
            "camera_id": str(resolved_cam_uuid),
            "camera_name": cam_name,
            "district": district_name,
            "object_class": obj_class,
            "confidence": confidence,
            "plate_number": plate_number,
            "track_id": track_id,
            "bounding_box": bbox,
            "timestamp": now_dt.isoformat(),
            "created_at": now_dt.isoformat(),
        }

        try:
            # Publish standard domain event
            await event_publisher.publish(
                event_name=event_type_enum,
                payload=event_payload,
                camera_id=str(resolved_cam_uuid),
                district=district_name,
                severity=severity,
                source="yolo26-alert-engine",
            )
            # Also publish specifically for listeners subscribed to specific alert type strings
            if alert_type != event_type_enum.value:
                await event_publisher.publish(
                    event_name=alert_type,
                    payload=event_payload,
                    camera_id=str(resolved_cam_uuid),
                    district=district_name,
                    severity=severity,
                    source="yolo26-alert-engine",
                )
        except Exception as pub_err:
            logger.warning(f"Non-fatal event publishing failure for alert {alert_code}: {pub_err}")

        return alert_record
