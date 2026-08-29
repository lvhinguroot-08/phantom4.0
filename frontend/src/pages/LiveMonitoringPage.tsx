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

  const fetchCameras = async () => {
    setIsLoading(true);
    try {
      let loaded: Camera[] = [];
      try {
        const res = await camerasApi.list({ page_size: 30 });
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
  }, []);

  const districts = Array.from(new Set(cameras.map((c) => c.district).filter(Boolean)));

  const filteredCameras = cameras.filter((c) => {
    if (filterDistrict !== 'ALL' && c.district !== filterDistrict) return false;
    return true;
  });

  const countToDisplay = layout === '1' ? 1 : layout === '4' ? 4 : layout === '9' ? 9 : layout === '16' ? 16 : 30;
  const displayCameras = filteredCameras.slice(0, countToDisplay);

  return (
    <div className="live-monitoring-page">
      {/* Top AI Telemetry Strip */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2 bg-slate-900/90 border-b border-cyan-500/20 backdrop-blur-md text-xs font-mono">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5 text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="font-bold">YOLO26 & ANPR LIVE ENGINE ACTIVE</span>
          </div>
          <div className="flex items-center gap-1 text-slate-300">
            <Car size={13} className="text-cyan-400" />
            <span>Vehicles: <b className="text-white">68 Active</b></span>
          </div>
          <div className="flex items-center gap-1 text-slate-300">
            <Scan size={13} className="text-amber-400" />
            <span>Plates Scanned: <b className="text-white">34/min</b></span>
          </div>
          <div className="flex items-center gap-1 text-slate-300">
            <User size={13} className="text-cyan-300" />
            <span>Pedestrians: <b className="text-white">18 Ingested</b></span>
          </div>
          <div className="flex items-center gap-1 text-rose-400 bg-rose-950/60 px-2 py-0.5 rounded border border-rose-500/30">
            <ShieldAlert size={13} className="text-rose-400 animate-pulse" />
            <span>Hotlist Matches: <b className="text-white">2 CRITICAL</b></span>
          </div>
        </div>

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
