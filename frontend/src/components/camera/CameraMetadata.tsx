import React from 'react';
import { Camera } from '../../types';
import { MapPin, Cpu, Radio, Video, Clock, AlertTriangle } from 'lucide-react';

export const CameraMetadata: React.FC<{ camera: Camera }> = ({ camera }) => {
  const codecLabel = camera.codec || 'H.264';
  const resolutionLabel = camera.resolution || '1080p';
  const streamType = camera.whep_url ? 'WHEP (WebRTC)' : 'HLS Fallback';
  const connectionState = camera.connection_state || camera.status;
  const isDegraded = connectionState === 'DEGRADED' || connectionState === 'RECONNECTING';

  return (
    <div className="cam-metadata-panel">
      <div className="cam-meta-row main">
        <span className="cam-code">{camera.camera_code}</span>
        <span className="cam-name">{camera.name || camera.location_description || 'Gujarat Police Feed'}</span>
      </div>

      <div className="cam-meta-row sub">
        <div className="cam-meta-item" title="Location & District">
          <MapPin size={11} className="text-cyan" />
          <span>{camera.location_description || camera.district || 'Gujarat Grid'}</span>
        </div>

        <div className="cam-meta-item" title="Stream Codec & Resolution">
          <Video size={11} className="text-cyan" />
          <span>{codecLabel} • {resolutionLabel}</span>
        </div>

        <div className="cam-meta-item" title="Stream Transport Protocol">
          <Radio size={11} className="text-muted" />
          <span>{streamType}</span>
        </div>

        {camera.last_seen && (
          <div className="cam-meta-item" title="Last Frame / Telemetry Timestamp">
            <Clock size={11} className="text-muted" />
            <span>{new Date(camera.last_seen).toLocaleTimeString()}</span>
          </div>
        )}

        {isDegraded && (
          <div className="cam-meta-item text-rose-400 font-bold" title={camera.last_error || 'Reconnecting...'}>
            <AlertTriangle size={11} className="animate-pulse" />
            <span>{connectionState} (Retry #{camera.reconnect_attempt || 1})</span>
          </div>
        )}
      </div>
    </div>
  );
};
