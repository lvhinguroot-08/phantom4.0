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
          setErrorMsg('Please select a video or image file to upload or choose a live Sentinel CCTV feed.');
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

      if (res && res.job_id) {
        setCurrentJobId(res.job_id);
        connectJobWebSocket(res.job_id);
        startJobPolling(res.job_id);
      } else {
        setErrorMsg('Invalid response from AI inference backend.');
        setIsProcessing(false);
      }
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to start AI video processing job.');
      setIsProcessing(false);
    }
  };

  const handleStopProcessing = () => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    if (wsRef.current) wsRef.current.close();
    setIsProcessing(false);
  };

  const connectJobWebSocket = (jobId: string) => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/api/process/${jobId}/ws`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data && data.job_id) {
            setJobState(data);
            if (data.status === 'COMPLETED' || data.status === 'FAILED') {
              setIsProcessing(false);
              if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            }
          }
        } catch (_) {}
      };

      ws.onerror = () => {
        // Fallback to polling handled smoothly
      };
    } catch (_) {}
  };

  const startJobPolling = (jobId: string) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

    pollIntervalRef.current = window.setInterval(async () => {
      try {
        const state = await aiTestingApi.getJobResults(jobId);
        if (state) {
          setJobState(state);
          if (state.status === 'COMPLETED' || state.status === 'FAILED') {
            setIsProcessing(false);
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          }
        }
      } catch (_) {}
    }, 1500);
  };

  const handleSetSpeed = (spd: number) => {
    setPlaybackSpeed(spd);
    if (videoPlayerRef.current) {
      videoPlayerRef.current.playbackRate = spd;
    }
  };

  const handleExportCsv = () => {
    if (!filteredPlates || filteredPlates.length === 0) return;
    const headers = ['ID', 'Plate Number', 'Confidence %', 'Timestamp', 'Vehicle Class', 'RTO Jurisdiction', 'Total Sightings'];
    const rows = filteredPlates.map((p) => [
      p.id,
      `"${p.plate_number}"`,
      `${Math.round(p.confidence * 100)}%`,
      `"${p.time_str}"`,
      `"${p.vehicle}"`,
      `"${p.rto_jurisdiction || 'Gujarat State'}"`,
      p.total_sightings,
    ]);

    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `ANPR_RECOGNIZED_PLATES_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Mock initial demo analytics if idle
  const analytics: ObjectAnalytics = jobState?.analytics || snapshotResult?.analytics || {
    total_objects_tracked: 28,
    cars_count: 14,
    trucks_count: 3,
    buses_count: 2,
    motorcycles_count: 7,
    pedestrians_count: 2,
    bicycles_count: 0,
    unique_vehicles_count: 19,
    peak_frame_density: 8,
    avg_confidence_pct: 88.5,
    congestion_level: 'MODERATE',
  };

  // Mock initial recent detections
  const recentDetections: DetectionEvent[] = jobState?.recent_detections || snapshotResult?.detections || [
    {
      id: 'det-1',
      object_class: 'CAR',
      display_name: 'White Sedan (Car)',
      confidence: 0.94,
      bbox: { x1: 120, y1: 240, x2: 380, y2: 460 },
      time_str: '14:28:10 IST',
      track_id: 104,
      vehicle_type: 'Sedan',
    },
    {
      id: 'det-2',
      object_class: 'AUTO_RICKSHAW',
      display_name: 'Bajaj RE Auto Rickshaw',
      confidence: 0.89,
      bbox: { x1: 420, y1: 310, x2: 600, y2: 520 },
      time_str: '14:28:11 IST',
      track_id: 105,
      vehicle_type: 'Auto',
    },
    {
      id: 'det-3',
      object_class: 'MOTORCYCLE',
      display_name: 'Hero Splendor (Bike)',
      confidence: 0.91,
      bbox: { x1: 650, y1: 350, x2: 780, y2: 530 },
      time_str: '14:28:12 IST',
      track_id: 106,
      vehicle_type: 'Motorcycle',
    },
    {
      id: 'det-4',
      object_class: 'TRUCK',
      display_name: 'Tata Heavy Cargo Truck',
      confidence: 0.88,
      bbox: { x1: 820, y1: 180, x2: 1100, y2: 590 },
      time_str: '14:28:13 IST',
      track_id: 107,
      vehicle_type: 'Heavy Truck',
    },
    {
      id: 'det-5',
      object_class: 'GJ-01-AB-1234',
      display_name: 'Plate: GJ-01-AB-1234',
      confidence: 0.95,
      bbox: { x1: 220, y1: 380, x2: 320, y2: 410 },
      time_str: '14:28:14 IST',
      track_id: 104,
      license_plate: 'GJ-01-AB-1234',
      vehicle_type: 'Car',
    },
  ];

  // Mock initial recognized plates
  const anprResults: ANPRTableItem[] = jobState?.anpr_results || snapshotResult?.plates || [
    {
      id: 'anpr-1',
      plate_number: 'GJ 01 AB 1234',
      confidence: 0.95,
      time_str: '14:28:10 IST',
      vehicle: 'Car (Sedan)',
      rto_jurisdiction: 'GJ-01: Ahmedabad City',
      total_sightings: 4,
    },
    {
      id: 'anpr-2',
      plate_number: 'GJ 05 CD 5678',
      confidence: 0.92,
      time_str: '14:28:11 IST',
      vehicle: 'Auto Rickshaw',
      rto_jurisdiction: 'GJ-05: Surat City',
      total_sightings: 2,
    },
    {
      id: 'anpr-3',
      plate_number: 'GJ 03 EF 9012',
      confidence: 0.89,
      time_str: '14:28:12 IST',
      vehicle: 'Motorcycle',
      rto_jurisdiction: 'GJ-03: Rajkot',
      total_sightings: 3,
    },
    {
      id: 'anpr-4',
      plate_number: 'GJ 06 GH 3456',
      confidence: 0.88,
      time_str: '14:28:13 IST',
      vehicle: 'Heavy Truck',
      rto_jurisdiction: 'GJ-06: Vadodara',
      total_sightings: 1,
    },
  ];

  // Filter ANPR table
  const filteredPlates = anprResults.filter((p) => {
    if (!tableSearch) return true;
    const q = tableSearch.toLowerCase();
    return (
      p.plate_number.toLowerCase().includes(q) ||
      p.vehicle.toLowerCase().includes(q) ||
      (p.rto_jurisdiction && p.rto_jurisdiction.toLowerCase().includes(q))
    );
  });

  // Filter Detection Events feed
  const filteredDetections = recentDetections.filter((ev) => {
    if (feedFilter === 'ALL') return true;
    if (feedFilter === 'CARS') return ev.object_class === 'CAR' || ev.vehicle_type?.toLowerCase() === 'car' || ev.vehicle_type?.toLowerCase() === 'sedan' || ev.vehicle_type?.toLowerCase() === 'suv';
    if (feedFilter === 'AUTOS') return ev.object_class === 'AUTO_RICKSHAW' || ev.vehicle_type?.toLowerCase().includes('auto') || ev.display_name?.toLowerCase().includes('auto');
    if (feedFilter === 'SCOOTERS') return ev.display_name?.toLowerCase().includes('scooter') || ev.display_name?.toLowerCase().includes('activa') || ev.display_name?.toLowerCase().includes('access');
    if (feedFilter === 'BIKES') return ev.object_class === 'MOTORCYCLE' || ev.vehicle_type?.toLowerCase() === 'motorcycle' || ev.display_name?.toLowerCase().includes('splendor') || ev.display_name?.toLowerCase().includes('bullet') || ev.display_name?.toLowerCase().includes('pulsar') || ev.display_name?.toLowerCase().includes('enfield');
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
        color: 'var(--text-primary)',
        fontFamily: 'var(--font-body)',
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
          background: 'var(--bg-card)',
          backdropFilter: 'var(--glass-blur)',
          WebkitBackdropFilter: 'var(--glass-blur)',
          border: '1px solid var(--border-medium)',
          borderRadius: 'var(--radius-lg)',
          padding: '18px 24px',
          boxShadow: 'var(--card-shadow)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            style={{
              width: '46px',
              height: '46px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--accent-purple-dim)',
              border: '1px solid var(--border-active)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent-purple)',
              boxShadow: 'var(--accent-purple-glow)',
            }}
          >
            <Shield size={24} className="animate-pulse" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1
                style={{
                  margin: 0,
                  fontSize: '1.25rem',
                  fontWeight: 900,
                  fontFamily: 'var(--font-heading)',
                  letterSpacing: '1.5px',
                  color: '#ffffff',
                }}
              >
                PHANTOM // AI INTELLIGENCE & REAL-WORLD TESTING
              </h1>
              <span
                style={{
                  background: 'var(--accent-purple-dim)',
                  border: '1px solid var(--border-active)',
                  color: 'var(--accent-purple)',
                  fontSize: '0.72rem',
                  fontWeight: 800,
                  padding: '3px 8px',
                  borderRadius: 'var(--radius-sm)',
                  fontFamily: 'var(--font-mono)',
                  letterSpacing: '0.5px',
                }}
              >
                YOLO + ANPR INFERENCE
              </span>
            </div>
            <p
              style={{
                margin: '4px 0 0',
                fontSize: '0.82rem',
                color: 'var(--text-muted)',
                fontFamily: 'var(--font-body)',
              }}
            >
              Gujarat Police Statewide Computer Vision & Automated License Plate Recognition Suite
            </p>
          </div>
        </div>

        {/* System Telemetry Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              padding: '6px 14px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-subtle)',
              fontSize: '0.78rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontFamily: 'var(--font-mono)',
            }}
          >
            <Cpu size={14} style={{ color: 'var(--accent-purple)' }} />
            <span style={{ color: 'var(--text-muted)' }}>ENGINE:</span>
            <strong style={{ color: 'var(--accent-purple)' }}>YOLOv8 + EasyOCR</strong>
          </div>

          <div
            style={{
              padding: '6px 14px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-subtle)',
              fontSize: '0.78rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontFamily: 'var(--font-mono)',
            }}
          >
            <Activity size={14} style={{ color: isProcessing ? 'var(--accent-purple)' : 'var(--accent-healthy)' }} />
            <span style={{ color: 'var(--text-muted)' }}>STATUS:</span>
            <strong style={{ color: isProcessing ? 'var(--accent-purple)' : 'var(--accent-healthy)' }}>
              {isProcessing ? 'PROCESSING ACTIVE' : 'SYSTEM READY'}
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
            background: 'var(--bg-card)',
            backdropFilter: 'var(--glass-blur)',
            WebkitBackdropFilter: 'var(--glass-blur)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
            boxShadow: 'var(--card-shadow)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={16} style={{ color: 'var(--accent-purple)' }} />
            <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 800, fontFamily: 'var(--font-tactical)', letterSpacing: '1px' }}>
              1. SELECT AI AGENT / MODEL
            </h3>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
            <button
              onClick={() => setAiMode('yolo')}
              style={{
                padding: '14px 10px',
                borderRadius: 'var(--radius-md)',
                border: aiMode === 'yolo' ? '1px solid var(--accent-purple)' : '1px solid var(--border-subtle)',
                background: aiMode === 'yolo' ? 'var(--accent-purple-dim)' : 'var(--bg-secondary)',
                color: aiMode === 'yolo' ? 'var(--accent-purple)' : 'var(--text-secondary)',
                fontWeight: 800,
                fontSize: '0.82rem',
                fontFamily: 'var(--font-tactical)',
                letterSpacing: '0.5px',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s',
                boxShadow: aiMode === 'yolo' ? 'var(--accent-purple-glow)' : 'none',
              }}
            >
              <User size={20} />
              <span>YOLO</span>
              <span style={{ fontSize: '0.68rem', opacity: 0.8, fontFamily: 'var(--font-mono)' }}>Object / Person</span>
            </button>

            <button
              onClick={() => setAiMode('anpr')}
              style={{
                padding: '14px 10px',
                borderRadius: 'var(--radius-md)',
                border: aiMode === 'anpr' ? '1px solid var(--accent-blue)' : '1px solid var(--border-subtle)',
                background: aiMode === 'anpr' ? 'var(--accent-blue-dim)' : 'var(--bg-secondary)',
                color: aiMode === 'anpr' ? 'var(--accent-blue)' : 'var(--text-secondary)',
                fontWeight: 800,
                fontSize: '0.82rem',
                fontFamily: 'var(--font-tactical)',
                letterSpacing: '0.5px',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s',
                boxShadow: aiMode === 'anpr' ? '0 0 16px var(--accent-blue-dim)' : 'none',
              }}
            >
              <Car size={20} />
              <span>ANPR</span>
              <span style={{ fontSize: '0.68rem', opacity: 0.8, fontFamily: 'var(--font-mono)' }}>Number Plates</span>
            </button>

            <button
              onClick={() => setAiMode('yolo_anpr')}
              style={{
                padding: '14px 10px',
                borderRadius: 'var(--radius-md)',
                border: aiMode === 'yolo_anpr' ? '1px solid var(--accent-healthy)' : '1px solid var(--border-subtle)',
                background: aiMode === 'yolo_anpr' ? 'var(--accent-healthy-dim)' : 'var(--bg-secondary)',
                color: aiMode === 'yolo_anpr' ? 'var(--accent-healthy)' : 'var(--text-secondary)',
                fontWeight: 800,
                fontSize: '0.82rem',
                fontFamily: 'var(--font-tactical)',
                letterSpacing: '0.5px',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s',
                boxShadow: aiMode === 'yolo_anpr' ? '0 0 16px var(--accent-healthy-dim)' : 'none',
              }}
            >
              <Sparkles size={20} />
              <span>YOLO + ANPR</span>
              <span style={{ fontSize: '0.68rem', opacity: 0.9, fontFamily: 'var(--font-mono)' }}>Unified Pipeline</span>
            </button>
          </div>

          {/* Quick Info */}
          <div
            style={{
              padding: '10px 14px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-input)',
              fontSize: '0.78rem',
              color: 'var(--text-secondary)',
              lineHeight: 1.5,
              borderLeft: '3px solid var(--accent-purple)',
              fontFamily: 'var(--font-body)',
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
            background: 'var(--bg-card)',
            backdropFilter: 'var(--glass-blur)',
            WebkitBackdropFilter: 'var(--glass-blur)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
            boxShadow: 'var(--card-shadow)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Video size={16} style={{ color: 'var(--accent-purple)' }} />
              <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 800, fontFamily: 'var(--font-tactical)', letterSpacing: '1px' }}>
                2. VIDEO INPUT & INFERENCE CONTROLS
              </h3>
            </div>

            {/* Source Mode Toggle */}
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                onClick={() => { setSelectedSource('sentinel_grid'); setSnapshotResult(null); }}
                style={{
                  padding: '5px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: selectedSource === 'sentinel_grid' ? '1px solid var(--accent-purple)' : '1px solid var(--border-subtle)',
                  background: selectedSource === 'sentinel_grid' ? 'var(--accent-purple-dim)' : 'var(--bg-secondary)',
                  color: selectedSource === 'sentinel_grid' ? 'var(--accent-purple)' : 'var(--text-secondary)',
                  fontSize: '0.74rem',
                  fontWeight: 800,
                  fontFamily: 'var(--font-tactical)',
                  letterSpacing: '0.5px',
                  cursor: 'pointer',
                }}
              >
                Live Sentinel Stream (10-15s Capture)
              </button>
              <button
                onClick={() => { setSelectedSource('sample'); setSnapshotResult(null); }}
                style={{
                  padding: '5px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: selectedSource === 'sample' ? '1px solid var(--accent-purple)' : '1px solid var(--border-subtle)',
                  background: selectedSource === 'sample' ? 'var(--accent-purple-dim)' : 'var(--bg-secondary)',
                  color: selectedSource === 'sample' ? 'var(--accent-purple)' : 'var(--text-secondary)',
                  fontSize: '0.74rem',
                  fontWeight: 800,
                  fontFamily: 'var(--font-tactical)',
                  letterSpacing: '0.5px',
                  cursor: 'pointer',
                }}
              >
                Captured CCTV Clips
              </button>
              <button
                onClick={() => { setSelectedSource('upload'); setSnapshotResult(null); }}
                style={{
                  padding: '5px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: selectedSource === 'upload' ? '1px solid var(--accent-purple)' : '1px solid var(--border-subtle)',
                  background: selectedSource === 'upload' ? 'var(--accent-purple-dim)' : 'var(--bg-secondary)',
                  color: selectedSource === 'upload' ? 'var(--accent-purple)' : 'var(--text-secondary)',
                  fontSize: '0.74rem',
                  fontWeight: 800,
                  fontFamily: 'var(--font-tactical)',
                  letterSpacing: '0.5px',
                  cursor: 'pointer',
                }}
              >
                Upload File (Video / Image)
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
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-medium)',
                    color: 'var(--text-primary)',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.84rem',
                    fontWeight: 700,
                    fontFamily: 'var(--font-heading)',
                  }}
                >
                  {sentinelCameras.length > 0 ? (
                    sentinelCameras.map((cam) => (
                      <option key={cam.id} value={cam.id} style={{ background: '#0a101d', color: '#fff' }}>
                        [{cam.id.toUpperCase()}] {cam.name} — {cam.district}
                      </option>
                    ))
                  ) : (
                    <option value="cam01" style={{ background: '#0a101d', color: '#fff' }}>[CAM01] 01 Chiman bhai Bridge — Ahmedabad</option>
                  )}
                </select>

                <button
                  onClick={handleLiveSnapshot}
                  disabled={isTakingSnapshot || isProcessing}
                  style={{
                    padding: '8px 16px',
                    background: 'var(--accent-blue-dim)',
                    border: '1px solid var(--accent-blue)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--accent-blue)',
                    fontSize: '0.78rem',
                    fontWeight: 800,
                    fontFamily: 'var(--font-mono)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    opacity: isTakingSnapshot ? 0.7 : 1,
                    boxShadow: '0 0 12px var(--accent-blue-dim)',
                  }}
                >
                  <Activity size={14} className={isTakingSnapshot ? 'animate-spin' : ''} />
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
                      borderRadius: 'var(--radius-sm)',
                      background: 'var(--bg-secondary)',
                      border: '1px solid var(--border-subtle)',
                      fontSize: '0.75rem',
                      color: 'var(--text-muted)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '8px',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    <span>
                      LIVE STREAM:{' '}
                      <code style={{ color: 'var(--accent-purple)' }}>
                        {selectedCameraId.toUpperCase()} (HLS Direct Capture)
                      </code>
                    </span>
                    <span style={{ color: 'var(--accent-healthy)', fontWeight: 800 }}>
                      ● SENTINEL ONLINE (Live 10-15s Direct Ingestion)
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
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border-medium)',
                  color: 'var(--text-primary)',
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.84rem',
                  fontFamily: 'var(--font-heading)',
                }}
              >
                <option value="cam01_sample" style={{ background: '#0a101d', color: '#fff' }}>cam01_sample.mp4 — Ahmedabad Chiman bhai Bridge (Real Footage)</option>
                <option value="cam02_sample" style={{ background: '#0a101d', color: '#fff' }}>cam02_sample.mp4 — Ahmedabad Janpath (Real Footage)</option>
                <option value="cam04_sample" style={{ background: '#0a101d', color: '#fff' }}>cam04_sample.mp4 — Ahmedabad Paldi Circle (Real Footage)</option>
                <option value="cam06_sample" style={{ background: '#0a101d', color: '#fff' }}>cam06_sample.mp4 — Junagadh Timbavadi Gate (Real Footage)</option>
                <option value="cam17_sample" style={{ background: '#0a101d', color: '#fff' }}>cam17_sample.mp4 — Rajkot Bus Port CCTV (Real Footage)</option>
                <option value="sample_traffic_cctv" style={{ background: '#0a101d', color: '#fff' }}>sample_traffic_cctv.mp4 — Surat Multi-Vehicle Traffic</option>
              </select>
            </div>
          ) : (
            <div
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: '2px dashed var(--border-medium)',
                borderRadius: 'var(--radius-md)',
                padding: '14px',
                textAlign: 'center',
                background: 'var(--bg-input)',
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
                accept="video/*,image/*"
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
              <Upload size={20} style={{ color: 'var(--accent-purple)' }} />
              <div>
                <strong style={{ color: 'var(--accent-purple)', fontSize: '0.84rem', fontFamily: 'var(--font-mono)' }}>
                  {uploadedFileName || 'Click to browse video or image file'}
                </strong>
                <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Supports MP4, AVI, MOV, MKV, WebM, JPG, PNG, WEBP
                </p>
              </div>
            </div>
          )}

          {/* Sliders & Action Buttons Row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px', flexWrap: 'wrap' }}>
            {/* FPS Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-tactical)', fontWeight: 700 }}>RATE:</span>
              <select
                value={sampleFps}
                onChange={(e) => setSampleFps(Number(e.target.value))}
                style={{
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border-medium)',
                  color: 'var(--text-primary)',
                  padding: '6px 10px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.78rem',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                <option value={2.0} style={{ background: '#0a101d', color: '#fff' }}>2 FPS (Fast)</option>
                <option value={5.0} style={{ background: '#0a101d', color: '#fff' }}>5 FPS (Balanced)</option>
                <option value={10.0} style={{ background: '#0a101d', color: '#fff' }}>10 FPS (High-Density)</option>
                <option value={25.0} style={{ background: '#0a101d', color: '#fff' }}>All Frames (25 FPS)</option>
              </select>
            </div>

            {/* Threshold Slider */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: '160px' }}>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-tactical)', fontWeight: 700 }}>CONF:</span>
              <input
                type="range"
                min="0.10"
                max="0.80"
                step="0.05"
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                style={{ flex: 1, accentColor: 'var(--accent-purple)', cursor: 'pointer' }}
              />
              <span style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--accent-purple)', fontFamily: 'var(--font-mono)', minWidth: '35px' }}>
                {(confidenceThreshold * 100).toFixed(0)}%
              </span>
            </div>

            {/* Buttons */}
            {!isProcessing ? (
              <button
                onClick={handleStartProcessing}
                style={{
                  padding: '10px 22px',
                  background: 'linear-gradient(135deg, #a855f7 0%, #7c3aed 100%)',
                  border: 'none',
                  borderRadius: 'var(--radius-sm)',
                  color: '#ffffff',
                  fontWeight: 900,
                  fontSize: '0.84rem',
                  fontFamily: 'var(--font-tactical)',
                  letterSpacing: '1px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: 'var(--accent-purple-glow)',
                  transition: 'all 0.2s',
                }}
              >
                <Play size={16} fill="#ffffff" />
                <span>{selectedSource === 'sentinel_grid' ? 'CAPTURE & PROCESS LIVE FEED (10-15s)' : 'START PROCESSING'}</span>
              </button>
            ) : (
              <button
                onClick={handleStopProcessing}
                style={{
                  padding: '10px 22px',
                  background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                  border: 'none',
                  borderRadius: 'var(--radius-sm)',
                  color: '#ffffff',
                  fontWeight: 900,
                  fontSize: '0.84rem',
                  fontFamily: 'var(--font-tactical)',
                  letterSpacing: '1px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: '0 0 16px var(--accent-danger-dim)',
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
                background: 'var(--accent-danger-dim)',
                border: '1px solid var(--accent-danger)',
                borderRadius: 'var(--radius-sm)',
                color: '#fca5a5',
                fontSize: '0.78rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontFamily: 'var(--font-mono)',
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
          background: 'var(--bg-card)',
          backdropFilter: 'var(--glass-blur)',
          WebkitBackdropFilter: 'var(--glass-blur)',
          border: '1px solid var(--border-medium)',
          borderRadius: 'var(--radius-lg)',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          boxShadow: 'var(--card-shadow)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <BarChart3 size={18} style={{ color: 'var(--accent-purple)' }} />
            <div>
              <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 800, fontFamily: 'var(--font-tactical)', letterSpacing: '1px' }}>
                3. REAL-TIME OBJECT & TRAFFIC ANALYTICS
              </h3>
              <p style={{ margin: '2px 0 0', fontSize: '0.76rem', color: 'var(--text-muted)', fontFamily: 'var(--font-body)' }}>
                Continuous vehicle velocity, density distribution, and classification telemetry
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)', fontFamily: 'var(--font-tactical)', fontWeight: 700 }}>CONGESTION LEVEL:</span>
            <span
              style={{
                padding: '4px 10px',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.74rem',
                fontWeight: 800,
                letterSpacing: '0.5px',
                fontFamily: 'var(--font-mono)',
                background:
                  analytics.congestion_level === 'HIGH'
                    ? 'var(--accent-danger-dim)'
                    : analytics.congestion_level === 'MODERATE'
                    ? 'var(--accent-attention-dim)'
                    : 'var(--accent-healthy-dim)',
                color:
                  analytics.congestion_level === 'HIGH'
                    ? '#f87171'
                    : analytics.congestion_level === 'MODERATE'
                    ? '#fbbf24'
                    : '#34d399',
                border:
                  analytics.congestion_level === 'HIGH'
                    ? '1px solid var(--accent-danger)'
                    : analytics.congestion_level === 'MODERATE'
                    ? '1px solid var(--accent-attention)'
                    : '1px solid var(--accent-healthy)',
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
              padding: '16px',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700, fontFamily: 'var(--font-tactical)' }}>TOTAL VEHICLES</span>
              <Car size={16} style={{ color: 'var(--accent-purple)' }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span style={{ fontSize: '1.6rem', fontWeight: 900, color: 'var(--text-primary)', fontFamily: 'var(--font-heading)' }}>
                {analytics.cars_count + analytics.buses_count + analytics.trucks_count + analytics.motorcycles_count}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--accent-purple)', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>
                ({analytics.unique_vehicles_count} Unique)
              </span>
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-body)' }}>
              {analytics.cars_count} Cars • {analytics.trucks_count} Trucks • {analytics.buses_count} Buses
            </span>
          </div>

          {/* 2. Peak Density */}
          <div
            style={{
              padding: '16px',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700, fontFamily: 'var(--font-tactical)' }}>PEAK SCENE DENSITY</span>
              <TrendingUp size={16} style={{ color: 'var(--accent-healthy)' }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span style={{ fontSize: '1.6rem', fontWeight: 900, color: 'var(--accent-healthy)', fontFamily: 'var(--font-heading)' }}>
                {analytics.peak_frame_density}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-body)' }}>concurrent objects</span>
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-body)' }}>
              Max simultaneous detections in 1 frame
            </span>
          </div>

          {/* 3. Model Confidence */}
          <div
            style={{
              padding: '16px',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700, fontFamily: 'var(--font-tactical)' }}>AVG MODEL CONFIDENCE</span>
              <Gauge size={16} style={{ color: 'var(--accent-attention)' }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span style={{ fontSize: '1.6rem', fontWeight: 900, color: 'var(--accent-attention)', fontFamily: 'var(--font-heading)' }}>
                {analytics.avg_confidence_pct}%
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-body)' }}>certainty</span>
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-body)' }}>
              Mean score across YOLO inference passes
            </span>
          </div>

          {/* 4. Number Plates Identified */}
          <div
            style={{
              padding: '16px',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700, fontFamily: 'var(--font-tactical)' }}>ANPR PLATES FOUND</span>
              <Zap size={16} style={{ color: 'var(--accent-blue)' }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span style={{ fontSize: '1.6rem', fontWeight: 900, color: 'var(--accent-blue)', fontFamily: 'var(--font-heading)' }}>
                {anprResults.length}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-body)' }}>recognized</span>
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-body)' }}>
              Gujarat RTO & Indian registration plates
            </span>
          </div>
        </div>

        {/* Object Classification Matrix Breakdown */}
        <div
          style={{
            padding: '16px',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--text-primary)', fontFamily: 'var(--font-tactical)', letterSpacing: '0.5px' }}>
              VEHICLE & OBJECT CLASSIFICATION MATRIX
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {analytics.total_objects_tracked} Total Frames Detected
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '12px' }}>
            {/* Cars */}
            <div style={{ background: 'var(--bg-tertiary)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-healthy)', fontSize: '0.75rem', fontWeight: 800, fontFamily: 'var(--font-tactical)' }}>
                <Car size={14} />
                <span>CARS</span>
              </div>
              <div style={{ fontSize: '1.2rem', fontWeight: 900, marginTop: '4px', fontFamily: 'var(--font-heading)' }}>{analytics.cars_count}</div>
              <div style={{ height: '4px', background: 'rgba(255,255,255,0.06)', borderRadius: '2px', marginTop: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${analytics.total_objects_tracked ? (analytics.cars_count / analytics.total_objects_tracked) * 100 : 0}%`, height: '100%', background: 'var(--accent-healthy)' }} />
              </div>
            </div>

            {/* Trucks */}
            <div style={{ background: 'var(--bg-tertiary)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-attention)', fontSize: '0.75rem', fontWeight: 800, fontFamily: 'var(--font-tactical)' }}>
                <Truck size={14} />
                <span>TRUCKS</span>
              </div>
              <div style={{ fontSize: '1.2rem', fontWeight: 900, marginTop: '4px', fontFamily: 'var(--font-heading)' }}>{analytics.trucks_count}</div>
              <div style={{ height: '4px', background: 'rgba(255,255,255,0.06)', borderRadius: '2px', marginTop: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${analytics.total_objects_tracked ? (analytics.trucks_count / analytics.total_objects_tracked) * 100 : 0}%`, height: '100%', background: 'var(--accent-attention)' }} />
              </div>
            </div>

            {/* Buses */}
            <div style={{ background: 'var(--bg-tertiary)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-warning)', fontSize: '0.75rem', fontWeight: 800, fontFamily: 'var(--font-tactical)' }}>
                <Bus size={14} />
                <span>BUSES</span>
              </div>
              <div style={{ fontSize: '1.2rem', fontWeight: 900, marginTop: '4px', fontFamily: 'var(--font-heading)' }}>{analytics.buses_count}</div>
              <div style={{ height: '4px', background: 'rgba(255,255,255,0.06)', borderRadius: '2px', marginTop: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${analytics.total_objects_tracked ? (analytics.buses_count / analytics.total_objects_tracked) * 100 : 0}%`, height: '100%', background: 'var(--accent-warning)' }} />
              </div>
            </div>

            {/* Motorcycles */}
            <div style={{ background: 'var(--bg-tertiary)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-purple)', fontSize: '0.75rem', fontWeight: 800, fontFamily: 'var(--font-tactical)' }}>
                <Bike size={14} />
                <span>2-WHEELERS</span>
              </div>
              <div style={{ fontSize: '1.2rem', fontWeight: 900, marginTop: '4px', fontFamily: 'var(--font-heading)' }}>{analytics.motorcycles_count}</div>
              <div style={{ height: '4px', background: 'rgba(255,255,255,0.06)', borderRadius: '2px', marginTop: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${analytics.total_objects_tracked ? (analytics.motorcycles_count / analytics.total_objects_tracked) * 100 : 0}%`, height: '100%', background: 'var(--accent-purple)' }} />
              </div>
            </div>

            {/* Pedestrians */}
            <div style={{ background: 'var(--bg-tertiary)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-blue)', fontSize: '0.75rem', fontWeight: 800, fontFamily: 'var(--font-tactical)' }}>
                <User size={14} />
                <span>PERSONS</span>
              </div>
              <div style={{ fontSize: '1.2rem', fontWeight: 900, marginTop: '4px', fontFamily: 'var(--font-heading)' }}>{analytics.pedestrians_count}</div>
              <div style={{ height: '4px', background: 'rgba(255,255,255,0.06)', borderRadius: '2px', marginTop: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${analytics.total_objects_tracked ? (analytics.pedestrians_count / analytics.total_objects_tracked) * 100 : 0}%`, height: '100%', background: 'var(--accent-blue)' }} />
              </div>
            </div>

            {/* Bicycles */}
            <div style={{ background: 'var(--bg-tertiary)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#facc15', fontSize: '0.75rem', fontWeight: 800, fontFamily: 'var(--font-tactical)' }}>
                <Activity size={14} />
                <span>BICYCLES</span>
              </div>
              <div style={{ fontSize: '1.2rem', fontWeight: 900, marginTop: '4px', fontFamily: 'var(--font-heading)' }}>{analytics.bicycles_count}</div>
              <div style={{ height: '4px', background: 'rgba(255,255,255,0.06)', borderRadius: '2px', marginTop: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${analytics.total_objects_tracked ? (analytics.bicycles_count / analytics.total_objects_tracked) * 100 : 0}%`, height: '100%', background: '#facc15' }} />
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
            background: 'var(--bg-card)',
            backdropFilter: 'var(--glass-blur)',
            WebkitBackdropFilter: 'var(--glass-blur)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
            boxShadow: 'var(--card-shadow)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Eye size={16} style={{ color: 'var(--accent-purple)' }} />
              <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 800, fontFamily: 'var(--font-tactical)', letterSpacing: '1px' }}>
                4. PROCESSED VIDEO & LIVE HUD DISPLAY
              </h3>
            </div>

            {snapshotResult ? (
              <span style={{ fontSize: '0.78rem', color: 'var(--accent-healthy)', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>
                ✔ LIVE SNAPSHOT CAPTURED ({snapshotResult.total_detections} OBJECTS, {snapshotResult.total_plates || 0} PLATES)
              </span>
            ) : jobState && (
              <span style={{ fontSize: '0.78rem', color: 'var(--accent-purple)', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>
                {jobState.status === 'PROCESSING' && (
                  <span className="animate-pulse">● LIVE INFERENCE ({jobState.progress_percent}%)</span>
                )}
                {jobState.status === 'COMPLETED' && (
                  <span style={{ color: 'var(--accent-healthy)' }}>✔ PROCESSING COMPLETE (100%)</span>
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
              background: '#000000',
              borderRadius: 'var(--radius-md)',
              overflow: 'hidden',
              border: '1px solid var(--border-medium)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 8px 30px rgba(0,0,0,0.8)',
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
              <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                <Video size={48} style={{ marginBottom: '12px', opacity: 0.3 }} />
                <p style={{ margin: 0, fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-tactical)', letterSpacing: '0.5px' }}>
                  Surveillance Stream Display Standby
                </p>
                <p style={{ margin: '4px 0 0', fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-body)' }}>
                  Select Sentinel Camera and click Live Snapshot or Start Processing
                </p>
              </div>
            )}
          </div>

          {/* Progress Bar & Playback Controls */}
          {jobState && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', fontFamily: 'var(--font-mono)' }}>
                <span style={{ color: 'var(--text-muted)' }}>
                  Frames: <strong style={{ color: 'var(--text-primary)' }}>{jobState.frames_processed}</strong> / {jobState.total_frames}
                </span>
                <span style={{ color: 'var(--accent-purple)', fontWeight: 800 }}>
                  {jobState.progress_percent.toFixed(1)}%
                </span>
                <span style={{ color: 'var(--text-muted)' }}>
                  Speed: <strong style={{ color: 'var(--text-primary)' }}>{jobState.processing_fps} FPS</strong> | Elapsed:{' '}
                  <strong style={{ color: 'var(--text-primary)' }}>{jobState.elapsed_seconds}s</strong>
                </span>
              </div>

              <div
                style={{
                  width: '100%',
                  height: '6px',
                  background: 'var(--bg-secondary)',
                  borderRadius: '3px',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${jobState.progress_percent}%`,
                    background: jobState.status === 'COMPLETED' ? 'var(--accent-healthy)' : 'var(--accent-purple)',
                    transition: 'width 0.3s ease',
                  }}
                />
              </div>

              {jobState.status === 'COMPLETED' && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                  {/* Speed Controls */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontFamily: 'var(--font-tactical)', fontWeight: 700 }}>SPEED:</span>
                    {[0.5, 1.0, 2.0].map((spd) => (
                      <button
                        key={spd}
                        onClick={() => handleSetSpeed(spd)}
                        style={{
                          padding: '2px 8px',
                          borderRadius: 'var(--radius-sm)',
                          border: 'none',
                          background: playbackSpeed === spd ? 'var(--accent-purple)' : 'var(--bg-secondary)',
                          color: '#ffffff',
                          fontSize: '0.72rem',
                          fontWeight: 800,
                          fontFamily: 'var(--font-mono)',
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
                        borderRadius: 'var(--radius-sm)',
                        border: 'none',
                        background: 'var(--bg-secondary)',
                        color: 'var(--text-muted)',
                        fontSize: '0.72rem',
                        fontWeight: 800,
                        fontFamily: 'var(--font-mono)',
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
                      background: 'var(--accent-healthy-dim)',
                      border: '1px solid var(--accent-healthy)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--accent-healthy)',
                      fontSize: '0.78rem',
                      fontWeight: 800,
                      fontFamily: 'var(--font-tactical)',
                      textDecoration: 'none',
                      boxShadow: '0 0 12px var(--accent-healthy-dim)',
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
            background: 'var(--bg-card)',
            backdropFilter: 'var(--glass-blur)',
            WebkitBackdropFilter: 'var(--glass-blur)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            maxHeight: '620px',
            boxShadow: 'var(--card-shadow)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={16} style={{ color: 'var(--accent-purple)' }} />
              <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 800, fontFamily: 'var(--font-tactical)', letterSpacing: '1px' }}>
                5. DETECTION FEED
              </h3>
            </div>
            <span
              style={{
                fontSize: '0.74rem',
                background: 'var(--accent-purple-dim)',
                border: '1px solid var(--border-active)',
                padding: '2px 8px',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--accent-purple)',
                fontWeight: 800,
                fontFamily: 'var(--font-mono)',
              }}
            >
              {recentDetections.length} DISPLAYED
            </span>
          </div>

          {/* Filter Bar */}
          <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
            {['ALL', 'CARS', 'AUTOS', 'SCOOTERS', 'BIKES', 'BUSES', 'TRUCKS', 'PERSONS', 'PLATES'].map((flt) => (
              <button
                key={flt}
                onClick={() => setFeedFilter(flt)}
                style={{
                  padding: '3px 8px',
                  borderRadius: 'var(--radius-sm)',
                  border: feedFilter === flt ? '1px solid var(--accent-purple)' : '1px solid var(--border-subtle)',
                  background: feedFilter === flt ? 'var(--accent-purple-dim)' : 'var(--bg-secondary)',
                  color: feedFilter === flt ? 'var(--accent-purple)' : 'var(--text-muted)',
                  fontSize: '0.72rem',
                  fontWeight: 800,
                  fontFamily: 'var(--font-tactical)',
                  letterSpacing: '0.5px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  boxShadow: feedFilter === flt ? '0 0 10px var(--accent-purple-dim)' : 'none',
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
              background: 'var(--bg-secondary)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.74rem',
              fontWeight: 800,
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-tactical)',
              letterSpacing: '0.5px',
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
                  color: 'var(--text-muted)',
                  fontSize: '0.8rem',
                  fontFamily: 'var(--font-body)',
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
                  const isAuto = ev.object_class === 'AUTO_RICKSHAW' || ev.vehicle_type?.toLowerCase().includes('auto') || ev.display_name?.toLowerCase().includes('auto');
                  const isScooter = ev.display_name?.toLowerCase().includes('scooter') || ev.display_name?.toLowerCase().includes('activa') || ev.display_name?.toLowerCase().includes('access');
                  const isBike = ev.object_class === 'MOTORCYCLE' || ev.vehicle_type?.toLowerCase() === 'motorcycle' || ev.display_name?.toLowerCase().includes('splendor') || ev.display_name?.toLowerCase().includes('bullet') || ev.display_name?.toLowerCase().includes('enfield') || ev.display_name?.toLowerCase().includes('pulsar');
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
                        padding: '10px 12px',
                        background: 'var(--bg-secondary)',
                        border: isPlate ? '1px solid var(--accent-danger)' : '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.78rem',
                        borderLeft: isPlate
                          ? '4px solid var(--accent-danger)'
                          : isCar
                          ? '4px solid var(--accent-healthy)'
                          : isAuto
                          ? '4px solid var(--accent-blue)'
                          : isScooter
                          ? '4px solid #06b6d4'
                          : isBike
                          ? '4px solid var(--accent-purple)'
                          : isBus
                          ? '4px solid var(--accent-warning)'
                          : isTruck
                          ? '4px solid var(--accent-attention)'
                          : isPerson
                          ? '4px solid #00f0ff'
                          : '4px solid var(--accent-purple)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {isPlate ? (
                          <span
                            style={{
                              background: 'var(--accent-danger)',
                              color: '#ffffff',
                              fontSize: '0.65rem',
                              fontWeight: 900,
                              padding: '1px 5px',
                              borderRadius: '2px',
                              fontFamily: 'var(--font-mono)',
                            }}
                          >
                            PLATE
                          </span>
                        ) : isCar ? (
                          <Car size={14} style={{ color: 'var(--accent-healthy)' }} />
                        ) : isAuto ? (
                          <Zap size={14} style={{ color: 'var(--accent-blue)' }} />
                        ) : isScooter ? (
                          <Bike size={14} style={{ color: '#06b6d4' }} />
                        ) : isBike ? (
                          <Bike size={14} style={{ color: 'var(--accent-purple)' }} />
                        ) : isBus ? (
                          <Bus size={14} style={{ color: 'var(--accent-warning)' }} />
                        ) : isTruck ? (
                          <Truck size={14} style={{ color: 'var(--accent-attention)' }} />
                        ) : isPerson ? (
                          <User size={14} style={{ color: '#00f0ff' }} />
                        ) : (
                          <Shield size={14} style={{ color: 'var(--accent-attention)' }} />
                        )}
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <strong
                            style={{
                              color: isPlate ? '#fca5a5' : 'var(--text-primary)',
                              fontFamily: isPlate ? 'var(--font-mono)' : 'var(--font-tactical)',
                              fontSize: '0.82rem',
                              letterSpacing: '0.4px',
                            }}
                          >
                            {ev.display_name || ev.object_class}
                          </strong>
                          {ev.track_id && (
                            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                              #TRK-{ev.track_id}
                            </span>
                          )}
                        </div>
                      </div>

                      <div style={{ textAlign: 'center' }}>
                        <span
                          style={{
                            color: confPct >= 75 ? 'var(--accent-healthy)' : confPct >= 50 ? 'var(--accent-attention)' : 'var(--accent-danger)',
                            fontWeight: 800,
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.78rem',
                          }}
                        >
                          {confPct}%
                        </span>
                      </div>

                      <div
                        style={{
                          textAlign: 'right',
                          color: 'var(--text-muted)',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.74rem',
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
          background: 'var(--bg-card)',
          backdropFilter: 'var(--glass-blur)',
          WebkitBackdropFilter: 'var(--glass-blur)',
          border: '1px solid var(--border-medium)',
          borderRadius: 'var(--radius-lg)',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          boxShadow: 'var(--card-shadow)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Car size={18} style={{ color: 'var(--accent-purple)' }} />
            <div>
              <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 800, fontFamily: 'var(--font-tactical)', letterSpacing: '1px' }}>
                6. ANPR RESULTS TABLE (RECOGNIZED NUMBER PLATES)
              </h3>
              <p style={{ margin: '2px 0 0', fontSize: '0.76rem', color: 'var(--text-muted)', fontFamily: 'var(--font-body)' }}>
                Identified Gujarat RTO and Indian vehicle registration plates with confidence & jurisdiction
              </p>
            </div>
          </div>

          {/* Search Box & CSV Export */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-medium)',
                borderRadius: 'var(--radius-sm)',
                padding: '6px 12px',
              }}
            >
              <Search size={14} style={{ color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Filter plates or vehicle..."
                value={tableSearch}
                onChange={(e) => setTableSearch(e.target.value)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-primary)',
                  fontSize: '0.78rem',
                  outline: 'none',
                  width: '180px',
                  fontFamily: 'var(--font-body)',
                }}
              />
            </div>

            <button
              onClick={handleExportCsv}
              disabled={filteredPlates.length === 0}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '7px 16px',
                background: filteredPlates.length > 0 ? 'var(--accent-healthy-dim)' : 'var(--bg-secondary)',
                color: filteredPlates.length > 0 ? 'var(--accent-healthy)' : 'var(--text-muted)',
                border: filteredPlates.length > 0 ? '1px solid var(--accent-healthy)' : '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.78rem',
                fontWeight: 800,
                fontFamily: 'var(--font-tactical)',
                letterSpacing: '0.5px',
                cursor: filteredPlates.length > 0 ? 'pointer' : 'not-allowed',
                boxShadow: filteredPlates.length > 0 ? '0 0 14px var(--accent-healthy-dim)' : 'none',
                transition: 'all 0.15s ease',
              }}
              title="Export detected license plates to CSV spreadsheet"
            >
              <Download size={13} />
              <span>EXPORT CSV ({filteredPlates.length})</span>
            </button>
          </div>
        </div>

        {/* Table View */}
        <div style={{ overflowX: 'auto' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              textAlign: 'left',
              fontSize: '0.82rem',
            }}
          >
            <thead>
              <tr
                style={{
                  borderBottom: '1px solid var(--border-medium)',
                  color: 'var(--text-muted)',
                  fontSize: '0.74rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.8px',
                  fontFamily: 'var(--font-tactical)',
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
                      color: 'var(--text-muted)',
                      fontSize: '0.82rem',
                      fontFamily: 'var(--font-body)',
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
                        borderBottom: '1px solid var(--border-subtle)',
                        background: 'var(--bg-secondary)',
                        transition: 'background-color 0.2s',
                      }}
                    >
                      {/* Number Plate with High-Contrast Badge */}
                      <td style={{ padding: '12px 16px' }}>
                        <div
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            background: '#ffffff',
                            color: '#000000',
                            border: '1px solid #000000',
                            borderRadius: '4px',
                            padding: '3px 8px',
                            fontFamily: 'var(--font-mono)',
                            fontWeight: 900,
                            fontSize: '0.82rem',
                            letterSpacing: '1px',
                            boxShadow: '0 2px 6px rgba(0,0,0,0.4)',
                          }}
                        >
                          <span
                            style={{
                              background: '#1e3a8a',
                              color: '#ffffff',
                              fontSize: '0.58rem',
                              padding: '1px 3px',
                              borderRadius: '2px',
                              marginRight: '6px',
                              fontWeight: 800,
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
                            color: confPct >= 85 ? 'var(--accent-healthy)' : 'var(--accent-attention)',
                            fontWeight: 800,
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.82rem',
                          }}
                        >
                          {confPct}%
                        </span>
                      </td>

                      {/* Timestamp */}
                      <td
                        style={{
                          padding: '12px 16px',
                          fontFamily: 'var(--font-mono)',
                          color: 'var(--text-muted)',
                          fontSize: '0.78rem',
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
                            color: 'var(--accent-purple)',
                            fontWeight: 700,
                            fontFamily: 'var(--font-tactical)',
                            fontSize: '0.82rem',
                          }}
                        >
                          <Car size={14} />
                          {plate.vehicle}
                        </span>
                      </td>

                      {/* RTO Jurisdiction */}
                      <td style={{ padding: '12px 16px', color: 'var(--text-primary)', fontFamily: 'var(--font-tactical)', fontWeight: 600 }}>
                        {plate.rto_jurisdiction || 'Gujarat State'}
                      </td>

                      {/* Sightings */}
                      <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                        <span
                          style={{
                            background: 'var(--bg-tertiary)',
                            border: '1px solid var(--border-subtle)',
                            padding: '2px 8px',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '0.75rem',
                            fontWeight: 800,
                            color: 'var(--text-secondary)',
                            fontFamily: 'var(--font-mono)',
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
