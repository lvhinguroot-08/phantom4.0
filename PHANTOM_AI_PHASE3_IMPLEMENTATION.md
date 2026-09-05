# PHANTOM // AI INTELLIGENCE PHASE 3 IMPLEMENTATION REPORT
## ANPR + License Plate Intelligence + Temporal OCR + Production AI Hardening

---

## 1. Executive Summary

Phase 3 concludes the core AI intelligence stack of the PHANTOM Gujarat Police AI CCTV Command Center. Building upon **Phase 1** (YOLO26 detection, Indian vehicle taxonomy, ByteTrack multi-object tracking) and **Phase 2** (spatial rider association, helmet compliance analysis, triple-riding detection, temporal violation engines, and visual evidence capture), **Phase 3** replaces naive, single-frame bottom-percentage cropping with an enterprise-grade, multi-stage Automated Number Plate Recognition (ANPR) and temporal voting subsystem.

Throughout this overhaul, the **Absolute Protection Rule** was strictly preserved: **Zero changes were made to HLS video streaming, stream gateways, camera manifests, segment caches, RTSP ingestion, or browser playback infrastructure**. All 7 HLS streaming and cache preservation verification suites continue to pass 100%.

---

## 2. Component Architecture & End-to-End Pipeline

The Phase 3 ANPR pipeline operates as an integrated module within the high-throughput `YOLO26StreamProcessor`:

```
                           +------------------------------+
                           |  Raw Frame (HLS / Live CCTV) |
                           +--------------+---------------+
                                          |
                                          v
                           +------------------------------+
                           |   YOLO26 Vehicle Detector    |
                           |   & ByteTrack Trajectory     |
                           +--------------+---------------+
                                          |
                                          v
                           +------------------------------+
                           |    Plate Candidate Search    |
                           |   (Dedicated Plate Model /   |
                           |   Vehicle ROI Band Analysis) |
                           +--------------+---------------+
                                          |
                                          v
                           +------------------------------+
                           |   Track-to-Plate Association |
                           |   (Spatial / Mutual Exclusion)
                           +--------------+---------------+
                                          |
                                          v
                           +------------------------------+
                           |   Image Quality Assessment   |
                           |   (Resolution, Blur, Glare)  |
                           +--------------+---------------+
                            /                            \
              [Unreadable: Blur/Low-Res]         [Quality OK]
                          |                               |
                          v                               v
             +-------------------------+    +---------------------------+
             | Flag UNREADABLE         |    | 4-Point Perspective Warp  |
             | (No Hallucinated Plates)|    | & Resolution Normalization|
             +-------------------------+    +-------------+-------------+
                                                          |
                                                          v
                                            +---------------------------+
                                            | Multi-Variant Enhancement |
                                            | (CLAHE / Bilateral Otsu / |
                                            |  Adaptive / Sharpening)   |
                                            +-------------+-------------+
                                                          |
                                                          v
                                            +---------------------------+
                                            |  EasyOCR Character Read   |
                                            +-------------+-------------+
                                                          |
                                                          v
                                            +---------------------------+
                                            | Indian Syntax Normalizer  |
                                            | & Position Disambiguation |
                                            +-------------+-------------+
                                                          |
                                                          v
                                            +---------------------------+
                                            | Multi-Frame Temporal ANPR |
                                            | Voting & Confidence Fusion|
                                            +-------------+-------------+
                                                          |
                                                          v
                                            +---------------------------+
                                            | Track-Aware State Machine |
                                            | & Cooldown Deduplication  |
                                            +-------------+-------------+
                                                          |
                                                          v
                                            +---------------------------+
                                            |  Violation Event Linking  |
                                            | (NO_HELMET / TRIPLE_RIDE) |
                                            +---------------------------+
```

---

## 3. Dedicated Plate Detection vs. Legacy Blind Cropping

### The Defect in Legacy ANPR
Legacy surveillance implementations cropped a static bounding box in the bottom 35% of detected vehicles (`y1 + vh * 0.65`). In real-world Indian traffic scenes, this resulted in:
1. **Severe false positives**: Signage, bumper stickers, radiator grilles, and road markings were fed into OCR.
2. **Missing plates on high-riding commercial vehicles**: Buses, trucks, tempos, and autorickshaws often have off-center or elevated plates.
3. **Severe aspect-ratio distortion**: Slanted or cropped characters caused OCR confusion.

### The Phase 3 Architecture (`plate_detector.py`)
1. **Pluggable Deep Learning Weights**: Configured via `PLATE_MODEL_PATH` or `YOLO_PLATE_MODEL_PATH` to run custom high-accuracy license plate detection models.
2. **Vehicle ROI Morphological Band Localization (Fallback)**:
   - Evaluates the lower 60% of the vehicle ROI.
   - Applies Sobel vertical edge filters to accentuate character stroke density.
   - Executes directional morphological closing (`cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))`).
   - Analyzes contour convex hulls against standard Indian plate aspect ratio constraints ($1.8 \le \text{AR} \le 6.0$) and horizontal centrality weighting.
   - Returns bounded `PlateDetectionResult` containing exact coordinates and high-resolution crops.

---

## 4. 4-Point Perspective Rectification & Image Quality Filtering (`perspective.py`)

### Image Quality Assessment (`PlateQualityAssessor`)
To avoid hallucinated plates and bogus alerts, every crop is assessed prior to OCR:
- **Minimum Dimensions**: Width $\ge 40$ px, Height $\ge 14$ px. Sub-resolution crops return `UNREADABLE`.
- **Blur Variance (Laplacian)**: Crops with $\sigma_{\text{Laplacian}}^2 < 18.0$ are rejected as `SEVERE_BLUR`.
- **Contrast & Illumination**: Pixel standard deviation $< 15.0$ or extreme mean values ($< 25$ dark or $> 240$ glare) are rejected.
- **Strict Non-Fabrication**: Completely unreadable crops return `UNREADABLE` without guessing characters.

### 4-Point Perspective Rectification (`PlatePerspectiveCorrector`)
Angled or skewed plates undergo 4-point quadrilateral rectification:
- Detects plate perimeter contours and approximates quadrilateral vertices via `cv2.approxPolyDP`.
- Enforces topological vertex ordering: top-left, top-right, bottom-right, bottom-left.
- Applies `cv2.getPerspectiveTransform` and `cv2.warpPerspective` to normalize the plate into a crisp, flat $320 \times 96$ px target canvas.
- Gracefully falls back to high-quality cubic interpolation if edge contours are non-quadrilateral.

---

## 5. Multi-Variant Preprocessing Pipeline (`preprocessor.py`)

License plates in Gujarat CCTV feeds encounter harsh midday glare, night sodium lighting, shadows, dust, and rain. `PlateImagePreprocessor` produces complementary representations:
1. **CLAHE Grayscale**: Contrast Limited Adaptive Histogram Equalization (`clipLimit=2.5`, `tileGridSize=(8,8)`), evening out uneven shadows across the plate.
2. **Bilateral Otsu Binarization**: Edge-preserving bilateral filter (`d=7`, $\sigma=50$) combined with Otsu thresholding to segment clean black-on-white/yellow characters.
3. **Adaptive Gaussian Binarization**: Overcomes extreme gradients across wide plates.
4. **Unsharp Masking / Sharpening**: Accentuated high-frequency character boundaries to assist character separation.

---

## 6. Context-Aware Indian Syntax Normalization (`normalize.py`)

Standard string sanitizers globally replace letters with digits, causing severe corruption. Phase 3 introduces **position-specific syntax disambiguation** tailored to the Ministry of Road Transport and Highways (MoRTH) standards:

### Standard State Syntax (`[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{1,4}`)
- **Positions 0–1 (State Code)**: Enforces letters. Disambiguates `0` $\to$ `O`/`G`, `6` $\to$ `G`, `1` $\to$ `I`/`J` (e.g. `6J` automatically corrects to `GJ`).
- **Positions 2–3 (District / RTO Code)**: Enforces digits. Disambiguates `O` $\to$ `0`, `I` $\to$ `1`, `Z` $\to$ `2`, `S` $\to$ `5`, `B` $\to$ `8`.
- **Middle (Series Letters)**: Enforces uppercase alphabets.
- **Suffix (Registration Number)**: Enforces digits (last 1–4 digits). `O` $\to$ `0`, `D` $\to$ `0`, `I` $\to$ `1`, `B` $\to$ `8`.

### Bharat Series (`[0-9]{2}BH[0-9]{4}[A-Z]{1,2}`)
- Handles all-India non-state registration (e.g. `22BH1234AA`), mapping first 2 digits to registration year, preserving `BH`, followed by 4 digits and 1–2 series letters.

### Format Validity Scoring (`score_plate_format`)
- Exact Standard / Bharat Series: `1.0`
- Recognised state prefix with valid digits: `0.85`–`0.90`
- Plausible partial plates: `0.60`–`0.70`
- Arbitrary text / signage noise: `< 0.20`

---

## 7. Multi-Frame Temporal Aggregation & Confidence Fusion (`temporal_anpr.py`)

### Character-Level Sliding Window Voting
Instead of trusting an isolated frame, `TemporalANPRAggregator` retains a sliding window of the last $N$ readings (default $N=8$):
1. **Length Selection**: Computes the statistical mode of candidate lengths.
2. **Positional Voting**: For each character position $i$, candidate characters are weighted by their individual OCR confidence:
   $$\text{Score}(c_i) = \sum_{r \in \text{Readings}} \text{Confidence}(r) \cdot \mathbb{I}(r[i] = c_i)$$
   The highest weighted character is chosen.
3. **Temporal Consistency**: Measures the fraction of window readings in agreement with the consensus plate.

### 5-Factor Composite Confidence Fusion
$$\text{Final Conf} = 0.25 \cdot C_{\text{Det}} + 0.20 \cdot Q_{\text{Image}} + 0.30 \cdot C_{\text{OCR}} + 0.15 \cdot S_{\text{Temporal}} + 0.10 \cdot V_{\text{Format}}$$
- $C_{\text{Det}}$: License plate detector localization score.
- $Q_{\text{Image}}$: Pre-OCR image quality score (sharpness, contrast, resolution).
- $C_{\text{OCR}}$: Raw EasyOCR character extraction confidence.
- $S_{\text{Temporal}}$: Multi-frame voting agreement ratio.
- $V_{\text{Format}}$: Syntax and jurisdiction validity score.

---

## 8. Track-Aware ANPR State Machine & Cooldown (`anpr_state_machine.py`)

Each tracked vehicle transitions through a deterministic state machine:

```
[NO_PLATE] 
    | (Plate localized in vehicle ROI)
    v
[PLATE_DETECTED] 
    | (First OCR reading obtained)
    v
[OCR_OBSERVING] 
    | (2+ consistent readings accumulated)
    v
[PLATE_HYPOTHESIS] 
    | (3+ confirmations, Conf >= 0.55, Format Valid >= 0.40)
    v
[PLATE_CONFIRMED] (Locked in trajectory)
    | (Vehicle track lost > 30 frames)
    v
[TRACK_EXITED] (Evicted from memory)
```

### Duplicate Alert Suppression Cooldown
Alert events are indexed by `(camera_id, plate_text)` with a 60-second cooldown period, preventing redundant alerts while a vehicle remains stationary or queued in traffic.

---

## 9. Violation Event Linking & Privacy Protection

When a Phase 2 violation occurs (`NO_HELMET`, `TRIPLE_RIDING`), the vehicle's persistent `track_id` is queried in the ANPR state machine:
- The confirmed plate number is linked: `viol.vehicle_plate = "GJ05AB1234"`, `viol.plate_confidence = 0.92`.
- Annotated evidence images render a tactical registration badge in the bottom-left corner with the recognized plate string and confidence percentage.
- **Privacy & Non-Inference Rule Enforced**: The system associates *only* the physical registration plate string and visual crop. It does **NOT** infer owner name, driver personal identity, Aadhaar number, or residential address.

---

## 10. Hardware Detection & Production AI Hardening (`hardware_detect.py`)

Provides hardware runtime inspection and dynamic thread allocation:
- Detects CUDA GPUs, Apple Silicon MPS, or multi-core CPUs.
- Allocates optimal PyTorch thread concurrency (`torch.set_num_threads`) for CPU inference.
- Validates ONNX Runtime execution providers (`CUDAExecutionProvider`, `CPUExecutionProvider`).

---

## 11. Test Matrix & Automated Test Suite Results

All 11 automated test suites in `backend/tests/test_phase3_anpr.py` executed and passed:

| Test Case | Objective | Result |
|---|---|:---:|
| `test_clear_daylight_plate_detection` | Daylight vehicle ROI plate localization & contour band detection | **PASS** |
| `test_low_resolution_plate_handling` | Sub-resolution crop ($< 40 \times 14$) rejected as `UNREADABLE` without guessing | **PASS** |
| `test_severe_blur_filtering` | Severe blur ($\sigma^2 < 18.0$) flagged as `UNREADABLE` | **PASS** |
| `test_perspective_rectification` | Skewed quadrilateral transformed to normalized $320 \times 96$ px | **PASS** |
| `test_multi_variant_preprocessing` | CLAHE, Bilateral Otsu, Adaptive Binarization, and Sharpening generation | **PASS** |
| `test_position_specific_disambiguation`| Context-aware substitution (`6J` $\to$ `GJ`, `O` vs `0`, `BH` series) | **PASS** |
| `test_format_validity_scoring` | Standard Gujarat (1.0), Bharat Series (1.0), partial (0.65), gibberish (0.0) | **PASS** |
| `test_temporal_voting_and_fusion` | Sliding-window character voting overcomes sporadic OCR misreadings | **PASS** |
| `test_state_machine_and_cooldown` | Track transitions to `PLATE_CONFIRMED`; duplicate suppression enforced | **PASS** |
| `test_violation_plate_linking_no_identity` | Links `vehicle_plate` to violation event without inferring personal identity | **PASS** |
| `test_hardware_detection` | Dynamic environment discovery and PyTorch thread optimization | **PASS** |

### Complete Regression Verification
- `test_phase1_ai_foundation.py` + `test_phase2_violations.py` + `test_phase3_anpr.py`: **43 / 43 tests PASSED (100%)**.
- `backend/verify_hls_cache_fix.py`: **All 7 HLS streaming and cache preservation suites PASSED**.

---

## 12. Real Footage Validation Findings (`validate_real_footage_anpr.py`)

Executed on `backend/test_traffic_scene.jpg` ($810 \times 1080$ px CCTV frame):
- **Objects Detected**: 4 (1 Commercial Vehicle, 3 Pedestrians)
- **Vehicle Track**: Track #1 (`BUS`, Confidence: 0.87)
- **License Plate Recognized**: `GJ14OR7700` (Gujarat State RTO, RTO jurisdiction: Amreli)
- **Quality Status**: `OK` (High sharpness, rectified to standard $320 \times 96$ px)
- **Pipeline Execution**: Zero runtime errors, zero crash exceptions, clean memory cleanup.

---

## 13. Acceptance Criteria Verification

- [x] **No modification to HLS streaming, stream gateway, manifests, or segment cache**.
- [x] **No blind bottom-35% cropping as primary plate localization**.
- [x] **Dedicated plate detection on vehicle ROI implemented**.
- [x] **Track-aware vehicle ↔ plate association with mutual exclusion implemented**.
- [x] **4-point perspective rectification and aspect ratio normalization active**.
- [x] **Image quality filtering active; unreadable plates return UNREADABLE without guessing**.
- [x] **Multi-variant preprocessing (CLAHE, bilateral, adaptive) active**.
- [x] **Position-specific Indian syntax normalization implemented**.
- [x] **Multi-frame temporal OCR aggregation and 5-factor confidence fusion active**.
- [x] **Track-aware ANPR state machine and cooldown duplicate suppression active**.
- [x] **Visual evidence snapshot with recognized plate badge active**.
- [x] **Phase 2 violation linking without personal identity inference active**.
- [x] **Production runtime detection (GPU/CPU/ONNX) implemented**.
- [x] **Automated test suite (11/11 Phase 3 tests, 43/43 full regression) passing**.
- [x] **Real footage validation verified**.
