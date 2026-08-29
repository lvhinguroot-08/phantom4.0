/**
 * PHANTOM Frontend AI Detection API Client
 * Interfaces with backend YOLO26 image, video, and multi-stream endpoints.
 */

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  width: number;
  height: number;
}

export interface DetectedObject {
  detection_id: string;
  camera_id?: string;
  timestamp?: string;
  object_class: string;
  confidence: number;
  bounding_box: BoundingBox;
  inference_time_ms?: number;
  model_name?: string;
  model_version?: string;
}

export interface ImageDetectionResponse {
  objects: DetectedObject[];
  count: number;
  image: string; // Base64 or URL
  camera_id?: string;
  latency_ms?: number;
}

export interface VideoJobResponse {
  job_id: string;
  status: "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";
  progress_percent: number;
  frames_processed: number;
  total_frames: number;
  fps: number;
  elapsed_seconds: number;
  eta_seconds?: number;
  total_detections: number;
  class_breakdown: Record<string, number>;
  download_url?: string;
  error_message?: string;
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const aiDetectionApi = {
  /**
   * Run YOLO26 inference on an uploaded image
   */
  async detectImage(file: File, cameraId: string = "FORENSIC_UPLOAD"): Promise<ImageDetectionResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("camera_id", cameraId);

    const res = await fetch(`${API_BASE}/api/v1/ai/detect/image`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err?.error?.message || err?.detail || "Failed to process image detection.");
    }

    return res.json();
  },

  /**
   * Submit a video for asynchronous frame-by-frame YOLO26 detection
   */
  async submitVideo(file: File, cameraId: string = "FORENSIC_VIDEO"): Promise<{ job_id: string; status: string }> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("camera_id", cameraId);

    const res = await fetch(`${API_BASE}/api/v1/ai/detect/video`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err?.error?.message || err?.detail || "Failed to submit video.");
    }

    return res.json();
  },

  /**
   * Poll status of an async video processing job
   */
  async getVideoJobStatus(jobId: string): Promise<VideoJobResponse> {
    const res = await fetch(`${API_BASE}/api/v1/ai/detect/video/${jobId}`);
    if (!res.ok) {
      throw new Error("Failed to fetch video job status.");
    }
    return res.json();
  },

  /**
   * Get download URL for the annotated video
   */
  getVideoDownloadUrl(jobId: string): string {
    return `${API_BASE}/api/v1/ai/detect/video/${jobId}/download`;
  },
};
