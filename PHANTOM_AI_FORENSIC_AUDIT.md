# PHANTOM // AI INTELLIGENCE FORENSIC AUDIT REPORT
**System:** PHANTOM Gujarat Police C2 Vision Intelligence Platform  
**Target:** YOLO Detection, Vehicle Classification, Multi-Object Tracking, Helmet Violation, Triple Riding, ANPR  
**Mode:** AUDIT ONLY — FORENSIC DISCOVERY & TECHNICAL BLUEPRINT  
**Audit Timestamp:** 2026-09-05T18:20:00Z  

---

## A. Executive Summary

A comprehensive, forensic audit of the PHANTOM AI surveillance repository was conducted to inspect the end-to-end computer vision pipeline across backend services, model weights, heuristic classifiers, tracking engines, ANPR/OCR routines, API routes, and frontend dashboard overlays.

### Key Audit Findings in Plain Language:
1. **Model Reality vs. Branding:** Despite branding throughout the codebase referencing `YOLO26`, there is **no custom YOLO26 neural network model in the repository**. The system falls back entirely to [`backend/yolov8n.pt`](file:///d:/PHANTOM(final)/backend/yolov8n.pt), an off-the-shelf **Ultralytics YOLOv8 Nano** model trained on standard Microsoft COCO (80 Western everyday object classes).
2. **Missing Essential Indian Traffic Classes:** The underlying neural network has **no concept of an Auto-Rickshaw, Scooter, Helmet, or License Plate**. COCO classes only include generic categories: `person`, `bicycle`, `car`, `motorcycle`, `bus`, and `truck`.
3. **The Heuristic Patchwork:** To simulate fine-grained vehicle classification (e.g., *Honda Activa vs. Hero Splendor*, *Maruti WagonR vs. Swift*, *Auto-Rickshaw vs. Truck*), the developers wrote hand-crafted OpenCV image-processing heuristics (Canny edge filters, pixel aspect-ratio thresholds, and HSV color masks) inside [`specialized_classifiers.py`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/specialized_classifiers.py). These rules fail under changing lighting, camera angles, weather, distance, or non-standard livery, causing severe classification errors and frame-to-frame label flickering.
4. **Active Suppression of Motorcycle Riders:** In [`detector.py`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/detector.py#L216-L234), when a `PERSON` bounding box overlaps (>22%) with a `MOTORCYCLE`, the detector **actively suppresses and deletes the person detection** to avoid bounding box clutter. As a direct consequence, **helmet detection and triple-riding detection cannot function**, because the riders are removed before any rule engine can evaluate them.
5. **Absent Violation Intelligence:** Helmet detection and triple-riding detection **do not exist as functional vision models or rule engines**. Only placeholder database schemas, mock incident cards, and hardcoded dictionary flags exist. Furthermore, the existing alert service triggers high-severity alerts on **any ordinary car or pedestrian detected in the scene** rather than actual traffic or criminal violations.
6. **ANPR Pipeline Disconnect:** The ANPR pipeline relies on EasyOCR, but because the neural network lacks a `LICENSE_PLATE` detector class, the pipeline **blindly crops the bottom 35% of detected vehicles**. This fails for two-wheelers, side views, angled vehicles, and distant traffic. Additionally, there is no multi-frame temporal voting across vehicle tracks.
7. **Footage Pipeline Integrity:** The working HLS video ingestion and streaming pipeline in [`stream_gateway_service.py`](file:///d:/PHANTOM(final)/backend/app/services/stream_gateway_service.py) is operating independently and **has been kept 100% untouched** during this audit.

---

## B. Current Architecture

The actual architecture discovered from the code differs significantly from conceptual documentation:

```
[ CCTV RTSP / HLS Stream ]
            │
            ▼
[ stream_gateway_service.py ]  ───> read_camera_frame() (OpenCV VideoCapture / TCP)
            │
            ▼
[ multi_stream_yolo26.py ]     ───> CameraStreamWorker (Decoupled 1-slot latest frame buffer)
            │
            ▼
[ yolo26/detector.py ]         ───> Loads backend/yolov8n.pt (COCO-80, input 640x640)
            │                       ├── Predicts raw COCO classes: person, car, truck, bus, motorcycle
            │                       └── Hard-Negative Suppressor: DELETES person overlapping motorcycle
            │
            ▼
[ specialized_classifiers.py ] ───> OpenCV Heuristic Secondary Filters (NO NEURAL NETWORKS):
            │                       ├── AutoRickshawDisambiguator (HSV Yellow/Green + Aspect Ratio)
            │                       ├── TwoWheelerSpecializedClassifier (Canny edge density on mid-crop)
            │                       └── CarSpecializedClassifier (Height/Width ratio + Roofline)
            │
            ▼
[ yolo26/tracker.py ]          ───> YOLO26Tracker (Greedy pairwise IoU matching; no Kalman, no Re-ID)
            │
            ▼
[ temporal_fusion.py ]         ───> 3-5 frame rolling vote for label stabilization
            │
            ▼
[ yolo26_alert_service.py ]    ───> Unconditional Alert Generator:
            │                       └── Alerts on any Person, Car, Motorcycle, Truck (no violation rules)
            │
            ▼
[ WebSocket & REST APIs ]      ───> /api/v1/streams/{id}/detections/ws & /detections/live
            │
            ▼
[ DetectionOverlay.tsx ]       ───> Frontend HUD Bounding Box & Label Overlay
```

---

## C. YOLO Audit

| Parameter | Current Configuration | File / Code Location |
| :--- | :--- | :--- |
| **Model Name** | Branded `YOLO26`, actually `yolov8n.pt` | [`model_loader.py:L120-L135`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/model_loader.py#L120-L135) |
| **Model Architecture** | YOLOv8 Nano (Anchor-free, C2f modules, decoupled head) | Ultralytics YOLOv8n (3.2M params) |
| **Model Weights** | `backend/yolov8n.pt` (6.55 MB, MD5 verified) | Physical file in repository |
| **Model Classes** | 80 MS COCO classes (0: person, 1: bicycle, 2: car, 3: motorcycle, 5: bus, 7: truck) | Standard COCO-80 |
| **Custom Training** | **NONE**. Zero fine-tuning weights exist. | No custom `.pt` / `.onnx` files |
| **Inference Resolution** | `640 x 640` (configurable via `YOLO_INPUT_SIZE`, default 640) | [`config.py:L60-L64`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/config.py#L60-L64) |
| **Confidence Threshold**| `0.35` (configurable via `YOLO_CONFIDENCE`, default 0.35) | [`config.py:L46-L51`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/config.py#L46-L51) |
| **IoU Threshold (NMS)** | `0.45` | [`config.py:L53-L58`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/config.py#L53-L58) |
| **Device Execution** | **CPU Only** (`torch.cuda.is_available() == False` on host) | [`model_loader.py:L55-L70`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/model_loader.py#L55-L70) |
| **Preprocessing** | Letterbox padding to 640x640, BGR to RGB normalization | Handled internally by Ultralytics |
| **Postprocessing** | Bounding box clamping, min-dimension filter (`bw < 14 or bh < 14`), aspect ratio filter (`0.25 <= AR <= 4.8`) | [`detector.py:L159-L186`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/detector.py#L159-L186) |
| **Frame Sampling Rate**| `2.0 FPS` default in stream worker; `10-15 FPS` in WebSocket HUD | [`config.py:L93-L98`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/config.py#L93-L98) |
| **Inference Latency** | **135.29 ms** per frame on CPU (~**7.39 FPS** maximum throughput) | Measured via benchmark test |

### Weaknesses in the Current YOLO Layer:
1. **Complete Absence of Indian Domain Classes:** Auto-rickshaws, e-rickshaws, tempos, delivery three-wheelers, helmets, and license plates do not exist in COCO-80.
2. **Small-Object Dropping:** The detector discards any bounding box smaller than 14x14 pixels. In high-mounted junction CCTV cameras, distant vehicles, helmets, and number plates fall below this threshold and are silently omitted.
3. **Class Conflict between Modules:** [`utils.py:L15`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/utils.py#L15) maps `"bike": "BICYCLE"`, while [`classes.py:L27`](file:///d:/PHANTOM(final)/backend/app/ai/postprocessing/classes.py#L27) maps `"bike": "MOTORCYCLE"`. This internal inconsistency leads to contradictory vehicle classification across routes.

---

## D. False Detection Root Causes

| Reported Symptom | Root Cause Component | Exact Technical Mechanism |
| :--- | :--- | :--- |
| **Rickshaw detected as Truck** | **Model & Heuristic** ([`specialized_classifiers.py:L442-L504`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/specialized_classifiers.py#L442-L504)) | Auto-rickshaws do not exist in COCO-80. YOLOv8n classifies their boxy geometry as `truck` or `car`. The code attempts an HSV color check for yellow/green pixels. In overcast weather, at night, or with non-CNG livery (white/black auto), the HSV check fails, leaving the detection as `Truck`. |
| **Bike detected as Taxi** | **Class Aliasing & Heuristic** ([`utils.py:L21`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/utils.py#L21)) | `"taxi": "CAR"` exists in alias dictionaries. When an auto-rickshaw or motorcycle with commercial yellow plates or yellow clothing is detected, or when COCO outputs class 2 (car) for a two-wheeler with side bags, the code attempts to map it through car heuristics, labeling it as a passenger automobile. |
| **Splendor detected as Activa (or vice-versa)** | **Heuristic Classifier** ([`specialized_classifiers.py:L100-L264`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/specialized_classifiers.py#L100-L264)) | No classifier model exists. `TwoWheelerSpecializedClassifier` runs Canny edge detection on the center crop: open floorboard = Activa, high edge density = Splendor. In real traffic, footboard luggage, leg guards, sarees, or riders' feet invert the edge density, causing random flipping between Activa and Splendor. |
| **Unstable labels across consecutive frames** | **Temporal Instability & Edge Sensitivity** ([`temporal_fusion.py:L40-L120`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/temporal_fusion.py#L40-L120)) | The heuristic scores swing from 0.20 to 0.85 as vehicle orientation changes relative to the camera. The 3-frame rolling history in `temporal_fusion.py` is too shallow to prevent rapid flip-flopping. |
| **Duplicate detections** | **NMS & IoU Thresholds** ([`config.py:L53-L58`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/config.py#L53-L58)) | Standard NMS IoU of 0.45 allows co-located predictions of `car` and `truck` for commercial pickups or large SUVs, emitting two overlapping boxes for the same physical vehicle. |
| **Missed vehicles** | **Resolution & Cropping Thresholds** ([`detector.py:L167-L173`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/detector.py#L167-L173)) | Downsampling to 640x640 shrinks distant vehicles. The hardcoded filter `bw < 14 or bh < 14` immediately suppresses them before classification. |
| **Incorrect person association (Riders ignored)** | **Deliberate Suppression Bug** ([`detector.py:L216-L234`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/detector.py#L216-L234)) | Lines 216-234 explicitly add any person overlapping a motorcycle by >22% IoU to `suppressed_indices`, completely deleting them from the frame output. |
| **False alerts (Continuous noise)** | **Alert Service Design** ([`yolo26_alert_service.py:L33-L61`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/yolo26_alert_service.py#L33-L61)) | `YOLO26AlertService` treats basic presence of `PERSON`, `CAR`, or `TRUCK` as an alert event (`PERSON_DETECTED` = HIGH, `CAR_DETECTED` = LOW), flooding the database on routine traffic. |

---

## E. Vehicle Intelligence Gap

### Current Capability:
The current system cannot reliably distinguish Indian vehicle categories. It relies on COCO-80 coarse categories (`car`, `truck`, `bus`, `motorcycle`, `bicycle`) and speculative rule-based guessing for sub-models.

### Why Make/Model Distinction Fails:
Distinguishing a *Hero Splendor* from a *Honda Activa* or a *Maruti WagonR* from a *Swift* using 640x640 CCTV footage via Canny edge detection is technically invalid. In real-world surveillance:
- Distant vehicles occupy only 40x40 to 80x80 pixels.
- Motion blur, perspective distortion, and atmospheric haze destroy sub-pixel edge boundaries.
- Heuristic edge counting cannot generalize across thousands of angles and lighting conditions.

### Minimum Practical Architecture Required:
1. **Primary Detector:** Retrain or fine-tune YOLO (e.g. YOLOv8s or YOLOv11s) with an **Indian Traffic Dataset** featuring 8 native classes:
   `[CAR, AUTO_RICKSHAW, MOTORCYCLE, SCOOTER, BUS, TRUCK, LCV_TEMPO, BICYCLE]`
2. **Eliminate Pseudo-Heuristics:** Deprecate `TwoWheelerSpecializedClassifier` and `CarSpecializedClassifier` heuristics. Let the neural network distinguish motorcycle vs. scooter based on learned visual representations rather than manual Canny thresholds.
3. **Optional Secondary Classification:** For specific make/model (e.g., *WagonR vs. Swift*), deploy a dedicated MobileNetV4 / EfficientNet-B0 classifier operating **only on high-resolution crops (>150x150 px) of tracked vehicles**.

---

## F. Helmet Detection Gap

### Current Status: **DOES NOT EXIST**
- There is no model or script in the repository that detects helmets or bare heads.
- Schema fields exist (`helmet_detected: Optional[bool]` in [`schemas.py`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/schemas.py#L35)), but are hardcoded to `False` in [`vehicle_attributes.py:L296`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/vehicle_attributes.py#L296).
- As noted in Section D, motorcycle riders are actively deleted from detection outputs.

### Recommended Implementation Blueprint:
1. **Stop Suppressing Riders:** Remove lines 216–234 in `detector.py` so that persons riding two-wheelers are preserved and tracked.
2. **Model Architecture:**
   - **Approach A (Recommended):** Unified YOLOv8s model trained with additional classes: `[HELMET, NO_HELMET, HEAD]`.
   - **Approach B (Two-Stage Pipeline):** 
     1. Primary detector detects `MOTORCYCLE`, `SCOOTER`, and `PERSON`.
     2. Spatial matcher associates the `PERSON` box with the two-wheeler track.
     3. Crop the top 25% of the person box (the head region).
     4. Pass the crop to a lightweight binary classifier (YOLOv8n-cls or MobileNetV4) outputting `HELMET` vs. `NO_HELMET` (confidence >= 0.80).
3. **Temporal Verification Rule:**
   - A violation must be confirmed over **at least 5 consecutive tracked frames** (with >= 80% consensus) to prevent false positives from headwear, turbans, or glare.
4. **Evidence Generation:**
   - Crop vehicle + rider + head region, annotate with timestamp, camera ID, and track ID, and push to the evidence store.

---

## G. Triple Riding Gap

### Current Status: **DOES NOT EXIST**
- The repository contains zero logic, schemas, or models for passenger counting on motorcycles.
- Global person counting is inadequate because pedestrians standing near a vehicle would trigger false alarms.

### Recommended Implementation Blueprint:
1. **Spatial Hierarchical Association:**
   - For every tracked `MOTORCYCLE` or `SCOOTER` bounding box $B_{moto}$:
   - Find all tracked `PERSON` bounding boxes $B_{person}$ whose lower boundary intersects or lies within $B_{moto}$.
   - Association criteria:
     $$\text{IoU}(B_{person}, B_{moto}) > 0.15 \quad \text{AND} \quad \text{Centroid}_y(B_{person}) < \text{Bottom}_y(B_{moto})$$
2. **Rider Count Accumulator:**
   - Count the number of associated persons:
     - $N = 1$: Solo Rider (NORMAL)
     - $N = 2$: Pillion Rider (LEGAL / NORMAL)
     - $N \ge 3$: **Triple Riding (VIOLATION)**
3. **Temporal Trajectory Confirmation:**
   - The associated person count must remain $\ge 3$ across **at least 6 frames** within the same vehicle track ID.
   - Prevents momentary false triggers when a pedestrian walks behind a stationary or moving motorcycle.
4. **Evidence Store Integration:**
   - Trigger alert: `VIOLATION_TRIPLE_RIDING` (Severity: HIGH).
   - Capture full frame + zoomed vehicle crop showing all riders.

---

## H. ANPR Forensic Audit

### Current Status: **HYBRID (Flawed Pipeline)**
The repository contains an ANPR module in [`backend/app/ai/anpr/`](file:///d:/PHANTOM(final)/backend/app/ai/anpr/), but it suffers from foundational structural weaknesses:

```
[ Input Frame ]
       │
       ▼
[ yolo26_anpr_pipeline.py ] ──> Detects vehicles via YOLOv8n
       │
       ├──> Checks for 'LICENSE_PLATE' class (NEVER FOUND - class not in COCO)
       │
       ▼
[ Blind Bottom-35% Crop ]   ──> x1 = vx1 + 0.2*vw, y1 = vy1 + 0.65*vh, y2 = vy2
       │
       ▼
[ ocr.py (EasyOCR) ]        ──> Preprocesses crop (CLAHE + Adaptive Threshold)
       │
       ▼
[ normalize.py ]            ──> Normalizes regex (GJ RTO codes, character swapping O/0, I/1)
```

### Flaws in Current ANPR Implementation:
1. **Blind Cropping (No Plate Localization):** Because `yolov8n.pt` has no license plate class, line 84 of `yolo26_anpr_pipeline.py` crops the bottom 35% of the vehicle box. This produces bumper, asphalt, exhaust, and tire crops instead of the actual plate.
2. **Missing Perspective Correction:** No quadrilateral detection or homography transformation (`cv2.warpPerspective`) exists. Angled plates cannot be rectified.
3. **No Temporal Multi-Frame Aggregation:** Each frame is processed as an isolated event. If a character is occluded in one frame, the plate is rejected or corrupted.
4. **Demo Mode Fallback Risk:** [`engines.py:L23`](file:///d:/PHANTOM(final)/backend/app/ai/detection/engines.py#L23) contains `DEMO_PLATE_RAW = "GJ 01 TEST 001"`. When `prefer_demo=True` or when OCR fails, the system outputs synthetic plate numbers rather than reporting unresolvable plates.

---

## I. ANPR Accuracy Improvement Plan

To transition ANPR into a production-grade system:

```
Step 1: Dedicated License Plate Detector (YOLOv8n-plate or YOLOv11n-plate)
        └── Detects high-precision [PLATE] bounding box directly on frame
Step 2: Keypoint / Corner Detection
        └── 4-point corner extraction for perspective rectification
Step 3: Perspective Transformation
        └── Warps skewed plate into a flat 320x96 pixel horizontal strip
Step 4: Enhanced Preprocessing
        └── Bilateral filtering + Contrast Limited Adaptive Histogram Equalization (CLAHE)
Step 5: High-Speed Recognition Engine
        └── PaddleOCR or CRNN / ONNX recognition model with character whitelist [A-Z0-9]
Step 6: Indian Syntax & RTO Disambiguation
        └── Apply existing normalize.py rules (State + RTO + Series + 4 Digits)
Step 7: Multi-Frame Track Voting (Temporal Aggregation)
        └── Aggregate OCR strings across all frames of the same vehicle track ID using character voting
```

---

## J. Tracking Audit

| Feature | Current Status | Finding |
| :--- | :--- | :--- |
| **Tracker Algorithm** | Custom Greedy IoU Tracker | [`tracker.py:L231-L495`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/tracker.py#L231-L495) |
| **Motion Prediction** | **NONE** | No Kalman filter; assumes object is stationary between frames. |
| **Appearance / Re-ID** | **NONE** | No visual embeddings or DeepSORT/BoT-SORT re-identification. |
| **Matching Strategy** | Pairwise IoU $\ge 0.30$ | Highly sensitive to camera frame drops and vehicle velocity. |
| **Track Persistence** | Low | At 2.0 FPS sampling, a vehicle moving at 40 km/h travels ~5.5m between inferences; IoU drops to 0.0, causing **track ID churn**. |
| **Lost Track Handling** | `frames_since_update > 20` | Simple frame counter; no trajectory extrapolation. |
| **Vehicle-Person Association**| **BROKEN** | Persons overlapping two-wheelers are deleted by `detector.py`. |

### Recommendation:
Replace the custom greedy tracker with **ByteTrack** or **BoT-SORT** (both natively supported in Ultralytics). ByteTrack maintains high- and low-confidence detection association with Kalman filter motion prediction, eliminating track fragmentation at low frame rates.

---

## K. Rule Engine Audit

### Current Violation / Alert Logic:
- [`yolo26_alert_service.py`](file:///d:/PHANTOM(final)/backend/app/services/yolo26_alert_service.py) evaluates detections against a cooldown cache (`_cooldown_cache`).
- However, its classification logic triggers on **routine presence**:
  - `PERSON` $\rightarrow$ `PERSON_DETECTED` (Severity: HIGH/MEDIUM)
  - `CAR` $\rightarrow$ `CAR_DETECTED` (Severity: LOW)
  - `TRUCK` $\rightarrow$ `HEAVY_VEHICLE_TRUCK` (Severity: MEDIUM)
  - `BUS` $\rightarrow$ `PUBLIC_TRANSPORT_BUS` (Severity: MEDIUM)
- **Zero traffic violation rules exist.** No checks for speeding, wrong-way driving, red-light running, helmet absence, or triple riding are implemented.

### Required Rule Engine Architecture:
Implement a decoupled rule evaluation engine ([`app/services/violation_rule_engine.py`](file:///d:/PHANTOM(final)/backend/app/services)) evaluating tracked entities:
- `RULE_NO_HELMET`: Two-wheeler track + rider head unhelmeted for $\ge 5$ frames.
- `RULE_TRIPLE_RIDING`: Two-wheeler track + person count $\ge 3$ for $\ge 6$ frames.
- `RULE_WATCHLIST_HIT`: ANPR normalized plate matches active SQL hotlist.
- `RULE_ILLEGAL_PARKING`: Vehicle track stationary in designated restricted polygon for $> 120$ seconds.

---

## L. Performance Audit

### Real Measured Benchmarks (Current CPU Host):
- **Single Frame YOLOv8n Inference Time:** **135.29 ms** (~**7.39 FPS**)
- **CUDA Acceleration:** `False` (Host CPU compute active)
- **Memory Footprint:** ~320 MB baseline + 180 MB model working set

### Concurrency & Scaling Reality:

| Scale | CPU Ingestion Demand (at 2 FPS sample rate) | Feasibility on Current Host |
| :--- | :--- | :--- |
| **1 Camera** | 2 frames/sec $\times$ 135 ms = **270 ms/sec** (~27% of 1 CPU core) | **FEASIBLE** |
| **6 Cameras** | 12 frames/sec $\times$ 135 ms = **1,620 ms/sec** (~1.6 CPU cores) | **FEASIBLE with load pacing** |
| **30 Cameras** | 60 frames/sec $\times$ 135 ms = **8,100 ms/sec** (~8.1 CPU cores) | **SATURATED / FRAMES DROPPED** |
| **60 Cameras** | 120 frames/sec $\times$ 135 ms = **16,200 ms/sec** (~16.2 CPU cores)| **UNSUSTAINABLE on CPU** |

### Recommended Production Hardware Architecture:
- For 30–60 cameras: Dedicated NVIDIA GPU (RTX 4090 or A4000/T4) running TensorRT FP16 / INT8.
- On TensorRT GPU: Inference drops to **4–8 ms** per frame, enabling 120–250 FPS aggregate throughput (supporting 60 cameras at 2–4 FPS easily).

---

## M. Model Architecture Recommendation

The recommended, battle-tested AI stack for PHANTOM:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PHANTOM PRODUCTION AI STACK                     │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Primary Detector: Fine-tuned YOLOv8s (Indian Traffic Edition)       │
│    Classes (10): Person, Car, Auto_Rickshaw, Motorcycle, Scooter,      │
│                  Bus, Truck, LCV, License_Plate, Helmet                │
│    Format: PyTorch (.pt) -> Exported to ONNX / TensorRT Engine         │
├────────────────────────────────────────────────────────────────────────┤
│ 2. Tracking Engine: ByteTrack with Kalman Filter Motion Prediction     │
│    Maintains identity through occlusions & camera frame drops          │
├────────────────────────────────────────────────────────────────────────┤
│ 3. Secondary Intelligence Modules:                                     │
│    a) Helmet & Triple-Riding Verification: Spatial IoU Association     │
│       between Rider Head and Two-Wheeler track                         │
│    b) Plate Recognition (ANPR): Plate Crop -> Perspective Warp ->     │
│       PaddleOCR / CRNN Text Recognition                                │
├────────────────────────────────────────────────────────────────────────┤
│ 4. State Machine Rule Engine: Multi-frame temporal consensus (>= 5     │
│    frames) before committing violation alerts to PostgreSQL DB         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## N. Dataset & Training Requirements

Currently, **no custom training datasets exist** in the repository. The following datasets are required for the next phase:

1. **Indian Traffic Detection Dataset:**
   - ~15,000 annotated images covering: Auto-Rickshaws (Bajaj, Piaggio), Indian two-wheelers (Splendor, Activa, Pulsar), buses (Tata, Ashok Leyland/GSRTC), trucks (Tata Ace, multi-axle), cars.
   - Recommended open sources: *Indian Driving Dataset (IDD)* + custom surveillance snapshots.
2. **Helmet & Rider Dataset:**
   - ~8,000 annotated crops: Riders with ISI standard helmets, full-face helmets, half helmets, bare heads, turbans, dupattas.
3. **Indian License Plate Dataset:**
   - ~10,000 annotated plate crops: High-security registration plates (HSRP), yellow commercial plates, white private plates, green EV plates, Bharat (BH) series plates under varying illumination and tilt.

---

## O. Implementation Roadmap

The implementation must proceed strictly in **THREE sequential phases**:

### PHASE 1: Detection, Vehicle Classification & Tracking Accuracy
- Replace heuristic classification (`TwoWheelerSpecializedClassifier`, `AutoRickshawDisambiguator`, `CarSpecializedClassifier`) with a unified Indian-traffic fine-tuned YOLO model.
- Add `AUTO_RICKSHAW`, `SCOOTER`, and `MOTORCYCLE` directly to the model's output classes.
- Remove the rider deletion bug in `detector.py`.
- Upgrade the custom greedy tracker to ByteTrack with Kalman filter motion prediction.
- Resolve conflicting class aliases in `utils.py` and `classes.py`.

### PHASE 2: Helmet, Triple Riding & Violation Intelligence
- Implement spatial person-vehicle hierarchical binding on two-wheelers.
- Deploy head-region helmet/no-helmet classification with temporal hysteresis ($\ge 5$ frames).
- Deploy passenger counting on two-wheelers for triple-riding detection ($\ge 3$ persons).
- Overhaul `yolo26_alert_service.py` to alert strictly on confirmed violations rather than routine object presence.
- Create automated violation snapshot evidence generation.

### PHASE 3: ANPR, OCR, Temporal Recognition & Production Hardening
- Integrate a dedicated license plate localization head/model to eliminate blind 35% cropping.
- Implement quadrilateral corner extraction and perspective warping (`cv2.warpPerspective`).
- Add multi-frame temporal character voting across tracked vehicle plates.
- Replace or harden EasyOCR with TensorRT/ONNX-accelerated PaddleOCR.
- Export all models to ONNX / TensorRT for high-throughput multi-camera scaling.

---

## P. Files That Must Change (In Future Implementation)

| Component | Exact File Path | Required Changes |
| :--- | :--- | :--- |
| **Model Loader** | [`backend/app/ai/yolo26/model_loader.py`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/model_loader.py) | Load custom fine-tuned weights; remove synthetic fallback. |
| **Object Detector** | [`backend/app/ai/yolo26/detector.py`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/detector.py) | Delete lines 216–234 (rider suppression); remove manual heuristic calls. |
| **Class Taxonomy** | [`backend/app/ai/yolo26/hierarchy.py`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/hierarchy.py) | Align taxonomy with trained neural network classes. |
| **Class Utilities** | [`backend/app/ai/yolo26/utils.py`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/utils.py) | Fix `"bike"` alias conflict; align with `postprocessing/classes.py`. |
| **Tracking Engine** | [`backend/app/ai/yolo26/tracker.py`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/tracker.py) | Integrate ByteTrack / Kalman filter; add person-vehicle binding. |
| **Specialized Classifiers** | [`backend/app/ai/yolo26/specialized_classifiers.py`](file:///d:/PHANTOM(final)/backend/app/ai/yolo26/specialized_classifiers.py) | Deprecate hand-crafted Canny/HSV heuristics. |
| **ANPR Pipeline** | [`backend/app/ai/anpr/yolo26_anpr_pipeline.py`](file:///d:/PHANTOM(final)/backend/app/ai/anpr/yolo26_anpr_pipeline.py) | Replace blind cropping with genuine plate detector bounding boxes. |
| **ANPR OCR Engine** | [`backend/app/ai/anpr/ocr.py`](file:///d:/PHANTOM(final)/backend/app/ai/anpr/ocr.py) | Add perspective rectification and multi-frame temporal voting. |
| **Alert Service** | [`backend/app/services/yolo26_alert_service.py`](file:///d:/PHANTOM(final)/backend/app/services/yolo26_alert_service.py) | Replace object presence alerts with violation state machines. |
| **Stream Ingestion** | [`backend/app/services/multi_stream_yolo26.py`](file:///d:/PHANTOM(final)/backend/app/services/multi_stream_yolo26.py) | Connect violation rule engine to event publisher. |

---

## Q. Files That Must NOT Change

The working camera stream, playback, and reverse-proxy infrastructure **must remain completely untouched**:

- [`backend/app/services/stream_gateway_service.py`](file:///d:/PHANTOM(final)/backend/app/services/stream_gateway_service.py) (HLS proxy, RTSP ingestion, manifest generation)
- [`backend/app/api/v1/endpoints/streams.py`](file:///d:/PHANTOM(final)/backend/app/api/v1/endpoints/streams.py) (HLS playlist and segment delivery)
- [`backend/manifest_cache/`](file:///d:/PHANTOM(final)/backend/manifest_cache) (HLS manifests & decryption keys)
- [`backend/segment_cache/`](file:///d:/PHANTOM(final)/backend/segment_cache) (MPEG-TS media segments)
- [`camera_sources.yaml`](file:///d:/PHANTOM(final)/camera_sources.yaml) (Camera registry and stream definitions)
- [`frontend/src/components/camera/CameraPlayer.tsx`](file:///d:/PHANTOM(final)/frontend/src/components/camera/CameraPlayer.tsx) (HLS.js player rendering)

---

## R. Risk Assessment

| Proposed Major Change | Inherent Risk | Dependency | Expected Benefit | Rollback Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **Replacing Heuristics with Fine-Tuned Model** | Higher GPU/CPU memory if model size increases. | Dataset availability & training pipeline. | Eliminates Auto-as-Truck and Splendor-as-Activa misclassifications; stable labels. | Maintain `yolov8n.pt` as a secondary fallback in `model_loader.py`. |
| **Removing Rider Suppression** | Temporary increase in overlapping bounding boxes. | Bounding box rendering in `DetectionOverlay.tsx`. | Enables helmet and passenger detection on two-wheelers. | Re-enable suppression flag via config variable `SUPPRESS_MOTO_RIDERS`. |
| **Upgrading Tracker to ByteTrack** | Minor increase in compute per frame for Kalman filter. | NumPy / SciPy linear assignment library. | Eliminates track ID churn and maintains persistence through occlusion. | Keep `YOLO26Tracker` class available via configuration switch. |
| **Plate Localization Head** | Two-stage model inference latency. | High-resolution input crops. | 90%+ improvement in OCR accuracy by eliminating non-plate bumper crops. | Fall back to vehicle ROI if plate detector confidence < 0.30. |

---

## S. Verification Plan

When implementation begins, each phase will be verified against real PHANTOM footage:

1. **Phase 1 Verification:**
   - Ingest static test images ([`backend/test_traffic_scene.jpg`](file:///d:/PHANTOM(final)/backend/test_traffic_scene.jpg), [`bus.jpg`](file:///d:/PHANTOM(final)/bus.jpg)) and live stream `cam01`–`cam30`.
   - Verify that three-wheelers are identified as `AUTO_RICKSHAW` with 0% misclassification as `TRUCK`.
   - Verify that Hero Splendor and Honda Activa maintain consistent labels for $\ge 20$ consecutive frames without flipping.
   - Run `benchmark_yolo26_pipeline.py` to confirm inference latency remains $< 150$ ms on CPU / $< 15$ ms on GPU.
2. **Phase 2 Verification:**
   - Execute test video sequence containing unhelmeted motorcycle riders.
   - Confirm `RULE_NO_HELMET` generates an alert only after 5 consecutive confirmed unhelmeted frames.
   - Test triple-riding footage: confirm alert triggers if and only if $\ge 3$ persons overlap the two-wheeler track.
3. **Phase 3 Verification:**
   - Run `tests/unit/test_anpr_pipeline.py` on real Gujarat plate samples (`GJ01...`, `GJ05...`).
   - Validate that plate crops contain only the license plate rectangle (no vehicle body/tires).
   - Validate character accuracy $\ge 92\%$ on clean daytime footage.
