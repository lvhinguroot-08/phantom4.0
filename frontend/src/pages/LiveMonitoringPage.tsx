import React, { useState, useEffect } from 'react';
import { Camera } from '../types';
import { camerasApi } from '../api/cameras';
import { CameraCard } from '../components/camera/CameraCard';
import { CameraPlayer } from '../components/camera/CameraPlayer';
import { CameraAiInfoPanel } from '../components/camera/CameraAiInfoPanel';
import { LoadingState } from '../components/common/LoadingError';
import {
  LayoutGrid,
  Grid3X3,
  Grid,
  Square,
  Filter,
  RefreshCw,
  Layers,
  Cpu,
  Car,
  User,
  ShieldAlert,
  X,
  Scan,
  Sparkles,
  Maximize2,
} from 'lucide-react';

export const LiveMonitoringPage: React.FC = () => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [layout, setLayout] = useState<'1' | '4' | '9' | '16' | '30'>('4');
  const [filterDistrict, setFilterDistrict] = useState<string>('ALL');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);
  const [globalAiHud, setGlobalAiHud] = useState<boolean>(true);
  const [sentinelState, setSentinelState] = useState<{
    status: string;
    catalogue: string;
    total: number;
    live: number;
    error?: string;
    reconnect_attempt: number;
  }>({
    status: 'ONLINE',
    catalogue: 'SYNCED',
    total: 0,
    live: 0,
    reconnect_attempt: 0,
  });

  const fetchSentinelHealth = async () => {
    try {
      const res = await fetch('/api/v1/cameras/health/sentinel');
      if (res.ok) {
        const json = await res.json();
        if (json.success && json.data) {
          const d = json.data;
          setSentinelState({
            status: d.sentinel_connection || 'ONLINE',
            catalogue: d.catalogue_state || 'SYNCED',
            total: d.total_discovered_cameras || 0,
            live: d.live_cameras || 0,
            error: d.last_error,
            reconnect_attempt: d.reconnect_attempt || 0,
          });
        }
      }
    } catch {
      setSentinelState((prev) => ({
        ...prev,
        status: 'DEGRADED',
        catalogue: 'OFFLINE',
      }));
    }
  };

  const fetchCameras = async () => {
    setIsLoading(true);
    try {
      let loaded: Camera[] = [];
      try {
        const res = await camerasApi.list({ page_size: 50 });
        if (res && res.data && res.data.length > 0) {
          loaded = res.data;
        }
      } catch {
        // Fallback
      }

      if (loaded.length === 0) {
        loaded = await camerasApi.fetchDirectCorp8Catalog();
      }

      setCameras(loaded);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCameras();
    fetchSentinelHealth();
    const interval = setInterval(() => {
      fetchSentinelHealth();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const districts = Array.from(new Set(cameras.map((c) => c.district).filter(Boolean)));

  const filteredCameras = cameras.filter((c) => {
    if (filterDistrict !== 'ALL' && c.district !== filterDistrict) return false;
    return true;
  });

  const countToDisplay = layout === '1' ? 1 : layout === '4' ? 4 : layout === '9' ? 9 : layout === '16' ? 16 : 30;
  const displayCameras = filteredCameras.slice(0, countToDisplay);

  const isSentinelDegraded = sentinelState.status !== 'ONLINE';

  return (
    <div className="live-monitoring-page">
      {/* Sentinel Connection & Resilience Status Banner */}
      <div className={`flex flex-wrap items-center justify-between gap-3 px-4 py-2 text-xs font-mono border-b ${
        isSentinelDegraded
          ? 'bg-rose-950/80 border-rose-500/40 text-rose-200'
          : 'bg-slate-900/95 border-cyan-500/20 text-slate-300'
      }`}>
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-bold">SENTINEL CONNECTION:</span>
            {isSentinelDegraded ? (
              <span className="flex items-center gap-1.5 text-amber-400 font-bold px-2 py-0.5 rounded bg-amber-950/70 border border-amber-500/40">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                ● DEGRADED
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-emerald-400 font-bold px-2 py-0.5 rounded bg-emerald-950/70 border border-emerald-500/40">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                ● ONLINE
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-bold">CAMERA CATALOGUE:</span>
            {isSentinelDegraded ? (
              <span className="flex items-center gap-1 text-rose-300 font-bold">
                ○ OFFLINE (RETRYING AUTOMATICALLY...)
              </span>
            ) : (
              <span className="flex items-center gap-1 text-emerald-300 font-bold">
                ● SYNCED ({sentinelState.total || filteredCameras.length} DISCOVERED)
              </span>
            )}
          </div>

          {isSentinelDegraded && sentinelState.reconnect_attempt > 0 && (
            <span className="text-amber-300 text-xs animate-pulse">
              Retry Attempt #{sentinelState.reconnect_attempt} (Exponential Backoff)
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              fetchCameras();
              fetchSentinelHealth();
            }}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 text-xs border border-slate-700 transition-colors"
            title="Refresh Ingest Stream Registry"
          >
            <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} />
            <span>SYNC CATALOGUE</span>
          </button>

          {/* Master AI HUD Toggle Switch */}
          <button
            onClick={() => setGlobalAiHud(!globalAiHud)}
            className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-bold transition-all shadow ${
              globalAiHud
                ? 'bg-emerald-600 hover:bg-emerald-500 text-white border border-emerald-400/50 shadow-emerald-900/40'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-400 border border-slate-700'
            }`}
            title="Toggle AI Bounding Boxes & Attributes across all video streams"
          >
            <Cpu size={13} className={globalAiHud ? 'animate-pulse' : ''} />
            <span>GLOBAL AI HUD: {globalAiHud ? 'ACTIVE' : 'OFF'}</span>
          </button>
        </div>
      </div>

      {/* Top Controls Toolbar */}
      <div className="monitoring-toolbar">
        <div className="toolbar-left">
          <h2 className="page-title">LIVE MULTI-CAMERA MONITORING WALL</h2>
          <span className="live-pill">● {filteredCameras.length} STREAMS INGESTED</span>
        </div>

        <div className="toolbar-right">
          {/* District Filter */}
          <div className="district-filter-select">
            <Filter size={12} className="text-cyan" />
            <select
              value={filterDistrict}
              onChange={(e) => setFilterDistrict(e.target.value)}
              className="registry-select"
            >
              <option value="ALL">ALL DISTRICTS ({cameras.length})</option>
              {districts.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          {/* Layout Switcher */}
          <div className="layout-btn-group">
            <button
              onClick={() => setLayout('1')}
              className={`btn-layout ${layout === '1' ? 'active' : ''}`}
              title="1-Way Focused Mode"
            >
              <Square size={13} />
              <span>1x1</span>
            </button>
            <button
              onClick={() => setLayout('4')}
              className={`btn-layout ${layout === '4' ? 'active' : ''}`}
              title="4-Way Quad (2x2)"
            >
              <LayoutGrid size={13} />
              <span>2x2</span>
            </button>
            <button
              onClick={() => setLayout('9')}
              className={`btn-layout ${layout === '9' ? 'active' : ''}`}
              title="9-Way Matrix (3x3)"
            >
              <Grid3X3 size={13} />
              <span>3x3</span>
            </button>
            <button
              onClick={() => setLayout('16')}
              className={`btn-layout ${layout === '16' ? 'active' : ''}`}
              title="16-Way High Density (4x4)"
            >
              <Grid size={13} />
              <span>4x4</span>
            </button>
            <button
              onClick={() => setLayout('30')}
              className={`btn-layout ${layout === '30' ? 'active' : ''}`}
              title="All 30 Live Feeds"
            >
              <Layers size={13} />
              <span>ALL 30</span>
            </button>
          </div>

          <button onClick={fetchCameras} className="btn-icon-action" title="Refresh Streams">
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Dynamic Responsive Video Grid */}
      {isLoading ? (
        <LoadingState message="Establishing HLS stream sessions across surveillance grid..." />
      ) : (
        <div className={`monitoring-grid grid-layout-${layout}`}>
          {displayCameras.map((cam) => (
            <CameraCard
              key={cam.id}
              camera={cam}
              isFocused={selectedCamera?.id === cam.id}
              onSelect={setSelectedCamera}
            />
          ))}
        </div>
      )}

      {/* Focused Camera Modal & Live Forensic Inspector */}
      {selectedCamera && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-cyan-500/40 rounded-xl w-full max-w-5xl overflow-hidden shadow-2xl flex flex-col max-h-[92vh]">
            {/* Modal Header */}
            <div className="px-4 py-3 bg-slate-950/80 border-b border-cyan-500/20 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                <h3 className="font-bold text-white tracking-wide">
                  TACTICAL LIVE INSPECTOR // {selectedCamera.camera_code} - {selectedCamera.name}
                </h3>
                <span className="bg-cyan-950 text-cyan-400 border border-cyan-500/30 text-xs px-2 py-0.5 rounded font-mono">
                  {selectedCamera.district || 'GUJARAT POLICE'}
                </span>
              </div>
              <button
                onClick={() => setSelectedCamera(null)}
                className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body: Magnified Live Player + Forensic Live Log */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 p-4 overflow-y-auto">
              {/* Video Player */}
              <div className="lg:col-span-2 aspect-video bg-black rounded-lg overflow-hidden border border-slate-800 relative">
                <CameraPlayer
                  camera={selectedCamera}
                  status={selectedCamera.status}
                  fps={selectedCamera.fps || 25}
                  quality="EXCELLENT"
                />
              </div>

              {/* Live AI Detections & Real-time Telemetry Panel */}
              <div className="lg:col-span-1">
                <CameraAiInfoPanel camera={selectedCamera} className="h-full" />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
