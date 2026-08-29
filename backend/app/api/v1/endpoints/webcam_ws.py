"""
PHANTOM Real-Time Webcam Inference Gateway
Low-latency WebSocket streaming endpoint receiving live video frames and returning YOLO26 detections.
"""
import base64
from datetime import datetime, timezone
import json
import logging
import time
from typing import Any, Dict, List, Optional
import uuid

import cv2
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
import numpy as np

from app.core.logging import logger
from app.services.event_publisher import event_publisher
from app.ai.yolo26.detector import get_detector

router = APIRouter(prefix="/ai/ws", tags=["AI Live Webcam Inference"])


def _decode_websocket_frame(data: Any) -> Optional[np.ndarray]:
    """Decode binary JPEG bytes or Base64 JSON payload into OpenCV BGR frame."""
    try:
        if isinstance(data, bytes):
            nparr = np.frombuffer(data, np.uint8)
            return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        elif isinstance(data, str):
            payload = json.loads(data) if data.startswith("{") else {"image": data}
            b64_str = payload.get("image", "")

            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]

            img_bytes = base64.b64decode(b64_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    except Exception as exc:
        logger.debug(f"Frame decode failure: {exc}")
    return None


@router.websocket("/webcam")
async def live_webcam_inference_websocket(
    websocket: WebSocket,
    camera_id: str = Query("WEBCAM_01", description="Camera or Terminal identifier"),
    broadcast_events: bool = Query(True, description="Broadcast detections to frontend event bus"),
):
    await websocket.accept()
    logger.info(f"Webcam inference WebSocket connected: camera_id={camera_id}")

    detector = get_detector()
    frame_counter = 0

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message and message["bytes"]:
                raw_data = message["bytes"]
            elif "text" in message and message["text"]:
                raw_data = message["text"]
            else:
                continue

            frame_bgr = _decode_websocket_frame(raw_data)
            if frame_bgr is None:
                await websocket.send_json({"error": "Failed to decode image frame.", "frame_id": frame_counter})
                continue

            frame_counter += 1
            now_dt = datetime.now(timezone.utc)
            start_infer = time.perf_counter()

            detections = detector.detect(frame_bgr, camera_id=camera_id, timestamp=now_dt)
            elapsed_ms = round((time.perf_counter() - start_infer) * 1000.0, 2)

            response_payload = {
                "type": "DETECTION_RESULT",
                "camera_id": camera_id,
                "frame_id": frame_counter,
                "timestamp": now_dt.isoformat(),
                "latency_ms": elapsed_ms,
                "count": len(detections),
                "objects": [
                    {
                        "detection_id": d["detection_id"],
                        "class": d["object_class"],
                        "confidence": d["confidence"],
                        "bounding_box": d["bounding_box"],
                    }
                    for d in detections
                ],
            }

            await websocket.send_json(response_payload)

            if broadcast_events and detections:
                unique_classes = list({d["object_class"] for d in detections})
                severity = "HIGH" if "PERSON" in unique_classes or "LICENSE_PLATE" in unique_classes else "LOW"

                await event_publisher.publish(
                    event_name="DETECTION",
                    payload={
                        "title": f"Live Detection: {', '.join(unique_classes)}",
                        "camera_id": camera_id,
                        "count": len(detections),
                        "classes": unique_classes,
                        "detections": detections,
                        "severity": severity,
                    },
                    camera_id=camera_id,
                    severity=severity,
                    source="webcam-live-ai",
                )

    except WebSocketDisconnect:
        logger.info(f"Webcam WebSocket disconnected gracefully: camera_id={camera_id}")
    except Exception as exc:
        logger.error(f"Webcam WebSocket error: {exc}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
