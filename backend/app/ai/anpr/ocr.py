"""
PHANTOM AI ANPR OCR Processor
Integrates EasyOCR with adaptive image enhancement, CLAHE, and Gujarat RTO normalization.
"""
import logging
import threading
from typing import Any, List, Optional, Tuple

import cv2
import numpy as np

from app.ai.anpr.normalize import extract_plate_structure, looks_like_indian_plate, normalize_plate_text
from app.ai.interfaces import OCRProcessor, PlateOCRResult

logger = logging.getLogger("phantom.ai.anpr.ocr")

_GLOBAL_EASYOCR_READER: Optional[Any] = None
_GLOBAL_READER_LOCK = threading.Lock()


def get_shared_easyocr_reader():
    """Singleton getter for EasyOCR Reader to avoid loading PyTorch OCR weights repeatedly."""
    global _GLOBAL_EASYOCR_READER
    if _GLOBAL_EASYOCR_READER is None:
        with _GLOBAL_READER_LOCK:
            if _GLOBAL_EASYOCR_READER is None:
                try:
                    import easyocr
                    import torch
                    use_gpu = torch.cuda.is_available()
                    logger.info(f"Initializing EasyOCR Reader (gpu={use_gpu})...")
                    _GLOBAL_EASYOCR_READER = easyocr.Reader(["en"], gpu=use_gpu, verbose=False)
                    logger.info("EasyOCR Reader successfully initialized.")
                except Exception as exc:
                    logger.warning(f"EasyOCR initialization failed: {exc}")
                    _GLOBAL_EASYOCR_READER = None
    return _GLOBAL_EASYOCR_READER


def preprocess_plate_image(plate_crop: np.ndarray) -> List[np.ndarray]:
    """
    Generate enhanced variations of the plate crop for optimal OCR extraction:
    1. Rescaled BGR image
    2. High-contrast CLAHE grayscale
    3. Bilateral filtered + Adaptive Gaussian thresholded image
    4. Morphological Black-Hat/Top-Hat character edge enhancement
    5. Otsu binarization
    """
    if plate_crop is None or plate_crop.size == 0:
        return []

    h, w = plate_crop.shape[:2]
    if h < 10 or w < 10:
        return []

    variants = []

    # 1. Scale up if crop is small (target height ~100-140px for optimal OCR)
    scale = 1.0
    if h < 100:
        scale = max(1.5, min(4.5, 120.0 / h))
        new_w = int(w * scale)
        new_h = int(h * scale)
        base = cv2.resize(plate_crop, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    else:
        base = plate_crop.copy()
    variants.append(base)

    # 2. CLAHE Contrast Enhanced Grayscale
    gray = None
    try:
        gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY) if len(base.shape) == 3 else base.copy()
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced_gray = clahe.apply(gray)
        variants.append(enhanced_gray)
    except Exception:
        pass

    # 3. Bilateral Filtered (Noise removal while keeping sharp character edges)
    if gray is not None:
        try:
            denoised = cv2.bilateralFilter(gray, d=7, sigmaColor=75, sigmaSpace=75)
            variants.append(denoised)

            # 4. Adaptive Thresholding
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4
            )
            variants.append(thresh)

            # 5. Morphological Top-Hat (Isolate bright characters on dark plate)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
            variants.append(tophat)
        except Exception:
            pass

    return variants


class NullOCRProcessor:
    """Safe fallback when no OCR backend is installed. Does not invent plates."""

    def read_text(self, plate_crop: Any) -> PlateOCRResult:
        return PlateOCRResult(raw_text="", normalized_text="", confidence=0.0)


IGNORED_SIGNAGE_WORDS = {
    "EMISSION", "EMISSIONS", "DIESEL", "PETROL", "CNG", "POLICE", "HIGHWAY",
    "SCHOOL", "BUS", "STOP", "SPEED", "FASTAG", "TURBO", "INDIA", "BHARAT",
    "GOVT", "GOVERNMENT", "PUBLIC", "CARRIER", "ALL", "PERMIT", "NATIONAL"
}


class EasyOCRProcessor:
    """Production EasyOCR processor with image enhancement and syntax scoring."""

    def __init__(self):
        self.reader = get_shared_easyocr_reader()

    def read_text(self, plate_crop: Any) -> PlateOCRResult:
        if plate_crop is None or not isinstance(plate_crop, np.ndarray):
            return PlateOCRResult(raw_text="", normalized_text="", confidence=0.0)

        reader = self.reader or get_shared_easyocr_reader()
        if reader is None:
            return PlateOCRResult(raw_text="", normalized_text="", confidence=0.0)

        variants = preprocess_plate_image(plate_crop)
        if not variants:
            return PlateOCRResult(raw_text="", normalized_text="", confidence=0.0)

        best_raw = ""
        best_norm = ""
        best_conf = 0.0
        best_score = -1.0

        for var_img in variants:
            try:
                results = reader.readtext(var_img)
                if not results:
                    continue

                for res in results:
                    # res format: (bbox, text, confidence)
                    if len(res) < 3:
                        continue
                    text = str(res[1]).strip()
                    conf = float(res[2])

                    clean_raw = "".join(c for c in text if c.isalnum()).upper()
                    if clean_raw in IGNORED_SIGNAGE_WORDS:
                        continue

                    norm = normalize_plate_text(text)
                    if len(norm) < 4 or norm in IGNORED_SIGNAGE_WORDS:
                        continue

                    # Syntax validation
                    is_indian = looks_like_indian_plate(norm)
                    is_gj = norm.startswith("GJ")
                    has_digits = any(c.isdigit() for c in norm)
                    has_letters = any(c.isalpha() for c in norm)

                    if not (has_digits and has_letters):
                        continue  # Plates must contain both state/series letters and numbers

                    score = conf
                    if is_gj:
                        score += 3.0
                    elif is_indian:
                        score += 2.0
                    elif 7 <= len(norm) <= 10:
                        score += 1.0

                    if score > best_score:
                        best_raw = text
                        best_norm = norm
                        best_conf = conf
                        best_score = score

                if best_score > 3.0 and best_conf > 0.60:
                    break  # High confidence hit found
            except Exception as e:
                logger.debug(f"OCR inference on variant error: {e}")

        return PlateOCRResult(
            raw_text=best_raw,
            normalized_text=best_norm,
            confidence=round(best_conf, 4),
        )



def build_ocr_processor(prefer_demo: bool = False) -> OCRProcessor:
    if prefer_demo:
        from app.ai.detection.engines import DemoOCRProcessor
        return DemoOCRProcessor()
    try:
        reader = get_shared_easyocr_reader()
        if reader is not None:
            return EasyOCRProcessor()
        return NullOCRProcessor()
    except Exception:
        return NullOCRProcessor()

