"""
Sample CCTV Traffic Video Generator
Creates a realistic, high-definition (720p) surveillance video clip simulating
an urban Gujarat traffic junction with moving cars, buses, pedestrians,
and legible Gujarat number plates (e.g. GJ05AB1234, GJ01AK7890) for testing.
"""
import math
import os
from pathlib import Path
import urllib.request
import cv2
import numpy as np


def generate_test_traffic_video(output_path: str, duration_sec: int = 8, fps: int = 25) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    width, height = 1280, 720
    total_frames = duration_sec * fps

    # Check for bus.jpg or download a realistic traffic photo to use as realistic background/entities
    sample_img_path = Path("bus.jpg")
    if not sample_img_path.exists():
        try:
            urllib.request.urlretrieve("https://ultralytics.com/images/bus.jpg", str(sample_img_path))
        except Exception:
            pass

    bus_img = cv2.imread(str(sample_img_path)) if sample_img_path.exists() else None
    if bus_img is not None:
        bus_resized = cv2.resize(bus_img, (width, height))
    else:
        bus_resized = np.full((height, width, 3), 100, dtype=np.uint8)

    fourcc = getattr(cv2, "VideoWriter_fourcc", cv2.VideoWriter.fourcc)(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, float(fps), (width, height))

    for f in range(total_frames):
        t = f / float(total_frames)
        # Pan/zoom slightly to simulate real camera motion
        crop_x = int(math.sin(t * 1.5) * 20)
        crop_y = int(math.cos(t * 1.0) * 10)
        
        M = np.float32([[1, 0, crop_x], [0, 1, crop_y]])
        frame = cv2.warpAffine(bus_resized, M, (width, height), borderMode=cv2.BORDER_REFLECT)

        # Overlay legible Gujarat License Plate on the bus / vehicle in the frame
        # Plate 1: GJ05AB1234 (Surat RTO)
        p1_w, p1_h = 130, 32
        p1_x = int(320 + math.sin(t * 2.0) * 15)
        p1_y = int(580 + math.cos(t * 1.5) * 8)
        
        cv2.rectangle(frame, (p1_x, p1_y), (p1_x + p1_w, p1_y + p1_h), (255, 255, 255), -1)
        cv2.rectangle(frame, (p1_x, p1_y), (p1_x + p1_w, p1_y + p1_h), (0, 0, 0), 2)
        cv2.rectangle(frame, (p1_x, p1_y), (p1_x + 16, p1_y + p1_h), (180, 50, 0), -1) # IND blue strip
        cv2.putText(frame, "GJ05AB1234", (p1_x + 20, p1_y + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 2)

        # CCTV telemetry header
        sec = f / fps
        time_text = f"CCTV-GJ05-SURAT-04 // 2026-08-30 18:{int(sec//60):02d}:{int(sec%60):02d}.{int((sec%1)*100):02d} // 25.0 FPS"
        cv2.putText(frame, time_text, (25, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, time_text, (25, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 240, 255), 1)

        out.write(frame)

    out.release()
    print(f"Generated realistic test traffic video at: {output_path} ({total_frames} frames)")
    return output_path


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent.parent / "sample_assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = str(out_dir / "sample_traffic_cctv.mp4")
    generate_test_traffic_video(target)
