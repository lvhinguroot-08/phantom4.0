"""
License Plate Perspective Rectification & Image Quality Assessment Engine
Provides:
1. 4-point perspective transformation for angled and skewed plates.
2. Comprehensive image quality assessment (resolution, blur, contrast, brightness).
3. Rejection of unreadable plates to prevent hallucinated OCR.
"""
from dataclasses import dataclass
import logging
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("phantom.ai.anpr.perspective")


@dataclass
class QualityAssessmentResult:
    """Detailed quality report for a license plate crop."""
    is_readable: bool
    quality_score: float  # 0.0 to 1.0
    blur_variance: float
    brightness_mean: float
    contrast_std: float
    dimensions: Tuple[int, int]
    failure_reason: Optional[str] = None
    status: str = "OK"

    @property
    def blur_score(self) -> float:
        return self.blur_variance


class PlateQualityAssessor:
    """
    Evaluates license plate image quality prior to OCR execution.
    """

    MIN_WIDTH = 40
    MIN_HEIGHT = 14
    MIN_BLUR_VAR = 18.0  # Laplacian variance threshold
    MIN_CONTRAST = 15.0  # Pixel standard deviation threshold
    MIN_BRIGHTNESS = 25.0
    MAX_BRIGHTNESS = 240.0

    def __init__(
        self,
        min_width: int = MIN_WIDTH,
        min_height: int = MIN_HEIGHT,
        min_blur_var: float = MIN_BLUR_VAR,
        min_contrast: float = MIN_CONTRAST,
        min_brightness: float = MIN_BRIGHTNESS,
        max_brightness: float = MAX_BRIGHTNESS,
    ):
        self.min_width = min_width
        self.min_height = min_height
        self.min_blur_var = min_blur_var
        self.min_contrast = min_contrast
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness

    def assess(self, plate_crop: np.ndarray) -> QualityAssessmentResult:
        if plate_crop is None or plate_crop.size == 0:
            return QualityAssessmentResult(
                is_readable=False,
                quality_score=0.0,
                blur_variance=0.0,
                brightness_mean=0.0,
                contrast_std=0.0,
                dimensions=(0, 0),
                failure_reason="EMPTY_CROP",
                status="UNREADABLE",
            )

        h, w = plate_crop.shape[:2]
        if w < self.min_width or h < self.min_height:
            return QualityAssessmentResult(
                is_readable=False,
                quality_score=0.10,
                blur_variance=0.0,
                brightness_mean=0.0,
                contrast_std=0.0,
                dimensions=(w, h),
                failure_reason=f"LOW_RESOLUTION_{w}x{h}",
                status="UNREADABLE",
            )

        gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY) if len(plate_crop.shape) == 3 else plate_crop

        # 1. Blur evaluation via Laplacian variance
        blur_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        # 2. Brightness and contrast
        mean_val = float(np.mean(gray))
        std_val = float(np.std(gray))

        # Check critical failure criteria
        if blur_var < self.min_blur_var:
            return QualityAssessmentResult(
                is_readable=False,
                quality_score=0.25,
                blur_variance=round(blur_var, 1),
                brightness_mean=round(mean_val, 1),
                contrast_std=round(std_val, 1),
                dimensions=(w, h),
                failure_reason="SEVERE_BLUR",
                status="UNREADABLE",
            )

        if std_val < self.min_contrast:
            return QualityAssessmentResult(
                is_readable=False,
                quality_score=0.20,
                blur_variance=round(blur_var, 1),
                brightness_mean=round(mean_val, 1),
                contrast_std=round(std_val, 1),
                dimensions=(w, h),
                failure_reason="LOW_CONTRAST",
                status="UNREADABLE",
            )

        if mean_val < self.min_brightness:
            return QualityAssessmentResult(
                is_readable=False,
                quality_score=0.20,
                blur_variance=round(blur_var, 1),
                brightness_mean=round(mean_val, 1),
                contrast_std=round(std_val, 1),
                dimensions=(w, h),
                failure_reason="UNDEREXPOSED_DARK",
                status="UNREADABLE",
            )

        if mean_val > self.max_brightness:
            return QualityAssessmentResult(
                is_readable=False,
                quality_score=0.20,
                blur_variance=round(blur_var, 1),
                brightness_mean=round(mean_val, 1),
                contrast_std=round(std_val, 1),
                dimensions=(w, h),
                failure_reason="OVEREXPOSED_GLARE",
                status="UNREADABLE",
            )

        # Composite quality score calculation
        blur_score = min(1.0, blur_var / 250.0)
        contrast_score = min(1.0, std_val / 65.0)
        res_score = min(1.0, (w * h) / (200.0 * 60.0))
        quality = (0.45 * blur_score) + (0.35 * contrast_score) + (0.20 * res_score)

        return QualityAssessmentResult(
            is_readable=True,
            quality_score=round(min(1.0, max(0.40, quality)), 3),
            blur_variance=round(blur_var, 1),
            brightness_mean=round(mean_val, 1),
            contrast_std=round(std_val, 1),
            dimensions=(w, h),
            failure_reason=None,
            status="OK",
        )


class PlatePerspectiveCorrector:
    """
    Applies 4-point quadrilateral perspective transformation to straighten angled license plates.
    """

    TARGET_WIDTH = 320
    TARGET_HEIGHT = 96

    def __init__(self, target_width: int = TARGET_WIDTH, target_height: int = TARGET_HEIGHT):
        self.target_width = target_width
        self.target_height = target_height

    @staticmethod
    def order_points(pts: np.ndarray) -> np.ndarray:
        """
        Orders quadrilateral coordinates: top-left, top-right, bottom-right, bottom-left.
        """
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    def rectify(self, plate_crop: np.ndarray) -> np.ndarray:
        """Rectify plate crop to standardized dimensions."""
        warped, _ = self.rectify_plate(plate_crop, self.target_width, self.target_height)
        return warped

    def normalize_resolution(self, plate_crop: np.ndarray) -> np.ndarray:
        """Standardized resize without warping."""
        if plate_crop is None or plate_crop.size == 0:
            return plate_crop
        return cv2.resize(plate_crop, (self.target_width, self.target_height), interpolation=cv2.INTER_CUBIC)

    @classmethod
    def rectify_plate(
        cls,
        plate_crop: np.ndarray,
        target_w: int = TARGET_WIDTH,
        target_h: int = TARGET_HEIGHT,
    ) -> Tuple[np.ndarray, bool]:
        """
        Straightens angled license plate crop using 4-point perspective warp.
        Returns: (rectified_image, was_warped)
        """
        if plate_crop is None or plate_crop.size == 0:
            return plate_crop, False

        h, w = plate_crop.shape[:2]
        if h < 14 or w < 30:
            return cv2.resize(plate_crop, (target_w, target_h), interpolation=cv2.INTER_CUBIC), False

        gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY) if len(plate_crop.shape) == 3 else plate_crop
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 200)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

        quad_pts: Optional[np.ndarray] = None
        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            if len(approx) == 4 and cv2.contourArea(c) > (w * h * 0.40):
                quad_pts = approx.reshape(4, 2)
                break

        if quad_pts is not None:
            try:
                rect = cls.order_points(quad_pts.astype("float32"))
                dst = np.array(
                    [
                        [0, 0],
                        [target_w - 1, 0],
                        [target_w - 1, target_h - 1],
                        [0, target_h - 1],
                    ],
                    dtype="float32",
                )
                matrix = cv2.getPerspectiveTransform(rect, dst)
                warped = cv2.warpPerspective(plate_crop, matrix, (target_w, target_h))
                return warped, True
            except Exception as err:
                logger.debug(f"Perspective warp failed: {err}; falling back to resize.")

        # Safe fallback: Standard bilinear resize preserving contents without artificial distortion
        resized = cv2.resize(plate_crop, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
        return resized, False
