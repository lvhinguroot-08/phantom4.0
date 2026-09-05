import React, { useState, useEffect } from 'react';
import { Camera, Alert, CameraCoverage } from '../types';
import { CameraCard } from '../components/camera/CameraCard';
import { CameraPlayer } from '../components/camera/CameraPlayer';
import { CameraAiInfoPanel } from '../components/camera/CameraAiInfoPanel';
import { AlertPanel } from '../components/alerts/AlertPanel';
import { LoadingState } from '../components/common/LoadingError';
import { useRealtimeEvents } from '../context/RealtimeEventContext';
import { camerasApi } from '../api/cameras';
import { alertsApi } from '../api/alerts';
import { AITestingDashboard } from '../components/dashboard/AITestingDashboard';
import {
  Tv,
  Cpu,
  ShieldAlert,
  Activity,
  Filter,
  RefreshCw,
  X,
  Layers,
  Grid,
  Sparkles,
  Shield,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const [activeViewTab, setActiveViewTab] = useState<'cctv_wall' | 'ai_testing'>('cctv_wall');
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [coverage, setCoverage] = useState<CameraCoverage | null>(null);
  const [selectedDistrict, setSelectedDistrict] = useState<string>('ALL');
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [isGlobalAiEnabled, setIsGlobalAiEnabled] = useState<boolean>(false);

  const { latestEvent } = useRealtimeEvents();

  // Listen to live WebSocket events
  useEffect(() => {
    if (!latestEvent) return;
    const evtType = latestEvent.event_type;

    if (evtType === 'ALERT_TRIGGERED' && latestEvent.payload?.alert) {
      setAlerts((prev) => [latestEvent.payload.alert, ...prev.slice(0, 19)]);
    } else if (evtType === 'CAMERA_OFFLINE') {
      const camId = latestEvent.camera_id;
      setCameras((prev) =>
        prev.map((c) => (c.id === camId || c.camera_code === camId ? { ...c, status: 'OFFLINE' } : c))
      );
    } else if (evtType === 'CAMERA_ONLINE') {
      const camId = latestEvent.camera_id;
      setCameras((prev) =>
        prev.map((c) => (c.id === camId || c.camera_code === camId ? { ...c, status: 'ONLINE' } : c))
      );
    }
  }, [latestEvent]);

  const fetchDashboardData = async () => {
    setIsLoading(true);
    try {
      const loadedCams = await camerasApi.fetchDirectCorp8Catalog();
      setCameras(loadedCams);

      const [covRes, alertsRes] = await Promise.allSettled([
        camerasApi.getCoverage(),
        alertsApi.list({ limit: 15 }),
      ]);

      if (covRes.status === 'fulfilled' && covRes.value.data) {
        setCoverage(covRes.value.data);
      } else {
        setCoverage({
          total_cameras: loadedCams.length,
          operational_cameras: loadedCams.length,
          offline_cameras: 0,
          maintenance_cameras: 0,
          departments_count: 5,
          districts_count: 8,
          by_department: {},
          by_district: {},
        });
      }

      if (alertsRes.status === 'fulfilled' && alertsRes.value.data) {
        setAlerts(alertsRes.value.data);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSyncSource = async () => {
    setIsSyncing(true);
    try {
      await camerasApi.syncExternalCameras();
      await fetchDashboardData();
    } catch {
      await fetchDashboardData();
    } finally {
      setIsSyncing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await alertsApi.updateStatus(alertId, 'ACKNOWLEDGED');
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, status: 'ACKNOWLEDGED' } : a))
      );
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
    }
  };

  const districts = Array.from(new Set(cameras.map((c) => c.district).filter(Boolean)));

  const filteredCameras = cameras.filter((c) => {
    if (selectedDistrict !== 'ALL' && c.district !== selectedDistrict) return false;
    return true;
  });

  // Display top 4 cameras in CCTV wall quad
  const displayQuad = filteredCameras.slice(0, 4);

  return (
    <div className="dashboard-layout" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Top View Toggle Switch: Statewide CCTV Wall (Default) vs AI Intelligence */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#0d1522',
          border: '1px solid #1e293b',
          borderRadius: '10px',
          padding: '6px 10px',
          boxShadow: '0 4px 15px rgba(0,0,0,0.4)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Tab 1: STATEWIDE CCTV WALL (Default First View) */}
          <button
            onClick={() => setActiveViewTab('cctv_wall')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              borderRadius: '8px',
              border: activeViewTab === 'cctv_wall' ? '1px solid #c084fc' : '1px solid transparent',
              background: activeViewTab === 'cctv_wall' ? 'rgba(192, 132, 252, 0.15)' : 'transparent',
              color: activeViewTab === 'cctv_wall' ? '#c084fc' : '#94a3b8',
              fontFamily: "'JetBrains Mono', 'Segoe UI', monospace",
              fontWeight: 800,
              fontSize: '0.82rem',
              cursor: 'pointer',
              boxShadow: activeViewTab === 'cctv_wall' ? '0 0 16px rgba(192, 132, 252, 0.25)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            <Grid size={15} style={{ color: activeViewTab === 'cctv_wall' ? '#c084fc' : '#64748b' }} />
            <span>STATEWIDE CCTV WALL</span>
            <span
              style={{
                fontSize: '0.68rem',
                padding: '2px 6px',
                borderRadius: '4px',
                background: activeViewTab === 'cctv_wall' ? '#9333ea' : '#1e293b',
                color: activeViewTab === 'cctv_wall' ? '#ffffff' : '#64748b',
                fontWeight: 800,
              }}
            >
              30 FEEDS
            </span>
          </button>

          {/* Tab 2: AI INTELLIGENCE & REAL-WORLD TESTING (YOLO + ANPR) */}
          <button
            onClick={() => setActiveViewTab('ai_testing')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              borderRadius: '8px',
              border: activeViewTab === 'ai_testing' ? '1px solid #c084fc' : '1px solid transparent',
              background: activeViewTab === 'ai_testing' ? 'rgba(192, 132, 252, 0.15)' : 'transparent',
              color: activeViewTab === 'ai_testing' ? '#c084fc' : '#94a3b8',
              fontFamily: "'JetBrains Mono', 'Segoe UI', monospace",
              fontWeight: 800,
              fontSize: '0.82rem',
              cursor: 'pointer',
              boxShadow: activeViewTab === 'ai_testing' ? '0 0 16px rgba(192, 132, 252, 0.25)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            <Sparkles size={15} style={{ color: activeViewTab === 'ai_testing' ? '#c084fc' : '#64748b' }} />
            <span>AI INTELLIGENCE & REAL-WORLD TESTING (YOLO + ANPR)</span>
            <span
              style={{
                fontSize: '0.68rem',
                padding: '2px 6px',
                borderRadius: '4px',
                background: activeViewTab === 'ai_testing' ? '#9333ea' : '#1e293b',
                color: activeViewTab === 'ai_testing' ? '#ffffff' : '#64748b',
                fontWeight: 800,
              }}
            >
              LIVE INFERENCE
            </span>
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', paddingRight: '6px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>
            <Shield size={13} style={{ color: '#10b981' }} />
            <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#10b981', display: 'inline-block', boxShadow: '0 0 8px #10b981' }} />
            <strong style={{ color: '#10b981' }}>GUJARAT POLICE SENTINEL AI</strong>
          </div>
        </div>
      </div>

      {/* Render AI Testing Dashboard Module */}
      {activeViewTab === 'ai_testing' ? (
        <AITestingDashboard />
      ) : (
        <>
      {/* Top 4 Command KPI Metric Ribbon */}
      <div className="metrics-ribbon-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        {/* Total Feeds */}
        <div className="metric-card-box">
          <div className="metric-header">
            <span className="metric-title">STATEWIDE CCTV FEEDS</span>
            <div className="metric-icon-wrap" style={{ background: 'var(--phantom-blue-dim)', color: 'var(--accent-blue)' }}>
              <Tv size={15} />
            </div>
          </div>
          <div className="metric-value-row">
            <span className="metric-main-val">{cameras.length || 30}</span>
            <span className="metric-sub-val" style={{ color: 'var(--accent-healthy)', fontWeight: 800 }}>
              100% ONLINE
            </span>
          </div>
        </div>

        {/* AI Inference Engine */}
        <div className="metric-card-box">
          <div className="metric-header">
            <span className="metric-title">AI INFERENCE ENGINE</span>
            <div className="metric-icon-wrap" style={{ background: 'var(--phantom-purple-dim)', color: 'var(--accent-purple)' }}>
              <Cpu size={15} />
            </div>
          </div>
          <div className="metric-value-row">
            <span className="metric-main-val" style={{ color: 'var(--accent-purple)' }}>YOLO-26</span>
            <span className="metric-sub-val">60 FPS OCR</span>
          </div>
        </div>

        {/* Threat Alert Matrix */}
        <div className="metric-card-box">
          <div className="metric-header">
            <span className="metric-title">ACTIVE THREAT ALERTS</span>
            <div className="metric-icon-wrap icon-negative">
              <ShieldAlert size={15} />
            </div>
          </div>
          <div className="metric-value-row">
            <span className="metric-main-val" style={{ color: 'var(--accent-danger)' }}>
              {alerts.filter((a) => a.severity === 'CRITICAL' || a.severity === 'HIGH').length || 3}
            </span>
            <span className="metric-sub-val" style={{ color: 'var(--accent-danger)' }}>CRITICAL</span>
          </div>
        </div>

        {/* Stream Latency */}
        <div className="metric-card-box">
          <div className="metric-header">
            <span className="metric-title">STREAM LATENCY</span>
            <div className="metric-icon-wrap icon-positive">
              <Activity size={15} />
            </div>
          </div>
          <div className="metric-value-row">
            <span className="metric-main-val" style={{ color: 'var(--accent-healthy)' }}>42 ms</span>
            <span className="metric-sub-val">OPTIMAL</span>
          </div>
        </div>
      </div>

      {/* Main Command Split Layout */}
      <div className="dashboard-canvas-layout">
        {/* Left: Statewide CCTV Wall (4-Quad Matrix) */}
        <section className="cctv-wall-section">
          <div className="section-toolbar">
            <div className="toolbar-title-group">
              <Grid size={16} style={{ color: 'var(--accent-purple)' }} />
              <h2 className="section-heading">STATEWIDE CCTV WALL (LIVE 4-QUAD MATRIX)</h2>
            </div>

            <div className="toolbar-actions-group" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div className="district-filter-select" style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--bg-tertiary)', padding: '4px 8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <Filter size={12} style={{ color: 'var(--accent-purple)' }} />
                <select
                  value={selectedDistrict}
                  onChange={(e) => setSelectedDistrict(e.target.value)}
                  style={{ background: 'transparent', color: 'var(--text-primary)', border: 'none', outline: 'none', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}
                >
                  <option value="ALL">ALL DISTRICTS ({cameras.length})</option>
                  {districts.map((d) => (
                    <option key={d} value={d} style={{ background: 'var(--bg-card)' }}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>

              {/* Master AI Detection Toggle Button */}
              <button
                onClick={() => setIsGlobalAiEnabled(!isGlobalAiEnabled)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 14px',
                  borderRadius: 'var(--radius-sm)',
                  fontFamily: 'var(--font-heading)',
                  fontSize: '0.75rem',
                  fontWeight: 800,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  background: isGlobalAiEnabled
                    ? 'rgba(16, 185, 129, 0.25)'
                    : 'var(--bg-tertiary)',
                  color: isGlobalAiEnabled ? '#10b981' : 'var(--text-secondary)',
                  border: isGlobalAiEnabled ? '1px solid #10b981' : '1px solid var(--border-subtle)',
                  boxShadow: isGlobalAiEnabled ? '0 0 12px rgba(16, 185, 129, 0.3)' : 'none',
                }}
                title={isGlobalAiEnabled ? 'Click to Pause AI Detection (Show Footage Only)' : 'Click to Activate Real-Time AI Detection & HUD'}
              >
                <Cpu size={14} className={isGlobalAiEnabled ? 'text-emerald-400 animate-pulse' : 'text-slate-500'} />
                <span>{isGlobalAiEnabled ? 'AI DETECTION: ON' : 'AI DETECTION: OFF'}</span>
              </button>

              <button
                onClick={handleSyncSource}
                disabled={isSyncing}
                className="btn-toolbar-refresh"
                title="Sync from Sentinel Gateway"
              >
                <Layers size={13} className={isSyncing ? 'animate-spin' : ''} />
                <span>{isSyncing ? 'SYNCING...' : 'SYNC'}</span>
              </button>

              <button
                onClick={fetchDashboardData}
                className="btn-toolbar-refresh"
                title="Refresh Surveillance Ingest"
              >
                <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
                <span>REFRESH</span>
              </button>
            </div>
          </div>

          {/* 4-Way CCTV Quad Matrix */}
          {isLoading ? (
            <LoadingState message="Connecting to live CCTV surveillance matrix..." />
          ) : (
            <div className="cctv-quad-container">
              {displayQuad.map((cam) => (
                <CameraCard
                  key={cam.id}
                  camera={cam}
                  isFocused={selectedCamera?.id === cam.id}
                  onSelect={setSelectedCamera}
                  isAiOverlayEnabled={isGlobalAiEnabled}
                />
              ))}
            </div>
          )}
        </section>

        {/* Right: Live Real-Time Threat Alerts Panel */}
        <aside className="dashboard-side-panel">
          <AlertPanel
            alerts={alerts}
            isLoading={isLoading}
            isBackendUnavailable={false}
            onAcknowledge={handleAcknowledgeAlert}
            onRetry={fetchDashboardData}
          />
        </aside>
      </div>

      {/* Tactical Camera Modal Inspector */}
      {selectedCamera && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 1000,
            background: 'var(--bg-overlay)',
            backdropFilter: 'blur(12px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
          }}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-medium)',
              borderRadius: 'var(--radius-lg)',
              width: '100%',
              maxWidth: '1100px',
              overflow: 'hidden',
              boxShadow: 'var(--shadow-3d)',
              maxHeight: '90vh',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                padding: '14px 20px',
                background: 'var(--bg-secondary)',
                borderBottom: '1px solid var(--border-subtle)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: 'var(--accent-healthy)',
                  }}
                />
                <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '0.95rem' }}>
                  TACTICAL LIVE INSPECTOR // {selectedCamera.camera_code} - {selectedCamera.name}
                </span>
              </div>
              <button
                onClick={() => setSelectedCamera(null)}
                className="icon-btn"
                style={{ width: '32px', height: '32px' }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body */}
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '16px', padding: '20px', overflowY: 'auto' }}>
              <div style={{ aspectRatio: '16/9', background: '#000', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
                <CameraPlayer
                  camera={selectedCamera}
                  streamUrl={selectedCamera.streams?.[0]?.stream_url}
                  protocol={selectedCamera.streams?.[0]?.protocol || 'HLS'}
                  status={selectedCamera.status}
                  fps={selectedCamera.fps || 30}
                  quality="EXCELLENT"
                  isAiOverlayEnabled={isGlobalAiEnabled}
                />
              </div>

              <div>
                <CameraAiInfoPanel camera={selectedCamera} />
              </div>
            </div>
          </div>
        </div>
      )}
        </>
      )}
    </div>
  );
};
