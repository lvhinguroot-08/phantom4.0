import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.services.yolo26_persistence_service import YOLO26PersistenceService, yolo26_persistence_service


def create_mock_session():
    mock = AsyncMock()
    # session.add is synchronous in SQLAlchemy AsyncSession
    mock.add = MagicMock()
    return mock


@pytest.mark.asyncio
async def test_resolve_camera_id_with_uuid():
    service = YOLO26PersistenceService()
    cam_id = uuid.uuid4()
    mock_session = create_mock_session()
    
    resolved = await service._resolve_camera_id(mock_session, cam_id)
    assert resolved == cam_id


@pytest.mark.asyncio
async def test_resolve_camera_id_with_str_uuid():
    service = YOLO26PersistenceService()
    cam_id = uuid.uuid4()
    mock_session = create_mock_session()
    
    resolved = await service._resolve_camera_id(mock_session, str(cam_id))
    assert resolved == cam_id


@pytest.mark.asyncio
async def test_save_detection_with_anpr():
    service = YOLO26PersistenceService()
    mock_session = create_mock_session()
    cam_id = uuid.uuid4()

    det = await service.save_detection(
        session=mock_session,
        camera_id=cam_id,
        object_class="CAR",
        confidence=0.92,
        bounding_box={"x1": 10, "y1": 20, "x2": 100, "y2": 150},
        plate_number="GJ 01 AB 1234",
        track_id="trk-42",
        speed_kmph=55.5,
        direction="NORTH",
    )

    assert det.camera_id == cam_id
    assert det.object_class == "CAR"
    assert det.confidence == 0.92
    assert det.detected_plate_number == "GJ 01 AB 1234"
    assert det.normalized_plate_number == "GJ01AB1234"
    assert mock_session.add.call_count >= 2  # Detection + VehicleObservation
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_detections_batch():
    service = YOLO26PersistenceService()
    mock_session = create_mock_session()
    cam_id = uuid.uuid4()

    batch = [
        {
            "object_class": "PERSON",
            "confidence": 0.88,
            "bounding_box": {"x1": 0, "y1": 0, "x2": 50, "y2": 100},
            "track_id": 1,
        },
        {
            "object_class": "TRUCK",
            "confidence": 0.95,
            "bounding_box": {"x1": 100, "y1": 100, "x2": 300, "y2": 300},
            "plate_number": "GJ05CD5678",
            "track_id": 2,
        },
    ]

    records = await service.save_detections_batch(
        session=mock_session,
        camera_id=cam_id,
        detections=batch,
    )

    assert len(records) == 2
    assert records[0].object_class == "PERSON"
    assert records[1].object_class == "TRUCK"
    assert records[1].normalized_plate_number == "GJ05CD5678"
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_ai_lifecycle_event():
    service = YOLO26PersistenceService()
    mock_session = create_mock_session()
    cam_id = uuid.uuid4()
    t0 = datetime(2026, 8, 27, 14, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 8, 27, 14, 0, 15, tzinfo=timezone.utc)

    event = await service.record_ai_lifecycle_event(
        session=mock_session,
        camera_id=cam_id,
        event_type="TRACK_ENDED",
        object_class="PERSON",
        confidence=0.96,
        track_id=12,
        first_seen=t0,
        last_seen=t1,
        dwell_time=15.0,
        bounding_box={"x1": 100, "y1": 50, "x2": 300, "y2": 450},
        severity="INFO",
    )

    assert event.event_type == "TRACK_ENDED"
    assert event.camera_id == cam_id
    assert event.severity == "INFO"
    assert event.metadata_["track_id"] == 12
    assert event.metadata_["object_class"] == "PERSON"
    assert event.metadata_["confidence"] == 0.96
    assert event.metadata_["dwell_time"] == 15.0
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_camera_ai_events():
    service = YOLO26PersistenceService()
    mock_session = create_mock_session()
    cam_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = ["event_1", "event_2"]
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    events = await service.get_camera_ai_events(mock_session, cam_id, limit=10, event_type="PERSON_DETECTED")
    assert len(events) == 2
    mock_session.execute.assert_awaited_once()
