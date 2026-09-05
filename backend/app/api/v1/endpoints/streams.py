import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, Response as RawResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.dependencies import get_db
from app.schemas.common import ApiResponse
from app.schemas.stream import (
    CameraStreamCreate,
    CameraStreamUpdate,
    CameraStreamResponse,
)
from app.services.stream_service import StreamService
from app.services.stream_gateway_service import stream_gateway_service

router = APIRouter(tags=["Camera Streams & Ingest"])
stream_service = StreamService()


def find_stream_asset(filename: str) -> Optional[Path]:
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent.parent / "sample_assets" / filename,
        Path(__file__).resolve().parent.parent.parent.parent.parent / "backend" / "sample_assets" / filename,
        Path.cwd() / "sample_assets" / filename,
        Path.cwd() / "backend" / "sample_assets" / filename,
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None

def get_sample_dirs() -> List[Path]:
    dirs = [
        Path(__file__).resolve().parent.parent.parent.parent.parent / "sample_assets",
        Path(__file__).resolve().parent.parent.parent.parent.parent / "backend" / "sample_assets",
        Path.cwd() / "sample_assets",
        Path.cwd() / "backend" / "sample_assets",
    ]
    return [d for d in dirs if d.is_dir()]


import asyncio
import httpx


@router.api_route(
    "/streams/{camera_id}/whep",
    methods=["POST", "OPTIONS", "PATCH", "DELETE"],
    summary="WebRTC WHEP Stream Proxy",
    description="Proxies WebRTC WHEP negotiation directly to low-latency stream gateway for 0-latency live CCTV playback.",
)
async def proxy_whep_stream(
    camera_id: str,
    request: Request,
):
    clean_id = camera_id.strip().lower()
    digits = re.sub(r"\D", "", clean_id)
    stream_id = f"cam{digits.zfill(2)}" if digits else clean_id
    target_url = f"http://103.250.160.189:8889/stream/{stream_id}/whep"

    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS, PATCH, DELETE, GET",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, If-Match",
        "Access-Control-Expose-Headers": "Location, Accept-Post, Link",
    }

    if request.method == "OPTIONS":
        return RawResponse(status_code=204, headers=cors_headers)

    body = await request.body()
    client = await stream_gateway_service.get_http_client()
    auth = None
    if settings.SENTINEL_RTSP_USER and settings.SENTINEL_RTSP_PASSWORD:
        auth = (settings.SENTINEL_RTSP_USER, settings.SENTINEL_RTSP_PASSWORD)

    try:
        upstream_resp = await client.request(
            method=request.method,
            url=target_url,
            content=body,
            headers={
                "Content-Type": request.headers.get("Content-Type", "application/sdp"),
            },
            auth=auth,
            timeout=10.0,
        )
        response_headers = dict(cors_headers)
        if "location" in upstream_resp.headers:
            response_headers["Location"] = upstream_resp.headers["location"]
        if "content-type" in upstream_resp.headers:
            response_headers["Content-Type"] = upstream_resp.headers["content-type"]
        else:
            response_headers["Content-Type"] = "application/sdp"

        return RawResponse(
            content=upstream_resp.content,
            status_code=upstream_resp.status_code,
            headers=response_headers,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"WHEP gateway proxy error: {str(exc)}")


@router.get(
    "/streams/{camera_id}/live.mjpg",
    summary="Live Motion-JPEG Continuous Video Stream",
    description="Streams real-time live frames from RTSP camera feed over continuous HTTP multipart stream.",
)
@router.get("/streams/{camera_id}/live.mjpeg")
async def get_live_mjpeg_stream(
    camera_id: str,
    request: Request,
    fps: int = Query(20, ge=1, le=30),
):
    clean_id = camera_id.strip().lower()
    digits = re.sub(r"\D", "", clean_id)
    stream_id = f"cam{digits.zfill(2)}" if digits else clean_id

    async def frame_generator():
        import cv2
        delay = 1.0 / max(1, fps)
        while True:
            if await request.is_disconnected():
                break
            success, frame, pts, _ = stream_gateway_service.read_camera_frame(stream_id)
            if success and frame is not None and frame.size > 0:
                ret, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                if ret:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
                    )
            await asyncio.sleep(delay)

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get(
    "/streams/{camera_id}/snapshot.jpg",
    summary="Live Camera Snapshot",
    description="Captures and returns the latest live JPEG frame from the RTSP camera stream.",
)
async def get_camera_snapshot_jpg(
    camera_id: str,
    request: Request,
):
    import cv2
    clean_id = camera_id.strip().lower()
    digits = re.sub(r"\D", "", clean_id)
    stream_id = f"cam{digits.zfill(2)}" if digits else clean_id

    success, frame, pts, _ = stream_gateway_service.read_camera_frame(stream_id)
    if success and frame is not None and frame.size > 0:
        ret, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if ret:
            return RawResponse(
                content=jpeg.tobytes(),
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Access-Control-Allow-Origin": "*",
                },
            )
    raise HTTPException(status_code=503, detail="Unable to capture live frame from camera")


@router.api_route(
    "/streams/{camera_id}/live.mp4",
    methods=["GET", "HEAD"],
    summary="[DEMO ONLY] Progressive MP4 Sample Video",
    description="Serves bundled static demo MP4 for local testing only. NOT used for Sentinel live production.",
)
@router.api_route(
    "/streams/{camera_id}/video.mp4",
    methods=["GET", "HEAD"],
    summary="[DEMO ONLY] Progressive MP4 Sample Video",
    description="Serves bundled static demo MP4 for local testing only. NOT used for Sentinel live production.",
)
async def get_live_video_stream(
    camera_id: str,
    request: Request,
):
    clean_id = stream_gateway_service.normalize_camera_id(camera_id)

    headers = {
        "Accept-Ranges": "bytes",
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "X-Stream-Source": "DEMO_SAMPLE_ASSET",
    }

    filenames = [
        f"{clean_id}_sample.mp4",
        f"{clean_id}.mp4",
    ]
    for fn in filenames:
        found = find_stream_asset(fn)
        if found and found.is_file():
            return FileResponse(
                path=str(found),
                media_type="video/mp4",
                headers=headers,
            )

    raise HTTPException(
        status_code=404,
        detail=f"Sample video asset not found for {clean_id}. Production feeds use Sentinel HLS directly: https://cctv.corp8.cloud/{clean_id}/index.m3u8",
    )


@router.get(
    "/streams/{camera_id}/live.m3u8",
    summary="Get Live HLS Playlist for Camera",
    description="Returns dynamic, browser-compatible HLS live manifest with proxied/transcoded chunk routes.",
)
async def get_live_hls_manifest(
    camera_id: str,
    request: Request,
) -> RawResponse:
    manifest_text, content_type = await stream_gateway_service.get_hls_manifest(camera_id)
    return RawResponse(
        content=manifest_text,
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get(
    "/streams/{camera_id}/enc.key",
    summary="Get Live HLS AES-128 Decryption Key",
    description="Proxies AES-128 decryption key from authenticated Sentinel gateway.",
)
async def get_live_hls_key(
    camera_id: str,
    request: Request,
) -> RawResponse:
    key_data, content_type = await stream_gateway_service.get_hls_key(camera_id)
    if not key_data:
        raise HTTPException(status_code=502, detail="Failed to retrieve encryption key from Sentinel gateway")
    return RawResponse(
        content=key_data,
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get(
    "/streams/{camera_id}/segment/{segment_path:path}",
    summary="Get Live Video Chunk / Segment",
    description="Streams binary video segment (.ts or .m4s) directly to the browser HLS player.",
)
async def get_live_hls_segment(
    camera_id: str,
    segment_path: str,
    request: Request,
) -> RawResponse:
    chunk_data, content_type = await stream_gateway_service.get_hls_segment(camera_id, segment_path)
    if not chunk_data:
        raise HTTPException(status_code=404, detail="Segment not found or empty")
    return RawResponse(
        content=chunk_data,
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Cache-Control": "public, max-age=10",
        },
    )


@router.get(
    "/streams/{camera_id}/{segment_name}",
    summary="Get Live Video Chunk / Segment by direct filename",
    description="Streams binary video segment (.ts or .m4s) requested directly by relative or absolute manifest path.",
)
async def get_live_hls_segment_direct(
    camera_id: str,
    segment_name: str,
    request: Request,
) -> RawResponse:
    if not (segment_name.endswith(".ts") or segment_name.endswith(".m4s") or segment_name.endswith(".mp4")):
        raise HTTPException(status_code=404, detail=f"Unrecognized stream asset {segment_name}")
    chunk_data, content_type = await stream_gateway_service.get_hls_segment(camera_id, segment_name)
    if not chunk_data:
        raise HTTPException(status_code=404, detail=f"Segment {segment_name} not found or empty")
    return RawResponse(
        content=chunk_data,
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Cache-Control": "public, max-age=10",
        },
    )


@router.get(
    "/streams/status",
    response_model=ApiResponse[Dict[str, Any]],
    summary="Query Statewide Stream Fleet Status",
    description="Returns aggregate health metrics across all active camera streams.",
)
async def get_all_streams_status(request: Request) -> ApiResponse[Dict[str, Any]]:
    summary = stream_gateway_service.get_gateway_summary()
    req_id = getattr(request.state, "request_id", None)
    return ApiResponse(success=True, data=summary, request_id=req_id)


@router.get(
    "/streams/{camera_id}/status",
    response_model=ApiResponse[Dict[str, Any]],
    summary="Query Live Stream Ingestion Status",
    description="Returns real-time status of stream gateway worker process and upstream connectivity.",
)
async def get_stream_status(
    camera_id: str,
    request: Request,
) -> ApiResponse[Dict[str, Any]]:
    health = await stream_gateway_service.get_stream_health(camera_id)
    req_id = getattr(request.state, "request_id", None)
    return ApiResponse(success=True, data=health, request_id=req_id)


@router.post(
    "/streams/{camera_id}/start",
    response_model=ApiResponse[Dict[str, Any]],
    summary="Start Managed Stream Transcoder / Ingestion",
)
async def start_stream(
    camera_id: str,
    request: Request,
) -> ApiResponse[Dict[str, Any]]:
    stream_info = await stream_gateway_service.resolve_stream(camera_id)
    req_id = getattr(request.state, "request_id", None)
    return ApiResponse(
        success=True,
        data={"message": f"Stream worker started for {camera_id}", "stream_info": stream_info},
        request_id=req_id,
    )


@router.post(
    "/streams/{camera_id}/stop",
    response_model=ApiResponse[Dict[str, Any]],
    summary="Stop Managed Stream Transcoder",
)
async def stop_stream(
    camera_id: str,
    request: Request,
) -> ApiResponse[Dict[str, Any]]:
    stopped = stream_gateway_service.stop_stream(camera_id)
    req_id = getattr(request.state, "request_id", None)
    return ApiResponse(
        success=True,
        data={"stopped": stopped, "camera_id": camera_id},
        request_id=req_id,
    )


# ------------------------------------------------------------------------------
# 2. Database-backed Camera Stream Attachment CRUD (Nested under /cameras/{id}/streams)
# ------------------------------------------------------------------------------

@router.post(
    "/cameras/{camera_id}/streams",
    response_model=ApiResponse[CameraStreamResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Attach Video Stream to Camera",
)
async def create_camera_stream(
    camera_id: uuid.UUID,
    data: CameraStreamCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CameraStreamResponse]:
    created = await stream_service.create_stream(db, camera_id, data)
    req_id = getattr(request.state, "request_id", None)
    return ApiResponse(
        success=True,
        data=CameraStreamResponse.model_validate(created),
        request_id=req_id,
    )


@router.get(
    "/cameras/{camera_id}/streams",
    response_model=ApiResponse[List[CameraStreamResponse]],
    summary="List Video Streams for Camera",
)
async def list_camera_streams(
    camera_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[CameraStreamResponse]]:
    streams = await stream_service.list_camera_streams(db, camera_id)
    req_id = getattr(request.state, "request_id", None)
    return ApiResponse(
        success=True,
        data=[CameraStreamResponse.model_validate(s) for s in streams],
        request_id=req_id,
    )


@router.get(
    "/cameras/{camera_id}/streams/{stream_id}",
    response_model=ApiResponse[CameraStreamResponse],
    summary="Get Stream Configuration",
)
async def get_stream(
    camera_id: uuid.UUID,
    stream_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CameraStreamResponse]:
    stream = await stream_service.get_stream(db, stream_id)
    req_id = getattr(request.state, "request_id", None)
    return ApiResponse(
        success=True,
        data=CameraStreamResponse.model_validate(stream),
        request_id=req_id,
    )


@router.patch(
    "/cameras/{camera_id}/streams/{stream_id}",
    response_model=ApiResponse[CameraStreamResponse],
    summary="Update Stream Parameters",
)
async def update_stream(
    camera_id: uuid.UUID,
    stream_id: uuid.UUID,
    data: CameraStreamUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CameraStreamResponse]:
    updated = await stream_service.update_stream(db, stream_id, data)
    req_id = getattr(request.state, "request_id", None)
    return ApiResponse(
        success=True,
        data=CameraStreamResponse.model_validate(updated),
        request_id=req_id,
    )


@router.delete(
    "/cameras/{camera_id}/streams/{stream_id}",
    response_model=ApiResponse[dict],
    summary="Detach Video Stream",
)
async def delete_stream(
    camera_id: uuid.UUID,
    stream_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    await stream_service.delete_stream(db, stream_id)
    req_id = getattr(request.state, "request_id", None)
    return ApiResponse(
        success=True,
        data={"message": f"Stream {stream_id} deleted successfully."},
        request_id=req_id,
    )
