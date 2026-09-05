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
import re
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

def find_sample_asset(filename: str) -> Optional[Path]:
    """Resolves sample video asset across multiple possible working directory paths."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent.parent / "sample_assets" / filename,
        Path(__file__).resolve().parent.parent.parent.parent.parent / "backend" / "sample_assets" / filename,
        Path.cwd() / "sample_assets" / filename,
        Path.cwd() / "backend" / "sample_assets" / filename,
        Path(__file__).resolve().parent.parent.parent / "sample_assets" / filename,
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "backend" / "sample_assets"
if not SAMPLE_DIR.exists():
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
    from app.core.security import validate_media_file_magic_bytes

    orig_name = file.filename or "uploaded_media.mp4"
    ext = Path(orig_name).suffix.lower()
    
    valid_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".jpg", ".jpeg", ".png", ".webp"}
    if ext not in valid_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security Alert: Unsupported file extension '{ext}'. Allowed formats: {', '.join(sorted(valid_exts))}",
        )

    # 1. Binary Magic Bytes Security Validation
    try:
        header_bytes = await file.read(64)
        await file.seek(0)
        is_valid_magic = validate_media_file_magic_bytes(header_bytes, orig_name)
        if not is_valid_magic:
            logger.warning(f"File upload blocked - Invalid magic header bytes for {orig_name}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security Validation Failed: File header signature does not match declared media format. Potential unauthorized binary payload blocked.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Magic byte check error: {exc}")

    upload_id = str(uuid.uuid4())
    saved_filename = f"{upload_id}{ext}"
    dest_path = UPLOAD_TEMP_DIR / saved_filename

    # 2. Write with size limit enforcement (Max 500 MB)
    MAX_FILE_BYTES = 500 * 1024 * 1024
    total_written = 0
    try:
        with open(dest_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total_written += len(chunk)
                if total_written > MAX_FILE_BYTES:
                    buffer.close()
                    if dest_path.is_file():
                        os.remove(dest_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File exceeds maximum allowed size of 500MB.",
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
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
                plate_text, p_conf, rto_name, _ = resolve_vehicle_license_plate(
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
# 4. Live Stream 10-15s Direct Capture & Unified Start Processing Endpoint
# ------------------------------------------------------------------------------
async def capture_live_stream_clip(camera_id: str, num_segments: int = 2) -> Optional[str]:
    """
    Directly captures 10-15 seconds of real live CCTV footage from the Sentinel camera stream.
    Fetches real encrypted MPEG-TS segments, decrypts them via AES-128 key,
    and combines them into a seamless playable .ts video clip ready for instant YOLO+ANPR inference.
    """
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        from app.services.stream_gateway_service import stream_gateway_service

        raw_id = str(camera_id).strip().lower()
        m = re.search(r"(cam\d+)", raw_id)
        if m:
            clean_id = m.group(1)
        elif raw_id.isdigit():
            clean_id = f"cam{int(raw_id):02d}"
        else:
            clean_id = "cam01"

        manifest_text, _ = await stream_gateway_service.get_hls_manifest(clean_id)
        key_bytes, _ = await stream_gateway_service.get_hls_key(clean_id)

        if not manifest_text or not key_bytes or len(key_bytes) != 16:
            logger.warning(f"Failed to fetch valid manifest/AES key for live capture of {clean_id}")
            return None

        lines = manifest_text.splitlines()
        segs = [l.strip().split('/')[-1] for l in lines if l.strip().endswith('.ts')]
        if not segs:
            return None

        chosen = segs[:num_segments] if len(segs) >= num_segments else segs[:1]

        combined_ts = bytearray()
        iv = b'\x00' * 16
        for sname in chosen:
            raw_seg, _ = await stream_gateway_service.get_hls_segment(clean_id, sname)
            if raw_seg and len(raw_seg) > 0:
                cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
                dec = cipher.decryptor()
                plain = dec.update(raw_seg) + dec.finalize()
                combined_ts.extend(plain)

        if len(combined_ts) > 10000:
            out_clip = UPLOAD_TEMP_DIR / f"{uuid.uuid4()}_{clean_id}_live_15s.ts"
            out_clip.write_bytes(combined_ts)
            cap = cv2.VideoCapture(str(out_clip))
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                if ret:
                    logger.info(f"Captured {len(chosen)} segments (~12-15s) of live {clean_id} footage: {out_clip}")
                    return str(out_clip)
    except Exception as ex:
        logger.warning(f"Error capturing live stream clip for {camera_id}: {ex}")

    return None


@router.post(
    "/process",
    response_model=ProcessJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start unified video AI processing (YOLO, ANPR, or YOLO+ANPR)",
)
async def start_video_processing(
    file: Optional[UploadFile] = File(None, description="Direct video or image upload"),
    upload_id: Optional[str] = Form(None, description="Pre-uploaded video ID or Camera ID"),
    mode: str = Form("yolo_anpr", description="Processing mode: yolo, anpr, yolo_anpr"),
    sample_fps: float = Form(4.0, description="Sampling FPS rate (e.g. 1.0 to 15.0)"),
    confidence_threshold: float = Form(0.35, description="Confidence threshold"),
    camera_id: str = Form("CAM_SURVEILLANCE_01", description="Camera or Junction code"),
) -> ProcessJobResponse:
    target_path = None

    if file and getattr(file, "filename", None):
        ext = Path(file.filename).suffix.lower()
        temp_input_path = str(UPLOAD_TEMP_DIR / f"{uuid.uuid4()}{ext}")
        with open(temp_input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # If user uploaded an image (JPG/PNG/WEBP), convert it to a 3-second 10-FPS MP4 clip
        if ext in (".jpg", ".jpeg", ".png", ".webp"):
            img = cv2.imread(temp_input_path)
            if img is not None:
                h, w = img.shape[:2]
                vid_path = str(UPLOAD_TEMP_DIR / f"{uuid.uuid4()}_imgvid.mp4")
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out_vid = cv2.VideoWriter(vid_path, fourcc, 10.0, (w, h))
                for _ in range(30):
                    out_vid.write(img)
                out_vid.release()
                target_path = vid_path
            else:
                target_path = temp_input_path
        else:
            target_path = temp_input_path

    elif upload_id:
        clean_id = upload_id.strip().lower().replace(".mp4", "")

        # 1. Primary: Direct 10-15s live video capture from the actual camera stream
        if any(keyword in clean_id for keyword in ("cam", "junction", "stream", "sentinel", "cctv")):
            live_clip = await capture_live_stream_clip(clean_id, num_segments=2)
            if live_clip:
                target_path = live_clip

        # 2. Check local sample assets or camera asset if live capture was not needed or unavailable
        if not target_path:
            cam_sample = (
                find_sample_asset(f"{clean_id}_sample.mp4")
                or find_sample_asset(f"{clean_id}.mp4")
                or find_sample_asset(f"{clean_id}")
            )
            if cam_sample and cam_sample.exists():
                temp_input_path = str(UPLOAD_TEMP_DIR / f"{uuid.uuid4()}_{clean_id}.mp4")
                shutil.copyfile(str(cam_sample), temp_input_path)
                target_path = temp_input_path

        # 3. Check previously uploaded file matches
        if not target_path:
            matches = list(UPLOAD_TEMP_DIR.glob(f"{upload_id}.*"))
            if matches:
                target_path = str(matches[0])

    # Final fallback if neither file nor upload_id found
    if not target_path or not os.path.exists(target_path):
        # Attempt live capture for default cam01
        live_clip = await capture_live_stream_clip("cam01", num_segments=2)
        if live_clip:
            target_path = live_clip
        else:
            sample_asset = find_sample_asset("sample_traffic_cctv.mp4") or find_sample_asset("cam01_sample.mp4")
            if sample_asset and sample_asset.exists():
                temp_input_path = str(UPLOAD_TEMP_DIR / f"{uuid.uuid4()}_default.mp4")
                shutil.copyfile(str(sample_asset), temp_input_path)
                target_path = temp_input_path
            else:
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
@router.get("/sample-cameras", summary="List all 30 Sentinel Gujarat CCTV cameras with full GIS metadata")
async def get_sentinel_cameras():
    """Returns the full 30 Sentinel Gujarat Police cameras with real GIS metadata."""
    from app.core.cctv_gis_data import get_all_cctv_gis_nodes
    gis_nodes = get_all_cctv_gis_nodes()
    enriched = []
    for c in gis_nodes:
        cid = c["id"]
        sample_file = find_sample_asset(f"{cid}_sample.mp4")
        enriched.append({
            **c,
            "rtsp_url": f"rtsp://103.250.160.189:8554/stream/{cid}",
            "hls_url": f"https://cctv.corp8.cloud/{cid}/index.m3u8",
            "webrtc_url": f"http://103.250.160.189:8889/stream/{cid}/whep",
            "has_local_sample": sample_file is not None and sample_file.exists(),
            "sample_id": cid,
        })
    return {"success": True, "total": len(enriched), "cameras": enriched}


@router.get("/camera/{camera_id}/snapshot", summary="Capture live real-time frame from Sentinel camera and run YOLO+ANPR")
async def get_camera_live_snapshot(
    camera_id: str,
    confidence_threshold: float = Query(0.35),
):
    """Fetches a real-time live frame from the RTSP/HLS camera stream and runs instant YOLO + ANPR."""
    clean_id = camera_id.strip().lower()
    m = re.search(r"(cam\d+)", clean_id)
    norm_cam = m.group(1) if m else clean_id
    
    frame = None

    # 1. Primary: capture directly from live Sentinel HLS stream
    try:
        live_clip = await capture_live_stream_clip(norm_cam, num_segments=1)
        if live_clip:
            cap_live = cv2.VideoCapture(live_clip)
            if cap_live.isOpened():
                ret, l_frame = cap_live.read()
                if ret and l_frame is not None:
                    frame = l_frame
                cap_live.release()
    except Exception as ex:
        logger.debug(f"Direct live HLS snapshot notice: {ex}")

    # 2. Secondary: RTSP capture fallback
    if frame is None:
        rtsp_url = f"rtsp://103.250.160.189:8554/stream/{clean_id}"
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        try:
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            if cap.isOpened():
                ret, read_frame = cap.read()
                if ret and read_frame is not None:
                    frame = read_frame
                cap.release()
        except Exception:
            pass

    if frame is None:
        # Fallback to local sample clip if live stream momentarily unreachable
        sample_path = find_sample_asset(f"{clean_id}_sample.mp4") or find_sample_asset("sample_traffic_cctv.mp4") or find_sample_asset("cam01_sample.mp4")
        if sample_path and sample_path.exists():
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
            plate_text, p_conf, rto_name, _ = resolve_vehicle_license_plate(
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
    sample_file = find_sample_asset("sample_traffic_cctv.mp4") or find_sample_asset("cam01_sample.mp4")
    if sample_file and sample_file.exists():
        return FileResponse(
            path=str(sample_file),
            media_type="video/mp4",
            filename="sample_traffic_cctv.mp4",
        )
    
    sample_path = SAMPLE_DIR / "sample_traffic_cctv.mp4"
    if not sample_path.exists():
        # Generate automatically
        try:
            from scripts.generate_sample_footage import generate_test_traffic_video
            generate_test_traffic_video(str(sample_path))
        except Exception:
            pass

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
