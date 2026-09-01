import os
from pathlib import Path
import re
from typing import Any, Dict, List
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, Response as RawResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

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


# ------------------------------------------------------------------------------
# 1. Direct Live Stream Gateway Endpoints (Video / HLS / Proxy / Lifecycle)
# ------------------------------------------------------------------------------

@router.get(
    "/streams/{camera_id}/video.mp4",
    summary="Get Direct Live Video Stream for Camera",
    description="Streams binary MP4 CCTV footage directly to the browser player with HTTP 206 partial content support.",
)
async def get_live_video_stream(
    camera_id: str,
    request: Request,
):
    video_path = stream_gateway_service.get_camera_video_path(camera_id)
    if not video_path or not video_path.is_file():
        candidates = [
            Path(__file__).resolve().parent.parent.parent.parent / "sample_assets" / "sample_traffic_cctv.mp4",
            Path(__file__).resolve().parent.parent.parent.parent.parent / "sample_assets" / "sample_traffic_cctv.mp4",
        ]
        for c in candidates:
            if c.is_file():
                video_path = c
                break

    if not video_path or not video_path.is_file():
        raise HTTPException(status_code=404, detail="Camera video footage not found.")

    file_size = video_path.stat().st_size
    range_header = request.headers.get("Range") or request.headers.get("range")

    if range_header:
        range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
            start = max(0, min(start, file_size - 1))
            end = max(start, min(end, file_size - 1))
            chunk_length = (end - start) + 1

            def iter_file(path_obj: Path, offset: int, length: int):
                with open(path_obj, "rb") as f:
                    f.seek(offset)
                    rem = length
                    while rem > 0:
                        buf = f.read(min(rem, 64 * 1024))
                        if not buf:
                            break
                        rem -= len(buf)
                        yield buf

            return StreamingResponse(
                iter_file(video_path, start, chunk_length),
                status_code=status.HTTP_206_PARTIAL_CONTENT,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(chunk_length),
                    "Content-Type": "video/mp4",
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "public, max-age=3600",
                },
            )

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600",
        },
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
    return RawResponse(
        content=chunk_data,
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "*",
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
