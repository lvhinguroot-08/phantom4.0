import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  User,
  Car,
  Bike,
  Truck,
  Sparkles,
  Activity,
  Clock,
  Navigation,
  ShieldAlert,
  Wifi,
  WifiOff,
  Layers,
  Cpu,
} from 'lucide-react';
import { Camera } from '../../types';

export interface TrackedObjectItem {
  detection_id?: string;
  track_id?: number;
  object_class?: string;
  class_name?: string;
  confidence: number;
  camera_id?: string;
  first_seen?: string;
  last_seen?: string;
  dwell_time?: number;
  movement_direction?: string;
  display_label?: string;
  bbox?: { x1: number; y1: number; x2: number; y2: number };
  attributes?: {
    is_vehicle?: boolean;
    display_name?: string;
    color?: string;
    color_hex?: string;
    license_plate?: string;
    speed_kmph?: number;
  };
  is_watchlist_match?: boolean;
}

export interface CameraAiInfoPanelProps {
  camera: Camera;
  className?: string;
}

export const CameraAiInfoPanel: React.FC<CameraAiInfoPanelProps> = ({ camera, className = '' }) => {
  const [objects, setObjects] = useState<TrackedObjectItem[]>([]);
  const [summary, setSummary] = useState<{
    persons: number;
    cars: number;
    other_vehicles: number;
    total_objects: number;
  }>({
    persons: 0,
    cars: 0,
    other_vehicles: 0,
    total_objects: 0,
  });
  const [aiStatus, setAiStatus] = useState<'CONNECTED' | 'RECONNECTING' | 'OFFLINE'>('RECONNECTING');
  const [aiFps, setAiFps] = useState<number>(2.0);
  const [latencyMs, setLatencyMs] = useState<number>(200);

  const wsRef = useRef<WebSocket | null>(null);
  const camId = camera.id || camera.camera_code || 'CAM-001';

  // Format ISO timestamp into clean local time HH:mm:ss
  const formatTime = (isoString?: string) => {
    if (!isoString) return '--:--:--';
    try {
      const dt = new Date(isoString);
      if (isNaN(dt.getTime())) return isoString;
      return dt.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  useEffect(() => {
    let isMounted = true;
    let reconnectTimer: number | null = null;

    // 1. Initial snapshot fetch
    fetch(`/api/v1/streams/${encodeURIComponent(camId)}/detections/live`)
      .then((res) => res.json())
      .then((data) => {
        if (!isMounted) return;
        if (data?.data) {
          const rawList: TrackedObjectItem[] = data.data.objects || data.data.detections || [];
          setObjects(rawList);
          updateSummary(rawList);
          if (data.data.ai_fps) setAiFps(data.data.ai_fps);
          if (data.data.latency_ms) setLatencyMs(data.data.latency_ms);
          setAiStatus('CONNECTED');
        }
      })
      .catch(() => {
        if (isMounted) setAiStatus('RECONNECTING');
      });

    // 2. Connect to Camera-Specific WebSocket Channel
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsHost = host.includes(':3000') ? host.replace(':3000', ':8000') : host;
    const wsUrl = `${protocol}//${wsHost}/api/v1/streams/${encodeURIComponent(camId)}/detections/ws?fps=15`;

    const connect = () => {
      if (!isMounted) return;
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMounted) return;
          setAiStatus('CONNECTED');
        };

        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(event.data);
            const rawList: TrackedObjectItem[] = data.objects || data.detections || [];
            setObjects(rawList);
            updateSummary(rawList, data.summary);
            if (data.ai_fps) setAiFps(data.ai_fps);
            if (data.latency_ms) setLatencyMs(data.latency_ms);
            setAiStatus('CONNECTED');
          } catch {
            // Ignore parse errors
          }
        };

        ws.onerror = () => {
          if (!isMounted) return;
          setAiStatus('RECONNECTING');
        };

        ws.onclose = () => {
          if (!isMounted) return;
          setAiStatus('OFFLINE');
          reconnectTimer = window.setTimeout(connect, 3000);
        };
      } catch {
        if (isMounted) {
          setAiStatus('OFFLINE');
          reconnectTimer = window.setTimeout(connect, 3000);
        }
      }
    };

    connect();

    return () => {
      isMounted = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [camId]);

  const updateSummary = (
    list: TrackedObjectItem[],
    remoteSummary?: { persons?: number; cars?: number; total_objects?: number }
  ) => {
    let persons = 0;
    let cars = 0;
    let other = 0;

    for (const item of list) {
      const cls = (item.class_name || item.object_class || '').toUpperCase();
      if (cls === 'PERSON') {
        persons++;
      } else if (cls === 'CAR') {
        cars++;
      } else {
        other++;
      }
    }

    setSummary({
      persons: remoteSummary?.persons ?? persons,
      cars: remoteSummary?.cars ?? cars,
      other_vehicles: other,
      total_objects: remoteSummary?.total_objects ?? list.length,
    });
  };

  const getObjectTheme = (item: TrackedObjectItem) => {
    if (item.is_watchlist_match) {
      return {
        bg: 'bg-rose-950/60 border-rose-500/50',
        text: 'text-rose-400',
        badge: 'bg-rose-950 text-rose-300 border-rose-500/40',
        icon: <ShieldAlert size={13} className="text-rose-400" />,
      };
    }
    const cls = (item.class_name || item.object_class || '').toUpperCase();
    if (cls === 'PERSON') {
      return {
        bg: 'bg-cyan-950/40 border-cyan-500/30',
        text: 'text-cyan-400',
        badge: 'bg-cyan-950 text-cyan-300 border-cyan-500/40',
        icon: <User size={13} className="text-cyan-400" />,
      };
    }
    if (cls === 'MOTORCYCLE' || cls === 'TWO_WHEELER') {
      return {
        bg: 'bg-purple-950/40 border-purple-500/30',
        text: 'text-purple-400',
        badge: 'bg-purple-950 text-purple-300 border-purple-500/40',
        icon: <Bike size={13} className="text-purple-400" />,
      };
    }
    if (cls === 'BUS' || cls === 'TRUCK') {
      return {
        bg: 'bg-amber-950/40 border-amber-500/30',
        text: 'text-amber-400',
        badge: 'bg-amber-950 text-amber-300 border-amber-500/40',
        icon: <Truck size={13} className="text-amber-400" />,
      };
    }
    return {
      bg: 'bg-emerald-950/40 border-emerald-500/30',
      text: 'text-emerald-400',
      badge: 'bg-emerald-950 text-emerald-300 border-emerald-500/40',
      icon: <Car size={13} className="text-emerald-400" />,
    };
  };

  return (
    <div
      className={`bg-slate-950/80 rounded-lg border border-cyan-500/30 p-3.5 flex flex-col font-mono text-xs shadow-xl ${className}`}
    >
      {/* Header Bar */}
      <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-800">
        <div className="flex items-center gap-1.5 text-cyan-400 font-bold tracking-wide">
          <Sparkles size={14} className="text-cyan-400" />
          <span>AI LIVE DETECTIONS</span>
        </div>

        {/* AI Stream Status Badge */}
        {aiStatus === 'CONNECTED' ? (
          <div className="flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-500/40 font-bold">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
            <span>ONLINE • {aiFps} FPS</span>
          </div>
        ) : aiStatus === 'RECONNECTING' ? (
          <div className="flex items-center gap-1 text-[10px] text-amber-400 bg-amber-950/80 px-2 py-0.5 rounded border border-amber-500/40">
            <Wifi size={11} className="animate-spin" />
            <span>RECONNECTING...</span>
          </div>
        ) : (
          <div className="flex items-center gap-1 text-[10px] text-rose-400 bg-rose-950/80 px-2 py-0.5 rounded border border-rose-500/40">
            <WifiOff size={11} />
            <span>AI OFFLINE</span>
          </div>
        )}
      </div>

      {/* Live Counters Section */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
        {/* Persons Counter */}
        <div className="bg-slate-900/90 border border-cyan-500/20 rounded p-2 flex flex-col items-center justify-center text-center">
          <div className="flex items-center gap-1 text-cyan-400 font-medium text-[11px] mb-0.5">
            <User size={12} />
            <span>Persons</span>
          </div>
          <span className="text-lg font-bold text-white tracking-wider">{summary.persons}</span>
        </div>

        {/* Cars Counter */}
        <div className="bg-slate-900/90 border border-emerald-500/20 rounded p-2 flex flex-col items-center justify-center text-center">
          <div className="flex items-center gap-1 text-emerald-400 font-medium text-[11px] mb-0.5">
            <Car size={12} />
            <span>Cars</span>
          </div>
          <span className="text-lg font-bold text-white tracking-wider">{summary.cars}</span>
        </div>

        {/* Other Vehicles Counter */}
        <div className="bg-slate-900/90 border border-amber-500/20 rounded p-2 flex flex-col items-center justify-center text-center">
          <div className="flex items-center gap-1 text-amber-400 font-medium text-[11px] mb-0.5">
            <Truck size={12} />
            <span>Vehicles</span>
          </div>
          <span className="text-lg font-bold text-white tracking-wider">{summary.other_vehicles}</span>
        </div>

        {/* Total Tracked Objects */}
        <div className="bg-slate-900/90 border border-purple-500/30 rounded p-2 flex flex-col items-center justify-center text-center">
          <div className="flex items-center gap-1 text-purple-400 font-medium text-[11px] mb-0.5">
            <Layers size={12} />
            <span>Active Objects</span>
          </div>
          <span className="text-lg font-bold text-white tracking-wider">{summary.total_objects}</span>
        </div>
      </div>

      {/* Active Object List Subheader */}
      <div className="flex items-center justify-between text-[11px] text-slate-400 mb-2 font-semibold">
        <span>ACTIVE TRACKED OBJECTS</span>
        <span>CAMERA: {camera.camera_code || camera.name || camId}</span>
      </div>

      {/* Active Object List */}
      <div className="flex-1 overflow-y-auto space-y-2 max-h-[320px] pr-1">
        {aiStatus === 'OFFLINE' ? (
          <div className="p-6 text-center text-rose-400/80 bg-rose-950/20 rounded border border-rose-900/40 flex flex-col items-center gap-2">
            <WifiOff size={22} className="text-rose-500" />
            <span className="font-bold">AI Detection Stream Offline</span>
            <span className="text-[10px] text-slate-400">
              Reconnecting to stream gateway ({camId})...
            </span>
          </div>
        ) : objects.length === 0 ? (
          <div className="p-6 text-center text-slate-500 bg-slate-900/40 rounded border border-slate-800 flex flex-col items-center gap-2">
            <Activity size={20} className="text-slate-600 animate-pulse" />
            <span className="font-semibold text-slate-400">No detections currently active in this camera feed</span>
            <span className="text-[10px] text-slate-600">
              Surveillance engine actively scanning frames at {aiFps} FPS
            </span>
          </div>
        ) : (
          objects.map((item, idx) => {
            const theme = getObjectTheme(item);
            const rawCls = item.class_name || item.object_class || 'OBJECT';
            const formattedType = rawCls.charAt(0).toUpperCase() + rawCls.slice(1).toLowerCase();
            const trackIdNum = item.track_id ?? idx + 1;
            const confPct = Math.round((item.confidence || 0.9) * 100);

            return (
              <div
                key={item.detection_id || `${camId}-track-${trackIdNum}-${idx}`}
                className={`p-2.5 rounded border transition-all ${theme.bg}`}
              >
                {/* Top Row: Track ID & Confidence */}
                <div className="flex items-center justify-between font-bold">
                  <span className={`flex items-center gap-1.5 text-[11px] ${theme.text}`}>
                    {theme.icon}
                    <span>
                      {formattedType} #{trackIdNum}
                    </span>
                  </span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded border font-mono ${theme.badge}`}
                  >
                    Confidence: {confPct}%
                  </span>
                </div>

                {/* Second Row: First Seen, Last Seen, Dwell Time */}
                <div className="mt-1.5 grid grid-cols-2 gap-1 text-[10px] text-slate-300">
                  <div className="flex items-center gap-1">
                    <Clock size={11} className="text-cyan-400" />
                    <span>First Seen: <b className="text-white">{formatTime(item.first_seen)}</b></span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock size={11} className="text-cyan-400" />
                    <span>Last Seen: <b className="text-white">{formatTime(item.last_seen)}</b></span>
                  </div>
                </div>

                {/* Optional Badges: Dwell Time, Direction, License Plate */}
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[10px]">
                  {item.dwell_time !== undefined && (
                    <span className="bg-slate-900 px-1.5 py-0.5 rounded border border-slate-700 text-slate-300">
                      Dwell: <b className="text-emerald-400">{item.dwell_time}s</b>
                    </span>
                  )}
                  {item.movement_direction && item.movement_direction !== 'STATIONARY' && (
                    <span className="bg-slate-900 px-1.5 py-0.5 rounded border border-slate-700 text-cyan-300 flex items-center gap-0.5">
                      <Navigation size={10} className="rotate-45" />
                      <span>{item.movement_direction}</span>
                    </span>
                  )}
                  {item.attributes?.license_plate && (
                    <span className="bg-amber-400 text-black font-black px-1.5 py-0.5 rounded">
                      {item.attributes.license_plate}
                    </span>
                  )}
                  {item.attributes?.display_name && (
                    <span className="bg-slate-900 px-1.5 py-0.5 rounded border border-slate-700 text-slate-300">
                      {item.attributes.display_name}
                    </span>
                  )}
                </div>

                {/* Watchlist Alert banner if hit */}
                {item.is_watchlist_match && (
                  <div className="mt-1.5 text-[10px] text-rose-300 font-bold flex items-center gap-1 bg-rose-950/80 p-1 rounded border border-rose-500/40">
                    <ShieldAlert size={12} className="text-rose-400" />
                    <span>🚨 MATCHED HOTLIST: IMMEDIATE ACTION REQUIRED</span>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
