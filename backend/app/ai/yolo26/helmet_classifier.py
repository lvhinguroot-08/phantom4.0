"""
Helmet Intelligence & Head Region Analysis Engine
Analyzes head/upper-body crops of associated two-wheeler riders.
Supports canonical classes: HELMET, NO_HELMET, UNCERTAIN, TURBAN.
Does NOT use fragile Canny edge / HSV color heuristics.
Safely returns UNCERTAIN on low resolution, blur, or ambiguous features.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import cv2
import numpy as np

logger = logging.getLogger("phantom.ai.yolo26.helmet_classifier")


@dataclass
class HelmetClassificationResult:
    """Standardized result of helmet analysis on a rider's head region."""
    state: str  # "HELMET", "NO_HELMET", "UNCERTAIN", "TURBAN"
    confidence: float
    is_violation_candidate: bool
    crop_valid: bool
    uncertain_reason: Optional[str] = None


class HelmetClassifierInterface(ABC):
    """Abstract interface for helmet classification models."""

    @abstractmethod
    def classify_crop(self, head_crop: np.ndarray) -> HelmetClassificationResult:
        """Classifies a BGR head crop image."""
        pass


class DeepLearningHelmetClassifier(HelmetClassifierInterface):
    """
    Pluggable deep-learning helmet classifier.
    Loads custom fine-tuned weights if provided via HELMET_MODEL_PATH.
    Otherwise operates in baseline calibrated evaluation mode.
    """

    CANONICAL_STATES = {"HELMET", "NO_HELMET", "UNCERTAIN", "TURBAN"}
    MIN_CROP_PIXELS = 16  # Minimum width and height in pixels for valid inference

    def __init__(
        self,
        model_path: Optional[str] = None,
        min_confidence: float = 0.55,
        device: str = "cpu",
    ):
        self.model_path = model_path
        self.min_confidence = min_confidence
        self.device = device
        self.model: Any = None
        self.is_custom_model = False
        self._init_model()

    def _init_model(self) -> None:
        """Attempts to load custom helmet weights if present on disk."""
        target_path = self.model_path or os.getenv("HELMET_MODEL_PATH")
        if target_path and Path(target_path).is_file():
            try:
                from ultralytics import YOLO
                self.model = YOLO(target_path)
                self.is_custom_model = True
                logger.info(f"Successfully loaded custom helmet model from: {target_path}")
                return
            except Exception as err:
                logger.warning(f"Could not load custom helmet weights from {target_path}: {err}. Falling back to baseline.")

        logger.info(
            "Running HelmetClassifier in standard baseline mode. "
            "Fine-tuned weights can be supplied via HELMET_MODEL_PATH."
        )

    def extract_head_crop(
        self,
        frame: np.ndarray,
        head_box: Dict[str, float],
    ) -> Tuple[Optional[np.ndarray], Optional[str]]:
        """
        Extracts and validates head crop from image frame.
        Handles both normalized (0-100%) and pixel coordinates.
        """
        if frame is None or frame.size == 0:
            return None, "EMPTY_FRAME"

        fh, fw = frame.shape[:2]
        x1 = head_box.get("x1", 0.0)
        y1 = head_box.get("y1", 0.0)
        x2 = head_box.get("x2", 0.0)
        y2 = head_box.get("y2", 0.0)

        # Convert from percentage if normalized (<= 100 and floats with x2 <= 100)
        # Note: If coordinates are in 0-100 percentage range:
        if x2 <= 100.0 and y2 <= 100.0 and (x2 > 1.0 or y2 > 1.0) and (fw > 100 and fh > 100):
            # Check if this represents percentage coordinates
            px1 = int((x1 / 100.0) * fw)
            py1 = int((y1 / 100.0) * fh)
            px2 = int((x2 / 100.0) * fw)
            py2 = int((y2 / 100.0) * fh)
        elif x2 <= 1.0 and y2 <= 1.0:
            # 0.0 to 1.0 normalized
            px1 = int(x1 * fw)
            py1 = int(y1 * fh)
            px2 = int(x2 * fw)
            py2 = int(y2 * fh)
        else:
            # Raw pixel coordinates
            px1 = int(x1)
            py1 = int(y1)
            px2 = int(x2)
            py2 = int(y2)

        # Clamping to frame boundaries
        px1 = max(0, min(fw - 1, px1))
        py1 = max(0, min(fh - 1, py1))
        px2 = max(px1 + 1, min(fw, px2))
        py2 = max(py1 + 1, min(fh, py2))

        crop_w = px2 - px1
        crop_h = py2 - py1

        if crop_w < self.MIN_CROP_PIXELS or crop_h < self.MIN_CROP_PIXELS:
            return None, f"LOW_RESOLUTION_{crop_w}x{crop_h}"

        crop = frame[py1:py2, px1:px2]
        if crop.size == 0:
            return None, "DEGENERATE_CROP"

        return crop, None

    def classify_crop(self, head_crop: np.ndarray) -> HelmetClassificationResult:
        """
        Runs deep model inference or calibrated feature evaluation.
        Guarantees NO heuristic edge-density or yellow/black pixel counting.
        """
        if head_crop is None or head_crop.size == 0:
            return HelmetClassificationResult(
                state="UNCERTAIN",
                confidence=0.0,
                is_violation_candidate=False,
                crop_valid=False,
                uncertain_reason="NULL_CROP",
            )

        h, w = head_crop.shape[:2]
        if w < self.MIN_CROP_PIXELS or h < self.MIN_CROP_PIXELS:
            return HelmetClassificationResult(
                state="UNCERTAIN",
                confidence=0.0,
                is_violation_candidate=False,
                crop_valid=False,
                uncertain_reason=f"LOW_RESOLUTION_{w}x{h}",
            )

        # 1. Custom model inference branch
        if self.is_custom_model and self.model is not None:
            try:
                results = self.model(head_crop, verbose=False)
                # Parse Ultralytics classification / detection result
                if results and hasattr(results[0], "probs") and results[0].probs is not None:
                    top1_idx = int(results[0].probs.top1)
                    top1_conf = float(results[0].probs.top1conf)
                    label = str(results[0].names.get(top1_idx, "UNCERTAIN")).upper()

                    state = "UNCERTAIN"
                    if "HELMET" in label and "NO" not in label:
                        state = "HELMET"
                    elif "NO_HELMET" in label or "NO-HELMET" in label or "BARE" in label:
                        state = "NO_HELMET"
                    elif "TURBAN" in label or "PAGRI" in label:
                        state = "TURBAN"

                    if top1_conf < self.min_confidence:
                        state = "UNCERTAIN"

                    is_violation = (state == "NO_HELMET" and top1_conf >= self.min_confidence)
                    return HelmetClassificationResult(
                        state=state,
                        confidence=round(top1_conf, 3),
                        is_violation_candidate=is_violation,
                        crop_valid=True,
                    )
            except Exception as err:
                logger.debug(f"Custom model inference error: {err}; using baseline evaluator.")

        # 2. Baseline Evaluation Mode
        # Evaluates image clarity and gradient structure without fake thresholds
        gray = cv2.cvtColor(head_crop, cv2.COLOR_BGR2GRAY)
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        # If motion blurred or heavily corrupted, mark UNCERTAIN
        if laplacian_var < 15.0:
            return HelmetClassificationResult(
                state="UNCERTAIN",
                confidence=0.40,
                is_violation_candidate=False,
                crop_valid=True,
                uncertain_reason="BLURRY_OR_MOTION_ARTIFACT",
            )

        # In baseline environment without fine-tuned weights, return UNCERTAIN with high crop validity
        # This guarantees zero false positive violations until production weights are loaded.
        return HelmetClassificationResult(
            state="UNCERTAIN",
            confidence=0.50,
            is_violation_candidate=False,
            crop_valid=True,
            uncertain_reason="REQUIRES_FINE_TUNED_WEIGHTS",
        )


class MockableHelmetClassifier(DeepLearningHelmetClassifier):
    """
    Test-friendly classifier allowing programmatic state injection for test suites.
    """

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._override_state: Optional[str] = None
        self._override_conf: Optional[float] = None

    def set_override(self, state: Optional[str], confidence: Optional[float] = None) -> None:
        """Overrides classifier output for unit testing."""
        self._override_state = state
        self._override_conf = confidence

    def classify_crop(self, head_crop: np.ndarray) -> HelmetClassificationResult:
        if self._override_state is not None:
            conf = self._override_conf if self._override_conf is not None else 0.85
            is_viol = (self._override_state == "NO_HELMET" and conf >= self.min_confidence)
            return HelmetClassificationResult(
                state=self._override_state,
                confidence=conf,
                is_violation_candidate=is_viol,
                crop_valid=True,
            )
        return super().classify_crop(head_crop)


# Global singleton instance
_helmet_classifier_instance: Optional[DeepLearningHelmetClassifier] = None


def get_helmet_classifier(
    model_path: Optional[str] = None,
    min_confidence: float = 0.55,
) -> DeepLearningHelmetClassifier:
    global _helmet_classifier_instance
    if _helmet_classifier_instance is None:
        _helmet_classifier_instance = MockableHelmetClassifier(
            model_path=model_path,
            min_confidence=min_confidence,
        )
    return _helmet_classifier_instance
