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
  BarChart3,
  TrendingUp,
  Gauge,
  Truck,
  Bus,
  Bike,
  RotateCcw,
  Zap,
} from 'lucide-react';
import {
  aiTestingApi,
  DetectionEvent,
  ANPRTableItem,
  VideoAIJobState,
  ObjectAnalytics,
} from '../../api/aiTestingApi';

export const AITestingDashboard: React.FC = () => {
  // AI Agent Mode: YOLO, ANPR, or YOLO + ANPR
  const [aiMode, setAiMode] = useState<'yolo' | 'anpr' | 'yolo_anpr'>('yolo_anpr');
  const [selectedSource, setSelectedSource] = useState<'sentinel_grid' | 'sample' | 'upload'>('sentinel_grid');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string>('');

  // Sentinel 30 Real CCTV Cameras
  const [sentinelCameras, setSentinelCameras] = useState<Array<{ id: string; name: string; district: string; rtsp_url: string; hls_url: string; webrtc_url: string; has_local_sample: boolean; sample_id: string; }>>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string>('cam01');
  const [selectedSampleClip, setSelectedSampleClip] = useState<string>('cam01_sample');

  // Live Snapshot State
  const [snapshotResult, setSnapshotResult] = useState<any | null>(null);
  const [isTakingSnapshot, setIsTakingSnapshot] = useState<boolean>(false);

  // Configuration Sliders
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.30);
  const [sampleFps, setSampleFps] = useState<number>(5.0);

  // Processing State & Job Telemetry
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [jobState, setJobState] = useState<VideoAIJobState | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Feed Filter & Table Search
  const [feedFilter, setFeedFilter] = useState<string>('ALL');
  const [tableSearch, setTableSearch] = useState<string>('');
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);

  const pollIntervalRef = useRef<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const videoPlayerRef = useRef<HTMLVideoElement | null>(null);

  // Load 30 Sentinel cameras on mount
  useEffect(() => {
    aiTestingApi.getSentinelCameras().then((res) => {
      if (res && res.cameras) {
        setSentinelCameras(res.cameras);
      }
    }).catch(() => {});

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
      setSnapshotResult(null);
      setErrorMsg(null);
    }
  };

  const handleLiveSnapshot = async () => {
    setErrorMsg(null);
    setIsTakingSnapshot(true);
    try {
      const snap = await aiTestingApi.getCameraSnapshot(selectedCameraId, confidenceThreshold);
      setSnapshotResult(snap);
    } catch (err: any) {
      setErrorMsg(err?.message || `Failed to capture live snapshot from ${selectedCameraId}`);
    } finally {
      setIsTakingSnapshot(false);
    }
  };

  const handleStartProcessing = async () => {
    setErrorMsg(null);
    setIsProcessing(true);
    setJobState(null);
    setSnapshotResult(null);

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
      } else if (selectedSource === 'sentinel_grid') {
        const camObj = sentinelCameras.find((c) => c.id === selectedCameraId);
        res = await aiTestingApi.startProcessing({
          uploadId: selectedCameraId,
          cameraId: camObj ? `${camObj.id} - ${camObj.name}` : selectedCameraId,
          mode: aiMode,
          sampleFps: sampleFps,
          confidenceThreshold: confidenceThreshold,
        });
      } else {
        res = await aiTestingApi.startProcessing({
          uploadId: selectedSampleClip,
          cameraId: selectedSampleClip,
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

  const handleSetSpeed = (spd: number) => {
    setPlaybackSpeed(spd);
    if (videoPlayerRef.current) {
      videoPlayerRef.current.playbackRate = spd;
    }
  };

  // Compute live analytics payload
  const analytics: ObjectAnalytics = jobState?.analytics || {
    total_objects_tracked: snapshotResult?.total_detections || 0,
    unique_vehicles_count: snapshotResult?.detections?.filter((d: any) => ['car', 'bus', 'truck', 'motorcycle'].includes(d.class_name.toLowerCase())).length || 0,
    cars_count: snapshotResult?.detections?.filter((d: any) => d.class_name.toLowerCase() === 'car').length || 0,
    buses_count: snapshotResult?.detections?.filter((d: any) => d.class_name.toLowerCase() === 'bus').length || 0,
    trucks_count: snapshotResult?.detections?.filter((d: any) => d.class_name.toLowerCase() === 'truck').length || 0,
    motorcycles_count: snapshotResult?.detections?.filter((d: any) => d.class_name.toLowerCase() === 'motorcycle').length || 0,
    pedestrians_count: snapshotResult?.detections?.filter((d: any) => d.class_name.toLowerCase() === 'person').length || 0,
    bicycles_count: snapshotResult?.detections?.filter((d: any) => d.class_name.toLowerCase() === 'bicycle').length || 0,
    peak_frame_density: snapshotResult?.total_detections || 0,
    avg_confidence_pct: snapshotResult?.detections?.length ? Math.round(snapshotResult.detections.reduce((acc: number, d: any) => acc + d.confidence, 0) / snapshotResult.detections.length * 100) : 0,
    congestion_level: (snapshotResult?.total_detections || 0) >= 5 ? 'HIGH' : ((snapshotResult?.total_detections || 0) >= 2 ? 'MODERATE' : 'LOW'),
    vehicle_distribution: {},
  };

  // Filtered ANPR Results Table
  const anprResults: ANPRTableItem[] = (isProcessing || jobState)
    ? (jobState?.anpr_results || [])
    : (snapshotResult?.plates
        ? snapshotResult.plates.map((p: any, idx: number) => ({
            id: `snap_plate_${idx}`,
            plate_number: p.plate_number,
            confidence: p.confidence,
            time_str: 'LIVE',
            timestamp_sec: 0,
            vehicle: p.vehicle,
            rto_jurisdiction: p.rto_jurisdiction,
            is_gujarat: p.is_gujarat,
            first_seen_frame: 1,
            last_seen_frame: 1,
            total_sightings: 1,
          }))
        : []);

  const filteredPlates = anprResults.filter((p) => {
    if (!tableSearch) return true;
    const q = tableSearch.toUpperCase();
    return (
      p.plate_number.includes(q) ||
      (p.vehicle && p.vehicle.toUpperCase().includes(q)) ||
      (p.rto_jurisdiction && p.rto_jurisdiction.toUpperCase().includes(q))
    );
  });

  // Raw Detections List
  const rawDetections: DetectionEvent[] = (isProcessing || jobState)
    ? (jobState?.recent_detections || [])
    : (snapshotResult?.detections
        ? snapshotResult.detections.map((d: any, idx: number) => ({
            id: `snap_det_${idx}`,
            frame_idx: 1,
            timestamp_sec: 0,
            time_str: 'LIVE',
            object_class: d.class_name.toUpperCase(),
            display_name: d.class_name,
            confidence: d.confidence,
            bounding_box: d.bbox,
            is_vehicle: ['car', 'bus', 'truck', 'motorcycle'].includes(d.class_name.toLowerCase()),
            vehicle_type: d.class_name,
            track_id: idx + 1,
          }))
        : []);

  const recentDetections = rawDetections.filter((ev) => {
    if (feedFilter === 'ALL') return true;
    if (feedFilter === 'CARS') return ev.object_class === 'CAR' || ev.vehicle_type?.toLowerCase() === 'car';
    if (feedFilter === 'AUTOS') return ev.object_class === 'AUTO_RICKSHAW' || ev.vehicle_type?.toLowerCase().includes('rickshaw');
    if (feedFilter === 'SCOOTERS') {
      const name = (ev.display_name || ev.vehicle_type || '').toLowerCase();
      return name.includes('activa') || name.includes('access') || name.includes('jupiter') || name.includes('scooter');
    }
    if (feedFilter === 'BIKES') {
      const name = (ev.display_name || ev.vehicle_type || '').toLowerCase();
      return name.includes('splendor') || name.includes('pulsar') || name.includes('royal') || name.includes('enfield') || name.includes('shine') || name.includes('apache') || (ev.object_class === 'MOTORCYCLE' && !name.includes('activa') && !name.includes('access') && !name.includes('jupiter'));
    }
    if (feedFilter === 'BUSES') return ev.object_class === 'BUS' || ev.vehicle_type?.toLowerCase() === 'bus';
    if (feedFilter === 'TRUCKS') return ev.object_class === 'TRUCK' || ev.vehicle_type?.toLowerCase() === 'truck';
    if (feedFilter === 'PERSONS') return ev.object_class === 'PERSON';
    if (feedFilter === 'PLATES') return Boolean(ev.license_plate);
    return true;
  });

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
            {aiMode === 'yolo' && 'YOLO Model detects Person, Car, Motorcycle, Bus, Truck, Bicycle with real-time multi-object tracking.'}
            {aiMode === 'anpr' && 'ANPR Model localizes vehicle license plates, crops ROI, and runs OCR with Gujarat RTO parsing.'}
            {aiMode === 'yolo_anpr' && 'Unified Pipeline: Executes full YOLO multi-object tracking + automatic plate OCR on all vehicles simultaneously.'}
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
                onClick={() => { setSelectedSource('sentinel_grid'); setSnapshotResult(null); }}
                style={{
                  padding: '4px 10px',
                  borderRadius: '4px',
                  border: 'none',
                  backgroundColor: selectedSource === 'sentinel_grid' ? '#0284c7' : '#1e293b',
                  color: '#ffffff',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Sentinel 30 CCTV Grid
              </button>
              <button
                onClick={() => { setSelectedSource('sample'); setSnapshotResult(null); }}
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
                Captured CCTV Clips
              </button>
              <button
                onClick={() => { setSelectedSource('upload'); setSnapshotResult(null); }}
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
                Upload File
              </button>
            </div>
          </div>

          {/* Source Selection Body */}
          {selectedSource === 'sentinel_grid' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <select
                  value={selectedCameraId}
                  onChange={(e) => { setSelectedCameraId(e.target.value); setSnapshotResult(null); }}
                  style={{
                    flex: 1,
                    backgroundColor: '#0d1522',
                    border: '1px solid #334155',
                    color: '#f8fafc',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    fontSize: '13px',
                    fontWeight: 600,
                  }}
                >
                  {sentinelCameras.length > 0 ? (
                    sentinelCameras.map((cam) => (
                      <option key={cam.id} value={cam.id}>
                        [{cam.id.toUpperCase()}] {cam.name} — {cam.district}
                      </option>
                    ))
                  ) : (
                    <option value="cam01">[CAM01] 01 Chiman bhai Bridge — Ahmedabad</option>
                  )}
                </select>

                <button
                  onClick={handleLiveSnapshot}
                  disabled={isTakingSnapshot || isProcessing}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#0f766e',
                    border: '1px solid #14b8a6',
                    borderRadius: '6px',
                    color: '#ffffff',
                    fontSize: '12px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    opacity: isTakingSnapshot ? 0.7 : 1,
                  }}
                >
                  <Activity size={14} />
                  <span>{isTakingSnapshot ? 'CAPTURING...' : 'LIVE SNAPSHOT'}</span>
                </button>
              </div>

              {/* Camera Details Card */}
              {(() => {
                const currentCam = sentinelCameras.find((c) => c.id === selectedCameraId);
                return (
                  <div
                    style={{
                      padding: '8px 12px',
                      borderRadius: '6px',
                      backgroundColor: '#0d1522',
                      border: '1px solid #1e293b',
                      fontSize: '11px',
                      color: '#94a3b8',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '8px',
                    }}
                  >
                    <span>
                      RTSP TCP:{' '}
                      <code style={{ color: '#38bdf8' }}>
                        rtsp://103.250.160.189:8554/stream/{selectedCameraId}
                      </code>
                    </span>
                    <span style={{ color: '#10b981', fontWeight: 700 }}>
                      ● SENTINEL ONLINE (H.264 1080p 25 FPS)
                    </span>
                  </div>
                );
              })()}
            </div>
          ) : selectedSource === 'sample' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <select
                value={selectedSampleClip}
                onChange={(e) => { setSelectedSampleClip(e.target.value); setSnapshotResult(null); }}
                style={{
                  width: '100%',
                  backgroundColor: '#0d1522',
                  border: '1px solid #334155',
                  color: '#f8fafc',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '13px',
                }}
              >
                <option value="cam01_sample">cam01_sample.mp4 — Ahmedabad Chiman bhai Bridge (Real Footage)</option>
                <option value="cam02_sample">cam02_sample.mp4 — Ahmedabad Janpath (Real Footage)</option>
                <option value="cam04_sample">cam04_sample.mp4 — Ahmedabad Paldi Circle (Real Footage)</option>
                <option value="cam06_sample">cam06_sample.mp4 — Junagadh Timbavadi Gate (Real Footage)</option>
                <option value="cam17_sample">cam17_sample.mp4 — Rajkot Bus Port CCTV (Real Footage)</option>
                <option value="sample_traffic_cctv">sample_traffic_cctv.mp4 — Surat Multi-Vehicle Traffic</option>
              </select>
            </div>
          ) : (
            <div
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: '2px dashed #334155',
                borderRadius: '8px',
                padding: '14px',
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
      {/* 3. Real-Time Object & Traffic Analytics Intelligence Suite */}
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
            <BarChart3 size={18} className="text-cyan" />
            <div>
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 800, letterSpacing: '0.5px' }}>
                3. REAL-TIME OBJECT & TRAFFIC ANALYTICS
              </h3>
              <p style={{ margin: '2px 0 0', fontSize: '11px', color: '#94a3b8' }}>
                Continuous vehicle velocity, density distribution, and classification telemetry
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '11px', color: '#94a3b8' }}>CONGESTION LEVEL:</span>
            <span
              style={{
                padding: '4px 10px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 800,
                letterSpacing: '0.5px',
                backgroundColor:
                  analytics.congestion_level === 'HIGH'
                    ? 'rgba(239, 68, 68, 0.2)'
                    : analytics.congestion_level === 'MODERATE'
                    ? 'rgba(245, 158, 11, 0.2)'
                    : 'rgba(16, 185, 129, 0.2)',
                color:
                  analytics.congestion_level === 'HIGH'
                    ? '#f87171'
                    : analytics.congestion_level === 'MODERATE'
                    ? '#fbbf24'
                    : '#34d399',
                border:
                  analytics.congestion_level === 'HIGH'
                    ? '1px solid #ef4444'
                    : analytics.congestion_level === 'MODERATE'
                    ? '1px solid #f59e0b'
                    : '1px solid #10b981',
              }}
            >
              ● {analytics.congestion_level === 'HIGH' ? 'HIGH (CONGESTED)' : analytics.congestion_level === 'MODERATE' ? 'MODERATE FLOW' : 'LOW (FREE FLOW)'}
            </span>
          </div>
        </div>

        {/* 4 KPI Top Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px' }}>
          {/* 1. Vehicles Tracked */}
          <div
            style={{
              padding: '14px',
              backgroundColor: '#0d1522',
              border: '1px solid #1e293b',
              borderRadius: '8px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 600 }}>TOTAL VEHICLES</span>
              <Car size={16} style={{ color: '#38bdf8' }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span style={{ fontSize: '26px', fontWeight: 800, color: '#f8fafc' }}>
                {analytics.cars_count + analytics.buses_count + analytics.trucks_count + analytics.motorcycles_count}
              </span>
              <span style={{ fontSize: '11px', color: '#38bdf8', fontWeight: 700 }}>
                ({analytics.unique_vehicles_count} Unique)
              </span>
            </div>
            <span style={{ fontSize: '10px', color: '#64748b' }}>
              {analytics.cars_count} Cars • {analytics.trucks_count} Trucks • {analytics.buses_count} Buses
            </span>
          </div>

          {/* 2. Peak Density */}
          <div
            style={{
              padding: '14px',
              backgroundColor: '#0d1522',
              border: '1px solid #1e293b',
              borderRadius: '8px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 600 }}>PEAK SCENE DENSITY</span>
              <TrendingUp size={16} style={{ color: '#10b981' }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span style={{ fontSize: '26px', fontWeight: 800, color: '#10b981' }}>
                {analytics.peak_frame_density}
              </span>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>concurrent objects</span>
            </div>
            <span style={{ fontSize: '10px', color: '#64748b' }}>
              Max simultaneous detections in 1 frame
            </span>
          </div>

          {/* 3. Model Confidence */}
          <div
            style={{
              padding: '14px',
              backgroundColor: '#0d1522',
              border: '1px solid #1e293b',
              borderRadius: '8px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 600 }}>AVG MODEL CONFIDENCE</span>
              <Gauge size={16} style={{ color: '#fbbf24' }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span style={{ fontSize: '26px', fontWeight: 800, color: '#fbbf24' }}>
                {analytics.avg_confidence_pct}%
              </span>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>certainty</span>
            </div>
            <span style={{ fontSize: '10px', color: '#64748b' }}>
              Mean score across YOLO inference passes
            </span>
          </div>

          {/* 4. Number Plates Identified */}
          <div
            style={{
              padding: '14px',
              backgroundColor: '#0d1522',
              border: '1px solid #1e293b',
              borderRadius: '8px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 600 }}>ANPR PLATES FOUND</span>
              <Zap size={16} style={{ color: '#c084fc' }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span style={{ fontSize: '26px', fontWeight: 800, color: '#c084fc' }}>
                {anprResults.length}
              </span>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>recognized</span>
            </div>
            <span style={{ fontSize: '10px', color: '#64748b' }}>
              Gujarat RTO & Indian registration plates
            </span>
          </div>
        </div>

        {/* Object Classification Matrix Breakdown */}
        <div
          style={{
            padding: '16px',
            backgroundColor: '#0d1522',
            border: '1px solid #1e293b',
            borderRadius: '8px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: '#e2e8f0', letterSpacing: '0.5px' }}>
              VEHICLE & OBJECT CLASSIFICATION MATRIX
            </span>
            <span style={{ fontSize: '11px', color: '#64748b' }}>
              {analytics.total_objects_tracked} Total Frames Detected
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '12px' }}>
            {/* Cars */}
            <div style={{ backgroundColor: '#111927', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#10b981', fontSize: '11px', fontWeight: 700 }}>
                <Car size={14} />
                <span>CARS</span>
              </div>
              <div style={{ fontSize: '18px', fontWeight: 800, marginTop: '4px' }}>{analytics.cars_count}</div>
              <div style={{ height: '4px', backgroundColor: '#1e293b', borderRadius: '2px', marginTop: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${analytics.total_objects_tracked ? (analytics.cars_count / analytics.total_objects_tracked) * 100 : 0}%`, height: '100%', backgroundColor: '#10b981' }} />
              </div>
            </div>

            {/* Trucks */}
            <div style={{ backgroundColor: '#111927', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#f59e0b', fontSize: '11px', fontWeight: 700 }}>
                <Truck size={14} />
                <span>TRUCKS</span>
              </div>
              <div style={{ fontSize: '18px', fontWeight: 800, marginTop: '4px' }}>{analytics.trucks_count}</div>
              <div style={{ height: '4px', backgroundColor: '#1e293b', borderRadius: '2px', marginTop: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${analytics.total_objects_tracked ? (analytics.trucks_count / analytics.total_objects_tracked) * 100 : 0}%`, height: '100%', backgroundColor: '#f59e0b' }} />
              </div>
            </div>

            {/* Buses */}
            <div style={{ backgroundColor: '#111927', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#d97706', fontSize: '11px', fontWeight: 700 }}>
                <Bus size={14} />
                <span>BUSES</span>
              </div>
              <div style={{ fontSize: '18px', fontWeight: 800, marginTop: '4px' }}>{analytics.buses_count}</div>
              <div style={{ height: '4px', backgroundColor: '#1e293b', borderRadius: '2px', marginTop: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${analytics.total_objects_tracked ? (analytics.buses_count / analytics.total_objects_tracked) * 100 : 0}%`, height: '100%', backgroundColor: '#d97706' }} />
              </div>
            </div>

            {/* Motorcycles */}
            <div style={{ backgroundColor: '#111927', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#c084fc', fontSize: '11px', fontWeight: 700 }}>
                <Bike size={14} />
                <span>2-WHEELERS</span>
              </div>
              <div style={{ fontSize: '18px', fontWeight: 800, marginTop: '4px' }}>{analytics.motorcycles_count}</div>
              <div style={{ height: '4px', backgroundColor: '#1e293b', borderRadius: '2px', marginTop: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${analytics.total_objects_tracked ? (analytics.motorcycles_count / analytics.total_objects_tracked) * 100 : 0}%`, height: '100%', backgroundColor: '#c084fc' }} />
              </div>
            </div>

            {/* Pedestrians */}
            <div style={{ backgroundColor: '#111927', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38bdf8', fontSize: '11px', fontWeight: 700 }}>
                <User size={14} />
                <span>PERSONS</span>
              </div>
              <div style={{ fontSize: '18px', fontWeight: 800, marginTop: '4px' }}>{analytics.pedestrians_count}</div>
              <div style={{ height: '4px', backgroundColor: '#1e293b', borderRadius: '2px', marginTop: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${analytics.total_objects_tracked ? (analytics.pedestrians_count / analytics.total_objects_tracked) * 100 : 0}%`, height: '100%', backgroundColor: '#38bdf8' }} />
              </div>
            </div>

            {/* Bicycles */}
            <div style={{ backgroundColor: '#111927', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#facc15', fontSize: '11px', fontWeight: 700 }}>
                <Activity size={14} />
                <span>BICYCLES</span>
              </div>
              <div style={{ fontSize: '18px', fontWeight: 800, marginTop: '4px' }}>{analytics.bicycles_count}</div>
              <div style={{ height: '4px', backgroundColor: '#1e293b', borderRadius: '2px', marginTop: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${analytics.total_objects_tracked ? (analytics.bicycles_count / analytics.total_objects_tracked) * 100 : 0}%`, height: '100%', backgroundColor: '#facc15' }} />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* 4. Main Center Workspace: Video Display & Detection Feed */}
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
                4. PROCESSED VIDEO & LIVE HUD DISPLAY
              </h3>
            </div>

            {snapshotResult ? (
              <span style={{ fontSize: '12px', color: '#10b981', fontWeight: 700 }}>
                ✔ LIVE SNAPSHOT CAPTURED ({snapshotResult.total_detections} OBJECTS, {snapshotResult.total_plates || 0} PLATES)
              </span>
            ) : jobState && (
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
            {/* 1. Live Snapshot Image */}
            {snapshotResult && snapshotResult.image ? (
              <img
                src={snapshotResult.image}
                alt="Live Camera Snapshot HUD"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            ) : isProcessing && jobState?.latest_frame_b64 ? (
              /* 2. Live Frame Base64 during processing */
              <img
                src={jobState.latest_frame_b64}
                alt="Live AI HUD"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            ) : jobState?.status === 'COMPLETED' && jobState.video_url ? (
              /* 3. In-Browser HTML5 H.264 Video Player */
              <video
                ref={videoPlayerRef}
                src={jobState.video_url}
                controls
                autoPlay
                loop
                playsInline
                style={{ width: '100%', height: '100%', objectFit: 'contain', backgroundColor: '#000000' }}
              />
            ) : (
              /* 4. Idle Standby Screen */
              <div style={{ textAlign: 'center', color: '#64748b' }}>
                <Video size={48} style={{ marginBottom: '12px', opacity: 0.4 }} />
                <p style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#94a3b8' }}>
                  Surveillance Stream Display Standby
                </p>
                <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#64748b' }}>
                  Select Sentinel Camera and click Live Snapshot or Start Processing
                </p>
              </div>
            )}
          </div>

          {/* Progress Bar & Playback Controls */}
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
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                  {/* Speed Controls */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '11px', color: '#94a3b8' }}>SPEED:</span>
                    {[0.5, 1.0, 2.0].map((spd) => (
                      <button
                        key={spd}
                        onClick={() => handleSetSpeed(spd)}
                        style={{
                          padding: '2px 8px',
                          borderRadius: '4px',
                          border: 'none',
                          backgroundColor: playbackSpeed === spd ? '#0284c7' : '#1e293b',
                          color: '#ffffff',
                          fontSize: '10px',
                          fontWeight: 700,
                          cursor: 'pointer',
                        }}
                      >
                        {spd}x
                      </button>
                    ))}
                    <button
                      onClick={() => {
                        if (videoPlayerRef.current) {
                          videoPlayerRef.current.currentTime = 0;
                          videoPlayerRef.current.play();
                        }
                      }}
                      style={{
                        padding: '2px 8px',
                        borderRadius: '4px',
                        border: 'none',
                        backgroundColor: '#1e293b',
                        color: '#94a3b8',
                        fontSize: '10px',
                        fontWeight: 700,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <RotateCcw size={10} />
                      <span>Replay</span>
                    </button>
                  </div>

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
            gap: '12px',
            maxHeight: '620px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={16} className="text-cyan" />
              <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 700, letterSpacing: '0.5px' }}>
                5. DETECTION FEED
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
              {recentDetections.length} DISPLAYED
            </span>
          </div>

          {/* Filter Bar */}
          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
            {['ALL', 'CARS', 'AUTOS', 'SCOOTERS', 'BIKES', 'BUSES', 'TRUCKS', 'PERSONS', 'PLATES'].map((flt) => (
              <button
                key={flt}
                onClick={() => setFeedFilter(flt)}
                style={{
                  padding: '3px 8px',
                  borderRadius: '4px',
                  border: 'none',
                  backgroundColor: feedFilter === flt ? '#0284c7' : '#0d1522',
                  color: feedFilter === flt ? '#ffffff' : '#94a3b8',
                  fontSize: '10px',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                {flt}
              </button>
            ))}
          </div>

          {/* Detection Events Column Header */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1.6fr 1fr 1fr',
              padding: '6px 10px',
              backgroundColor: '#0d1522',
              borderRadius: '6px',
              fontSize: '11px',
              fontWeight: 700,
              color: '#94a3b8',
            }}
          >
            <span>OBJECT & TRACK</span>
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
                No live detection events match filter. Start processing to stream events.
              </div>
            ) : (
              recentDetections
                .slice()
                .reverse()
                .map((ev, idx) => {
                  const isPlate = Boolean(ev.license_plate && ev.object_class === ev.license_plate);
                  const isCar = ev.object_class === 'CAR' || ev.vehicle_type?.toLowerCase() === 'car';
                  const isAutoRickshaw = ev.object_class === 'AUTO_RICKSHAW' || ev.vehicle_type?.toLowerCase().includes('rickshaw');
                  const nameLower = (ev.display_name || ev.vehicle_type || '').toLowerCase();
                  const isScooter = nameLower.includes('activa') || nameLower.includes('access') || nameLower.includes('jupiter') || nameLower.includes('scooter');
                  const isBike = nameLower.includes('splendor') || nameLower.includes('pulsar') || nameLower.includes('royal') || nameLower.includes('enfield') || nameLower.includes('shine') || nameLower.includes('apache') || (ev.object_class === 'MOTORCYCLE' && !isScooter);
                  const isBus = ev.object_class === 'BUS' || ev.vehicle_type?.toLowerCase() === 'bus';
                  const isTruck = ev.object_class === 'TRUCK' || ev.vehicle_type?.toLowerCase() === 'truck';
                  const isPerson = ev.object_class === 'PERSON';
                  const confPct = Math.round(ev.confidence * 100);

                  return (
                    <div
                      key={`${ev.id}-${idx}`}
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '1.6fr 1fr 1fr',
                        alignItems: 'center',
                        padding: '10px',
                        backgroundColor: '#0d1522',
                        border: isPlate ? '1px solid #ef4444' : '1px solid #1e293b',
                        borderRadius: '6px',
                        fontSize: '12px',
                        borderLeft: isPlate
                          ? '4px solid #ef4444'
                          : isAutoRickshaw
                          ? '4px solid #38bdf8'
                          : isScooter
                          ? '4px solid #06b6d4'
                          : isBike
                          ? '4px solid #c084fc'
                          : isCar
                          ? '4px solid #10b981'
                          : isBus
                          ? '4px solid #d97706'
                          : isTruck
                          ? '4px solid #f59e0b'
                          : isPerson
                          ? '4px solid #00f0ff'
                          : '4px solid #38bdf8',
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
                        ) : isAutoRickshaw ? (
                          <Car size={14} style={{ color: '#38bdf8' }} />
                        ) : isScooter ? (
                          <Bike size={14} style={{ color: '#06b6d4' }} />
                        ) : isBike ? (
                          <Bike size={14} style={{ color: '#c084fc' }} />
                        ) : isCar ? (
                          <Car size={14} style={{ color: '#10b981' }} />
                        ) : isBus ? (
                          <Bus size={14} style={{ color: '#d97706' }} />
                        ) : isTruck ? (
                          <Truck size={14} style={{ color: '#f59e0b' }} />
                        ) : isPerson ? (
                          <User size={14} style={{ color: '#00f0ff' }} />
                        ) : (
                          <Shield size={14} style={{ color: '#f59e0b' }} />
                        )}
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <strong
                            style={{
                              color: isPlate ? '#fca5a5' : '#f8fafc',
                              fontFamily: isPlate ? "'Courier New', monospace" : 'inherit',
                              fontSize: '12px',
                            }}
                          >
                            {ev.display_name || ev.object_class}
                          </strong>
                          {ev.track_id && (
                            <span style={{ fontSize: '10px', color: '#64748b' }}>
                              #TRK-{ev.track_id}
                            </span>
                          )}
                        </div>
                      </div>

                      <div style={{ textAlign: 'center' }}>
                        <span
                          style={{
                            color: confPct >= 75 ? '#34d399' : confPct >= 50 ? '#fbbf24' : '#f87171',
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
                          fontSize: '11px',
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
      {/* 5. Bottom Table: ANPR Results */}
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
                6. ANPR RESULTS TABLE (RECOGNIZED NUMBER PLATES)
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

