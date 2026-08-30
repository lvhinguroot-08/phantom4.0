import React, { useState, useEffect, useRef } from 'react';
import {
  Play,
  Square,
  Upload,
  Video,
  Shield,
  Car,
  User,
  Cpu,
  Layers,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Download,
  Search,
  Activity,
  Sliders,
  Radio,
  FileVideo,
  Eye,
} from 'lucide-react';
import {
  aiTestingApi,
  DetectionEvent,
  ANPRTableItem,
  VideoAIJobState,
} from '../../api/aiTestingApi';

export const AITestingDashboard: React.FC = () => {
  // AI Agent Mode: YOLO, ANPR, or YOLO + ANPR
  const [aiMode, setAiMode] = useState<'yolo' | 'anpr' | 'yolo_anpr'>('yolo_anpr');
  const [selectedSource, setSelectedSource] = useState<'upload' | 'sample'>('sample');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string>('');

  // Configuration Sliders
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.30);
  const [sampleFps, setSampleFps] = useState<number>(5.0);

  // Processing State & Job Telemetry
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [jobState, setJobState] = useState<VideoAIJobState | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Table Filter
  const [tableSearch, setTableSearch] = useState<string>('');

  const pollIntervalRef = useRef<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const videoPlayerRef = useRef<HTMLVideoElement | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setUploadedFile(file);
      setUploadedFileName(file.name);
      setSelectedSource('upload');
      setErrorMsg(null);
    }
  };

  const handleStartProcessing = async () => {
    setErrorMsg(null);
    setIsProcessing(true);
    setJobState(null);

    try {
      let res;
      if (selectedSource === 'upload') {
        if (!uploadedFile) {
          setErrorMsg('Please choose a video file to upload or select sample CCTV footage.');
          setIsProcessing(false);
          return;
        }
        res = await aiTestingApi.startProcessing({
          file: uploadedFile,
          mode: aiMode,
          sampleFps: sampleFps,
          confidenceThreshold: confidenceThreshold,
        });
      } else {
        // Pre-bundled sample traffic footage
        res = await aiTestingApi.startProcessing({
          uploadId: 'SAMPLE_TRAFFIC',
          mode: aiMode,
          sampleFps: sampleFps,
          confidenceThreshold: confidenceThreshold,
        });
      }

      const jobId = res.job_id;
      setCurrentJobId(jobId);

      // Connect WebSocket for high-frequency live frame preview & events
      connectJobWebSocket(jobId);

      // Fallback interval polling
      pollIntervalRef.current = window.setInterval(async () => {
        try {
          const state = await aiTestingApi.getJobResults(jobId);
          setJobState(state);

          if (
            state.status === 'COMPLETED' ||
            state.status === 'FAILED' ||
            state.status === 'CANCELLED'
          ) {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            setIsProcessing(false);
          }
        } catch {
          // ignore
        }
      }, 1000);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to start AI processing pipeline.');
      setIsProcessing(false);
    }
  };

  const connectJobWebSocket = (jobId: string) => {
    if (wsRef.current) wsRef.current.close();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/process/${jobId}/ws`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data && data.job_id) {
            setJobState((prev) => ({
              ...(prev || ({} as any)),
              ...data,
            }));
            if (
              data.status === 'COMPLETED' ||
              data.status === 'FAILED' ||
              data.status === 'CANCELLED'
            ) {
              setIsProcessing(false);
              if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            }
          }
        } catch {
          // ignore
        }
      };
    } catch {
      // ignore
    }
  };

  const handleStopProcessing = async () => {
    if (!currentJobId) return;
    try {
      await aiTestingApi.stopJob(currentJobId);
      setIsProcessing(false);
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    } catch (err: any) {
      setErrorMsg('Failed to stop job.');
    }
  };

  // Filtered ANPR Results Table
  const anprResults = jobState?.anpr_results || [];
  const filteredPlates = anprResults.filter((p) => {
    if (!tableSearch) return true;
    const q = tableSearch.toUpperCase();
    return (
      p.plate_number.includes(q) ||
      (p.vehicle && p.vehicle.toUpperCase().includes(q)) ||
      (p.rto_jurisdiction && p.rto_jurisdiction.toUpperCase().includes(q))
    );
  });

  const recentDetections = jobState?.recent_detections || [];

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        padding: '24px',
        color: '#f8fafc',
        backgroundColor: '#0a0f1d',
        minHeight: '100vh',
        fontFamily: "'JetBrains Mono', 'Segoe UI', sans-serif",
      }}
    >
      {/* ------------------------------------------------------------- */}
      {/* 1. Header Banner */}
      {/* ------------------------------------------------------------- */}
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#111927',
          border: '1px solid #1e293b',
          borderRadius: '12px',
          padding: '20px 24px',
          boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.4)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '10px',
              backgroundColor: 'rgba(56, 189, 248, 0.12)',
              border: '1px solid #38bdf8',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#38bdf8',
            }}
          >
            <Shield size={26} className="animate-pulse" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1
                style={{
                  margin: 0,
                  fontSize: '24px',
                  fontWeight: 800,
                  letterSpacing: '1px',
                  color: '#f8fafc',
                }}
              >
                PHANTOM 2.0
              </h1>
              <span
                style={{
                  backgroundColor: '#0284c7',
                  color: '#ffffff',
                  fontSize: '11px',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '4px',
                  letterSpacing: '0.5px',
                }}
              >
                PROD v4.8
              </span>
            </div>
            <p
              style={{
                margin: '4px 0 0',
                fontSize: '13px',
                color: '#94a3b8',
                fontWeight: 500,
              }}
            >
              AI-Powered Surveillance & Vehicle Intelligence
            </p>
          </div>
        </div>

        {/* System Telemetry Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              padding: '6px 12px',
              borderRadius: '6px',
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Cpu size={14} className="text-cyan" />
            <span style={{ color: '#94a3b8' }}>ENGINE:</span>
            <strong style={{ color: '#38bdf8' }}>YOLOv8 + EasyOCR</strong>
          </div>

          <div
            style={{
              padding: '6px 12px',
              borderRadius: '6px',
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Activity size={14} style={{ color: '#10b981' }} />
            <span style={{ color: '#94a3b8' }}>STATUS:</span>
            <strong style={{ color: isProcessing ? '#38bdf8' : '#10b981' }}>
              {isProcessing ? 'PROCESSING ACTIVE' : 'READY'}
            </strong>
          </div>
        </div>
      </header>

      {/* ------------------------------------------------------------- */}
      {/* 2. Control Bar: AI Agent Selector & Video Input Controls */}
      {/* ------------------------------------------------------------- */}
      <section
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1.5fr',
          gap: '20px',
        }}
      >
        {/* Left: AI Agent Selection */}
        <div
          style={{
            backgroundColor: '#111927',
            border: '1px solid #1e293b',
            borderRadius: '12px',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={16} className="text-cyan" />
            <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 700, letterSpacing: '0.5px' }}>
              1. SELECT AI AGENT / MODEL
            </h3>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
            <button
              onClick={() => setAiMode('yolo')}
              style={{
                padding: '14px 10px',
                borderRadius: '8px',
                border: aiMode === 'yolo' ? '2px solid #38bdf8' : '1px solid #334155',
                backgroundColor: aiMode === 'yolo' ? 'rgba(56, 189, 248, 0.15)' : '#0d1522',
                color: aiMode === 'yolo' ? '#38bdf8' : '#94a3b8',
                fontWeight: 700,
                fontSize: '13px',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s',
              }}
            >
              <User size={20} />
              <span>YOLO</span>
              <span style={{ fontSize: '10px', opacity: 0.8 }}>Object / Person</span>
            </button>

            <button
              onClick={() => setAiMode('anpr')}
              style={{
                padding: '14px 10px',
                borderRadius: '8px',
                border: aiMode === 'anpr' ? '2px solid #38bdf8' : '1px solid #334155',
                backgroundColor: aiMode === 'anpr' ? 'rgba(56, 189, 248, 0.15)' : '#0d1522',
                color: aiMode === 'anpr' ? '#38bdf8' : '#94a3b8',
                fontWeight: 700,
                fontSize: '13px',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s',
              }}
            >
              <Car size={20} />
              <span>ANPR</span>
              <span style={{ fontSize: '10px', opacity: 0.8 }}>Number Plates</span>
            </button>

            <button
              onClick={() => setAiMode('yolo_anpr')}
              style={{
                padding: '14px 10px',
                borderRadius: '8px',
                border: aiMode === 'yolo_anpr' ? '2px solid #10b981' : '1px solid #334155',
                backgroundColor: aiMode === 'yolo_anpr' ? 'rgba(16, 185, 129, 0.18)' : '#0d1522',
                color: aiMode === 'yolo_anpr' ? '#34d399' : '#94a3b8',
                fontWeight: 800,
                fontSize: '13px',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s',
                boxShadow: aiMode === 'yolo_anpr' ? '0 0 12px rgba(16, 185, 129, 0.25)' : 'none',
              }}
            >
              <Sparkles size={20} />
              <span>YOLO + ANPR</span>
              <span style={{ fontSize: '10px', opacity: 0.9 }}>Unified Pipeline</span>
            </button>
          </div>

          {/* Quick Info */}
          <div
            style={{
              padding: '10px 12px',
              borderRadius: '6px',
              backgroundColor: '#0d1522',
              fontSize: '11px',
              color: '#94a3b8',
              lineHeight: 1.5,
              borderLeft: '3px solid #38bdf8',
            }}
          >
            {aiMode === 'yolo' && 'YOLO Model detects Person, Car, Motorcycle, Bus, Truck, Bicycle frame-by-frame.'}
            {aiMode === 'anpr' && 'ANPR Model localizes license plates on vehicles, crops ROI, and runs OCR with Gujarat RTO parsing.'}
            {aiMode === 'yolo_anpr' && 'Unified Pipeline: Executes full YOLO object detection + automatic plate OCR on all vehicles simultaneously.'}
          </div>
        </div>

        {/* Right: Video Input & Processing Execution */}
        <div
          style={{
            backgroundColor: '#111927',
            border: '1px solid #1e293b',
            borderRadius: '12px',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Video size={16} className="text-cyan" />
              <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 700, letterSpacing: '0.5px' }}>
                2. VIDEO INPUT & INFERENCE CONTROLS
              </h3>
            </div>

            {/* Source Mode Toggle */}
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                onClick={() => setSelectedSource('sample')}
                style={{
                  padding: '4px 10px',
                  borderRadius: '4px',
                  border: 'none',
                  backgroundColor: selectedSource === 'sample' ? '#0284c7' : '#1e293b',
                  color: '#ffffff',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Sample CCTV Video
              </button>
              <button
                onClick={() => setSelectedSource('upload')}
                style={{
                  padding: '4px 10px',
                  borderRadius: '4px',
                  border: 'none',
                  backgroundColor: selectedSource === 'upload' ? '#0284c7' : '#1e293b',
                  color: '#ffffff',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Upload Video File
              </button>
            </div>
          </div>

          {/* File Input or Sample Ingest */}
          {selectedSource === 'upload' ? (
            <div
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: '2px dashed #334155',
                borderRadius: '8px',
                padding: '16px',
                textAlign: 'center',
                backgroundColor: '#0d1522',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '12px',
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
              <Upload size={20} className="text-cyan" />
              <div>
                <strong style={{ color: '#38bdf8', fontSize: '13px' }}>
                  {uploadedFileName || 'Click to browse video file'}
                </strong>
                <p style={{ margin: 0, fontSize: '11px', color: '#64748b' }}>
                  Supports MP4, AVI, MOV, MKV, WebM
                </p>
              </div>
            </div>
          ) : (
            <div
              style={{
                borderRadius: '8px',
                padding: '12px 16px',
                backgroundColor: '#0d1522',
                border: '1px solid #1e293b',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileVideo size={20} className="text-cyan" />
                <div>
                  <div style={{ fontWeight: 600, fontSize: '13px' }}>
                    sample_traffic_cctv.mp4
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>
                    Gujarat Surat Junction Traffic (Bus, Cars, Pedestrians, Plate: GJ05AB1234)
                  </div>
                </div>
              </div>
              <span style={{ fontSize: '11px', color: '#10b981', fontWeight: 700 }}>
                ● READY FOR INGEST
              </span>
            </div>
          )}

          {/* Sliders & Action Buttons Row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            {/* FPS Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>RATE:</span>
              <select
                value={sampleFps}
                onChange={(e) => setSampleFps(Number(e.target.value))}
                style={{
                  backgroundColor: '#0d1522',
                  border: '1px solid #334155',
                  color: '#f8fafc',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  fontSize: '12px',
                }}
              >
                <option value={2.0}>2 FPS (Fast)</option>
                <option value={5.0}>5 FPS (Balanced)</option>
                <option value={10.0}>10 FPS (High-Density)</option>
                <option value={25.0}>All Frames (25 FPS)</option>
              </select>
            </div>

            {/* Threshold Slider */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>CONF:</span>
              <input
                type="range"
                min="0.10"
                max="0.80"
                step="0.05"
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                style={{ flex: 1, accentColor: '#38bdf8', cursor: 'pointer' }}
              />
              <span style={{ fontSize: '12px', fontWeight: 700, color: '#38bdf8', minWidth: '35px' }}>
                {(confidenceThreshold * 100).toFixed(0)}%
              </span>
            </div>

            {/* Buttons */}
            {!isProcessing ? (
              <button
                onClick={handleStartProcessing}
                style={{
                  padding: '10px 22px',
                  backgroundColor: '#0284c7',
                  border: 'none',
                  borderRadius: '6px',
                  color: '#ffffff',
                  fontWeight: 700,
                  fontSize: '13px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: '0 4px 14px rgba(2, 132, 199, 0.4)',
                  transition: 'all 0.2s',
                }}
              >
                <Play size={16} fill="#ffffff" />
                <span>START PROCESSING</span>
              </button>
            ) : (
              <button
                onClick={handleStopProcessing}
                style={{
                  padding: '10px 22px',
                  backgroundColor: '#dc2626',
                  border: 'none',
                  borderRadius: '6px',
                  color: '#ffffff',
                  fontWeight: 700,
                  fontSize: '13px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: '0 4px 14px rgba(220, 38, 38, 0.4)',
                }}
              >
                <Square size={16} fill="#ffffff" />
                <span>STOP PROCESSING</span>
              </button>
            )}
          </div>

          {errorMsg && (
            <div
              style={{
                padding: '8px 12px',
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid #ef4444',
                borderRadius: '6px',
                color: '#fca5a5',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <AlertCircle size={14} />
              <span>{errorMsg}</span>
            </div>
          )}
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* 3. Main Center Workspace: Video Display & Detection Feed */}
      {/* ------------------------------------------------------------- */}
      <section
        style={{
          display: 'grid',
          gridTemplateColumns: '1.8fr 1fr',
          gap: '20px',
        }}
      >
        {/* Left: Video Display Player / Live Canvas */}
        <div
          style={{
            backgroundColor: '#111927',
            border: '1px solid #1e293b',
            borderRadius: '12px',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Eye size={16} className="text-cyan" />
              <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 700, letterSpacing: '0.5px' }}>
                3. PROCESSED VIDEO & LIVE HUD DISPLAY
              </h3>
            </div>

            {jobState && (
              <span style={{ fontSize: '12px', color: '#38bdf8', fontWeight: 700 }}>
                {jobState.status === 'PROCESSING' && (
                  <span className="animate-pulse">● LIVE INFERENCE ({jobState.progress_percent}%)</span>
                )}
                {jobState.status === 'COMPLETED' && (
                  <span style={{ color: '#10b981' }}>✔ PROCESSING COMPLETE (100%)</span>
                )}
              </span>
            )}
          </div>

          {/* Video / Frame Screen */}
          <div
            style={{
              position: 'relative',
              width: '100%',
              aspectRatio: '16 / 9',
              backgroundColor: '#020617',
              borderRadius: '8px',
              overflow: 'hidden',
              border: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {/* 1. Live Frame Base64 during processing */}
            {isProcessing && jobState?.latest_frame_b64 ? (
              <img
                src={jobState.latest_frame_b64}
                alt="Live AI HUD"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            ) : jobState?.status === 'COMPLETED' && jobState.video_url ? (
              /* 2. Processed Video Player on completion */
              <video
                ref={videoPlayerRef}
                src={jobState.video_url}
                controls
                autoPlay
                loop
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            ) : (
              /* 3. Idle Standby Screen */
              <div style={{ textAlign: 'center', color: '#64748b' }}>
                <Video size={48} style={{ marginBottom: '12px', opacity: 0.4 }} />
                <p style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#94a3b8' }}>
                  Surveillance Stream Display Standby
                </p>
                <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#64748b' }}>
                  Select AI Agent and click Start Processing to view live detections
                </p>
              </div>
            )}
          </div>

          {/* Progress Bar & Telemetry */}
          {jobState && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                <span style={{ color: '#94a3b8' }}>
                  Frames: <strong>{jobState.frames_processed}</strong> / {jobState.total_frames}
                </span>
                <span style={{ color: '#38bdf8', fontWeight: 700 }}>
                  {jobState.progress_percent.toFixed(1)}%
                </span>
                <span style={{ color: '#94a3b8' }}>
                  Speed: <strong>{jobState.processing_fps} FPS</strong> | Elapsed:{' '}
                  <strong>{jobState.elapsed_seconds}s</strong>
                </span>
              </div>

              <div
                style={{
                  width: '100%',
                  height: '6px',
                  backgroundColor: '#1e293b',
                  borderRadius: '3px',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${jobState.progress_percent}%`,
                    backgroundColor: jobState.status === 'COMPLETED' ? '#10b981' : '#38bdf8',
                    transition: 'width 0.3s ease',
                  }}
                />
              </div>

              {jobState.status === 'COMPLETED' && (
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                  <a
                    href={jobState.download_url}
                    download
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '6px 14px',
                      backgroundColor: '#10b981',
                      borderRadius: '6px',
                      color: '#ffffff',
                      fontSize: '12px',
                      fontWeight: 700,
                      textDecoration: 'none',
                    }}
                  >
                    <Download size={14} />
                    <span>Download Annotated Video</span>
                  </a>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right: Live Detection Stream Panel */}
        <div
          style={{
            backgroundColor: '#111927',
            border: '1px solid #1e293b',
            borderRadius: '12px',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
            maxHeight: '560px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={16} className="text-cyan" />
              <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 700, letterSpacing: '0.5px' }}>
                4. DETECTION FEED
              </h3>
            </div>
            <span
              style={{
                fontSize: '11px',
                backgroundColor: '#1e293b',
                padding: '2px 8px',
                borderRadius: '4px',
                color: '#38bdf8',
                fontWeight: 700,
              }}
            >
              {jobState?.total_detections || 0} TOTAL
            </span>
          </div>

          {/* Detection Events Column Header */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1.5fr 1fr 1fr',
              padding: '6px 10px',
              backgroundColor: '#0d1522',
              borderRadius: '6px',
              fontSize: '11px',
              fontWeight: 700,
              color: '#94a3b8',
            }}
          >
            <span>DETECTION</span>
            <span style={{ textAlign: 'center' }}>CONFIDENCE</span>
            <span style={{ textAlign: 'right' }}>TIMESTAMP</span>
          </div>

          {/* Detection Items List */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              paddingRight: '4px',
            }}
          >
            {recentDetections.length === 0 ? (
              <div
                style={{
                  textAlign: 'center',
                  padding: '40px 10px',
                  color: '#64748b',
                  fontSize: '12px',
                }}
              >
                No live detection events yet. Start processing to stream events.
              </div>
            ) : (
              recentDetections
                .slice()
                .reverse()
                .map((ev, idx) => {
                  const isPlate = Boolean(ev.license_plate && ev.object_class === ev.license_plate);
                  const isCar = ev.object_class === 'CAR' || ev.vehicle_type === 'Car';
                  const isPerson = ev.object_class === 'PERSON';
                  const confPct = Math.round(ev.confidence * 100);

                  return (
                    <div
                      key={`${ev.id}-${idx}`}
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '1.5fr 1fr 1fr',
                        alignItems: 'center',
                        padding: '10px',
                        backgroundColor: '#0d1522',
                        border: isPlate ? '1px solid #ef4444' : '1px solid #1e293b',
                        borderRadius: '6px',
                        fontSize: '12px',
                        borderLeft: isPlate
                          ? '4px solid #ef4444'
                          : isCar
                          ? '4px solid #10b981'
                          : isPerson
                          ? '4px solid #00f0ff'
                          : '4px solid #f59e0b',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {isPlate ? (
                          <span
                            style={{
                              backgroundColor: '#ef4444',
                              color: '#ffffff',
                              fontSize: '10px',
                              fontWeight: 800,
                              padding: '1px 5px',
                              borderRadius: '3px',
                            }}
                          >
                            PLATE
                          </span>
                        ) : isCar ? (
                          <Car size={13} style={{ color: '#10b981' }} />
                        ) : isPerson ? (
                          <User size={13} style={{ color: '#00f0ff' }} />
                        ) : (
                          <Shield size={13} style={{ color: '#f59e0b' }} />
                        )}
                        <strong
                          style={{
                            color: isPlate ? '#fca5a5' : '#f8fafc',
                            fontFamily: isPlate ? "'Courier New', monospace" : 'inherit',
                          }}
                        >
                          {ev.display_name || ev.object_class}
                        </strong>
                      </div>

                      <div style={{ textAlign: 'center' }}>
                        <span
                          style={{
                            color: confPct >= 85 ? '#34d399' : confPct >= 65 ? '#fbbf24' : '#f87171',
                            fontWeight: 700,
                          }}
                        >
                          {confPct}%
                        </span>
                      </div>

                      <div
                        style={{
                          textAlign: 'right',
                          color: '#94a3b8',
                          fontFamily: "'Courier New', monospace",
                        }}
                      >
                        {ev.time_str}
                      </div>
                    </div>
                  );
                })
            )}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* 4. Bottom Table: ANPR Results */}
      {/* ------------------------------------------------------------- */}
      <section
        style={{
          backgroundColor: '#111927',
          border: '1px solid #1e293b',
          borderRadius: '12px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Car size={18} className="text-cyan" />
            <div>
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 800, letterSpacing: '0.5px' }}>
                5. ANPR RESULTS TABLE (RECOGNIZED NUMBER PLATES)
              </h3>
              <p style={{ margin: '2px 0 0', fontSize: '11px', color: '#94a3b8' }}>
                Identified Gujarat RTO and Indian vehicle registration plates with confidence & jurisdiction
              </p>
            </div>
          </div>

          {/* Search Box */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                backgroundColor: '#0d1522',
                border: '1px solid #334155',
                borderRadius: '6px',
                padding: '6px 12px',
              }}
            >
              <Search size={14} style={{ color: '#64748b' }} />
              <input
                type="text"
                placeholder="Filter plates or vehicle..."
                value={tableSearch}
                onChange={(e) => setTableSearch(e.target.value)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#f8fafc',
                  fontSize: '12px',
                  outline: 'none',
                  width: '180px',
                }}
              />
            </div>
          </div>
        </div>

        {/* Table View */}
        <div style={{ overflowX: 'auto' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              textAlign: 'left',
              fontSize: '13px',
            }}
          >
            <thead>
              <tr
                style={{
                  borderBottom: '2px solid #1e293b',
                  color: '#94a3b8',
                  fontSize: '11px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                <th style={{ padding: '12px 16px' }}>Number Plate</th>
                <th style={{ padding: '12px 16px' }}>Confidence</th>
                <th style={{ padding: '12px 16px' }}>Time</th>
                <th style={{ padding: '12px 16px' }}>Vehicle</th>
                <th style={{ padding: '12px 16px' }}>RTO Jurisdiction</th>
                <th style={{ padding: '12px 16px', textAlign: 'right' }}>Sightings</th>
              </tr>
            </thead>
            <tbody>
              {filteredPlates.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    style={{
                      padding: '32px',
                      textAlign: 'center',
                      color: '#64748b',
                      fontSize: '13px',
                    }}
                  >
                    No license plates recognized yet. Start ANPR or YOLO+ANPR processing on vehicle footage.
                  </td>
                </tr>
              ) : (
                filteredPlates.map((plate) => {
                  const confPct = Math.round(plate.confidence * 100);
                  return (
                    <tr
                      key={plate.id}
                      style={{
                        borderBottom: '1px solid #1e293b',
                        backgroundColor: '#0b121e',
                        transition: 'background-color 0.2s',
                      }}
                    >
                      {/* Number Plate with High-Contrast Badge */}
                      <td style={{ padding: '12px 16px' }}>
                        <div
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            backgroundColor: '#ffffff',
                            color: '#000000',
                            border: '1px solid #000000',
                            borderRadius: '4px',
                            padding: '3px 8px',
                            fontFamily: "'Courier New', monospace",
                            fontWeight: 800,
                            fontSize: '13px',
                            letterSpacing: '1px',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
                          }}
                        >
                          <span
                            style={{
                              backgroundColor: '#1e3a8a',
                              color: '#ffffff',
                              fontSize: '8px',
                              padding: '1px 3px',
                              borderRadius: '2px',
                              marginRight: '6px',
                            }}
                          >
                            IND
                          </span>
                          <span>{plate.plate_number}</span>
                        </div>
                      </td>

                      {/* Confidence Score */}
                      <td style={{ padding: '12px 16px' }}>
                        <span
                          style={{
                            color: confPct >= 85 ? '#34d399' : '#fbbf24',
                            fontWeight: 700,
                          }}
                        >
                          {confPct}%
                        </span>
                      </td>

                      {/* Timestamp */}
                      <td
                        style={{
                          padding: '12px 16px',
                          fontFamily: "'Courier New', monospace",
                          color: '#94a3b8',
                        }}
                      >
                        {plate.time_str}
                      </td>

                      {/* Vehicle Class */}
                      <td style={{ padding: '12px 16px' }}>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            color: '#38bdf8',
                            fontWeight: 600,
                          }}
                        >
                          <Car size={14} />
                          {plate.vehicle}
                        </span>
                      </td>

                      {/* RTO Jurisdiction */}
                      <td style={{ padding: '12px 16px', color: '#e2e8f0' }}>
                        {plate.rto_jurisdiction || 'Gujarat State'}
                      </td>

                      {/* Sightings */}
                      <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                        <span
                          style={{
                            backgroundColor: '#1e293b',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: 700,
                            color: '#94a3b8',
                          }}
                        >
                          {plate.total_sightings}x
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
