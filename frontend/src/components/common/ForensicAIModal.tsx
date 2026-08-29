import React, { useState, useRef } from "react";
import { aiDetectionApi, DetectedObject, ImageDetectionResponse, VideoJobResponse } from "../../api/aiDetection";

interface ForensicAIModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ForensicAIModal: React.FC<ForensicAIModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<"image" | "video">("image");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [imageResult, setImageResult] = useState<ImageDetectionResponse | null>(null);
  const [videoJob, setVideoJob] = useState<VideoJobResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollIntervalRef = useRef<number | null>(null);

  React.useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const handleClose = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }
    setIsProcessing(false);
    onClose();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setImageResult(null);
      setVideoJob(null);
      setError(null);
    }
  };

  const handleProcessImage = async () => {
    if (!selectedFile) return;
    setIsProcessing(true);
    setError(null);

    try {
      const res = await aiDetectionApi.detectImage(selectedFile);
      setImageResult(res);
    } catch (err: any) {
      setError(err?.message || "Failed to process image with YOLO26.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleProcessVideo = async () => {
    if (!selectedFile) return;
    setIsProcessing(true);
    setError(null);

    try {
      const submitRes = await aiDetectionApi.submitVideo(selectedFile);
      const jobId = submitRes.job_id;

      // Poll video progress
      pollIntervalRef.current = window.setInterval(async () => {
        try {
          const statusRes = await aiDetectionApi.getVideoJobStatus(jobId);
          setVideoJob(statusRes);

          if (statusRes.status === "COMPLETED" || statusRes.status === "FAILED") {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            setIsProcessing(false);
          }
        } catch {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          setIsProcessing(false);
        }
      }, 1500);
    } catch (err: any) {
      setError(err?.message || "Failed to submit video.");
      setIsProcessing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        backgroundColor: "rgba(10, 15, 29, 0.85)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
      }}
    >
      <div
        style={{
          width: "900px",
          maxHeight: "90vh",
          backgroundColor: "#111927",
          border: "1px solid #1e293b",
          borderRadius: "12px",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.6)",
          display: "flex",
          flexDirection: "column",
          color: "#f8fafc",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "16px 24px",
            borderBottom: "1px solid #1e293b",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            backgroundColor: "#0d1522",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "20px" }}>⚡</span>
            <h3 style={{ margin: 0, fontSize: "18px", fontWeight: 700, letterSpacing: "0.5px" }}>
              YOLO26 FORENSIC AI INSPECTOR
            </h3>
          </div>
          <button
            onClick={handleClose}
            style={{
              background: "transparent",
              border: "none",
              color: "#94a3b8",
              fontSize: "20px",
              cursor: "pointer",
            }}
          >
            ✕
          </button>
        </div>

        {/* Tab Selection */}
        <div style={{ display: "flex", borderBottom: "1px solid #1e293b", backgroundColor: "#0b1320" }}>
          <button
            onClick={() => {
              setActiveTab("image");
              setSelectedFile(null);
              setImageResult(null);
            }}
            style={{
              flex: 1,
              padding: "12px",
              background: activeTab === "image" ? "#1e293b" : "transparent",
              border: "none",
              color: activeTab === "image" ? "#38bdf8" : "#94a3b8",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            🖼️ Image Forensics
          </button>
          <button
            onClick={() => {
              setActiveTab("video");
              setSelectedFile(null);
              setVideoJob(null);
            }}
            style={{
              flex: 1,
              padding: "12px",
              background: activeTab === "video" ? "#1e293b" : "transparent",
              border: "none",
              color: activeTab === "video" ? "#38bdf8" : "#94a3b8",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            🎬 Video Ingestion & Tracking
          </button>
        </div>

        {/* Content Body */}
        <div style={{ padding: "24px", overflowY: "auto", flex: 1 }}>
          {error && (
            <div
              style={{
                padding: "12px 16px",
                backgroundColor: "rgba(239, 68, 68, 0.15)",
                border: "1px solid #ef4444",
                borderRadius: "6px",
                color: "#fca5a5",
                marginBottom: "16px",
              }}
            >
              {error}
            </div>
          )}

          {/* File Upload Box */}
          <div
            style={{
              border: "2px dashed #334155",
              borderRadius: "8px",
              padding: "24px",
              textAlign: "center",
              backgroundColor: "#0d1522",
              marginBottom: "20px",
            }}
          >
            <input
              type="file"
              accept={activeTab === "image" ? "image/*" : "video/*"}
              onChange={handleFileChange}
              style={{ display: "none" }}
              id="forensic-file-input"
            />
            <label htmlFor="forensic-file-input" style={{ cursor: "pointer" }}>
              <div style={{ fontSize: "32px", marginBottom: "8px" }}>
                {activeTab === "image" ? "📷" : "🎥"}
              </div>
              <p style={{ margin: 0, fontWeight: 600, color: "#cbd5e1" }}>
                {selectedFile ? selectedFile.name : `Click to choose ${activeTab} file`}
              </p>
              <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#64748b" }}>
                {activeTab === "image" ? "Supports JPG, PNG, WEBP" : "Supports MP4, AVI, MOV"}
              </p>
            </label>
          </div>

          {/* Action Buttons */}
          {selectedFile && (
            <button
              onClick={activeTab === "image" ? handleProcessImage : handleProcessVideo}
              disabled={isProcessing}
              style={{
                width: "100%",
                padding: "12px",
                backgroundColor: isProcessing ? "#475569" : "#0284c7",
                border: "none",
                borderRadius: "6px",
                color: "#ffffff",
                fontWeight: 700,
                cursor: isProcessing ? "not-allowed" : "pointer",
                marginBottom: "20px",
              }}
            >
              {isProcessing
                ? `⚡ Processing with YOLO26...`
                : `Run YOLO26 ${activeTab === "image" ? "Inference" : "Video Analysis"}`}
            </button>
          )}

          {/* Image Results */}
          {imageResult && (
            <div>
              <h4 style={{ color: "#38bdf8", marginTop: 0 }}>
                Detections Found: {imageResult.count}
              </h4>
              <div style={{ display: "flex", gap: "20px" }}>
                <div style={{ flex: 1, backgroundColor: "#020617", borderRadius: "8px", padding: "8px" }}>
                  <img
                    src={imageResult.image.startsWith("data:") ? imageResult.image : `data:image/jpeg;base64,${imageResult.image}`}
                    alt="Annotated"
                    style={{ width: "100%", borderRadius: "4px" }}
                  />
                </div>
                <div style={{ width: "300px", display: "flex", flexDirection: "column", gap: "8px" }}>
                  {imageResult.objects.map((obj, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "10px",
                        backgroundColor: "#1e293b",
                        borderRadius: "6px",
                        borderLeft: "4px solid #38bdf8",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ fontWeight: 700 }}>{obj.object_class}</span>
                        <span style={{ color: "#4ade80" }}>{(obj.confidence * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Video Results & Progress */}
          {videoJob && (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <span>Status: <strong>{videoJob.status}</strong></span>
                <span>{videoJob.progress_percent.toFixed(1)}%</span>
              </div>
              <div
                style={{
                  height: "8px",
                  backgroundColor: "#334155",
                  borderRadius: "4px",
                  overflow: "hidden",
                  marginBottom: "16px",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${videoJob.progress_percent}%`,
                    backgroundColor: "#38bdf8",
                    transition: "width 0.3s",
                  }}
                />
              </div>

              {videoJob.status === "COMPLETED" && videoJob.download_url && (
                <a
                  href={aiDetectionApi.getVideoDownloadUrl(videoJob.job_id)}
                  download
                  style={{
                    display: "block",
                    textAlign: "center",
                    padding: "12px",
                    backgroundColor: "#16a34a",
                    borderRadius: "6px",
                    color: "#ffffff",
                    textDecoration: "none",
                    fontWeight: 700,
                  }}
                >
                  📥 Download Annotated Video ({videoJob.total_detections} Detections)
                </a>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
