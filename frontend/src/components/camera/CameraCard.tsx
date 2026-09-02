import React from 'react';
import { Camera } from '../../types';
import { CameraPlayer } from './CameraPlayer';
import { CameraStatusBadge } from './CameraStatusBadge';
import { Maximize2, MapPin, Shield } from 'lucide-react';

export interface CameraCardProps {
  camera: Camera;
  onSelect?: (camera: Camera) => void;
  isFocused?: boolean;
  isAiOverlayEnabled?: boolean;
}

export const CameraCard: React.FC<CameraCardProps> = ({
  camera,
  onSelect,
  isFocused = false,
  isAiOverlayEnabled,
}) => {
  const primaryStream = camera.streams && camera.streams.length > 0 ? camera.streams[0] : undefined;

  const handleInspectClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onSelect) onSelect(camera);
  };

  return (
    <div
      className={`camera-card-wrapper ${isFocused ? 'focused' : ''}`}
      onClick={() => onSelect && onSelect(camera)}
      style={{
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg-card)',
        backdropFilter: 'var(--glass-blur)',
        WebkitBackdropFilter: 'var(--glass-blur)',
        border: isFocused ? '1px solid var(--accent-purple)' : '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        boxShadow: isFocused ? '0 0 20px var(--phantom-purple-dim)' : 'var(--card-shadow)',
        transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        cursor: 'pointer',
      }}
    >
      {/* Top Header: Clean Camera Identity + ONE Primary Action Button */}
      <div
        className="camera-card-header"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 12px',
          background: 'var(--bg-secondary)',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
          <CameraStatusBadge status={camera.status} />
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontWeight: 800,
              fontSize: '0.8rem',
              color: 'var(--accent-purple)',
              letterSpacing: '0.5px',
            }}
          >
            {camera.camera_code || camera.id}
          </span>
          <span
            style={{
              fontSize: '0.78rem',
              color: 'var(--text-secondary)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              maxWidth: '180px',
            }}
          >
            {camera.name}
          </span>
        </div>

        {/* ONE Primary Action Button: INSPECT */}
        <button
          onClick={handleInspectClick}
          className="icon-btn highlight-btn"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            background: 'var(--accent-purple-dim)',
            border: '1px solid var(--border-medium)',
            color: 'var(--accent-purple)',
            padding: '5px 12px',
            borderRadius: 'var(--radius-sm)',
            fontWeight: 800,
            fontSize: '0.7rem',
            fontFamily: 'var(--font-mono)',
            height: 'auto',
            width: 'auto',
            cursor: 'pointer',
          }}
          title="Open Tactical Live Inspector"
        >
          <Maximize2 size={12} />
          <span>INSPECT</span>
        </button>
      </div>

      {/* Video Player (Large, Clean Preview) */}
      <div
        className="camera-card-player-wrap"
        style={{
          position: 'relative',
          width: '100%',
          aspectRatio: '16/9',
          background: '#000',
          overflow: 'hidden',
        }}
      >
        <CameraPlayer
          camera={camera}
          streamUrl={primaryStream?.stream_url}
          protocol={primaryStream?.protocol || 'WEBRTC'}
          status={camera.status}
          fps={camera.fps || 25}
          quality={camera.status === 'ONLINE' ? 'EXCELLENT' : 'OFFLINE'}
          isAiOverlayEnabled={isAiOverlayEnabled}
        />
      </div>

      {/* Bottom Information Toolbar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 12px',
          background: 'var(--bg-tertiary)',
          borderTop: '1px solid var(--border-subtle)',
          fontSize: '0.72rem',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-muted)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <MapPin size={12} style={{ color: 'var(--accent-purple)' }} />
          <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
            {camera.district || 'Gujarat'}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              padding: '1px 6px',
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '3px',
              color: 'var(--text-secondary)',
              fontSize: '0.68rem',
            }}
          >
            {camera.camera_type || 'ANPR'}
          </span>
          <span style={{ color: 'var(--accent-healthy)', fontWeight: 800 }}>
            1080p • 25 FPS
          </span>
        </div>
      </div>
    </div>
  );
};
