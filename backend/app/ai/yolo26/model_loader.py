"""
YOLO26 Model Loader & Runtime Initializer
Handles device detection (CUDA/CPU), model weight resolution, and baseline fallback loading.
Thread-safe singleton pattern ensures weights are loaded strictly once into memory.
"""
import logging
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Tuple

from .config import YOLO26Config

logger = logging.getLogger("phantom.ai.yolo26.loader")


class YOLO26ModelLoader:
    """
    Thread-safe Singleton Model Loading Service.
    Loads YOLO26 weights once and manages compute device lifecycle without per-frame reloading.
    """

    _instance: Optional["YOLO26ModelLoader"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, config: Optional[YOLO26Config] = None) -> "YOLO26ModelLoader":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super(YOLO26ModelLoader, cls).__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self, config: Optional[YOLO26Config] = None) -> None:
        if getattr(self, "_initialized", False):
            return

        with self._lock:
            if getattr(self, "_initialized", False):
                return

            self.config = config or YOLO26Config()
            self.model: Optional[Any] = None
            self.device: str = "cpu"
            self.resolved_model_path: Optional[str] = None
            self.active_weights_source: str = "NONE"
            self.is_loaded: bool = False
            self.is_baseline_fallback: bool = False
            self.error_message: Optional[str] = None
            self._load_lock = threading.Lock()

            self._initialize()
            self._initialized = True

    def _resolve_device(self) -> str:
        """Detect and validate available compute hardware."""
        requested = (self.config.device or "auto").strip().lower()
        if requested in ("auto", "cuda", "gpu", "0", "cuda:0"):
            try:
                import torch
                if torch.cuda.is_available() and torch.cuda.device_count() > 0:
                    device_name = torch.cuda.get_device_name(0)
                    logger.info(f"CUDA hardware acceleration detected: {device_name}. Target compute: cuda:0")
                    return "cuda:0"
            except Exception as e:
                logger.debug(f"CUDA hardware detection notice: {e}")
            if requested not in ("auto",):
                logger.info("CUDA not available on this host. Falling back to CPU compute.")
            return "cpu"
        return "cpu"

    def _get_candidate_weight_paths(self) -> List[Path]:
        """Ordered candidate paths to search for custom YOLO26 weights."""
        base_dir = Path(__file__).resolve().parent
        return [
            Path(self.config.model_path),
            base_dir / "models" / "yolo26.pt",
            base_dir / "models" / "yolo26n.pt",
            base_dir / "models" / "yolo26s.pt",
            base_dir / "yolo26.pt",
            Path("backend/app/ai/yolo26/models/yolo26.pt"),
            Path("yolo26.pt"),
        ]

    def _get_baseline_fallback_paths(self) -> List[Path]:
        """Candidate paths for baseline fallback weights (e.g. yolov8n.pt)."""
        base_dir = Path(__file__).resolve().parent
        return [
            Path(self.config.fallback_baseline_path),
            Path("yolov8n.pt"),
            Path("backend/yolov8n.pt"),
            base_dir.parent.parent.parent / "yolov8n.pt",
            base_dir.parent.parent.parent.parent / "yolov8n.pt",
        ]

    def _initialize(self) -> None:
        """Execute hierarchical weight discovery and model instantiation."""
        with self._load_lock:
            self.device = self._resolve_device()
            self.error_message = None

            # 1. Primary: Search for custom YOLO26 weights
            for weight_path in self._get_candidate_weight_paths():
                if weight_path.is_file():
                    try:
                        from ultralytics import YOLO
                        logger.info(f"Loading primary YOLO26 weights from {weight_path} onto {self.device}...")
                        self.model = YOLO(str(weight_path))
                        self.is_loaded = True
                        self.is_baseline_fallback = False
                        self.resolved_model_path = str(weight_path.resolve())
                        self.active_weights_source = f"YOLO26 ({weight_path.name})"
                        logger.info("YOLO26 model weights successfully loaded into memory.")
                        self._warmup_model()
                        return
                    except Exception as exc:
                        logger.warning(f"Failed loading custom YOLO26 weights from {weight_path}: {exc}")

            # 2. Secondary: Search for local baseline weights (yolov8n.pt) during migration
            for fb_path in self._get_baseline_fallback_paths():
                if fb_path.is_file():
                    try:
                        from ultralytics import YOLO
                        logger.info(f"Initializing baseline fallback model from {fb_path} onto {self.device}...")
                        self.model = YOLO(str(fb_path))
                        self.is_loaded = True
                        self.is_baseline_fallback = True
                        self.resolved_model_path = str(fb_path.resolve())
                        self.active_weights_source = f"BASELINE_FALLBACK ({fb_path.name})"
                        logger.info("Baseline YOLO engine loaded successfully (yolov8n migration fallback active).")
                        self._warmup_model()
                        return
                    except Exception as fb_exc:
                        logger.warning(f"Failed loading fallback baseline from {fb_path}: {fb_exc}")

            # 3. Tertiary: Standard ultralytics lookup / synthetic fallback
            try:
                from ultralytics import YOLO
                logger.info(f"Attempting standard baseline resolution on {self.device}...")
                self.model = YOLO("yolov8n.pt")
                self.is_loaded = True
                self.is_baseline_fallback = True
                self.resolved_model_path = "yolov8n.pt"
                self.active_weights_source = "BASELINE_FALLBACK (ultralytics standard)"
                logger.info("Standard baseline YOLO engine loaded successfully.")
                self._warmup_model()
                return
            except Exception as fallback_exc:
                logger.info(
                    f"Ultralytics weights unavailable or offline ({fallback_exc}). "
                    "Operating in high-precision synthetic deterministic mode."
                )
                self.model = None
                self.is_loaded = False
                self.is_baseline_fallback = False
                self.resolved_model_path = None
                self.active_weights_source = "SYNTHETIC_DETERMINISTIC"
                self.error_message = "No custom YOLO26 or baseline weights found. Synthetic mode active."

    def _warmup_model(self) -> None:
        """Executes a single dummy warm-up pass to prime PyTorch/Ultralytics JIT kernels."""
        if self.model is not None:
            try:
                import numpy as np
                dummy = np.zeros((384, 384, 3), dtype=np.uint8)
                self.model.predict(source=dummy, imgsz=384, verbose=False, device=self.device)
                logger.info("YOLO26 runtime warm-up pass completed.")
            except Exception as w_err:
                logger.debug(f"Model warmup notice: {w_err}")

    def get_status(self) -> Dict[str, Any]:
        """Returns runtime status without exposing internal memory pointers or stack traces."""
        return {
            "model_name": self.config.model_name,
            "model_version": self.config.model_version,
            "is_loaded": self.is_loaded,
            "is_baseline_fallback": self.is_baseline_fallback,
            "device": self.device,
            "resolved_model_path": self.resolved_model_path or "N/A (Synthetic Mode)",
            "configured_model_path": self.config.model_path,
            "active_weights_source": self.active_weights_source,
            "half_precision": self.config.half_precision,
            "target_classes": self.config.target_classes,
            "confidence_threshold": self.config.confidence_threshold,
            "iou_threshold": self.config.iou_threshold,
            "error": self.error_message,
        }


def get_model_loader(config: Optional[YOLO26Config] = None) -> YOLO26ModelLoader:
    return YOLO26ModelLoader(config=config)
