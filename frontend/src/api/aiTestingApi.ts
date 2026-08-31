/**
 * PHANTOM 2.0 AI Testing API Client
 * Interfaces with unified backend AI endpoints: /api/upload, /api/process, /api/yolo/detect, /api/anpr/recognize, /api/results/{id}
 */

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  width?: number;
  height?: number;
}

export interface DetectionEvent {
  id: string;
  frame_idx: number;
  timestamp_sec: number;
  time_str: string;
  object_class: string;
  display_name: string;
  confidence: number;
  bounding_box: BoundingBox;
  is_vehicle: boolean;
  vehicle_type?: string;
  license_plate?: string;
  plate_confidence?: number;
  rto_jurisdiction?: string;
  track_id?: number;
}

export interface ANPRTableItem {
  id: string;
  plate_number: string;
  confidence: number;
  time_str: string;
  timestamp_sec: number;
  vehicle: string;
  rto_jurisdiction?: string;
  is_gujarat: boolean;
  first_seen_frame: number;
  last_seen_frame: number;
  total_sightings: number;
}

export interface ObjectAnalytics {
  total_objects_tracked: number;
  unique_vehicles_count: number;
  cars_count: number;
  buses_count: number;
  trucks_count: number;
  motorcycles_count: number;
  pedestrians_count: number;
  bicycles_count: number;
  peak_frame_density: number;
  avg_confidence_pct: number;
  congestion_level: 'LOW' | 'MODERATE' | 'HIGH';
  vehicle_distribution: Record<string, number>;
}

export interface VideoAIJobState {
  job_id: string;
  mode: "yolo" | "anpr" | "yolo_anpr";
  status: "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED" | "CANCELLED";
  progress_percent: number;
  frames_processed: number;
  total_frames: number;
  fps: number;
  processing_fps: number;
  elapsed_seconds: number;
  eta_seconds?: number;
  total_detections: number;
  total_plates_recognized: number;
  class_breakdown: Record<string, number>;
  recent_detections: DetectionEvent[];
  anpr_results: ANPRTableItem[];
  analytics?: ObjectAnalytics;
  latest_frame_b64?: string;
  download_url?: string;
  video_url?: string;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface UploadResponse {
  success: boolean;
  upload_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  file_path: string;
  preview_url?: string;
}

const API_BASE = "";

export const aiTestingApi = {
  /**
   * Upload video or image file
   */
  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/api/upload`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err?.detail || err?.error?.message || "Failed to upload file.");
    }
    return res.json();
  },

  /**
   * Start asynchronous video AI processing
   */
  async startProcessing(params: {
    file?: File;
    uploadId?: string;
    mode: "yolo" | "anpr" | "yolo_anpr";
    sampleFps?: number;
    confidenceThreshold?: number;
    cameraId?: string;
  }): Promise<{ success: boolean; job_id: string; status: string; status_url: string }> {
    const formData = new FormData();
    if (params.file) {
      formData.append("file", params.file);
    }
    if (params.uploadId) {
      formData.append("upload_id", params.uploadId);
    }
    formData.append("mode", params.mode);
    formData.append("sample_fps", String(params.sampleFps || 4.0));
    formData.append("confidence_threshold", String(params.confidenceThreshold || 0.35));
    formData.append("camera_id", params.cameraId || "CAM_SURVEILLANCE_01");

    const res = await fetch(`${API_BASE}/api/process`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err?.detail || err?.error?.message || "Failed to start AI processing.");
    }
    return res.json();
  },

  /**
   * Query status, telemetry, live detections, and ANPR results
   */
  async getJobResults(jobId: string): Promise<VideoAIJobState> {
    const res = await fetch(`${API_BASE}/api/results/${jobId}`);
    if (!res.ok) {
      throw new Error(`Failed to fetch job ${jobId} status.`);
    }
    return res.json();
  },

  /**
   * Stop / abort a running job
   */
  async stopJob(jobId: string): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE}/api/process/${jobId}/stop`, {
      method: "POST",
    });
    if (!res.ok) {
      throw new Error("Failed to stop processing job.");
    }
    return res.json();
  },

  /**
   * Direct YOLO inference on image
   */
  async detectYoloDirect(file: File, confThreshold: number = 0.35) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("confidence_threshold", String(confThreshold));

    const res = await fetch(`${API_BASE}/api/yolo/detect`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("YOLO direct detection failed.");
    return res.json();
  },

  /**
   * Direct ANPR recognition on image
   */
  async recognizeAnprDirect(file: File, confThreshold: number = 0.35) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("confidence_threshold", String(confThreshold));

    const res = await fetch(`${API_BASE}/api/anpr/recognize`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("ANPR direct recognition failed.");
    return res.json();
  },

  /**
   * Fetch 30 real-life Sentinel Gujarat CCTV camera streams
   */
  async getSentinelCameras(): Promise<{ success: boolean; total: number; cameras: Array<{ id: string; name: string; district: string; rtsp_url: string; hls_url: string; webrtc_url: string; has_local_sample: boolean; sample_id: string; }> }> {
    const res = await fetch(`${API_BASE}/api/sample-cameras`);
    if (!res.ok) throw new Error("Failed to fetch Sentinel camera list.");
    return res.json();
  },

  /**
   * Capture real-time live frame from Sentinel camera and run YOLO+ANPR
   */
  async getCameraSnapshot(cameraId: string, confThreshold: number = 0.35) {
    const res = await fetch(`${API_BASE}/api/camera/${cameraId}/snapshot?confidence_threshold=${confThreshold}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err?.detail || "Failed to capture live camera snapshot.");
    }
    return res.json();
  },
};
