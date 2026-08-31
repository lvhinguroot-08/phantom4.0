"""
PHANTOM Unified AI API Endpoints
Provides direct /api/upload, /api/yolo/detect, /api/anpr/recognize, /api/process,
and /api/results/{id} endpoints matching PHANTOM 2.0 specifications.
"""
import asyncio
import base64
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Dict, List, Optional
import uuid

import cv2
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse, JSONResponse, Response
import numpy as np
from pydantic import BaseModel, Field

from app.ai.anpr.normalize import extract_plate_structure, looks_like_indian_plate, normalize_plate_text
from app.ai.anpr.ocr import build_ocr_processor
from app.ai.yolo26.detector import get_detector
from app.ai.yolo26.utils import normalize_class_name
from app.services.video_ai_service import (
    ANPRTableItem,
    DetectionEvent,
    JobStatus,
    OUTPUT_DIR,
    ProcessingMode,
    VideoAIJobState,
    resolve_vehicle_license_plate,
    video_ai_service,
)

logger = logging.getLogger("phantom.api.unified_ai")

router = APIRouter(tags=["PHANTOM 2.0 Unified AI Intelligence"])

UPLOAD_TEMP_DIR = Path(tempfile.gettempdir()) / "phantom_uploads"
UPLOAD_TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Sample test video storage
SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "sample_assets"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


class UploadResponse(BaseModel):
    success: bool = True
    upload_id: str
    filename: str
    file_type: str
    file_size: int
    file_path: str
    preview_url: Optional[str] = None


class ProcessJobRequest(BaseModel):
    upload_id: Optional[str] = None
    mode: ProcessingMode = ProcessingMode.YOLO_ANPR
    sample_fps: float = 4.0
    confidence_threshold: float = 0.35
    camera_id: str = "CAM_TEST_01"


class ProcessJobResponse(BaseModel):
    success: bool = True
    job_id: str
    mode: ProcessingMode
    status: JobStatus
    message: str
    status_url: str
    stream_url: str


# ------------------------------------------------------------------------------
# 1. Direct Media Upload Endpoint
# ------------------------------------------------------------------------------
@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload image or video file for AI processing",
)
async def upload_media_file(
    file: UploadFile = File(..., description="Image or video media file"),
) -> UploadResponse:
    orig_name = file.filename or "uploaded_media.mp4"
    ext = Path(orig_name).suffix.lower()
    
    valid_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".jpg", ".jpeg", ".png", ".webp"}
    if ext not in valid_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed formats: {', '.join(sorted(valid_exts))}",
        )

    upload_id = str(uuid.uuid4())
    saved_filename = f"{upload_id}{ext}"
    dest_path = UPLOAD_TEMP_DIR / saved_filename

    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        logger.error(f"Upload write failure: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file on server.",
        )

    file_size = os.path.getsize(dest_path)
    file_type = "video" if ext in (".mp4", ".avi", ".mov", ".mkv", ".webm") else "image"

    return UploadResponse(
        success=True,
        upload_id=upload_id,
        filename=orig_name,
        file_type=file_type,
        file_size=file_size,
        file_path=str(dest_path),
        preview_url=f"/api/upload/{upload_id}/preview",
    )


@router.get("/upload/{upload_id}/preview")
async def get_upload_preview(upload_id: str):
    matches = list(UPLOAD_TEMP_DIR.glob(f"{upload_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Uploaded file not found.")
    file_path = matches[0]
    return FileResponse(path=str(file_path))


# ------------------------------------------------------------------------------
# 2. Direct YOLO Inference Endpoint
# ------------------------------------------------------------------------------
@router.post("/yolo/detect", summary="Direct YOLO inference on image or video")
async def direct_yolo_detect(
    file: Optional[UploadFile] = File(None),
    upload_id: Optional[str] = Form(None),
    confidence_threshold: float = Form(0.35),
    camera_id: str = Form("YOLO_DIRECT"),
):
    target_path = None
    if file:
        ext = Path(file.filename or "frame.jpg").suffix.lower()
        temp_path = UPLOAD_TEMP_DIR / f"{uuid.uuid4()}{ext}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        target_path = temp_path
    elif upload_id:
        matches = list(UPLOAD_TEMP_DIR.glob(f"{upload_id}.*"))
        if matches:
            target_path = matches[0]

    if not target_path or not os.path.exists(target_path):
        raise HTTPException(status_code=400, detail="Please provide a valid file upload or upload_id.")

    ext = Path(target_path).suffix.lower()

    if ext in (".mp4", ".avi", ".mov", ".mkv", ".webm"):
        # Launch video job with YOLO mode
        job = video_ai_service.create_job(
            input_file_path=str(target_path),
            mode=ProcessingMode.YOLO,
            sample_fps=4.0,
            conf_threshold=confidence_threshold,
            camera_id=camera_id,
        )
        return {
            "success": True,
            "job_id": job.job_id,
            "mode": "yolo",
            "status": job.status,
            "status_url": f"/api/results/{job.job_id}",
        }
    else:
        # Image inference
        img = cv2.imread(str(target_path))
        if img is None:
            raise HTTPException(status_code=400, detail="Failed to decode image.")

        detector = get_detector()
        dets = detector.detect_frame(img, confidence_threshold=confidence_threshold)
        
        # Annotate
        annotated = img.copy()
        h, w = annotated.shape[:2]
        for d in dets:
            bx = d["bbox"]
            cls_name = d["class_name"].upper()
            conf = d["confidence"]
            cv2.rectangle(annotated, (bx["x1"], bx["y1"]), (bx["x2"], bx["y2"]), (0, 240, 255), 2)
            cv2.putText(annotated, f"{cls_name} {int(conf*100)}%", (bx["x1"], max(15, bx["y1"] - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 240, 255), 1)

        _, jpg_buf = cv2.imencode(".jpg", annotated)
        b64 = base64.b64encode(jpg_buf.tobytes()).decode("utf-8")

        return {
            "success": True,
            "mode": "yolo",
            "total_detections": len(dets),
            "detections": dets,
            "image": f"data:image/jpeg;base64,{b64}",
        }


# ------------------------------------------------------------------------------
# 3. Direct ANPR Recognition Endpoint
# ------------------------------------------------------------------------------
@router.post("/anpr/recognize", summary="Direct ANPR OCR license plate recognition")
async def direct_anpr_recognize(
    file: Optional[UploadFile] = File(None),
    upload_id: Optional[str] = Form(None),
    confidence_threshold: float = Form(0.35),
    camera_id: str = Form("ANPR_DIRECT"),
):
    target_path = None
    if file:
        ext = Path(file.filename or "frame.jpg").suffix.lower()
        temp_path = UPLOAD_TEMP_DIR / f"{uuid.uuid4()}{ext}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        target_path = temp_path
    elif upload_id:
        matches = list(UPLOAD_TEMP_DIR.glob(f"{upload_id}.*"))
        if matches:
            target_path = matches[0]

    if not target_path or not os.path.exists(target_path):
        raise HTTPException(status_code=400, detail="Please provide a valid file upload or upload_id.")

    ext = Path(target_path).suffix.lower()

    if ext in (".mp4", ".avi", ".mov", ".mkv", ".webm"):
        # Launch video job with ANPR mode
        job = video_ai_service.create_job(
            input_file_path=str(target_path),
            mode=ProcessingMode.ANPR,
            sample_fps=4.0,
            conf_threshold=confidence_threshold,
            camera_id=camera_id,
        )
        return {
            "success": True,
            "job_id": job.job_id,
            "mode": "anpr",
            "status": job.status,
            "status_url": f"/api/results/{job.job_id}",
        }
    else:
        # Image inference
        img = cv2.imread(str(target_path))
        if img is None:
            raise HTTPException(status_code=400, detail="Failed to decode image.")

        detector = get_detector()
        ocr_proc = build_ocr_processor()
        raw_dets = detector.detect_frame(img, confidence_threshold=confidence_threshold)
        
        plates_found = []
        annotated = img.copy()

        for idx, d in enumerate(raw_dets):
            cls_name = normalize_class_name(d["class_name"])
            if cls_name in ("CAR", "TRUCK", "BUS", "MOTORCYCLE", "OTHER_VEHICLE"):
                bx = d["bbox"]
                vx1, vy1, vx2, vy2 = bx["x1"], bx["y1"], bx["x2"], bx["y2"]
                plate_text, p_conf, rto_name = resolve_vehicle_license_plate(
                    frame=img,
                    bbox=bx,
                    vehicle_class=cls_name,
                    track_id=idx + 1,
                    camera_id=camera_id,
                    ocr_proc=ocr_proc,
                )
                if plate_text:
                    struct = extract_plate_structure(plate_text)
                    plates_found.append({
                        "plate_number": plate_text,
                        "confidence": round(p_conf, 4),
                        "vehicle": cls_name.capitalize(),
                        "rto_jurisdiction": rto_name or struct.get("rto_jurisdiction"),
                        "is_gujarat": plate_text.startswith("GJ"),
                        "bounding_box": bx,
                    })
                    cv2.rectangle(annotated, (vx1, vy1), (vx2, vy2), (16, 185, 129), 2)
                    cv2.putText(annotated, f"IND {plate_text}", (vx1, max(22, vy1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (239, 68, 68), 2)

        _, jpg_buf = cv2.imencode(".jpg", annotated)
        b64 = base64.b64encode(jpg_buf.tobytes()).decode("utf-8")

        return {
            "success": True,
            "mode": "anpr",
            "total_plates": len(plates_found),
            "plates": plates_found,
            "image": f"data:image/jpeg;base64,{b64}",
        }


# ------------------------------------------------------------------------------
# 4. Unified Start Processing Endpoint
# ------------------------------------------------------------------------------
@router.post(
    "/process",
    response_model=ProcessJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start unified video AI processing (YOLO, ANPR, or YOLO+ANPR)",
)
async def start_video_processing(
    file: Optional[UploadFile] = File(None, description="Direct video upload"),
    upload_id: Optional[str] = Form(None, description="Pre-uploaded video ID or Camera ID"),
    mode: str = Form("yolo_anpr", description="Processing mode: yolo, anpr, yolo_anpr"),
    sample_fps: float = Form(4.0, description="Sampling FPS rate (e.g. 1.0 to 15.0)"),
    confidence_threshold: float = Form(0.35, description="Confidence threshold"),
    camera_id: str = Form("CAM_SURVEILLANCE_01", description="Camera or Junction code"),
) -> ProcessJobResponse:
    target_path = None

    if file:
        ext = Path(file.filename or "traffic_footage.mp4").suffix.lower()
        temp_input_path = str(UPLOAD_TEMP_DIR / f"{uuid.uuid4()}{ext}")
        with open(temp_input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        target_path = temp_input_path
    elif upload_id:
        # Check if upload_id matches a Sentinel camera or preset
        clean_id = upload_id.strip()
        cam_sample = SAMPLE_DIR / f"{clean_id}_sample.mp4"
        cam_real = SAMPLE_DIR / f"{clean_id}_real_cctv.mp4"

        if cam_sample.exists():
            temp_input_path = str(UPLOAD_TEMP_DIR / f"{uuid.uuid4()}_{clean_id}.mp4")
            shutil.copyfile(str(cam_sample), temp_input_path)
            target_path = temp_input_path
        elif cam_real.exists():
            temp_input_path = str(UPLOAD_TEMP_DIR / f"{uuid.uuid4()}_{clean_id}.mp4")
            shutil.copyfile(str(cam_real), temp_input_path)
            target_path = temp_input_path
        elif clean_id.startswith("cam") and len(clean_id) <= 6:
            # Capture 5 seconds live from the requested RTSP camera
            temp_input_path = str(UPLOAD_TEMP_DIR / f"{uuid.uuid4()}_{clean_id}.mp4")
            rtsp_url = f"rtsp://103.250.160.189:8554/stream/{clean_id}"
            try:
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
                cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                if cap.isOpened():
                    fps = 25.0
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920)
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    out = cv2.VideoWriter(temp_input_path, fourcc, fps, (w, h))
                    import time
                    st = time.time()
                    fc = 0
                    while (time.time() - st) < 4.0 and fc < 100:
                        ret, frame = cap.read()
                        if not ret or frame is None:
                            break
                        out.write(frame)
                        fc += 1
                    cap.release()
                    out.release()
                    if fc > 10:
                        target_path = temp_input_path
            except Exception as cap_err:
                logger.warning(f"Failed to capture live clip from {clean_id}: {cap_err}")

        if not target_path:
            if clean_id == "SAMPLE_TRAFFIC" or not target_path:
                sample_path = SAMPLE_DIR / "sample_traffic_cctv.mp4"
                if sample_path.exists():
                    temp_input_path = str(UPLOAD_TEMP_DIR / f"{uuid.uuid4()}_sample.mp4")
                    shutil.copyfile(str(sample_path), temp_input_path)
                    target_path = temp_input_path
                else:
                    matches = list(UPLOAD_TEMP_DIR.glob(f"{upload_id}.*"))
                    if matches:
                        target_path = str(matches[0])

    if not target_path or not os.path.exists(target_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid video file or upload_id is required.",
        )

    try:
        proc_mode = ProcessingMode(mode.lower().strip())
    except ValueError:
        proc_mode = ProcessingMode.YOLO_ANPR

    job = video_ai_service.create_job(
        input_file_path=target_path,
        mode=proc_mode,
        sample_fps=sample_fps,
        conf_threshold=confidence_threshold,
        camera_id=camera_id,
    )

    return ProcessJobResponse(
        success=True,
        job_id=job.job_id,
        mode=proc_mode,
        status=job.status,
        message=f"Video processing initiated with mode [{proc_mode.value}].",
        status_url=f"/api/results/{job.job_id}",
        stream_url=f"/api/results/{job.job_id}/stream",
    )


# ------------------------------------------------------------------------------
# 5. Sentinel Cameras Directory & Live Snapshot
# ------------------------------------------------------------------------------
@router.get("/sample-cameras", summary="List all 30 Sentinel Gujarat CCTV cameras for testing")
async def get_sentinel_cameras():
    """Returns the full 30 Sentinel Gujarat Police cameras for live AI testing."""
    candidates = [
        Path("sentinel_cameras_full.json"),
        Path.cwd() / "sentinel_cameras_full.json",
        Path.cwd().parent / "sentinel_cameras_full.json",
        Path(__file__).resolve().parent.parent.parent.parent.parent / "sentinel_cameras_full.json",
        Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "sentinel_cameras_full.json",
    ]
    cams_list = []
    for c in candidates:
        if c.is_file():
            try:
                with open(c, "r", encoding="utf-8") as f:
                    cams_list = json.load(f)
                    if cams_list:
                        break
            except Exception:
                pass

    # Enrich with RTSP, HLS, sample availability, and inferred district
    enriched = []
    for c in cams_list:
        cid = c["id"]
        cname = c["name"]
        sample_file = SAMPLE_DIR / f"{cid}_sample.mp4"
        enriched.append({
            "id": cid,
            "name": cname,
            "district": "Ahmedabad" if "ahmedabad" in cname.lower() or any(k in cname.lower() for k in ["chiman", "janpath", "ongc", "paldi", "visat", "vidhyalaya", "delight", "suvidha"]) else ("Junagadh" if "junagadh" in cname.lower() or any(k in cname.lower() for k in ["timbavadi", "majewadi", "dolatpara", "char-chowk"]) else ("Gir Somnath" if "somnath" in cname.lower() else ("Rajkot" if "rajkot" in cname.lower() else ("Gandhinagar" if "adalaj" in cname.lower() or "dehgam" in cname.lower() else ("Navsari" if "bilimora" in cname.lower() or "khaparia" in cname.lower() else "Gujarat"))))),
            "rtsp_url": f"rtsp://103.250.160.189:8554/stream/{cid}",
            "hls_url": f"https://cctv.corp8.cloud/{cid}/index.m3u8",
            "webrtc_url": f"http://103.250.160.189:8889/stream/{cid}/whep",
            "has_local_sample": sample_file.exists(),
            "sample_id": cid,
        })
    return {"success": True, "total": len(enriched), "cameras": enriched}


@router.get("/camera/{camera_id}/snapshot", summary="Capture live real-time frame from Sentinel camera and run YOLO+ANPR")
async def get_camera_live_snapshot(
    camera_id: str,
    confidence_threshold: float = Query(0.35),
):
    """Fetches a real-time live frame from the RTSP camera stream and runs instant YOLO + ANPR."""
    clean_id = camera_id.strip().lower()
    rtsp_url = f"rtsp://103.250.160.189:8554/stream/{clean_id}"

    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    
    frame = None
    if cap.isOpened():
        ret, read_frame = cap.read()
        if ret and read_frame is not None:
            frame = read_frame
        cap.release()

    if frame is None:
        # Fallback to local sample clip if live RTSP momentarily unreachable
        sample_path = SAMPLE_DIR / f"{clean_id}_sample.mp4"
        if sample_path.exists():
            cap_sample = cv2.VideoCapture(str(sample_path))
            if cap_sample.isOpened():
                ret, s_frame = cap_sample.read()
                if ret and s_frame is not None:
                    frame = s_frame
                cap_sample.release()

    if frame is None:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to capture live frame from camera {clean_id}. Upstream feed connecting...",
        )

    # Run YOLO & ANPR
    detector = get_detector()
    ocr_proc = build_ocr_processor()
    raw_dets = detector.detect_frame(frame, confidence_threshold=confidence_threshold)

    annotated = frame.copy()
    h, w = annotated.shape[:2]
    plates_found = []

    for idx, d in enumerate(raw_dets):
        bx = d["bbox"]
        cls_name = normalize_class_name(d["class_name"])
        conf = d["confidence"]
        vx1, vy1, vx2, vy2 = bx["x1"], bx["y1"], bx["x2"], bx["y2"]
        
        cv2.rectangle(annotated, (bx["x1"], bx["y1"]), (bx["x2"], bx["y2"]), (0, 240, 255), 2)
        cv2.putText(annotated, f"{cls_name} {int(conf*100)}%", (bx["x1"], max(18, bx["y1"] - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 240, 255), 1)

        if cls_name in ("CAR", "TRUCK", "BUS", "MOTORCYCLE", "OTHER_VEHICLE"):
            plate_text, p_conf, rto_name = resolve_vehicle_license_plate(
                frame=frame,
                bbox=bx,
                vehicle_class=cls_name,
                track_id=idx + 1,
                camera_id=clean_id,
                ocr_proc=ocr_proc,
            )
            if plate_text:
                struct = extract_plate_structure(plate_text)
                plates_found.append({
                    "plate_number": plate_text,
                    "confidence": round(p_conf, 4),
                    "vehicle": cls_name.capitalize(),
                    "rto_jurisdiction": rto_name or struct.get("rto_jurisdiction"),
                    "is_gujarat": plate_text.startswith("GJ"),
                    "bounding_box": bx,
                })
                cv2.rectangle(annotated, (vx1, vy1), (vx2, vy2), (16, 185, 129), 2)
                cv2.putText(annotated, f"IND {plate_text}", (vx1, max(22, vy1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (239, 68, 68), 2)

    _, jpg_buf = cv2.imencode(".jpg", annotated)
    b64 = base64.b64encode(jpg_buf.tobytes()).decode("utf-8")

    return {
        "success": True,
        "camera_id": clean_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_detections": len(raw_dets),
        "total_plates": len(plates_found),
        "detections": raw_dets,
        "plates": plates_found,
        "image": f"data:image/jpeg;base64,{b64}",
    }


# ------------------------------------------------------------------------------
# 5. Query Results & Telemetry
# ------------------------------------------------------------------------------
@router.get(
    "/results/{job_id}",
    response_model=VideoAIJobState,
    summary="Query real-time video AI processing progress and results",
)
async def get_job_results(job_id: str) -> VideoAIJobState:
    job = video_ai_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found.")
    return job


# ------------------------------------------------------------------------------
# 6. Stop / Abort Job Endpoint
# ------------------------------------------------------------------------------
@router.post("/process/{job_id}/stop", summary="Stop ongoing video processing job")
async def stop_processing_job(job_id: str):
    success = video_ai_service.stop_job(job_id)
    if not success:
        job = video_ai_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        return {"success": False, "message": f"Job is currently in state {job.status}"}
    return {"success": True, "message": f"Processing job {job_id} stopped."}


# ------------------------------------------------------------------------------
# 7. Video Stream / Download Endpoint
# ------------------------------------------------------------------------------
@router.get("/results/{job_id}/video", summary="Stream or download processed annotated MP4 video")
async def get_processed_video(job_id: str):
    job = video_ai_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    output_path = OUTPUT_DIR / f"{job_id}_annotated.mp4"
    if not output_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Video output not ready yet. Status is {job.status} ({job.progress_percent}%).",
        )

    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=f"phantom_processed_{job_id[:8]}.mp4",
    )


# ------------------------------------------------------------------------------
# 8. Sample Video Generator / Fetcher Endpoint
# ------------------------------------------------------------------------------
@router.get("/sample-video", summary="Get bundled sample CCTV traffic video for testing")
async def get_sample_traffic_video():
    sample_path = SAMPLE_DIR / "sample_traffic_cctv.mp4"
    if not sample_path.exists():
        # Generate automatically
        from scripts.generate_sample_footage import generate_test_traffic_video
        generate_test_traffic_video(str(sample_path))

    return FileResponse(
        path=str(sample_path),
        media_type="video/mp4",
        filename="sample_traffic_cctv.mp4",
    )


# ------------------------------------------------------------------------------
# 9. Real-Time WebSocket for Live Detection Stream
# ------------------------------------------------------------------------------
@router.websocket("/process/{job_id}/ws")
async def live_video_processing_ws(websocket: WebSocket, job_id: str):
    """
    Websocket streaming real-time live preview frames and newly detected objects/plates
    as the video processes.
    """
    await websocket.accept()
    logger.info(f"Connected live WS for job {job_id}")

    try:
        while True:
            job = video_ai_service.get_job(job_id)
            if not job:
                await websocket.send_json({"error": "Job not found", "status": "FAILED"})
                break

            payload = {
                "job_id": job.job_id,
                "status": job.status.value,
                "progress_percent": job.progress_percent,
                "frames_processed": job.frames_processed,
                "total_frames": job.total_frames,
                "processing_fps": job.processing_fps,
                "elapsed_seconds": job.elapsed_seconds,
                "eta_seconds": job.eta_seconds,
                "total_detections": job.total_detections,
                "total_plates_recognized": job.total_plates_recognized,
                "class_breakdown": job.class_breakdown,
                "latest_frame_b64": job.latest_frame_b64,
                "recent_detections": [d.model_dump() for d in job.recent_detections[-10:]],
                "anpr_results": [a.model_dump() for a in job.anpr_results],
                "download_url": job.download_url,
                "video_url": job.video_url,
            }
            await websocket.send_json(payload)

            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                # Send final state and close cleanly
                await asyncio.sleep(0.5)
                break

            await asyncio.sleep(0.15)  # ~6-7 updates per second for smooth rendering

    except WebSocketDisconnect:
        logger.info(f"Live WS disconnected for job {job_id}")
    except Exception as exc:
        logger.debug(f"Live WS ended for job {job_id}: {exc}")
