"""
PHANTOM AI Vehicle Tracking & Trajectory Telemetry API
Exposes endpoints for vehicle multi-object tracking, tripwire counts, and visualization data.
"""
from typing import Dict, List, Optional
import cv2
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
import numpy as np

from app.ai.tracking.vehicle_tracker import (
    TrackingFrameResult,
    TrafficFlowStats,
    YOLO26VehicleTracker,
)

router = APIRouter(prefix="/ai/tracking", tags=["AI Vehicle Tracking & Trajectory"])

# Global tracker dictionary keyed by camera_id
ACTIVE_VEHICLE_TRACKERS: Dict[str, YOLO26VehicleTracker] = {}


def _get_or_create_tracker(camera_id: str) -> YOLO26VehicleTracker:
    if camera_id not in ACTIVE_VEHICLE_TRACKERS:
        ACTIVE_VEHICLE_TRACKERS[camera_id] = YOLO26VehicleTracker(camera_id=camera_id)
    return ACTIVE_VEHICLE_TRACKERS[camera_id]


@router.post(
    "/vehicle/frame",
    response_model=TrackingFrameResult,
    summary="Process a single frame for persistent vehicle tracking and flow counting",
)
async def process_vehicle_tracking_frame(
    file: UploadFile = File(...),
    camera_id: str = Form("CAM-AMD-ITX-01"),
) -> TrackingFrameResult:
    data = await file.read()
    nparr = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decode image frame.",
        )

    tracker = _get_or_create_tracker(camera_id)
    result = tracker.process_frame(frame)
    return result


@router.get(
    "/vehicle/stats/{camera_id}",
    response_model=TrafficFlowStats,
    summary="Retrieve cumulative traffic flow statistics (entry/exit counts) for a camera",
)
async def get_camera_traffic_stats(camera_id: str) -> TrafficFlowStats:
    tracker = ACTIVE_VEHICLE_TRACKERS.get(camera_id)
    if not tracker:
        return TrafficFlowStats()
    return TrafficFlowStats(
        total_entered=tracker.total_entered,
        total_exited=tracker.total_exited,
        current_active=len(tracker.tracks),
        class_breakdown=tracker.class_breakdown,
    )
