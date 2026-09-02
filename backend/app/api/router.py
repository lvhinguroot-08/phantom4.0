from fastapi import APIRouter

from app.api.v1.health import router as system_health_router
from app.api.v1.info import router as info_router
from app.api.v1.endpoints import (
    departments_router,
    districts_router,
    locations_router,
    cameras_router,
    streams_router,
    health_router as camera_health_router,
    gis_router,
    sources_router,
    auth_router,
    users_router,
    detections_router,
    anpr_router,
    vehicles_router,
    sightings_router,
    ai_results_router,
    watchlists_router,
    alerts_router,
    events_router,
    incidents_router,
    investigations_router,
    evidence_router,
    audit_router,
    copilot_router,
)
from app.api.v1.endpoints.image_detection import router as image_detection_router
from app.api.v1.endpoints.video_detection import router as video_detection_router
from app.api.v1.endpoints.webcam_ws import router as webcam_ws_router
from app.api.v1.endpoints.stream_ai_routes import router as stream_ai_router
from app.api.v1.endpoints.vehicle_tracking_api import router as vehicle_tracking_router
from app.api.v1.endpoints.anpr_pipeline_routes import router as anpr_pipeline_router
from app.api.v1.endpoints.live_detection_ws import router as live_detection_ws_router
from app.api.v1.endpoints.unified_ai_routes import router as unified_ai_router

api_v1_router = APIRouter()

# Unified PHANTOM 2.0 AI Testing & Processing Endpoints (/upload, /yolo/detect, /anpr/recognize, /process, /results/{id})
api_v1_router.include_router(unified_ai_router)
api_v1_router.include_router(copilot_router)

api_v1_router.include_router(system_health_router)
api_v1_router.include_router(info_router)

api_v1_router.include_router(departments_router)
api_v1_router.include_router(districts_router)
api_v1_router.include_router(locations_router)
api_v1_router.include_router(cameras_router)
api_v1_router.include_router(streams_router)
api_v1_router.include_router(camera_health_router)
api_v1_router.include_router(gis_router)
api_v1_router.include_router(sources_router)

api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(detections_router)
api_v1_router.include_router(anpr_router)
api_v1_router.include_router(vehicles_router)
api_v1_router.include_router(sightings_router)
api_v1_router.include_router(ai_results_router)
api_v1_router.include_router(watchlists_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(events_router)
api_v1_router.include_router(incidents_router)
api_v1_router.include_router(investigations_router)
api_v1_router.include_router(evidence_router)
api_v1_router.include_router(audit_router)

# YOLO26 Real-Time AI & Tracking Routers
api_v1_router.include_router(image_detection_router)
api_v1_router.include_router(video_detection_router)
api_v1_router.include_router(webcam_ws_router)
api_v1_router.include_router(stream_ai_router)
api_v1_router.include_router(vehicle_tracking_router)
api_v1_router.include_router(anpr_pipeline_router)
api_v1_router.include_router(live_detection_ws_router)


