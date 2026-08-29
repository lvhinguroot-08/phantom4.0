"""
PHANTOM AI Image Detection Endpoint
Accepts multipart image upload, executes YOLO26 inference, annotates bounding boxes, and returns structured results.
"""
import base64
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

import cv2
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
import numpy as np
from pydantic import BaseModel, Field

from app.ai.yolo26.detector import get_detector

logger = logging.getLogger("phantom.ai.image")

router = APIRouter(prefix="/ai/detect", tags=["AI Image Detection"])


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    width: float
    height: float


class DetectedObject(BaseModel):
    detection_id: str
    object_class: str
    confidence: float
    bounding_box: BoundingBox
    inference_time_ms: float = 0.0
    model_name: str = "YOLO26"
    model_version: str = "26.0.0"


class ImageDetectionResponse(BaseModel):
    objects: List[DetectedObject]
    count: int
    image: str = Field(..., description="Annotated JPEG image encoded in Base64")
    camera_id: str
    latency_ms: float


def _draw_tactical_annotations(frame: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
    annotated = frame.copy()
    h, w = annotated.shape[:2]

    color_palette = {
        "PERSON": (0, 255, 128),
        "CAR": (255, 191, 0),
        "TRUCK": (255, 128, 0),
        "BUS": (0, 165, 255),
        "MOTORCYCLE": (255, 0, 128),
        "BICYCLE": (255, 255, 0),
        "LICENSE_PLATE": (0, 0, 255),
    }

    for det in detections:
        bbox = det.get("bounding_box", {})
        x1, y1 = int(bbox.get("x1", 0)), int(bbox.get("y1", 0))
        x2, y2 = int(bbox.get("x2", 0)), int(bbox.get("y2", 0))
        obj_class = det.get("object_class", "OBJECT")
        conf = det.get("confidence", 0.0)

        color = color_palette.get(obj_class, (0, 255, 255))
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        # Label Banner
        label = f"{obj_class} {conf * 100:.1f}%"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        by1 = max(0, y1 - th - 6)
        cv2.rectangle(annotated, (x1, by1), (x1 + tw + 6, by1 + th + 6), color, -1)
        cv2.putText(annotated, label, (x1 + 3, by1 + th + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

    # Tactical HUD Overlay
    cv2.putText(annotated, f"PHANTOM YOLO26 // DETS: {len(detections)}", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
    return annotated


@router.post(
    "/image",
    response_model=ImageDetectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Run YOLO26 inference on an uploaded image",
)
async def detect_image(
    file: UploadFile = File(..., description="Multipart image file (JPEG/PNG/WEBP)"),
    camera_id: Optional[str] = Form("FORENSIC_UPLOAD", description="Optional Camera ID"),
) -> ImageDetectionResponse:
    data = await file.read()
    nparr = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format. Please upload a valid JPEG, PNG, or WEBP image.",
        )

    cam_id_str = camera_id or "FORENSIC_UPLOAD"
    detector = get_detector()
    now_dt = datetime.now(timezone.utc)

    raw_dets = detector.detect(frame, camera_id=cam_id_str, timestamp=now_dt)
    annotated_frame = _draw_tactical_annotations(frame, raw_dets)

    _, encoded_jpg = cv2.imencode(".jpg", annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    b64_image = base64.b64encode(encoded_jpg.tobytes()).decode("utf-8")

    total_latency = sum(d.get("inference_time_ms", 0.0) for d in raw_dets) or 15.0

    objects_formatted = [
        DetectedObject(
            detection_id=d.get("detection_id", str(uuid.uuid4())),
            object_class=d.get("object_class", "UNKNOWN"),
            confidence=d.get("confidence", 0.0),
            bounding_box=BoundingBox(**d.get("bounding_box", {})),
            inference_time_ms=d.get("inference_time_ms", 0.0),
            model_name=d.get("model_name", "YOLO26"),
            model_version=d.get("model_version", "26.0.0"),
        )
        for d in raw_dets
    ]

    return ImageDetectionResponse(
        objects=objects_formatted,
        count=len(objects_formatted),
        image=f"data:image/jpeg;base64,{b64_image}",
        camera_id=cam_id_str,
        latency_ms=round(total_latency, 2),
    )
