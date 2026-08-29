"""
PHANTOM Multi-Stream CCTV AI Manager
Decoupled, non-blocking, multi-threaded continuous YOLO26 live inference engine.
Employs latest-frame single-slot buffer architecture to eliminate lag and frame queuing.
"""
import asyncio
from datetime import datetime, timezone
import threading
import time
from typing import Any, Dict, List, Optional, Set, Union
import uuid

import numpy as np
from pydantic import BaseModel, Field

from app.ai.yolo26.detector import get_detector
from app.ai.yolo26.tracker import YOLO26Tracker
from app.core.logging import logger
from app.services.event_publisher import event_publisher


# ------------------------------------------------------------------------------
# 1. Models & Stream Configuration
# ------------------------------------------------------------------------------

class StreamStatus(BaseModel):
    camera_id: str
    source_url: str
    source_type: str = "GATEWAY"  # RTSP, IP_CAM, USB, FILE, GATEWAY
    is_running: bool
    stream_fps: float = 0.0
    ai_processed_fps: float = 0.0
    total_frames_read: int = 0
    total_inferences: int = 0
    total_detections: int = 0
    total_alerts: int = 0
    latency_ms: float = 0.0
    device: str = "cpu"
    last_seen: Optional[str] = None
    reconnect_attempts: int = 0
    error_message: Optional[str] = None


class StreamConfigRequest(BaseModel):
    camera_id: str = Field(..., description="Unique camera ID (e.g., CAM-AMD-ITX-01)")
    source_url: str = Field(..., description="RTSP URL, HTTP HLS stream, or USB index ('0', '1')")
    sample_fps: float = Field(default=2.0, ge=0.2, le=30.0, description="Inference sampling rate (FPS)")
    alert_classes: List[str] = Field(
        default_factory=lambda: ["PERSON", "CAR", "LICENSE_PLATE", "MOTORCYCLE", "TRUCK", "BUS"],
        description="Target classes that trigger high-priority alerts",
    )
    confidence_threshold: float = Field(default=0.35, ge=0.1, le=1.0)
    alert_cooldown_seconds: float = Field(default=30.0, description="Minimum seconds between duplicate alerts")


# ------------------------------------------------------------------------------
# 2. Individual Stream Worker Thread (Decoupled Ingest + Inference)
# ------------------------------------------------------------------------------

class CameraStreamWorker:
    """
    Dedicated worker per camera stream.
    Decoupled Architecture:
    - Reader thread grabs frames from source at full camera FPS into a 1-slot latest frame buffer.
    - Inference thread runs YOLO26 at configured sample_fps on the newest frame, dropping stale frames.
    """

    def __init__(self, config: StreamConfigRequest) -> None:
        self.config: StreamConfigRequest = config
        self.camera_id: str = config.camera_id
        self.source_url: str = config.source_url
        self.is_running: bool = False

        self._capture_thread: Optional[threading.Thread] = None
        self._inference_thread: Optional[threading.Thread] = None

        # 1-slot latest frame buffer
        self._frame_lock: threading.Lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_frame_ts: Optional[datetime] = None
        self._new_frame_available: threading.Event = threading.Event()

        # Telemetry metrics
        self.stream_fps: float = 0.0
        self.ai_processed_fps: float = 0.0
        self.total_frames_read: int = 0
        self.total_inferences: int = 0
        self.total_detections: int = 0
        self.total_alerts: int = 0
        self.latency_ms: float = 0.0
        self.device: str = "cpu"
        self.last_seen: Optional[str] = None
        self.reconnect_attempts: int = 0
        self.error_message: Optional[str] = None

        self._last_alert_time: Dict[str, float] = {}
        self.latest_hud_payload: Optional[Dict[str, Any]] = None
        self.tracker: YOLO26Tracker = YOLO26Tracker(camera_id=self.camera_id)

    def _resolve_capture_source(self) -> Union[int, str]:
        src = self.source_url.strip()
        if src.isdigit():
            return int(src)
        return src

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True

        # 1. Start continuous frame ingestion reader thread
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
            name=f"YOLO26-Capture-{self.camera_id}",
        )
        self._capture_thread.start()

        # 2. Start decoupled AI inference thread
        self._inference_thread = threading.Thread(
            target=self._inference_loop,
            daemon=True,
            name=f"YOLO26-Infer-{self.camera_id}",
        )
        self._inference_thread.start()

        logger.info(f"Started continuous YOLO26 stream worker for [{self.camera_id}] (Target FPS: {self.config.sample_fps})")

    def stop(self) -> None:
        self.is_running = False
        self._new_frame_available.set()

        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=1.5)
        if self._inference_thread and self._inference_thread.is_alive():
            self._inference_thread.join(timeout=1.5)

        logger.info(f"Stopped continuous stream worker for [{self.camera_id}]")

    def _should_trigger_alert(self, obj_class: str, now_epoch: float) -> bool:
        if obj_class not in self.config.alert_classes:
            return False
        last_time = self._last_alert_time.get(obj_class, 0.0)
        if now_epoch - last_time >= self.config.alert_cooldown_seconds:
            self._last_alert_time[obj_class] = now_epoch
            return True
        return False

    def _capture_loop(self) -> None:
        """Continuously reads frames from camera source into the 1-slot buffer."""
        from app.services.stream_gateway_service import stream_gateway_service

        fps_timer = time.perf_counter()
        frames_in_second = 0

        while self.is_running:
            success, frame, _ = stream_gateway_service.read_camera_frame(self.camera_id)
            if success and frame is not None:
                now_ts = datetime.now(timezone.utc)
                with self._frame_lock:
                    self._latest_frame = frame
                    self._latest_frame_ts = now_ts

                self._new_frame_available.set()
                self.total_frames_read += 1
                frames_in_second += 1

                now_time = time.perf_counter()
                if now_time - fps_timer >= 1.0:
                    self.stream_fps = round(frames_in_second / (now_time - fps_timer), 1)
                    frames_in_second = 0
                    fps_timer = now_time

            time.sleep(0.04)  # ~25 FPS ingestion rate

    def _inference_loop(self) -> None:
        """Pulls the latest frame from the 1-slot buffer at configured sample_fps."""
        detector = get_detector()
        self.device = detector.device
        target_interval = 1.0 / max(0.1, self.config.sample_fps)

        while self.is_running:
            start_cycle = time.perf_counter()

            try:
                # Retrieve latest frame from buffer
                frame_to_process = None
                frame_ts = None
                with self._frame_lock:
                    if self._latest_frame is not None:
                        frame_to_process = self._latest_frame.copy()
                        frame_ts = self._latest_frame_ts

                if frame_to_process is None:
                    self._new_frame_available.wait(timeout=0.1)
                    continue

                # Run YOLO26 Inference
                ts = frame_ts or datetime.now(timezone.utc)
                start_infer = time.perf_counter()
                detections = detector.detect(frame_to_process, camera_id=self.camera_id, timestamp=ts)
                infer_dur_ms = (time.perf_counter() - start_infer) * 1000.0
                self.latency_ms = round(infer_dur_ms, 1)
                self.last_seen = ts.isoformat()
                self.total_inferences += 1

                # Apply Multi-Object Trajectory Tracking across consecutive frames
                h, w = frame_to_process.shape[:2]
                if self.tracker:
                    detections = self.tracker.update(detections, frame_shape=(h, w), timestamp=ts)

                # Instantaneous AI throughput estimate
                self.ai_processed_fps = round(min(self.config.sample_fps, 1000.0 / max(1.0, infer_dur_ms)), 2)

                valid_dets = [d for d in detections if d.get("confidence", 0.0) >= self.config.confidence_threshold]
                self.total_detections += len(valid_dets)

                # Check alerts
                now_epoch = time.time()
                alert_classes_found: Set[str] = set()
                for d in valid_dets:
                    cls_name = d.get("object_class", "OBJECT")
                    if self._should_trigger_alert(cls_name, now_epoch):
                        alert_classes_found.add(cls_name)

                if alert_classes_found:
                    self.total_alerts += 1
                    severity = "HIGH" if "PERSON" in alert_classes_found or "LICENSE_PLATE" in alert_classes_found else "MEDIUM"
                    try:
                        asyncio.run(
                            event_publisher.publish(
                                event_name="WATCHLIST_MATCH" if "LICENSE_PLATE" in alert_classes_found else "DETECTION",
                                payload={
                                    "title": f"TACTICAL ALERT [{self.camera_id}]: {', '.join(alert_classes_found)}",
                                    "camera_id": self.camera_id,
                                    "source_url": self.source_url,
                                    "severity": severity,
                                    "matched_classes": list(alert_classes_found),
                                    "detections_count": len(valid_dets),
                                    "detections": valid_dets,
                                    "timestamp": ts.isoformat(),
                                },
                                camera_id=self.camera_id,
                                severity=severity,
                                source="yolo26-cctv-stream",
                            )
                        )
                    except Exception as pub_err:
                        logger.debug(f"Alert broadcast notice: {pub_err}")

                # Format HUD overlay frame
                formatted_objects = []
                for d in valid_dets:
                    raw_box = d.get("bounding_box", {})
                    bx1 = raw_box.get("x1", 0.0)
                    by1 = raw_box.get("y1", 0.0)
                    bx2 = raw_box.get("x2", 0.0)
                    by2 = raw_box.get("y2", 0.0)

                    if bx2 > 1.0 or by2 > 1.0:
                        nx1 = round((bx1 / max(1, w)) * 100, 2)
                        ny1 = round((by1 / max(1, h)) * 100, 2)
                        nx2 = round((bx2 / max(1, w)) * 100, 2)
                        ny2 = round((by2 / max(1, h)) * 100, 2)
                    else:
                        nx1 = round(bx1 * 100, 2)
                        ny1 = round(by1 * 100, 2)
                        nx2 = round(bx2 * 100, 2)
                        ny2 = round(by2 * 100, 2)

                    cls_name = d.get("object_class", "OBJECT")
                    track_id = d.get("track_id")
                    conf = round(d.get("confidence", 0.0), 4)
                    disp_label = d.get("display_label") or (
                        f"{cls_name.capitalize()} #{track_id} | {int(round(conf * 100))}%"
                        if track_id
                        else f"{cls_name.capitalize()} {int(round(conf * 100))}%"
                    )

                    formatted_objects.append({
                        "detection_id": d.get("detection_id", str(uuid.uuid4())),
                        "camera_id": self.camera_id,
                        "object_class": cls_name.upper(),
                        "class_name": cls_name.lower(),
                        "confidence": conf,
                        "track_id": track_id,
                        "bbox": {
                            "x1": round(bx1, 1),
                            "y1": round(by1, 1),
                            "x2": round(bx2, 1),
                            "y2": round(by2, 1),
                        },
                        "bounding_box": {
                            "x1": nx1,
                            "y1": ny1,
                            "x2": nx2,
                            "y2": ny2,
                            "width": round(abs(nx2 - nx1), 2),
                            "height": round(abs(ny2 - ny1), 2),
                        },
                        "first_seen": d.get("first_seen", ts.isoformat()),
                        "last_seen": d.get("last_seen", ts.isoformat()),
                        "dwell_time": d.get("dwell_time", 0.0),
                        "movement_direction": d.get("movement_direction", "STATIONARY"),
                        "display_label": disp_label,
                        "attributes": d.get("attributes", {}),
                        "is_watchlist_match": d.get("is_watchlist_match", False),
                        "threat_level": d.get("threat_level", "NORMAL"),
                    })

                cam_info: Dict[str, Any] = {}
                try:
                    from app.services.stream_gateway_service import stream_gateway_service
                    if hasattr(stream_gateway_service, "source_registry") and stream_gateway_service.source_registry:
                        cam_info = stream_gateway_service.source_registry.sources.get(self.camera_id, {})
                except Exception:
                    pass
                cam_name = cam_info.get("name") or cam_info.get("camera_name") or f"Camera {self.camera_id}"

                persons_count = sum(1 for o in formatted_objects if o.get("class_name") == "person" or o.get("object_class") == "PERSON")
                cars_count = sum(1 for o in formatted_objects if o.get("class_name") == "car" or o.get("object_class") == "CAR")
                vehicles_count = sum(1 for o in formatted_objects if o.get("attributes", {}).get("is_vehicle") or o.get("object_class") in {"CAR", "TRUCK", "BUS", "MOTORCYCLE"})
                plates_count = sum(1 for o in formatted_objects if o.get("attributes", {}).get("license_plate"))

                summary_payload = {
                    "persons": persons_count,
                    "cars": cars_count,
                    "total_objects": len(formatted_objects),
                    "vehicles_count": vehicles_count,
                    "persons_count": persons_count,
                    "plates_count": plates_count,
                    "critical_alerts": sum(1 for o in formatted_objects if o.get("is_watchlist_match")),
                }

                self.latest_hud_payload = {
                    "type": "ai_detection",
                    "camera_id": self.camera_id,
                    "camera_name": cam_name,
                    "frame_seq": self.total_inferences,
                    "timestamp": ts.isoformat(),
                    "ai_fps": self.ai_processed_fps or self.config.sample_fps,
                    "stream_fps": self.stream_fps,
                    "latency_ms": self.latency_ms,
                    "summary": summary_payload,
                    "objects": formatted_objects,
                    "detections": formatted_objects,
                }
            except Exception as infer_err:
                logger.error(f"Inference error in worker {self.camera_id}: {infer_err}")

            # Sleep to match target inference sampling interval
            elapsed_cycle = time.perf_counter() - start_cycle
            sleep_time = max(0.001, target_interval - elapsed_cycle)
            time.sleep(sleep_time)


# ------------------------------------------------------------------------------
# 3. Global Multi-Stream Manager Singleton
# ------------------------------------------------------------------------------

class MultiStreamYOLO26Manager:
    """Manages all concurrent camera AI streams."""

    _instance: Optional["MultiStreamYOLO26Manager"] = None
    _lock: threading.Lock = threading.Lock()
    workers: Dict[str, CameraStreamWorker]

    def __new__(cls) -> "MultiStreamYOLO26Manager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super(MultiStreamYOLO26Manager, cls).__new__(cls)
                    instance.workers = {}
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "workers"):
            self.workers = {}

    def register_and_start(self, config: StreamConfigRequest) -> StreamStatus:
        cam_id = config.camera_id
        if cam_id in self.workers:
            self.workers[cam_id].stop()

        worker = CameraStreamWorker(config)
        self.workers[cam_id] = worker
        worker.start()
        st = self.get_status(cam_id)
        if st is None:
            return StreamStatus(
                camera_id=cam_id,
                source_url=config.source_url,
                source_type="GATEWAY",
                is_running=True,
                stream_fps=0.0,
                ai_processed_fps=0.0,
                total_frames_read=0,
                total_inferences=0,
                total_detections=0,
                total_alerts=0,
                latency_ms=0.0,
                device="cpu",
                last_seen=None,
                reconnect_attempts=0,
                error_message=None,
            )
        return st

    def stop_stream(self, camera_id: str) -> bool:
        worker = self.workers.get(camera_id)
        if worker:
            worker.stop()
            del self.workers[camera_id]
            return True
        return False

    def get_status(self, camera_id: str) -> Optional[StreamStatus]:
        w = self.workers.get(camera_id)
        if not w:
            return None
        return StreamStatus(
            camera_id=w.camera_id,
            source_url=w.source_url,
            source_type="USB" if str(w.source_url).isdigit() else ("RTSP" if str(w.source_url).startswith("rtsp") else "GATEWAY"),
            is_running=w.is_running,
            stream_fps=w.stream_fps,
            ai_processed_fps=w.ai_processed_fps,
            total_frames_read=w.total_frames_read,
            total_inferences=w.total_inferences,
            total_detections=w.total_detections,
            total_alerts=w.total_alerts,
            latency_ms=w.latency_ms,
            device=w.device,
            last_seen=w.last_seen,
            reconnect_attempts=w.reconnect_attempts,
            error_message=w.error_message,
        )

    def get_latest_hud(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Returns the latest real-time detection HUD frame if a live stream worker is active."""
        w = self.workers.get(camera_id)
        if w and w.is_running and getattr(w, "latest_hud_payload", None):
            return w.latest_hud_payload
        return None

    def get_camera_ai_status(self, camera_id: str) -> Dict[str, Any]:
        """Returns standard per-camera AI operational status."""
        w = self.workers.get(camera_id)
        if not w:
            return {
                "camera_id": camera_id,
                "online": False,
                "ai_enabled": False,
                "inference_fps": 0.0,
                "active_tracks": 0,
            }
        active_tracks_count = len(w.tracker.tracks) if getattr(w, "tracker", None) else 0
        return {
            "camera_id": camera_id,
            "online": w.is_running and (w.stream_fps > 0 or w.total_frames_read > 0),
            "ai_enabled": w.is_running,
            "inference_fps": round(w.ai_processed_fps, 1),
            "active_tracks": active_tracks_count,
        }

    def start_all_configured_cameras(
        self, sample_fps: float = 2.0, max_cameras: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Orchestrates continuous YOLO26 inference across all configured cameras from camera_sources.yaml.
        Each camera runs an isolated capture & tracker thread while sharing the singleton YOLO26 detector.
        """
        from app.services.stream_gateway_service import stream_gateway_service
        sources = stream_gateway_service.source_registry.sources if hasattr(stream_gateway_service, "source_registry") and stream_gateway_service.source_registry else {}

        started_statuses: List[Dict[str, Any]] = []
        count = 0

        # Unique camera codes
        seen_codes: Set[str] = set()
        for cam_key, info in sources.items():
            cam_code = info.get("camera_code") or cam_key
            if cam_code in seen_codes:
                continue
            seen_codes.add(cam_code)

            src_url = info.get("source_url") or f"https://live.corp8.cloud/live/stream/{info.get('source_id', '13')}/index.m3u8"
            cfg = StreamConfigRequest(
                camera_id=cam_code,
                source_url=src_url,
                sample_fps=sample_fps,
                confidence_threshold=0.30,
            )
            self.register_and_start(cfg)
            started_statuses.append(self.get_camera_ai_status(cam_code))
            count += 1
            if max_cameras and count >= max_cameras:
                break

        logger.info("Initialized multi-camera YOLO26 stream cluster with %d active cameras.", len(started_statuses))
        return started_statuses

    def list_all_streams(self) -> List[StreamStatus]:
        statuses: List[StreamStatus] = []
        for cid in list(self.workers.keys()):
            st = self.get_status(cid)
            if st is not None:
                statuses.append(st)
        return statuses

    def stop_all(self) -> int:
        """Cleanly stops all running camera stream workers and releases resources."""
        count = 0
        for cid in list(self.workers.keys()):
            if self.stop_stream(cid):
                count += 1
        logger.info("Stopped all %d active YOLO26 camera workers.", count)
        return count


stream_manager = MultiStreamYOLO26Manager()
