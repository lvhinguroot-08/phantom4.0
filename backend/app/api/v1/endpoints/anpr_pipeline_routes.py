"""
PHANTOM Unified YOLO26 + ANPR API Endpoints
Runs vehicle detection, plate localization, and OCR with RTO jurisdiction parsing.
"""
from typing import Optional
import cv2
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
import numpy as np

from app.ai.anpr.yolo26_anpr_pipeline import (
    ANPRInferenceResult,
    YOLO26ANPRPipeline,
)

router = APIRouter(prefix="/ai/anpr", tags=["AI ANPR & Plate OCR"])

_pipeline_instance = YOLO26ANPRPipeline(camera_id="CAM-ANPR-GLOBAL")


@router.post(
    "/process",
    response_model=ANPRInferenceResult,
    summary="Detect vehicles and extract license plate numbers using OCR in a single pass",
)
async def process_anpr_frame(
    file: UploadFile = File(..., description="High-resolution traffic snapshot"),
    camera_id: str = Form("CAM-ANPR-01", description="Camera or Junction code"),
) -> ANPRInferenceResult:
    data = await file.read()
    nparr = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decode image frame.",
        )

    pipeline = YOLO26ANPRPipeline(camera_id=camera_id)
    result = pipeline.process_frame(frame)
    return result
