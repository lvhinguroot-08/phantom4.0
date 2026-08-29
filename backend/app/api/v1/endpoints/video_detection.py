"""
PHANTOM AI Video Detection Service
Asynchronous frame-by-frame YOLO26 inference and annotated video rendering.
"""
import asyncio
from datetime import datetime, timezone
from enum import Enum
import logging
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any, Dict, List, Optional
import uuid

import cv2
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
import numpy as np
from pydantic import BaseModel, Field

from app.core.config import settings
from app.ai.yolo26.detector import get_detector

logger = logging.getLogger("phantom.ai.video")

router = APIRouter(prefix="/ai/detect", tags=["AI Video Detection"])


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class VideoJobState(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    progress_percent: float = 0.0
    frames_processed: int = 0
    total_frames: int = 0
    fps: float = 0.0
    elapsed_seconds: float = 0.0
    eta_seconds: Optional[float] = None
    total_detections: int = 0
    class_breakdown: Dict[str, int] = Field(default_factory=dict)
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None


class VideoJobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str
    status_url: str


VIDEO_JOBS: Dict[str, VideoJobState] = {}
OUTPUT_VIDEO_DIR = Path(tempfile.gettempdir()) / "phantom_evidence_videos"
OUTPUT_VIDEO_DIR.mkdir(parents=True, exist_ok=True)


def _annotate_frame(frame: np.ndarray, detections: List[Dict[str, Any]], frame_idx: int, total_frames: int) -> np.ndarray:
    annotated = frame.copy()
    h, w = annotated.shape[:2]

    color_map = {
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

        color = color_map.get(obj_class, (0, 255, 255))
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        label = f"{obj_class} {conf * 100:.1f}%"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        by1 = max(0, y1 - th - 6)
        cv2.rectangle(annotated, (x1, by1), (x1 + tw + 6, by1 + th + 6), color, -1)
        cv2.putText(annotated, label, (x1 + 3, by1 + th + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

    hud_text = f"YOLO26 // F:{frame_idx}/{total_frames} // DETS:{len(detections)}"
    cv2.putText(annotated, hud_text, (max(10, w - 320), 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)
    return annotated


def process_video_background(job_id: str, input_path: str, output_path: str, camera_id: str) -> None:
    job = VIDEO_JOBS.get(job_id)
    if not job:
        return

    job.status = JobStatus.PROCESSING
    detector = get_detector()
    cap = cv2.VideoCapture(input_path)

    if not cap.isOpened():
        job.status = JobStatus.FAILED
        job.error_message = "Failed to open video file stream."
        return

    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        job.total_frames = total_frames
        job.fps = round(fps, 2)

        fourcc = getattr(cv2, "VideoWriter_fourcc", cv2.VideoWriter.fourcc)(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        start_time = time.perf_counter()
        frame_idx = 0
        total_dets = 0
        class_counts: Dict[str, int] = {}

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            now = datetime.now(timezone.utc)

            detections = detector.detect(frame, camera_id=camera_id, timestamp=now)
            total_dets += len(detections)

            for d in detections:
                cls_name = d.get("object_class", "OBJECT")
                class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

            annotated_frame = _annotate_frame(frame, detections, frame_idx, total_frames)
            out.write(annotated_frame)

            if frame_idx % 5 == 0 or frame_idx == total_frames:
                elapsed = time.perf_counter() - start_time
                progress = round((frame_idx / total_frames) * 100.0, 2)
                rate = frame_idx / elapsed if elapsed > 0 else 1.0
                eta = round((total_frames - frame_idx) / rate, 1) if rate > 0 else 0.0

                job.frames_processed = frame_idx
                job.progress_percent = min(100.0, progress)
                job.elapsed_seconds = round(elapsed, 1)
                job.eta_seconds = eta
                job.total_detections = total_dets
                job.class_breakdown = class_counts

        cap.release()
        out.release()

        job.status = JobStatus.COMPLETED
        job.progress_percent = 100.0
        job.eta_seconds = 0.0
        job.completed_at = datetime.now(timezone.utc).isoformat()
        job.download_url = f"/api/ai/detect/video/{job_id}/download"
        logger.info(f"Video job {job_id} completed. Total frames: {frame_idx}, Detections: {total_dets}")

    except Exception as exc:
        logger.error(f"Error processing video job {job_id}: {exc}")
        job.status = JobStatus.FAILED
        job.error_message = "Internal video processing failure."
    finally:
        cap.release()
        if os.path.exists(input_path):
            try:
                os.remove(input_path)
            except OSError:
                pass


@router.post(
    "/video",
    response_model=VideoJobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit video for asynchronous YOLO26 detection",
)
async def submit_video_detection(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(..., description="Video file (MP4, AVI, MOV, MKV)"),
    camera_id: Optional[str] = Form(None, description="Optional camera identifier"),
) -> VideoJobCreateResponse:
    ext = Path(file.filename or "video.mp4").suffix.lower()
    if ext not in (".mp4", ".avi", ".mov", ".mkv", ".webm"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported video format. Allowed formats: .mp4, .avi, .mov, .mkv, .webm",
        )

    job_id = str(uuid.uuid4())
    temp_input_dir = Path(tempfile.gettempdir()) / "phantom_video_in"
    temp_input_dir.mkdir(parents=True, exist_ok=True)
    temp_input_path = str(temp_input_dir / f"{job_id}_raw{ext}")
    output_video_path = str(OUTPUT_VIDEO_DIR / f"{job_id}_annotated.mp4")

    try:
        with open(temp_input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded video file.",
        )

    cam_id_str = camera_id or "VIDEO_UPLOAD"
    job_state = VideoJobState(job_id=job_id, status=JobStatus.QUEUED)
    VIDEO_JOBS[job_id] = job_state

    background_tasks.add_task(
        process_video_background,
        job_id=job_id,
        input_path=temp_input_path,
        output_path=output_video_path,
        camera_id=cam_id_str,
    )

    return VideoJobCreateResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        message="Video submitted successfully. Processing has started.",
        status_url=f"/api/ai/detect/video/{job_id}",
    )


@router.get(
    "/video/{job_id}",
    response_model=VideoJobState,
    summary="Query video processing progress and results",
)
async def get_video_job_status(job_id: str) -> VideoJobState:
    job = VIDEO_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found.")
    return job


@router.get(
    "/video/{job_id}/download",
    summary="Download final annotated video",
)
async def download_annotated_video(job_id: str) -> FileResponse:
    job = VIDEO_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found.")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video processing is {job.status}. Download only available when COMPLETED.",
        )

    output_path = OUTPUT_VIDEO_DIR / f"{job_id}_annotated.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotated video file not found.")

    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=f"phantom_annotated_{job_id[:8]}.mp4",
    )
