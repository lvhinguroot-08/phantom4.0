"""
YOLO26 Data Schemas & Type Contracts
Standardized Pydantic models for bounding boxes, vehicle attributes, detections, and tracking telemetry.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Normalized (0-100%) or pixel coordinate bounding box."""
    x1: float = Field(..., description="Top-left X coordinate")
    y1: float = Field(..., description="Top-left Y coordinate")
    x2: float = Field(..., description="Bottom-right X coordinate")
    y2: float = Field(..., description="Bottom-right Y coordinate")
    width: float = Field(..., description="Width of bounding box")
    height: float = Field(..., description="Height of bounding box")


class VehicleAttributes(BaseModel):
    """Enriched visual intelligence attributes for detected vehicles and pedestrians."""
    is_vehicle: bool = Field(False, description="True if object is an automotive or 2-wheeler")
    structure_type: Optional[str] = Field(None, description="Body structure (SEDAN, SUV, TRUCK, BUS, etc.)")
    make: Optional[str] = Field(None, description="Estimated manufacturer make (Hyundai, Maruti, etc.)")
    model: Optional[str] = Field(None, description="Estimated vehicle model (Creta, Dzire, etc.)")
    display_name: Optional[str] = Field(None, description="Formatted vehicle title (e.g. Hyundai Creta)")
    color: Optional[str] = Field(None, description="Dominant vehicle color (White, Black, Silver, etc.)")
    color_hex: Optional[str] = Field(None, description="Representative color hex code")
    color_confidence: Optional[float] = Field(None, description="Color estimation confidence score")
    license_plate: Optional[str] = Field(None, description="Detected registration plate string")
    plate_confidence: Optional[float] = Field(None, description="Plate OCR recognition score")
    speed_kmph: Optional[float] = Field(None, description="Estimated speed in km/h from tracking")
    activity: Optional[str] = Field(None, description="Pedestrian activity (Walking, Standing, etc.)")
    helmet_detected: Optional[bool] = Field(None, description="Rider helmet status")
    occupant_count: Optional[int] = Field(None, description="Number of associated occupants for two-wheelers")
    associated_riders: List[int] = Field(default_factory=list, description="Associated rider person track IDs")
    active_violations: List[str] = Field(default_factory=list, description="Active confirmed violations (e.g. NO_HELMET, TRIPLE_RIDING)")
    threat_level: str = Field("NORMAL", description="Threat level (NORMAL, ELEVATED, CRITICAL)")


class TrafficViolationEvent(BaseModel):
    """Canonical traffic violation event representation (Phase 2)."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    violation_type: str = Field(..., description="Violation type: NO_HELMET, TRIPLE_RIDING")
    camera_id: str = Field(..., description="Source camera identifier")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    vehicle_track_id: int = Field(..., description="Target vehicle track ID")
    vehicle_type: str = Field(..., description="MOTORCYCLE, SCOOTER, etc.")
    person_track_ids: List[int] = Field(default_factory=list, description="Associated person track IDs")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall violation confidence")
    severity: str = Field("MEDIUM", description="Violation severity: LOW, MEDIUM, HIGH, CRITICAL")
    status: str = Field("CONFIRMED", description="Violation status: SUSPECTED, CONFIRMED, RESOLVED")
    evidence_reference: Optional[str] = Field(None, description="Path or URI to annotated evidence image")
    rider_track_id: Optional[int] = Field(None, description="Specific rider track ID for single-person violations")
    helmet_state: Optional[str] = Field(None, description="HELMET, NO_HELMET, UNCERTAIN, TURBAN")
    occupant_count: Optional[int] = Field(None, description="Total occupants on vehicle for over-occupancy violations")
    vehicle_plate: Optional[str] = Field(None, description="Linked license plate recognized by ANPR")
    plate_confidence: Optional[float] = Field(None, description="Confidence of linked license plate")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary forensic metadata")


class DetectedObject(BaseModel):
    """Canonical single object detection representation."""
    detection_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    camera_id: str = Field(..., description="Source camera or stream identifier")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    object_class: str = Field(..., description="Canonical class (PERSON, CAR, TRUCK, etc.)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    bounding_box: BoundingBox
    attributes: Optional[VehicleAttributes] = None
    track_id: Optional[int] = Field(None, description="Persistent tracking ID across frames")
    speed_kmph: Optional[float] = None
    direction: Optional[str] = None
    model_name: str = Field("YOLO26", description="Active inference engine name")
    model_version: str = Field("26.0.0", description="Active model version")
    device: str = Field("cpu", description="Compute device (cpu, cuda:0)")
    inference_time_ms: float = Field(0.0, description="Model execution latency")
    is_demo: bool = Field(False, description="Whether detection is synthetic or real")
    is_watchlist_match: bool = Field(False, description="Whether plate or object matched hotlist")
    threat_level: str = Field("NORMAL", description="NORMAL, ELEVATED, CRITICAL")
    raw_class: Optional[str] = None


class DetectionSummary(BaseModel):
    """Aggregated frame detection counters."""
    total_objects: int = 0
    vehicles_count: int = 0
    persons_count: int = 0
    plates_count: int = 0
    critical_alerts: int = 0


class DetectionBatchResult(BaseModel):
    """Complete multi-object detection frame result."""
    type: str = "LIVE_DETECTION_OVERLAY"
    camera_id: str
    frame_seq: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ai_fps: float = 25.0
    latency_ms: float = 0.0
    summary: DetectionSummary = Field(default_factory=DetectionSummary)
    detections: List[DetectedObject] = Field(default_factory=list)


class TrackedVehicleState(BaseModel):
    """Persistent tracker trajectory and state record."""
    track_id: int
    object_class: str
    confidence: float
    bounding_box: BoundingBox
    centroid: Dict[str, float]
    speed_kmph: Optional[float] = None
    direction: str = "UNKNOWN"
    history: List[Dict[str, Any]] = Field(default_factory=list)
    state: str = "ACTIVE"
    first_seen: str
    last_seen: str
