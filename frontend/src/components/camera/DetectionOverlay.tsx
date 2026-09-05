import React, { useEffect, useState, useRef, useCallback } from 'react';
import { ShieldAlert, Car, User, Bike, Truck, Sparkles, Activity, Eye, Zap, AlertCircle } from 'lucide-react';

export interface DetectionAttribute {
  is_vehicle?: boolean;
  structure_type?: string;
  make?: string;
  model?: string;
  display_name?: string;
  classification_status?: 'CONFIDENT' | 'LIKELY' | 'UNCERTAIN' | 'UNKNOWN';
  color?: string;
  color_hex?: string;
  color_confidence?: number;
  license_plate?: string;
  plate_confidence?: number;
  speed_kmph?: number;
  activity?: string;
  helmet_detected?: boolean;
  threat_level?: string;
}

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  width: number;
  height: number;
}

export interface LiveDetectionItem {
  detection_id: string;
  camera_id?: string;
  object_class: string;
  confidence: number;
  track_id?: number;
  first_seen?: string;
  last_seen?: string;
  dwell_time?: number;
  movement_direction?: string;
  display_label?: string;
  classification_status?: 'CONFIDENT' | 'LIKELY' | 'UNCERTAIN' | 'UNKNOWN';
  event_lifecycle?: 'DETECTED' | 'TRACKING' | 'CONFIRMED' | 'ENDED';
  bounding_box: BoundingBox;
  attributes?: DetectionAttribute;
  is_watchlist_match?: boolean;
  is_hard_negative?: boolean;
  threat_level?: 'NORMAL' | 'ELEVATED' | 'CRITICAL';
}

export interface LiveHudPayload {
  type: string;
  camera_id: string;
  frame_seq: number;
  timestamp: string;
  ai_fps?: number;
  latency_ms?: number;
  summary?: {
    total_objects: number;
    vehicles_count: number;
    persons_count: number;
    plates_count: number;
    critical_alerts: number;
  };
  detections: LiveDetectionItem[];
}

export interface DetectionOverlayProps {
  cameraId: string;
  isEnabled?: boolean;
  showPlates?: boolean;
  showAttributes?: boolean;
  showLabels?: boolean;
  customDetections?: LiveDetectionItem[];
}

export type DetectionRingState = 'IDLE' | 'ANALYZING' | 'DETECTION_FOUND' | 'NO_DETECTION' | 'ERROR';

export const DetectionOverlay: React.FC<DetectionOverlayProps> = ({
  cameraId,
  isEnabled = true,
  showPlates = true,
  showAttributes = true,
  showLabels = true,
  customDetections,
}) => {
  const [detections, setDetections] = useState<LiveDetectionItem[]>([]);
  const [detectionState, setDetectionState] = useState<DetectionRingState>('ANALYZING');
  const [aiStats, setAiStats] = useState<{ fps: number; latency: number; objects: number }>({
    fps: 25,
    latency: 18,
    objects: 0,
  });
  const [selectedDet, setSelectedDet] = useState<LiveDetectionItem | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Connect to live detection endpoint and WebSocket
  useEffect(() => {
    if (!isEnabled) {
      setDetectionState('IDLE');
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    setDetectionState('ANALYZING');

    if (customDetections && customDetections.length > 0) {
      setDetections(customDetections);
      setDetectionState('DETECTION_FOUND');
      return;
    }

    let isMounted = true;

    // 1. Initial snapshot fetch
    fetch(`/api/v1/streams/${encodeURIComponent(cameraId)}/detections/live`)
      .then((res) => res.json())
      .then((data) => {
        if (isMounted) {
          const objs = data?.data?.detections || [];
          setDetections(objs);
          setDetectionState(objs.length > 0 ? 'DETECTION_FOUND' : 'NO_DETECTION');
          setAiStats({
            fps: data.data.ai_fps || 25,
            latency: data.data.latency_ms || 18,
            objects: objs.length,
          });
        }
      })
      .catch(() => {
        if (isMounted) setDetectionState('NO_DETECTION');
      });

    // 2. WebSocket Real-time live HUD stream with auto-reconnection
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsHost = host.includes(':3000') ? host.replace(':3000', ':8000') : host;
    const wsUrl = `${protocol}//${wsHost}/api/v1/streams/${encodeURIComponent(cameraId)}/detections/ws?fps=15`;

    let reconnectTimeout: number | null = null;

    const connectWs = () => {
      if (!isMounted) return;
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const data: any = JSON.parse(event.data);
            const rawObjs = data?.objects || data?.detections || [];
            setDetections(rawObjs);
            setDetectionState(rawObjs.length > 0 ? 'DETECTION_FOUND' : 'NO_DETECTION');
            setAiStats({
              fps: data.ai_fps || 25,
              latency: data.latency_ms || 18,
              objects: rawObjs.length,
            });
          } catch {
            // ignore parse error
          }
        };

        ws.onclose = () => {
          if (isMounted) {
            setDetectionState('ANALYZING');
            reconnectTimeout = window.setTimeout(connectWs, 3000);
          }
        };

        ws.onerror = () => {
          if (isMounted) {
            setDetectionState('ERROR');
          }
        };
      } catch {
        if (isMounted) {
          setDetectionState('ERROR');
          reconnectTimeout = window.setTimeout(connectWs, 3000);
        }
      }
    };

    connectWs();

    return () => {
      isMounted = false;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [cameraId, isEnabled, customDetections]);

  if (!isEnabled) {
    return null;
  }

  const getClassTheme = (det: LiveDetectionItem) => {
    if (det.is_watchlist_match || det.threat_level === 'CRITICAL') {
      return {
        color: '#EF4444',
        border: 'rgba(239, 68, 68, 0.95)',
        bg: 'rgba(239, 68, 68, 0.22)',
        badgeBg: '#DC2626',
        badgeText: '#FFFFFF',
        icon: <ShieldAlert size={12} style={{ color: '#FFFFFF' }} />,
      };
    }
    const cls = det.object_class?.toUpperCase();
    if (cls === 'PERSON') {
      return {
        color: '#00F0FF',
        border: 'rgba(0, 240, 255, 0.95)',
        bg: 'rgba(0, 240, 255, 0.16)',
        badgeBg: '#0891B2',
        badgeText: '#FFFFFF',
        icon: <User size={12} />,
      };
    }
    if (cls === 'MOTORCYCLE' || cls === 'TWO_WHEELER' || cls === 'SCOOTER' || cls === 'BICYCLE') {
      return {
        color: '#C084FC',
        border: 'rgba(192, 132, 252, 0.95)',
        bg: 'rgba(192, 132, 252, 0.16)',
        badgeBg: '#9333EA',
        badgeText: '#FFFFFF',
        icon: <Bike size={12} />,
      };
    }
    if (cls === 'AUTO_RICKSHAW') {
      return {
        color: '#FACC15',
        border: 'rgba(250, 204, 21, 0.95)',
        bg: 'rgba(250, 204, 21, 0.16)',
        badgeBg: '#CA8A04',
        badgeText: '#08131E',
        icon: <Car size={12} />,
      };
    }
    if (cls === 'TRUCK' || cls === 'BUS') {
      return {
        color: '#F59E0B',
        border: 'rgba(245, 158, 11, 0.95)',
        bg: 'rgba(245, 158, 11, 0.16)',
        badgeBg: '#D97706',
        badgeText: '#08131E',
        icon: <Truck size={12} />,
      };
    }
    // Default Car / Vehicle (Emerald Cyber Green)
    return {
      color: '#10B981',
      border: 'rgba(16, 185, 129, 0.95)',
      bg: 'rgba(16, 185, 129, 0.16)',
      badgeBg: '#059669',
      badgeText: '#FFFFFF',
      icon: <Car size={12} />,
    };
  };

  return (
    <div className="phantom-ai-detection-overlay">
      {/* Top HUD Telemetry Banner & Detection Ring Indicator */}
      <div className="phantom-hud-status-strip">
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '12px',
            height: '12px',
            borderRadius: '50%',
            border: `2px solid ${
              detectionState === 'DETECTION_FOUND'
                ? '#10b981'
                : detectionState === 'NO_DETECTION'
                ? '#06b6d4'
                : detectionState === 'ANALYZING'
                ? '#38bdf8'
                : '#ef4444'
            }`,
            backgroundColor:
              detectionState === 'DETECTION_FOUND'
                ? 'rgba(16, 185, 129, 0.3)'
                : detectionState === 'NO_DETECTION'
                ? 'rgba(6, 182, 212, 0.2)'
                : 'transparent',
          }}
        >
          {detectionState === 'ANALYZING' && (
            <span
              style={{
                width: '6px',
                height: '6px',
                border: '1.5px solid #38bdf8',
                borderTopColor: 'transparent',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
              }}
            />
          )}
          {detectionState === 'DETECTION_FOUND' && (
            <span
              style={{
                width: '4px',
                height: '4px',
                borderRadius: '50%',
                backgroundColor: '#10b981',
              }}
            />
          )}
        </span>
        <span>YOLO26 AI</span>
        <span style={{ color: '#64748b' }}>|</span>
        <span style={{ color: detectionState === 'DETECTION_FOUND' ? '#34d399' : '#94a3b8' }}>
          {detectionState === 'DETECTION_FOUND'
            ? `${aiStats.objects} OBJECTS DETECTED`
            : detectionState === 'NO_DETECTION'
            ? 'NO OBJECTS IN VIEW'
            : detectionState === 'ANALYZING'
            ? 'ANALYZING SCENE...'
            : 'AI OFFLINE'}
        </span>
        <span style={{ color: '#64748b' }}>|</span>
        <span>{aiStats.fps} FPS</span>
      </div>

      {/* Render Detection Bounding Boxes */}
      {detections.map((det) => {
        const box = det.bounding_box;
        if (!box) return null;

        const theme = getClassTheme(det);
        const attr = det.attributes || {};
        const isCar = attr.is_vehicle || det.object_class === 'CAR' || det.object_class === 'TWO_WHEELER' || det.object_class === 'AUTO_RICKSHAW';
        const hasPlate = showPlates && Boolean(attr.license_plate);
        const confidencePct = Math.round((det.confidence || 0.9) * 100);
        const cStatus = det.classification_status || attr.classification_status || 'CONFIDENT';

        return (
          <div
            key={det.detection_id}
            className="phantom-detection-box-wrap"
            style={{
              left: `${box.x1}%`,
              top: `${box.y1}%`,
              width: `${box.width}%`,
              height: `${box.height}%`,
            }}
            onClick={(e) => {
              e.stopPropagation();
              setSelectedDet(selectedDet?.detection_id === det.detection_id ? null : det);
            }}
          >
            {/* Main Bounding Box */}
            <div
              className="phantom-detection-box"
              style={{
                borderColor: theme.border,
                backgroundColor: theme.bg,
                boxShadow: `0 0 14px ${theme.color}60`,
              }}
            >
              {/* Tactical Corner Reticles */}
              <div className="phantom-corner-tl" style={{ borderColor: theme.color }} />
              <div className="phantom-corner-tr" style={{ borderColor: theme.color }} />
              <div className="phantom-corner-bl" style={{ borderColor: theme.color }} />
              <div className="phantom-corner-br" style={{ borderColor: theme.color }} />

              {/* Crosshair Center Point */}
              <div
                className="phantom-crosshair-center"
                style={{ backgroundColor: theme.color }}
              />

              {/* Top Label & Classification Tag (e.g. Person 96%, Car #7 | WagonR 84%) */}
              {showLabels && (
                <div
                  className="phantom-box-top-tag"
                  style={{
                    backgroundColor: theme.badgeBg,
                    color: theme.badgeText,
                  }}
                >
                  {theme.icon}
                  <span style={{ fontWeight: 600 }}>
                    {det.is_watchlist_match
                      ? `🚨 Watchlist Hit | ${confidencePct}%`
                      : det.display_label
                      ? det.display_label
                      : `${det.object_class ? det.object_class.charAt(0).toUpperCase() + det.object_class.slice(1).toLowerCase() : 'Object'}${det.track_id ? ` #${det.track_id}` : ''} | ${confidencePct}%`}
                  </span>
                </div>
              )}

              {/* Bottom Metadata Badges (Make/Model, Color, License Plate) */}
              {showAttributes && (isCar || hasPlate) && (
                <div className="phantom-box-bottom-badges">
                  {/* Make & Model Badge (Only when not uncertain) */}
                  {isCar && attr.display_name && cStatus !== 'UNCERTAIN' && (
                    <div
                      className="phantom-badge-pill"
                      style={{
                        color: '#6ee7b7',
                        borderColor: 'rgba(16, 185, 129, 0.5)',
                      }}
                    >
                      <span>{attr.display_name}</span>
                    </div>
                  )}

                  {/* Uncertainty Status Pill */}
                  {cStatus === 'UNCERTAIN' && (
                    <div
                      className="phantom-badge-pill"
                      style={{
                        color: '#FDE047',
                        borderColor: 'rgba(250, 204, 21, 0.5)',
                        backgroundColor: 'rgba(250, 204, 21, 0.15)',
                      }}
                    >
                      <span>Model Uncertain</span>
                    </div>
                  )}

                  {/* Color Badge with Color Swatch */}
                  {isCar && attr.color && (
                    <div
                      className="phantom-badge-pill"
                      style={{
                        color: '#f1f5f9',
                        borderColor: 'rgba(255, 255, 255, 0.25)',
                      }}
                    >
                      <span
                        style={{
                          display: 'inline-block',
                          width: '8px',
                          height: '8px',
                          borderRadius: '50%',
                          backgroundColor: attr.color_hex || '#FFFFFF',
                          border: '1px solid rgba(255,255,255,0.6)',
                        }}
                      />
                      <span>{attr.color}</span>
                    </div>
                  )}

                  {/* License Plate Number Badge */}
                  {hasPlate && (
                    <div
                      className={det.is_watchlist_match ? 'phantom-badge-pill phantom-badge-watchlist' : 'phantom-badge-pill phantom-badge-plate'}
                    >
                      <span style={{ fontSize: '8px', opacity: 0.8 }}>IND</span>
                      <span style={{ textDecoration: 'underline' }}>{attr.license_plate}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
