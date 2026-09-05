from collections import Counter, defaultdict
from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.ai.anpr.normalize import (
    normalize_plate_text,
    score_plate_format,
    extract_plate_structure,
)


@dataclass
class PlateReading:
    """A single frame's license plate reading and associated metrics."""
    raw_text: str
    normalized_text: str
    ocr_confidence: float
    detection_confidence: float
    quality_score: float
    format_validity: float
    plate_crop: Optional[np.ndarray] = None
    frame_index: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class AggregatedPlateResult:
    """Consolidated result after multi-frame temporal voting and confidence fusion."""
    plate_text: str
    confidence: float
    confirmations: int
    temporal_consistency: float
    format_validity: float
    best_crop: Optional[np.ndarray] = None
    is_confirmed: bool = False
    structural_info: Dict[str, Any] = field(default_factory=dict)


class TemporalANPRAggregator:
    """
    Multi-frame sliding-window temporal aggregator with character-level weighted voting
    and 5-factor confidence fusion.
    """

    def __init__(self, window_size: int = 8, min_confirmations: int = 3, min_confidence: float = 0.55):
        self.window_size = window_size
        self.min_confirmations = min_confirmations
        self.min_confidence = min_confidence
        self.readings: List[PlateReading] = []

    def add_reading(self, reading: PlateReading) -> None:
        """Add a new frame reading and maintain sliding window size."""
        if not reading.normalized_text or reading.normalized_text == "UNREADABLE":
            return
        self.readings.append(reading)
        if len(self.readings) > self.window_size:
            self.readings.pop(0)

    def clear(self) -> None:
        """Clear all stored readings."""
        self.readings.clear()

    def count(self) -> int:
        return len(self.readings)

    def vote(self) -> AggregatedPlateResult:
        """
        Perform character-level weighted voting across sliding window readings
        and compute composite fused confidence.
        """
        if not self.readings:
            return AggregatedPlateResult(
                plate_text="",
                confidence=0.0,
                confirmations=0,
                temporal_consistency=0.0,
                format_validity=0.0,
                is_confirmed=False,
            )

        # 1. Determine most likely plate length
        lengths = [len(r.normalized_text) for r in self.readings]
        length_counts = Counter(lengths)
        target_len, _ = length_counts.most_common(1)[0]

        # Filter readings matching target length (or within +/- 1)
        valid_readings = [r for r in self.readings if len(r.normalized_text) == target_len]
        if not valid_readings:
            valid_readings = self.readings

        # 2. Position-by-position character voting weighted by OCR confidence
        voted_chars = []
        for pos in range(target_len):
            char_weights: Dict[str, float] = defaultdict(float)
            for r in valid_readings:
                if pos < len(r.normalized_text):
                    c = r.normalized_text[pos]
                    char_weights[c] += max(0.1, r.ocr_confidence)
            best_char = max(char_weights.items(), key=lambda x: x[1])[0]
            voted_chars.append(best_char)

        voted_raw_string = "".join(voted_chars)
        # Apply syntax disambiguation on voted string
        resolved_text = normalize_plate_text(voted_raw_string)

        # 3. Calculate temporal consistency
        # Fraction of readings that match the resolved text or have high character similarity
        exact_matches = sum(1 for r in self.readings if r.normalized_text == resolved_text)
        temporal_consistency = exact_matches / len(self.readings)

        # 4. Average metric values from matching or valid readings
        sample_readings = [r for r in self.readings if r.normalized_text == resolved_text]
        if not sample_readings:
            sample_readings = valid_readings

        avg_det_conf = float(np.mean([r.detection_confidence for r in sample_readings]))
        avg_quality = float(np.mean([r.quality_score for r in sample_readings]))
        avg_ocr_conf = float(np.mean([r.ocr_confidence for r in sample_readings]))
        format_validity = score_plate_format(resolved_text)

        # 5. Composite Confidence Fusion Formula:
        # Final Conf = 0.25 * Det Conf + 0.20 * Quality + 0.30 * OCR Conf + 0.15 * Temporal Consistency + 0.10 * Format Validity
        composite_confidence = (
            0.25 * avg_det_conf +
            0.20 * avg_quality +
            0.30 * avg_ocr_conf +
            0.15 * temporal_consistency +
            0.10 * format_validity
        )
        composite_confidence = round(min(1.0, max(0.0, composite_confidence)), 4)

        # 6. Find best crop (highest quality score with matching reading)
        best_reading = max(self.readings, key=lambda r: (r.quality_score, r.ocr_confidence))
        best_crop = best_reading.plate_crop

        # 7. Confirmation criteria
        is_confirmed = (
            len(self.readings) >= self.min_confirmations and
            exact_matches >= max(2, self.min_confirmations - 1) and
            composite_confidence >= self.min_confidence and
            format_validity >= 0.40
        )

        structural_info = extract_plate_structure(resolved_text)

        return AggregatedPlateResult(
            plate_text=resolved_text,
            confidence=composite_confidence,
            confirmations=exact_matches,
            temporal_consistency=round(temporal_consistency, 3),
            format_validity=round(format_validity, 3),
            best_crop=best_crop,
            is_confirmed=is_confirmed,
            structural_info=structural_info,
        )
