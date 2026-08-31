"""
PHANTOM Unified Video & Stream AI Intelligence Engine
Performs asynchronous frame-by-frame YOLO, ANPR, and combined YOLO+ANPR processing
with real-time live preview buffer, tactical HUD annotations, and Gujarati RTO OCR.
"""
import asyncio
import base64
from datetime import datetime, timezone
from enum import Enum
import logging
import math
import os
from pathlib import Path
import shutil
import tempfile
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import uuid

import cv2
import numpy as np
from pydantic import BaseModel, Field

from app.ai.anpr.normalize import extract_plate_structure, looks_like_indian_plate, normalize_plate_text
from app.ai.anpr.ocr import build_ocr_processor
from app.ai.yolo26.detector import get_detector
from app.ai.yolo26.tracker import YOLO26Tracker
from app.ai.yolo26.utils import normalize_class_name

logger = logging.getLogger("phantom.services.video_ai")


class ProcessingMode(str, Enum):
    YOLO = "yolo"
    ANPR = "anpr"
    YOLO_ANPR = "yolo_anpr"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class DetectionEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    frame_idx: int = 0
    timestamp_sec: float = 0.0
    time_str: str = "00:00"
    object_class: str = "OBJECT"
    display_name: str = "Object"
    confidence: float = 0.0
    bounding_box: Dict[str, float] = Field(default_factory=dict)
    is_vehicle: bool = False
    vehicle_type: Optional[str] = None
    license_plate: Optional[str] = None
    plate_confidence: Optional[float] = None
    rto_jurisdiction: Optional[str] = None
    track_id: Optional[int] = None


class ANPRTableItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    plate_number: str
    confidence: float
    time_str: str
    timestamp_sec: float
    vehicle: str
    rto_jurisdiction: Optional[str] = None
    is_gujarat: bool = False
    first_seen_frame: int = 0
    last_seen_frame: int = 0
    total_sightings: int = 1


class ObjectAnalytics(BaseModel):
    total_objects_tracked: int = 0
    unique_vehicles_count: int = 0
    cars_count: int = 0
    buses_count: int = 0
    trucks_count: int = 0
    motorcycles_count: int = 0
    pedestrians_count: int = 0
    bicycles_count: int = 0
    peak_frame_density: int = 0
    avg_confidence_pct: float = 0.0
    congestion_level: str = "LOW"  # LOW, MODERATE, HIGH
    vehicle_distribution: Dict[str, float] = Field(default_factory=dict)


class VideoAIJobState(BaseModel):
    job_id: str
    mode: ProcessingMode = ProcessingMode.YOLO_ANPR
    status: JobStatus = JobStatus.QUEUED
    progress_percent: float = 0.0
    frames_processed: int = 0
    total_frames: int = 0
    fps: float = 0.0
    processing_fps: float = 0.0
    elapsed_seconds: float = 0.0
    eta_seconds: Optional[float] = None
    total_detections: int = 0
    total_plates_recognized: int = 0
    class_breakdown: Dict[str, int] = Field(default_factory=dict)
    recent_detections: List[DetectionEvent] = Field(default_factory=list)
    anpr_results: List[ANPRTableItem] = Field(default_factory=list)
    analytics: ObjectAnalytics = Field(default_factory=ObjectAnalytics)
    latest_frame_b64: Optional[str] = None
    download_url: Optional[str] = None
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    is_cancelled: bool = False


# Global In-Memory Job Storage
VIDEO_AI_JOBS: Dict[str, VideoAIJobState] = {}
OUTPUT_DIR = Path(tempfile.gettempdir()) / "phantom_ai_processed_videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def format_seconds_to_time(seconds: float) -> str:
    """Format floating seconds into MM:SS format (e.g. 00:13)."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def crop_plate_roi(frame_bgr: np.ndarray, vehicle_box: Dict[str, float]) -> Optional[np.ndarray]:
    """Extract license plate region from the lower-middle portion of a detected vehicle."""
    h, w = frame_bgr.shape[:2]
    vx1 = max(0, int(vehicle_box.get("x1", 0)))
    vy1 = max(0, int(vehicle_box.get("y1", 0)))
    vx2 = min(w, int(vehicle_box.get("x2", w)))
    vy2 = min(h, int(vehicle_box.get("y2", h)))

    vh = vy2 - vy1
    vw = vx2 - vx1
    if vh < 20 or vw < 20:
        return None

    # Lower 45% and middle 70% of vehicle
    x1 = max(0, int(vx1 + vw * 0.15))
    y1 = max(0, int(vy1 + vh * 0.55))
    x2 = min(w, int(vx2 - vw * 0.15))
    y2 = min(h, vy2)

    if y2 > y1 and x2 > x1:
        return frame_bgr[y1:y2, x1:x2]
    return None


def draw_hud_annotations(
    frame: np.ndarray,
    detections: List[Dict[str, Any]],
    mode: ProcessingMode,
    frame_idx: int,
    total_frames: int,
    time_str: str,
) -> np.ndarray:
    """Renders tactical bounding boxes, plate tags, and HUD information on frame."""
    annotated = frame.copy()
    h, w = annotated.shape[:2]

    color_map = {
        "PERSON": (0, 240, 255),      # Cyan
        "CAR": (16, 185, 129),        # Emerald Green
        "MOTORCYCLE": (192, 132, 252),# Purple
        "BUS": (245, 158, 11),        # Amber
        "TRUCK": (217, 119, 6),       # Dark Amber
        "BICYCLE": (250, 204, 21),    # Yellow
        "LICENSE_PLATE": (239, 68, 68)# Red
    }

    for det in detections:
        bbox = det.get("bounding_box", {})
        x1 = max(0, min(w, int(bbox.get("x1", 0))))
        y1 = max(0, min(h, int(bbox.get("y1", 0))))
        x2 = max(0, min(w, int(bbox.get("x2", 0))))
        y2 = max(0, min(h, int(bbox.get("y2", 0))))

        if x2 <= x1 or y2 <= y1:
            continue

        obj_class = det.get("object_class", "OBJECT").upper()
        conf = det.get("confidence", 0.0)
        conf_pct = int(round(conf * 100))
        plate_str = det.get("license_plate")
        plate_conf = det.get("plate_confidence")

        color = color_map.get(obj_class, (0, 255, 128))

        # 1. Main Bounding Box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        # 2. Tactical Corner Reticles
        corner_len = min(15, max(5, int((x2 - x1) * 0.15)))
        cv2.line(annotated, (x1, y1), (x1 + corner_len, y1), color, 3)
        cv2.line(annotated, (x1, y1), (x1, y1 + corner_len), color, 3)
        cv2.line(annotated, (x2, y1), (x2 - corner_len, y1), color, 3)
        cv2.line(annotated, (x2, y1), (x2, y1 + corner_len), color, 3)
        cv2.line(annotated, (x1, y2), (x1 + corner_len, y2), color, 3)
        cv2.line(annotated, (x1, y2), (x1, y2 - corner_len), color, 3)
        cv2.line(annotated, (x2, y2), (x2 - corner_len, y2), color, 3)
        cv2.line(annotated, (x2, y2), (x2, y2 - corner_len), color, 3)

        # 3. Label Tag (e.g. Car 94%, Person 91%)
        if mode in (ProcessingMode.YOLO, ProcessingMode.YOLO_ANPR):
            label = f"{obj_class} {conf_pct}%"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            by1 = max(0, y1 - th - 6)
            cv2.rectangle(annotated, (x1, by1), (x1 + tw + 8, by1 + th + 6), color, -1)
            cv2.putText(annotated, label, (x1 + 4, by1 + th + 1), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

        # 4. Number Plate Tag Banner (e.g. [IND] GJ05AB1234 89%)
        if (mode in (ProcessingMode.ANPR, ProcessingMode.YOLO_ANPR)) and plate_str:
            p_conf_pct = int(round((plate_conf or conf) * 100))
            plate_label = f"IND {plate_str} | {p_conf_pct}%"
            (ptw, pth), _ = cv2.getTextSize(plate_label, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
            
            # Position plate label near bottom of vehicle box
            py1 = min(h - pth - 6, y2 - pth - 8) if y2 > y1 + 40 else y2 + 4
            cv2.rectangle(annotated, (x1 + 2, py1), (x1 + ptw + 10, py1 + pth + 6), (15, 23, 42), -1)
            cv2.rectangle(annotated, (x1 + 2, py1), (x1 + ptw + 10, py1 + pth + 6), (239, 68, 68), 1)
            cv2.putText(annotated, plate_label, (x1 + 6, py1 + pth + 1), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)

    # 5. Top Left HUD Telemetry Banner
    mode_text = "YOLO+ANPR" if mode == ProcessingMode.YOLO_ANPR else mode.value.upper()
    hud_banner = f"PHANTOM 2.0 // MODE: {mode_text} // T: {time_str} // F: {frame_idx}/{total_frames} // DETS: {len(detections)}"
    (hw, hh), _ = cv2.getTextSize(hud_banner, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    cv2.rectangle(annotated, (8, 8), (20 + hw, 20 + hh), (10, 15, 29), -1)
    cv2.rectangle(annotated, (8, 8), (20 + hw, 20 + hh), (56, 189, 248), 1)
    cv2.putText(annotated, hud_banner, (14, 14 + hh), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (56, 189, 248), 1, cv2.LINE_AA)

    return annotated


def process_video_ai_task(
    job_id: str,
    input_path: str,
    output_path: str,
    mode: ProcessingMode,
    sample_fps: float = 4.0,
    conf_threshold: float = 0.35,
    camera_id: str = "CAM_TEST_01",
) -> None:
    """
    Asynchronous worker processing video frame-by-frame with YOLO & ANPR intelligence.
    """
    job = VIDEO_AI_JOBS.get(job_id)
    if not job:
        return

    job.status = JobStatus.PROCESSING
    detector = get_detector()
    ocr_proc = build_ocr_processor()
    tracker = YOLO26Tracker(camera_id=camera_id)

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        job.status = JobStatus.FAILED
        job.error_message = "Unable to open input video stream."
        return

    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        job.total_frames = total_frames
        job.fps = round(video_fps, 2)

        # Output video writer using PyAV for direct HTML5 H.264 playback, with cv2 fallback
        use_av = False
        av_container = None
        av_stream = None
        cv_out = None

        try:
            import av
            av_container = av.open(output_path, mode="w")
            av_stream = av_container.add_stream("h264", rate=int(round(video_fps)))
            av_stream.width = width
            av_stream.height = height
            av_stream.pix_fmt = "yuv420p"
            av_stream.options = {"crf": "23", "preset": "veryfast"}
            use_av = True
        except Exception as av_err:
            logger.warning(f"PyAV H264 init fallback to cv2: {av_err}")
            fourcc = getattr(cv2, "VideoWriter_fourcc", cv2.VideoWriter.fourcc)(*"mp4v")
            cv_out = cv2.VideoWriter(output_path, fourcc, video_fps, (width, height))

        frame_step = max(1, int(round(video_fps / max(1.0, min(video_fps, sample_fps))))) if sample_fps > 0 else 1

        start_time = time.perf_counter()
        frame_idx = 0
        total_dets = 0
        total_plates = 0
        class_counts: Dict[str, int] = {}
        unique_vehicle_tracks: Set[int] = set()
        confidences_list: List[float] = []
        peak_frame_density = 0
        anpr_dict: Dict[str, ANPRTableItem] = {}
        all_recent_events: List[DetectionEvent] = []

        last_cached_detections: List[Dict[str, Any]] = []

        # OCR cache for tracks/vehicles to avoid re-running OCR on identical vehicle every frame
        plate_cache: Dict[str, Tuple[str, float, Optional[str]]] = {}

        while True:
            if job.is_cancelled:
                job.status = JobStatus.CANCELLED
                logger.info(f"Video AI job {job_id} cancelled by user.")
                break

            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            pts_sec = (frame_idx - 1) / max(1.0, video_fps)
            time_str = format_seconds_to_time(pts_sec)

            # Determine whether to execute heavy AI inference on this frame or reuse tracks
            should_infer = (frame_idx % frame_step == 0) or (frame_idx == 1) or (frame_idx == total_frames)

            current_frame_dets: List[Dict[str, Any]] = []

            if should_infer:
                raw_dets = detector.detect_frame(frame, confidence_threshold=conf_threshold)
                tracked_dets = tracker.update(raw_dets, frame_shape=(height, width), pts_msec=pts_sec * 1000.0)

                peak_frame_density = max(peak_frame_density, len(tracked_dets))

                for d in tracked_dets:
                    raw_cls = d.get("class_name", "OBJECT")
                    canon_cls = normalize_class_name(raw_cls)
                    conf = float(d.get("confidence", 0.0))
                    bbox = d.get("bbox", {})
                    tid = d.get("track_id")
                    confidences_list.append(conf)

                    is_vehicle = canon_cls in ("CAR", "TRUCK", "BUS", "MOTORCYCLE", "OTHER_VEHICLE", "BICYCLE")
                    if is_vehicle and tid:
                        unique_vehicle_tracks.add(tid)

                    # Mode filtering
                    if mode == ProcessingMode.ANPR and not is_vehicle:
                        continue  # Skip non-vehicles in ANPR only mode

                    det_item: Dict[str, Any] = {
                        "object_class": canon_cls,
                        "confidence": conf,
                        "bounding_box": bbox,
                        "track_id": tid,
                        "is_vehicle": is_vehicle,
                    }

                    # ANPR Plate Extraction & OCR (Always check on vehicle bounding boxes)
                    if is_vehicle:
                        track_key = f"track_{tid}" if tid else f"box_{bbox.get('x1')}_{bbox.get('y1')}"
                        
                        # Check cache
                        if track_key in plate_cache:
                            plate_text, plate_conf, rto_name = plate_cache[track_key]
                        else:
                            p_crop = crop_plate_roi(frame, bbox)
                            plate_text = ""
                            plate_conf = 0.0
                            rto_name = None

                            if p_crop is not None:
                                ocr_res = ocr_proc.read_text(p_crop)
                                norm_p = normalize_plate_text(ocr_res.raw_text or ocr_res.normalized_text)
                                if norm_p and (len(norm_p) >= 5 or looks_like_indian_plate(norm_p)):
                                    plate_text = norm_p
                                    plate_conf = float(ocr_res.confidence or 0.88)
                                    struct = extract_plate_structure(norm_p)
                                    rto_name = struct.get("rto_jurisdiction")
                                    plate_cache[track_key] = (plate_text, plate_conf, rto_name)

                        if plate_text:
                            det_item["license_plate"] = plate_text
                            det_item["plate_confidence"] = plate_conf
                            det_item["rto_jurisdiction"] = rto_name

                            # Update ANPR Table
                            if plate_text in anpr_dict:
                                item = anpr_dict[plate_text]
                                item.last_seen_frame = frame_idx
                                item.total_sightings += 1
                                if plate_conf > item.confidence:
                                    item.confidence = round(plate_conf, 4)
                                    item.time_str = time_str
                            else:
                                anpr_dict[plate_text] = ANPRTableItem(
                                    plate_number=plate_text,
                                    confidence=round(plate_conf, 4),
                                    time_str=time_str,
                                    timestamp_sec=round(pts_sec, 2),
                                    vehicle=canon_cls.capitalize(),
                                    rto_jurisdiction=rto_name or "Gujarat RTO",
                                    is_gujarat=plate_text.startswith("GJ"),
                                    first_seen_frame=frame_idx,
                                    last_seen_frame=frame_idx,
                                    total_sightings=1,
                                )
                                total_plates += 1

                            # Push to detection feed
                            event_plate = DetectionEvent(
                                frame_idx=frame_idx,
                                timestamp_sec=round(pts_sec, 2),
                                time_str=time_str,
                                object_class=plate_text,
                                display_name=f"Plate: {plate_text}",
                                confidence=round(plate_conf, 4),
                                bounding_box=bbox,
                                is_vehicle=True,
                                vehicle_type=canon_cls.capitalize(),
                                license_plate=plate_text,
                                plate_confidence=round(plate_conf, 4),
                                rto_jurisdiction=rto_name,
                                track_id=tid,
                            )
                            all_recent_events.append(event_plate)

                    # Push main detection
                    total_dets += 1
                    class_counts[canon_cls] = class_counts.get(canon_cls, 0) + 1

                    disp_name = canon_cls.capitalize() if canon_cls != "CAR" else "Car"
                    event = DetectionEvent(
                        frame_idx=frame_idx,
                        timestamp_sec=round(pts_sec, 2),
                        time_str=time_str,
                        object_class=canon_cls,
                        display_name=disp_name,
                        confidence=round(conf, 4),
                        bounding_box=bbox,
                        is_vehicle=is_vehicle,
                        vehicle_type=canon_cls.capitalize() if is_vehicle else None,
                        license_plate=det_item.get("license_plate"),
                        plate_confidence=det_item.get("plate_confidence"),
                        rto_jurisdiction=det_item.get("rto_jurisdiction"),
                        track_id=tid,
                    )
                    all_recent_events.append(event)
                    current_frame_dets.append(det_item)

                last_cached_detections = current_frame_dets
            else:
                current_frame_dets = last_cached_detections

            # Annotate Frame
            annotated_frame = draw_hud_annotations(
                frame,
                current_frame_dets,
                mode=mode,
                frame_idx=frame_idx,
                total_frames=total_frames,
                time_str=time_str,
            )

            # Write output frame
            if use_av and av_stream is not None and av_container is not None:
                av_frame = av.VideoFrame.from_ndarray(annotated_frame, format="bgr24")
                for packet in av_stream.encode(av_frame):
                    av_container.mux(packet)
            elif cv_out is not None:
                cv_out.write(annotated_frame)

            # Update live preview buffer and progress every 2 frames
            if frame_idx % 2 == 0 or frame_idx == total_frames:
                elapsed = time.perf_counter() - start_time
                progress = round((frame_idx / total_frames) * 100.0, 1)
                proc_rate = frame_idx / elapsed if elapsed > 0 else 1.0
                eta = round((total_frames - frame_idx) / proc_rate, 1) if proc_rate > 0 else 0.0

                # Encode small preview frame
                preview_scale = 0.5 if width > 960 else 1.0
                if preview_scale != 1.0:
                    pw = int(width * preview_scale)
                    ph = int(height * preview_scale)
                    small_annotated = cv2.resize(annotated_frame, (pw, ph), interpolation=cv2.INTER_AREA)
                else:
                    small_annotated = annotated_frame

                _, jpg_buffer = cv2.imencode(".jpg", small_annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                b64_frame = base64.b64encode(jpg_buffer.tobytes()).decode("utf-8")

                # Compute rich real-time analytics
                cars_c = class_counts.get("CAR", 0)
                buses_c = class_counts.get("BUS", 0)
                trucks_c = class_counts.get("TRUCK", 0)
                motos_c = class_counts.get("MOTORCYCLE", 0)
                pers_c = class_counts.get("PERSON", 0)
                bikes_c = class_counts.get("BICYCLE", 0)
                tot_veh = cars_c + buses_c + trucks_c + motos_c

                distrib = {}
                if tot_veh > 0:
                    distrib = {
                        "Car": round((cars_c / tot_veh) * 100.0, 1),
                        "Bus": round((buses_c / tot_veh) * 100.0, 1),
                        "Truck": round((trucks_c / tot_veh) * 100.0, 1),
                        "Motorcycle": round((motos_c / tot_veh) * 100.0, 1),
                    }

                avg_conf = round(sum(confidences_list) / len(confidences_list) * 100.0, 1) if confidences_list else 0.0
                cong_level = "HIGH" if peak_frame_density >= 7 else ("MODERATE" if peak_frame_density >= 3 else "LOW")

                job.analytics = ObjectAnalytics(
                    total_objects_tracked=total_dets,
                    unique_vehicles_count=len(unique_vehicle_tracks) or tot_veh,
                    cars_count=cars_c,
                    buses_count=buses_c,
                    trucks_count=trucks_c,
                    motorcycles_count=motos_c,
                    pedestrians_count=pers_c,
                    bicycles_count=bikes_c,
                    peak_frame_density=peak_frame_density,
                    avg_confidence_pct=avg_conf,
                    congestion_level=cong_level,
                    vehicle_distribution=distrib,
                )

                job.frames_processed = frame_idx
                job.progress_percent = min(100.0, progress)
                job.elapsed_seconds = round(elapsed, 1)
                job.processing_fps = round(proc_rate, 1)
                job.eta_seconds = eta
                job.total_detections = total_dets
                job.total_plates_recognized = len(anpr_dict)
                job.class_breakdown = class_counts
                job.recent_detections = all_recent_events[-60:]  # Keep last 60 events
                job.anpr_results = list(anpr_dict.values())
                job.latest_frame_b64 = f"data:image/jpeg;base64,{b64_frame}"

        cap.release()
        if use_av and av_container is not None:
            try:
                for packet in av_stream.encode():
                    av_container.mux(packet)
                av_container.close()
            except Exception as e:
                logger.warning(f"Error finalizing PyAV container: {e}")
        elif cv_out is not None:
            cv_out.release()

        if job.status != JobStatus.CANCELLED:
            job.status = JobStatus.COMPLETED
            job.progress_percent = 100.0
            job.eta_seconds = 0.0
            job.completed_at = datetime.now(timezone.utc).isoformat()
            job.download_url = f"/api/results/{job_id}/video"
            job.video_url = f"/api/results/{job_id}/video"
            logger.info(
                f"Video AI job [{job_id}] finished successfully in {job.elapsed_seconds}s. "
                f"Frames: {frame_idx}, Detections: {total_dets}, Plates: {len(anpr_dict)}"
            )

    except Exception as exc:
        logger.error(f"Error processing video AI job [{job_id}]: {exc}", exc_info=True)
        job.status = JobStatus.FAILED
        job.error_message = f"Inference processing error: {str(exc)}"
    finally:
        cap.release()
        if os.path.exists(input_path):
            try:
                os.remove(input_path)
            except OSError:
                pass


class VideoAIService:
    """Service facade for managing video and AI processing jobs."""

    @staticmethod
    def create_job(
        input_file_path: str,
        mode: ProcessingMode = ProcessingMode.YOLO_ANPR,
        sample_fps: float = 4.0,
        conf_threshold: float = 0.35,
        camera_id: str = "CAM_SURVEILLANCE",
    ) -> VideoAIJobState:
        job_id = str(uuid.uuid4())
        output_path = str(OUTPUT_DIR / f"{job_id}_annotated.mp4")

        job_state = VideoAIJobState(
            job_id=job_id,
            mode=mode,
            status=JobStatus.QUEUED,
        )
        VIDEO_AI_JOBS[job_id] = job_state

        # Launch worker thread
        t = threading.Thread(
            target=process_video_ai_task,
            kwargs={
                "job_id": job_id,
                "input_path": input_file_path,
                "output_path": output_path,
                "mode": mode,
                "sample_fps": sample_fps,
                "conf_threshold": conf_threshold,
                "camera_id": camera_id,
            },
            daemon=True,
        )
        t.start()

        return job_state

    @staticmethod
    def get_job(job_id: str) -> Optional[VideoAIJobState]:
        return VIDEO_AI_JOBS.get(job_id)

    @staticmethod
    def stop_job(job_id: str) -> bool:
        job = VIDEO_AI_JOBS.get(job_id)
        if job and job.status == JobStatus.PROCESSING:
            job.is_cancelled = True
            return True
        return False


video_ai_service = VideoAIService()
