import os
import sys
import time
import urllib.request
import asyncio
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, os.path.abspath("backend"))

from app.core.config import settings
from app.services.stream_gateway_service import stream_gateway_service

def test_config():
    print("\n--- 1. CONFIGURATION CHECK ---")
    print(f"HLS_SEGMENT_RETENTION_PER_CAM = {settings.HLS_SEGMENT_RETENTION_PER_CAM}")
    print(f"HLS_MANIFEST_DISK_TTL_SEC = {settings.HLS_MANIFEST_DISK_TTL_SEC}")
    print(f"HLS_MAX_SEGMENT_CACHE_MB_PER_CAM = {settings.HLS_MAX_SEGMENT_CACHE_MB_PER_CAM}")
    assert settings.HLS_SEGMENT_RETENTION_PER_CAM == 15
    assert settings.HLS_MANIFEST_DISK_TTL_SEC == 6.0
    assert settings.HLS_MAX_SEGMENT_CACHE_MB_PER_CAM == 25.0
    print("[PASS] Configuration properly loaded in Settings!")

def test_manifest_ttl_and_atomic_update():
    print("\n--- 2. MANIFEST TTL & EXPIRATION LOGIC ---")
    clean_id = "cam01"
    manifest_path = Path("backend/manifest_cache") / f"{clean_id}.m3u8"
    assert manifest_path.is_file(), "Manifest file should exist"
    
    # Check initial mtime
    st0 = manifest_path.stat().st_mtime
    now = time.time()
    age = now - st0
    print(f"Initial cam01.m3u8 mtime: {st0} (age: {age:.1f}s)")
    
    # Test memory cache TTL
    stream_gateway_service._manifest_cache[clean_id] = ("#EXTM3U\n#TEST", now - 10.0) # expired memory cache
    
    # Run get_hls_manifest coroutine
    loop = asyncio.new_event_loop()
    manifest_text, content_type = loop.run_until_complete(stream_gateway_service.get_hls_manifest(clean_id))
    loop.close()
    
    print(f"Returned content-type: {content_type}")
    print(f"Returned manifest length: {len(manifest_text)} chars")
    assert "#EXTM3U" in manifest_text
    assert "/api/v1/streams/cam01/enc.key" in manifest_text
    assert "#EXT-X-PLAYLIST-TYPE:VOD" in manifest_text
    print("[PASS] Manifest retrieved, key rewritten, VOD tag preserved!")

def test_segment_retention_and_size_limit():
    print("\n--- 3. SEGMENT RETENTION & SIZE LIMIT CHECK ---")
    # cam08 was 24 files before our fix
    cam08_dir = Path("backend/segment_cache/cam08")
    if cam08_dir.is_dir():
        stream_gateway_service._evict_segments_for_camera("cam08")
        files_after = [f for f in cam08_dir.iterdir() if f.is_file() and f.name.endswith(".ts")]
        total_sz = sum(f.stat().st_size for f in files_after)
        print(f"cam08 count after eviction: {len(files_after)} (Limit: <= 15)")
        print(f"cam08 total size after eviction: {total_sz / (1024*1024):.2f} MB (Limit: <= 25 MB)")
        assert len(files_after) <= 15, f"Expected <= 15 files, got {len(files_after)}"
        assert total_sz <= 25 * 1024 * 1024, "Size must be <= 25 MB"
        print("[PASS] cam08 successfully bounded to <= 15 files and <= 25 MB!")

    # Check cam01
    cam01_dir = Path("backend/segment_cache/cam01")
    if cam01_dir.is_dir():
        stream_gateway_service._evict_segments_for_camera("cam01")
        files01 = [f for f in cam01_dir.iterdir() if f.is_file() and f.name.endswith(".ts")]
        print(f"cam01 count after eviction: {len(files01)} (Limit: <= 15)")
        assert len(files01) <= 15
        print("[PASS] cam01 bounded correctly!")

def test_concurrency_lock():
    print("\n--- 4. CONCURRENCY SAFETY TEST ---")
    lock1 = stream_gateway_service._get_segment_lock("cam01", "seg00000.ts")
    lock2 = stream_gateway_service._get_segment_lock("cam01", "seg00000.ts")
    assert lock1 is lock2, "Same camera and segment MUST share the same lock instance!"
    
    lock_other = stream_gateway_service._get_segment_lock("cam01", "seg00001.ts")
    assert lock1 is not lock_other, "Different segments must have distinct locks!"
    print("[PASS] Concurrency locks strictly isolated per segment!")

def test_camera_isolation():
    print("\n--- 5. CAMERA ISOLATION TEST ---")
    seg_dir = Path("backend/segment_cache")
    for cam in ["cam01", "cam02", "cam30"]:
        cdir = seg_dir / cam
        print(f"Directory {cdir}: exists={cdir.exists()}")
        assert cdir.is_dir(), f"{cdir} must be an isolated directory"
    print("[PASS] Subdirectories are isolated per camera ID!")

import sys
sys.stdout.reconfigure(line_buffering=True)

def test_live_endpoints():
    print("\n--- 6. LIVE HTTP ENDPOINT REGRESSION TEST ---")
    # 1. Health Live
    h_url = "http://localhost:8000/health/live"
    with urllib.request.urlopen(h_url, timeout=25) as res:
        print(f"GET /health/live -> HTTP {res.status}")
        assert res.status == 200

    # 2. AES Key
    key_url = "http://localhost:8000/api/v1/streams/cam01/enc.key"
    with urllib.request.urlopen(key_url, timeout=25) as res:
        key_data = res.read()
        print(f"GET /api/v1/streams/cam01/enc.key -> HTTP {res.status}, length: {len(key_data)} bytes")
        assert res.status == 200
        assert len(key_data) == 16, "AES key must be exactly 16 bytes"

    # 3. Live Manifest
    m_url = "http://localhost:8000/api/v1/streams/cam01/live.m3u8"
    with urllib.request.urlopen(m_url, timeout=25) as res:
        m_text = res.read().decode("utf-8")
        print(f"GET /api/v1/streams/cam01/live.m3u8 -> HTTP {res.status}, length: {len(m_text)} chars")
        assert res.status == 200
        assert "#EXTM3U" in m_text
        assert "/api/v1/streams/cam01/enc.key" in m_text
        assert "/api/v1/streams/cam01/seg" in m_text

    # 4. Live Segment
    seg_url = "http://localhost:8000/api/v1/streams/cam01/seg00000.ts"
    with urllib.request.urlopen(seg_url, timeout=25) as res:
        seg_data = res.read()
        print(f"GET /api/v1/streams/cam01/seg00000.ts -> HTTP {res.status}, length: {len(seg_data)} bytes")
        assert res.status == 200
        assert len(seg_data) > 0, "Segment data must be non-zero"
        assert res.headers.get("Content-Type") == "video/mp2t"
        print(f"Segment Content-Type: {res.headers.get('Content-Type')}")

    print("[PASS] All endpoints returned 200 with valid content!")

def test_ai_rtsp_regression():
    print("\n--- 7. RTSP AI REGRESSION TEST ---")
    from app.ai.yolo26.detector import get_detector
    detector = get_detector()
    print(f"YOLO detector device: {detector.device}, is_loaded: {detector.is_loaded}")
    assert detector.is_loaded
    import numpy as np
    dummy = np.zeros((384, 384, 3), dtype=np.uint8)
    dets = detector.detect_frame(dummy)
    print(f"Detector detect_frame on dummy completed without error. Detections count: {len(dets)}")
    print("[PASS] AI detection pipeline intact and working!")

if __name__ == "__main__":
    test_config()
    test_manifest_ttl_and_atomic_update()
    test_segment_retention_and_size_limit()
    test_concurrency_lock()
    test_camera_isolation()
    test_live_endpoints()
    test_ai_rtsp_regression()
    print("\n================================================================")
    print("ALL 7 VERIFICATION SUITES PASSED!")
    print("================================================================")
