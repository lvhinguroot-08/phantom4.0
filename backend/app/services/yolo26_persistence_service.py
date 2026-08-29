"""
PHANTOM YOLO26 Database Persistence Service
Persists detections, video snapshots, tracking IDs, and plate numbers using existing ORM models.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Sequence, Union
import uuid

# pyrefly: ignore [missing-import]
from sqlalchemy import select
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.anpr.normalize import normalize_plate_text
from app.ai.evidence_store import evidence_store
from app.models.analytics import Detection, Evidence, VehicleObservation
from app.models.camera import Camera

logger = logging.getLogger("phantom.ai.yolo26.persistence")


class YOLO26PersistenceService:
    """
    Directly persists YOLO26 multi-modal detection batches to PostgreSQL.
    """

    async def _resolve_camera_id(
        self, session: AsyncSession, camera_identifier: Union[str, uuid.UUID]
    ) -> uuid.UUID:
        if isinstance(camera_identifier, uuid.UUID):
            return camera_identifier

        cam_str = camera_identifier.strip() if camera_identifier else ""
        if not cam_str:
            return uuid.uuid4()

        try:
            return uuid.UUID(cam_str)
        except (ValueError, TypeError, AttributeError):
            pass

        query = select(Camera.id).where(Camera.camera_code == cam_str)
        res = await session.execute(query)
        row = res.scalar_one_or_none()
        if row:
            return row

        res_first = await session.execute(select(Camera.id).limit(1))
        first_cam = res_first.scalar_one_or_none()
        if first_cam:
            return first_cam

        logger.warning(
            "No camera record found for camera_identifier '%s'; using fallback UUID.",
            camera_identifier,
        )
        return uuid.uuid4()

    async def save_detection(
        self,
        session: AsyncSession,
        *,
        camera_id: Union[str, uuid.UUID],
        object_class: str,
        confidence: float,
        bounding_box: Optional[Dict[str, float]] = None,
        timestamp: Optional[datetime] = None,
        track_id: Optional[Union[int, str]] = None,
        plate_number: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        image_path: Optional[str] = None,
        video_path: Optional[str] = None,
        speed_kmph: Optional[float] = None,
        direction: Optional[str] = None,
        model_name: str = "YOLO26",
        model_version: str = "26.0.0",
    ) -> Detection:
        now_dt = timestamp or datetime.now(timezone.utc)
        resolved_cam_id = await self._resolve_camera_id(session, camera_id)
        detection_id = uuid.uuid4()

        evidence_row = None
        frame_ref = image_path

        if image_bytes:
            obj_key, digest, size_b, provider = evidence_store.put(
                data=image_bytes,
                logical_name=f"yolo26_{detection_id.hex[:8]}.jpg",
                camera_id=str(resolved_cam_id),
                captured_at=now_dt,
                file_format="jpg",
            )
            frame_ref = obj_key

            evidence_row = Evidence(
                id=uuid.uuid4(),
                evidence_code=f"EVD-{now_dt.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
                evidence_type="AI_DETECTION_SNAPSHOT",
                storage_provider=provider,
                bucket_name="phantom-evidence",
                object_key=obj_key,
                file_format="jpg",
                file_size_bytes=size_b,
                file_hash_sha256=digest,
                captured_at=now_dt,
                camera_id=resolved_cam_id,
                detection_id=detection_id,
                created_at=now_dt,
                metadata_={
                    "origin": "YOLO26_DETECTOR",
                    "object_class": object_class,
                    "confidence": confidence,
                    "track_id": track_id,
                },
            )

        raw_plate = plate_number.strip() if plate_number and plate_number.strip() else None
        cleaned_plate = normalize_plate_text(raw_plate) if raw_plate else ""
        norm_plate = cleaned_plate if cleaned_plate else None

        metadata = {
            "origin": "YOLO26_AI_ENGINE",
            "track_id": track_id,
            "video_reference": video_path,
            "speed_kmph": speed_kmph,
            "direction": direction,
            "raw_class": object_class.lower() if object_class else "unknown",
        }

        confidence_val = round(confidence, 4) if confidence is not None else 0.0

        detection_record = Detection(
            id=detection_id,
            camera_id=resolved_cam_id,
            detection_type=(object_class or "UNKNOWN").upper(),
            object_class=(object_class or "UNKNOWN").upper(),
            detected_at=now_dt,
            confidence=confidence_val,
            bounding_box=bounding_box or {},
            detected_plate_number=raw_plate,
            normalized_plate_number=norm_plate,
            frame_reference=frame_ref,
            crop_image_url=frame_ref,
            model_name=model_name,
            model_version=model_version,
            speed_estimate_kmph=speed_kmph,
            direction_heading=direction,
            evidence_id=evidence_row.id if evidence_row else None,
            metadata_=metadata,
            created_at=now_dt,
        )

        session.add(detection_record)
        if evidence_row:
            session.add(evidence_row)

        if norm_plate:
            obs = VehicleObservation(
                id=uuid.uuid4(),
                camera_id=resolved_cam_id,
                detection_id=detection_id,
                evidence_id=evidence_row.id if evidence_row else None,
                observed_at=now_dt,
                raw_plate=raw_plate,
                normalized_plate=norm_plate,
                plate_confidence=confidence_val,
                vehicle_confidence=confidence_val,
                frame_reference=frame_ref,
                metadata_={"track_id": track_id, "video_reference": video_path},
                created_at=now_dt,
            )
            session.add(obs)

        await session.flush()
        logger.info(
            "Persisted YOLO26 Detection [%s] class=%s cam=%s track_id=%s",
            detection_id,
            object_class,
            resolved_cam_id,
            track_id,
        )
        return detection_record

    async def save_detections_batch(
        self,
        session: AsyncSession,
        *,
        camera_id: Union[str, uuid.UUID],
        detections: Sequence[Dict[str, Any]],
        timestamp: Optional[datetime] = None,
        video_path: Optional[str] = None,
        model_name: str = "YOLO26",
        model_version: str = "26.0.0",
    ) -> List[Detection]:
        """
        Persists a batch of detections in a single database flush.
        """
        now_dt = timestamp or datetime.now(timezone.utc)
        resolved_cam_id = await self._resolve_camera_id(session, camera_id)
        persisted_records: List[Detection] = []

        for det in detections:
            obj_class = det.get("object_class", "OBJECT")
            confidence = det.get("confidence", 0.0)
            bbox = det.get("bounding_box", {})
            track_id = det.get("track_id")
            plate_num = det.get("plate_number")
            img_bytes = det.get("image_bytes")
            img_path = det.get("image_path")
            speed = det.get("speed_kmph")
            direction = det.get("direction")

            detection_id = uuid.uuid4()
            evidence_row = None
            frame_ref = img_path

            if img_bytes:
                obj_key, digest, size_b, provider = evidence_store.put(
                    data=img_bytes,
                    logical_name=f"yolo26_{detection_id.hex[:8]}.jpg",
                    camera_id=str(resolved_cam_id),
                    captured_at=now_dt,
                    file_format="jpg",
                )
                frame_ref = obj_key

                evidence_row = Evidence(
                    id=uuid.uuid4(),
                    evidence_code=f"EVD-{now_dt.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
                    evidence_type="AI_DETECTION_SNAPSHOT",
                    storage_provider=provider,
                    bucket_name="phantom-evidence",
                    object_key=obj_key,
                    file_format="jpg",
                    file_size_bytes=size_b,
                    file_hash_sha256=digest,
                    captured_at=now_dt,
                    camera_id=resolved_cam_id,
                    detection_id=detection_id,
                    created_at=now_dt,
                    metadata_={
                        "origin": "YOLO26_DETECTOR",
                        "object_class": obj_class,
                        "confidence": confidence,
                        "track_id": track_id,
                    },
                )

            raw_plate = plate_num.strip() if plate_num and plate_num.strip() else None
            cleaned_plate = normalize_plate_text(raw_plate) if raw_plate else ""
            norm_plate = cleaned_plate if cleaned_plate else None

            confidence_val = round(float(confidence), 4) if confidence is not None else 0.0

            metadata = {
                "origin": "YOLO26_AI_ENGINE",
                "track_id": track_id,
                "video_reference": video_path,
                "speed_kmph": speed,
                "direction": direction,
                "raw_class": obj_class.lower() if obj_class else "unknown",
            }

            detection_record = Detection(
                id=detection_id,
                camera_id=resolved_cam_id,
                detection_type=(obj_class or "UNKNOWN").upper(),
                object_class=(obj_class or "UNKNOWN").upper(),
                detected_at=now_dt,
                confidence=confidence_val,
                bounding_box=bbox or {},
                detected_plate_number=raw_plate,
                normalized_plate_number=norm_plate,
                frame_reference=frame_ref,
                crop_image_url=frame_ref,
                model_name=model_name,
                model_version=model_version,
                speed_estimate_kmph=speed,
                direction_heading=direction,
                evidence_id=evidence_row.id if evidence_row else None,
                metadata_=metadata,
                created_at=now_dt,
            )

            session.add(detection_record)
            if evidence_row:
                session.add(evidence_row)

            if norm_plate:
                obs = VehicleObservation(
                    id=uuid.uuid4(),
                    camera_id=resolved_cam_id,
                    detection_id=detection_id,
                    evidence_id=evidence_row.id if evidence_row else None,
                    observed_at=now_dt,
                    raw_plate=raw_plate,
                    normalized_plate=norm_plate,
                    plate_confidence=confidence_val,
                    vehicle_confidence=confidence_val,
                    frame_reference=frame_ref,
                    metadata_={"track_id": track_id, "video_reference": video_path},
                    created_at=now_dt,
                )
                session.add(obs)

            persisted_records.append(detection_record)

        await session.flush()
        logger.info(
            "Persisted YOLO26 Batch [%d detections] cam=%s",
            len(persisted_records),
            resolved_cam_id,
        )
        return persisted_records

    async def record_ai_lifecycle_event(
        self,
        session: AsyncSession,
        *,
        camera_id: Union[str, uuid.UUID],
        event_type: str,
        object_class: str,
        confidence: float,
        track_id: Optional[Union[int, str]] = None,
        first_seen: Optional[Union[datetime, str]] = None,
        last_seen: Optional[Union[datetime, str]] = None,
        dwell_time: Optional[float] = None,
        bounding_box: Optional[Dict[str, float]] = None,
        snapshot_reference: Optional[str] = None,
        severity: str = "INFO",
        description: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> Any:
        """
        Persists discrete AI lifecycle events without continuous per-frame database thrashing.
        Valid event_type values:
          - TRACK_STARTED
          - TRACK_ENDED
          - PERSON_DETECTED
          - VEHICLE_DETECTED
          - CONFIGURED_ALERT
          - EVIDENCE_SNAPSHOT_CREATED
        """
        from app.models.analytics import Event
        now_dt = timestamp or datetime.now(timezone.utc)
        resolved_cam_id = await self._resolve_camera_id(session, camera_id)

        first_seen_str = first_seen.isoformat() if isinstance(first_seen, datetime) else (first_seen or now_dt.isoformat())
        last_seen_str = last_seen.isoformat() if isinstance(last_seen, datetime) else (last_seen or now_dt.isoformat())

        metadata = {
            "origin": "YOLO26_EVENT_PIPELINE",
            "track_id": track_id,
            "object_class": object_class.upper() if object_class else "OBJECT",
            "confidence": round(float(confidence), 4) if confidence is not None else 0.0,
            "first_seen": first_seen_str,
            "last_seen": last_seen_str,
            "dwell_time": round(float(dwell_time), 1) if dwell_time is not None else 0.0,
            "bounding_box": bounding_box or {},
            "snapshot_reference": snapshot_reference,
        }

        desc = description or f"YOLO26 {event_type}: {object_class.capitalize()} #{track_id or 'N/A'} (Confidence: {int(round((confidence or 0.0)*100))}%)"

        event_record = Event(
            id=uuid.uuid4(),
            event_type=event_type.upper(),
            camera_id=resolved_cam_id,
            occurred_at=now_dt,
            severity=severity.upper(),
            description=desc,
            processed_by_worker="YOLO26-EventPersistenceWorker",
            metadata_=metadata,
            created_at=now_dt,
            is_demo=False,
        )

        session.add(event_record)
        await session.flush()
        logger.info(
            "Recorded AI Lifecycle Event [%s] cam=%s track_id=%s cls=%s",
            event_type,
            resolved_cam_id,
            track_id,
            object_class,
        )
        return event_record

    async def get_camera_ai_events(
        self,
        session: AsyncSession,
        camera_id: Union[str, uuid.UUID],
        limit: int = 50,
        event_type: Optional[str] = None,
    ) -> List[Any]:
        """
        Reads recent AI detection events for a camera.
        """
        from app.models.analytics import Event
        resolved_cam_id = await self._resolve_camera_id(session, camera_id)
        stmt = select(Event).where(Event.camera_id == resolved_cam_id)
        if event_type:
            stmt = stmt.where(Event.event_type == event_type.upper())
        stmt = stmt.order_by(Event.occurred_at.desc()).limit(limit)

        result = await session.execute(stmt)
        return list(result.scalars().all())


yolo26_persistence_service = YOLO26PersistenceService()
