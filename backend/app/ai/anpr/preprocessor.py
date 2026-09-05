import cv2
import numpy as np
from typing import List, Tuple, Optional


class PlateImagePreprocessor:
    """
    Multi-variant preprocessing pipeline for license plate crops to optimize OCR character extraction.
    Generates complementary image representations to handle difficult lighting, contrast, and noise:
    1. Grayscale + CLAHE (enhanced contrast across uneven illumination)
    2. Bilateral Filter + Adaptive Thresholding (crisp binarized characters, edge-preserving)
    3. Unsharp Masking / Sharpening (recovering edge definition on soft crops)
    4. Contrast-Normalized Standard Grayscale
    """

    def __init__(self, target_width: int = 320, target_height: int = 96):
        self.target_width = target_width
        self.target_height = target_height
        self._clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))

    def ensure_standard_size(self, img: np.ndarray) -> np.ndarray:
        """Resize to standardized OCR dimensions (320x96) if necessary."""
        h, w = img.shape[:2]
        if w == self.target_width and h == self.target_height:
            return img
        return cv2.resize(img, (self.target_width, self.target_height), interpolation=cv2.INTER_CUBIC)

    def preprocess_best(self, plate_img: np.ndarray) -> np.ndarray:
        """
        Produce single best balanced representation (CLAHE contrast-enhanced grayscale).
        """
        if plate_img is None or plate_img.size == 0:
            return plate_img

        resized = self.ensure_standard_size(plate_img)
        if len(resized.shape) == 3 and resized.shape[2] == 3:
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        else:
            gray = resized.copy()

        enhanced = self._clahe.apply(gray)
        return enhanced

    def generate_variants(self, plate_img: np.ndarray) -> List[Tuple[str, np.ndarray]]:
        """
        Generate multiple processed variations of the plate crop for multi-pass OCR voting.
        Returns:
            List of (variant_name, processed_image)
        """
        if plate_img is None or plate_img.size == 0:
            return []

        resized = self.ensure_standard_size(plate_img)
        if len(resized.shape) == 3 and resized.shape[2] == 3:
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        else:
            gray = resized.copy()

        variants = []

        # 1. CLAHE Contrast Enhanced
        clahe_img = self._clahe.apply(gray)
        variants.append(("clahe", clahe_img))

        # 2. Bilateral Filter + Otsu Binarization
        bilateral = cv2.bilateralFilter(gray, d=7, sigmaColor=50, sigmaSpace=50)
        _, otsu_bin = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(("otsu_bin", otsu_bin))

        # 3. Adaptive Gaussian Thresholding (handles shadows across plate)
        adaptive_bin = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 19, 9
        )
        variants.append(("adaptive_bin", adaptive_bin))

        # 4. Sharpened / Unsharp Mask
        gaussian_blur = cv2.GaussianBlur(gray, (0, 0), 2.0)
        sharpened = cv2.addWeighted(gray, 1.5, gaussian_blur, -0.5, 0)
        variants.append(("sharpened", sharpened))

        return variants


_preprocessor_singleton: Optional[PlateImagePreprocessor] = None


def get_plate_preprocessor() -> PlateImagePreprocessor:
    global _preprocessor_singleton
    if _preprocessor_singleton is None:
        _preprocessor_singleton = PlateImagePreprocessor()
    return _preprocessor_singleton
