import React, { useState, useEffect } from 'react';
import { Camera } from '../types';
import { CameraCard } from '../components/camera/CameraCard';
import { CameraPlayer } from '../components/camera/CameraPlayer';
import { CameraAiInfoPanel } from '../components/camera/CameraAiInfoPanel';
import { LoadingState } from '../components/common/LoadingError';
import { camerasApi } from '../api/cameras';
import {
  Tv,
  Filter,
  RefreshCw,
  LayoutGrid,
  Grid,
  Square,
  Grid3X3,
  Layers,
  X,
  MapPin,
  Radio,
  Sparkles,
  Cpu,
} from 'lucide-react';

export const LiveMonitoringPage: React.FC = () => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [layout, setLayout] = useState<'1' | '4' | '9' | '16' | '30'>('9');
  const [filterDistrict, setFilterDistrict] = useState<string>('ALL');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);
  const [isGlobalAiEnabled, setIsGlobalAiEnabled] = useState<boolean>(false);

  const fetchCameras = async () => {
    setIsLoading(true);
    try {
      const loaded = await camerasApi.fetchDirectCorp8Catalog();
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

  const getGridColsStyle = () => {
    switch (layout) {
      case '1':
        return { gridTemplateColumns: '1fr', maxWidth: '1200px', margin: '0 auto' };
      case '4':
        return { gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' };
      case '9':
        return { gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px' };
      case '16':
        return { gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' };
      case '30':
        return { gridTemplateColumns: 'repeat(6, 1fr)', gap: '10px' };
      default:
        return { gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px' };
    }
  };

  return (
    <div className="live-monitoring-page" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
      {/* Scaled-Up Prominent Surveillance Control Bar */}
      <div
        style={{
          background: 'var(--glass-bg)',
          backdropFilter: 'var(--glass-blur)',
          WebkitBackdropFilter: 'var(--glass-blur)',
          border: '1px solid var(--border-medium)',
          borderRadius: 'var(--radius-lg)',
          padding: '16px 22px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          boxShadow: 'var(--card-shadow)',
        }}
      >
        {/* Left: Prominent Title & Live Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '46px',
              height: '46px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(0, 240, 255, 0.12)',
              border: '1px solid rgba(0, 240, 255, 0.4)',
              color: 'var(--accent-cyan)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 15px rgba(0, 240, 255, 0.25)',
            }}
          >
            <Tv size={24} />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span
                style={{
                  width: '9px',
                  height: '9px',
                  borderRadius: '50%',
                  background: 'var(--accent-healthy)',
                  boxShadow: '0 0 10px var(--accent-healthy)',
                  display: 'inline-block',
                }}
              />
              <h1
                style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize: '1.25rem',
                  fontWeight: 900,
                  color: '#fff',
                  letterSpacing: '1.5px',
                  margin: 0,
                }}
              >
                LIVE CCTV MONITORING MATRIX
              </h1>
              <span
                className="badge-live"
                style={{
                  fontSize: '0.75rem',
                  padding: '4px 10px',
                  borderRadius: 'var(--radius-sm)',
                  fontWeight: 800,
                  fontFamily: 'var(--font-mono)',
                  letterSpacing: '0.5px',
                }}
              >
                {filteredCameras.length} / 30 STREAMS LIVE
              </span>
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: '4px 0 0 0', fontFamily: 'var(--font-body)' }}>
              Real-time high-definition CCTV video feeds streaming across Gujarat highways and city checkpoints
            </p>
          </div>
        </div>

        {/* Right: Scaled Up District Filter & Layout Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          {/* Scaled-Up District & City Filter Dropdown */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-medium)',
              borderRadius: 'var(--radius-md)',
              padding: '8px 16px',
              boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.1)',
            }}
          >
            <MapPin size={16} className="text-cyan" />
            <span style={{ fontSize: '0.8rem', fontFamily: 'var(--font-tactical)', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.5px' }}>
              DISTRICT:
            </span>
            <select
              value={filterDistrict}
              onChange={(e) => setFilterDistrict(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#fff',
                fontFamily: 'var(--font-heading)',
                fontSize: '0.88rem',
                fontWeight: 700,
                outline: 'none',
                cursor: 'pointer',
                minWidth: '160px',
              }}
            >
              <option value="ALL" style={{ background: '#0a101d', color: '#fff' }}>
                ALL GUJARAT ({cameras.length})
              </option>
              {districts.map((d) => (
                <option key={d} value={d} style={{ background: '#0a101d', color: '#fff' }}>
                  {d?.toUpperCase()} ({cameras.filter((c) => c.district === d).length} CAMS)
                </option>
              ))}
            </select>
          </div>

          {/* Scaled-Up Matrix Layout Switcher (1x1, 2x2, 3x3, 4x4, ALL 30) */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-medium)',
              borderRadius: 'var(--radius-md)',
              padding: '4px',
              gap: '4px',
            }}
          >
            <button
              onClick={() => setLayout('1')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-sm)',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.82rem',
                fontWeight: 800,
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                background: layout === '1' ? 'var(--accent-cyan)' : 'transparent',
                color: layout === '1' ? '#070b14' : 'var(--text-secondary)',
                boxShadow: layout === '1' ? '0 0 14px var(--accent-cyan-dim)' : 'none',
              }}
              title="1x1 Single Focus Stream"
            >
              <Square size={15} />
              <span>1x1</span>
            </button>

            <button
              onClick={() => setLayout('4')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-sm)',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.82rem',
                fontWeight: 800,
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                background: layout === '4' ? 'var(--accent-cyan)' : 'transparent',
                color: layout === '4' ? '#070b14' : 'var(--text-secondary)',
                boxShadow: layout === '4' ? '0 0 14px var(--accent-cyan-dim)' : 'none',
              }}
              title="2x2 Quad Matrix"
            >
              <LayoutGrid size={15} />
              <span>2x2</span>
            </button>

            <button
              onClick={() => setLayout('9')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-sm)',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.82rem',
                fontWeight: 800,
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                background: layout === '9' ? 'var(--accent-cyan)' : 'transparent',
                color: layout === '9' ? '#070b14' : 'var(--text-secondary)',
                boxShadow: layout === '9' ? '0 0 14px var(--accent-cyan-dim)' : 'none',
              }}
              title="3x3 Tactical Matrix"
            >
              <Grid3X3 size={15} />
              <span>3x3</span>
            </button>

            <button
              onClick={() => setLayout('16')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-sm)',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.82rem',
                fontWeight: 800,
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                background: layout === '16' ? 'var(--accent-cyan)' : 'transparent',
                color: layout === '16' ? '#070b14' : 'var(--text-secondary)',
                boxShadow: layout === '16' ? '0 0 14px var(--accent-cyan-dim)' : 'none',
              }}
              title="4x4 High Density Wall"
            >
              <Grid size={15} />
              <span>4x4</span>
            </button>

            <button
              onClick={() => setLayout('30')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-sm)',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.82rem',
                fontWeight: 800,
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                background: layout === '30' ? 'var(--accent-cyan)' : 'transparent',
                color: layout === '30' ? '#070b14' : 'var(--text-secondary)',
                boxShadow: layout === '30' ? '0 0 14px var(--accent-cyan-dim)' : 'none',
              }}
              title="All 30 Live Gujarat Cameras"
            >
              <Layers size={15} />
              <span>ALL 30</span>
            </button>
          </div>

          {/* Master AI Detection Toggle Button (Manual On/Off) */}
          <button
            onClick={() => setIsGlobalAiEnabled(!isGlobalAiEnabled)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '9px 18px',
              borderRadius: 'var(--radius-md)',
              fontFamily: 'var(--font-heading)',
              fontSize: '0.82rem',
              fontWeight: 800,
              letterSpacing: '0.5px',
              cursor: 'pointer',
              transition: 'all 0.25s ease',
              background: isGlobalAiEnabled
                ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.25) 0%, rgba(5, 150, 105, 0.45) 100%)'
                : 'rgba(15, 23, 42, 0.85)',
              color: isGlobalAiEnabled ? '#10b981' : 'var(--text-secondary)',
              border: isGlobalAiEnabled ? '1px solid #10b981' : '1px solid var(--border-medium)',
              boxShadow: isGlobalAiEnabled ? '0 0 16px rgba(16, 185, 129, 0.4)' : 'none',
            }}
            title={isGlobalAiEnabled ? 'Click to Pause AI Detection (Show Clean Footage Only)' : 'Click to Activate Real-Time AI Detection & HUD'}
          >
            <Cpu size={16} className={isGlobalAiEnabled ? 'text-emerald-400 animate-pulse' : 'text-slate-500'} />
            <span>{isGlobalAiEnabled ? '⚡ AI DETECTION: ACTIVE' : '🤖 AI DETECTION: OFF'}</span>
          </button>

          {/* Refresh Button */}
          <button
            onClick={fetchCameras}
            className="icon-btn highlight-btn"
            style={{
              padding: '10px 14px',
              height: 'auto',
              width: 'auto',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.8rem',
              fontWeight: 700,
              cursor: 'pointer',
            }}
            title="Refresh All 30 Camera Streams"
          >
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
            <span>REFRESH</span>
          </button>
        </div>
      </div>

      {/* Dynamic Scaled Camera Matrix Grid */}
      {isLoading ? (
        <LoadingState message="Establishing HLS stream sessions across Gujarat surveillance grid..." />
      ) : (
        <div style={{ display: 'grid', ...getGridColsStyle() }}>
          {displayCameras.map((cam) => (
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

      {/* Tactical Live Inspector Modal */}
      {selectedCamera && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 1000,
            background: 'rgba(0, 0, 0, 0.88)',
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
              maxHeight: '92vh',
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
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: 'var(--accent-healthy)',
                    boxShadow: '0 0 8px var(--accent-healthy)',
                  }}
                />
                <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '0.95rem', color: '#fff', letterSpacing: '1px' }}>
                  TACTICAL LIVE INSPECTOR // {selectedCamera.camera_code} - {selectedCamera.name}
                </span>
                <span
                  style={{
                    background: 'var(--accent-cyan-dim)',
                    color: 'var(--accent-cyan)',
                    border: '1px solid var(--border-medium)',
                    fontSize: '0.72rem',
                    padding: '3px 10px',
                    borderRadius: 'var(--radius-sm)',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 800,
                  }}
                >
                  {selectedCamera.district || 'GUJARAT POLICE'}
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
              <div style={{ aspectRatio: '16/9', background: '#000', borderRadius: 'var(--radius-md)', overflow: 'hidden', boxShadow: '0 8px 30px rgba(0,0,0,0.7)' }}>
                <CameraPlayer
                  camera={selectedCamera}
                  status={selectedCamera.status}
                  fps={selectedCamera.fps || 25}
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
    </div>
  );
};
