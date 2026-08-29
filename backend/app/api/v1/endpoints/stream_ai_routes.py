"""
PHANTOM Continuous Multi-Stream CCTV AI Control API
Endpoints to start, stop, and monitor live RTSP, IP Camera, and USB streams.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.multi_stream_yolo26 import (
    MultiStreamYOLO26Manager,
    StreamConfigRequest,
    StreamStatus,
    stream_manager,
)

router = APIRouter(prefix="/ai/streams", tags=["AI Multi-Stream CCTV Control"])


@router.post(
    "/start",
    response_model=StreamStatus,
    status_code=status.HTTP_200_OK,
    summary="Start continuous YOLO26 inference on an RTSP/IP/USB stream",
)
async def start_camera_stream(config: StreamConfigRequest) -> StreamStatus:
    status_obj = stream_manager.register_and_start(config)
    return status_obj


@router.post(
    "/stop/{camera_id}",
    summary="Stop continuous inference worker for a camera stream",
)
async def stop_camera_stream(camera_id: str):
    success = stream_manager.stop_stream(camera_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active stream found for camera '{camera_id}'",
        )
    return {"success": True, "message": f"Stream worker for camera {camera_id} stopped."}


@router.get(
    "/status/{camera_id}",
    response_model=StreamStatus,
    summary="Get real-time telemetry and statistics for a camera stream",
)
async def get_stream_status(camera_id: str) -> StreamStatus:
    status_obj = stream_manager.get_status(camera_id)
    if not status_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No stream found for camera '{camera_id}'",
        )
    return status_obj


@router.get(
    "/list",
    response_model=List[StreamStatus],
    summary="List all active CCTV AI streams and their current performance metrics",
)
async def list_all_active_streams() -> List[StreamStatus]:
    return stream_manager.list_all_streams()
