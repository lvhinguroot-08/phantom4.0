import React, { useState, useEffect, useRef } from 'react';
import {
  Search,
  X,
  Camera,
  Car,
  Bell,
  Compass,
  MapPin,
  Tv,
  ArrowRight,
  Shield,
  Activity,
} from 'lucide-react';
import { NavView } from './Sidebar';
import { camerasApi } from '../../api/cameras';
import { alertsApi } from '../../api/alerts';
import { Camera as CameraType, Alert } from '../../types';

interface GlobalSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (view: NavView) => void;
  onSelectCamera?: (camera: CameraType) => void;
}

export const GlobalSearchModal: React.FC<GlobalSearchModalProps> = ({
  isOpen,
  onClose,
  onNavigate,
  onSelectCamera,
}) => {
  const [query, setQuery] = useState('');
  const [cameras, setCameras] = useState<CameraType[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load searchable data
  useEffect(() => {
    if (isOpen) {
      camerasApi.fetchDirectCorp8Catalog().then((cams) => setCameras(cams)).catch(() => {});
      alertsApi.list({ limit: 20 }).then((res) => {
        if (res.data) setAlerts(res.data);
      }).catch(() => {});
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Quick navigation shortcuts
  const navShortcuts: Array<{ id: NavView; label: string; icon: React.ElementType; category: string; description: string }> = [
    { id: 'dashboard', label: 'CCTV Command Dashboard', icon: Tv, category: 'Navigation', description: 'Statewide CCTV Wall & AI detections' },
    { id: 'live_monitoring', label: '30-Feed Live Monitoring', icon: Tv, category: 'Navigation', description: 'Real-time multi-grid CCTV streams' },
    { id: 'camera_registry', label: 'Camera Registry', icon: Camera, category: 'Navigation', description: 'Statewide camera inventory & statuses' },
    { id: 'copilot', label: 'AI Tactical Copilot', icon: Compass, category: 'Navigation', description: 'ChatGPT-style surveillance intelligence agent' },
    { id: 'anpr', label: 'ANPR & Vehicle Intelligence', icon: Car, category: 'Navigation', description: 'Gujarat license plate tracking & trajectories' },
    { id: 'watchlist', label: 'Watchlist & Suspect Hotlist', icon: Shield, category: 'Navigation', description: 'Bolo alerts, stolen cars & wanted vehicles' },
    { id: 'alerts', label: 'Alerts & Incident Dispatch', icon: Bell, category: 'Navigation', description: 'Live threat triage, violations & critical alerts' },
    { id: 'map', label: 'CCTV Satellite Map & Gaps', icon: MapPin, category: 'Navigation', description: 'Geospatial coverage & blindspot density analysis' },
    { id: 'system_health', label: 'Stream & System Health', icon: Activity, category: 'Navigation', description: 'RTSP latency, GPU inference & audit logs' },
  ];

  // Filtered Results
  const q = query.trim().toLowerCase();

  const filteredShortcuts = navShortcuts.filter(
    (n) => !q || n.label.toLowerCase().includes(q) || n.description.toLowerCase().includes(q)
  );

  const filteredCameras = cameras.filter(
    (c) =>
      !q ||
      c.name.toLowerCase().includes(q) ||
      c.camera_code.toLowerCase().includes(q) ||
      (c.district && c.district.toLowerCase().includes(q)) ||
      (c.city && c.city.toLowerCase().includes(q))
  ).slice(0, 8);

  const filteredAlerts = alerts.filter(
    (a) =>
      !q ||
      a.title?.toLowerCase().includes(q) ||
      (a.description && a.description.toLowerCase().includes(q)) ||
      (a.camera_name && a.camera_name.toLowerCase().includes(q)) ||
      (a.camera_id && a.camera_id.toLowerCase().includes(q))
  ).slice(0, 4);

  // Watchlist mock matches
  const sampleWatchlist = [
    { plate: 'GJ01AB1234', reason: 'Stolen Vehicle - Ahmedabad East FIR #492', district: 'Ahmedabad' },
    { plate: 'GJ05CD5678', reason: 'High-Speed Hit & Run Suspect', district: 'Surat' },
    { plate: 'GJ11XY9012', reason: 'Wanted Suspect Vehicle - Junagadh Toll', district: 'Junagadh' },
    { plate: 'GJ06KL3456', reason: 'Revoked Registration Checkpoint', district: 'Vadodara' },
  ].filter((w) => !q || w.plate.toLowerCase().includes(q) || w.reason.toLowerCase().includes(q));

  const allItems = [
    ...filteredShortcuts.map((s) => ({ type: 'NAV' as const, data: s })),
    ...filteredCameras.map((c) => ({ type: 'CAM' as const, data: c })),
    ...sampleWatchlist.map((w) => ({ type: 'WATCH' as const, data: w })),
    ...filteredAlerts.map((a) => ({ type: 'ALERT' as const, data: a })),
  ];

  const handleSelect = (index: number) => {
    const item = allItems[index];
    if (!item) return;

    if (item.type === 'NAV') {
      onNavigate(item.data.id);
      onClose();
    } else if (item.type === 'CAM') {
      if (onSelectCamera) onSelectCamera(item.data);
      onNavigate('live_monitoring');
      onClose();
    } else if (item.type === 'WATCH') {
      onNavigate('watchlist');
      onClose();
    } else if (item.type === 'ALERT') {
      onNavigate('alerts');
      onClose();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, allItems.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + allItems.length) % Math.max(1, allItems.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      handleSelect(selectedIndex);
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="spotlight-backdrop"
      onClick={onClose}
    >
      <div
        className="spotlight-card"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search Bar Header */}
        <div className="spotlight-input-wrap">
          <Search size={18} className="text-cyan" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search 30 cameras, vehicle plates, districts, alerts, or jump to view..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              color: '#fff',
              fontSize: '0.85rem',
              outline: 'none',
              fontFamily: 'var(--font-body)',
            }}
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="icon-btn"
              style={{ width: '24px', height: '24px' }}
            >
              <X size={14} />
            </button>
          )}
          <span className="search-kbd" style={{ position: 'static' }}>
            ESC
          </span>
        </div>

        {/* Results Container */}
        <div className="spotlight-results-scroll">
          {/* Navigation Shortcuts */}
          {filteredShortcuts.length > 0 && (
            <div style={{ marginBottom: '8px' }}>
              <div style={{ fontSize: '0.62rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-muted)', padding: '4px 8px', letterSpacing: '0.5px' }}>
                COMMAND NAVIGATION
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {filteredShortcuts.map((s, idx) => {
                  const itemIdx = idx;
                  const isSelected = selectedIndex === itemIdx;
                  const Icon = s.icon;
                  return (
                    <div
                      key={s.id}
                      onClick={() => handleSelect(itemIdx)}
                      className={`spotlight-result-item ${isSelected ? 'selected' : ''}`}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div
                          style={{
                            padding: '6px',
                            borderRadius: 'var(--radius-sm)',
                            background: isSelected ? 'var(--accent-cyan)' : 'var(--bg-secondary)',
                            color: isSelected ? '#070b14' : 'var(--accent-cyan)',
                          }}
                        >
                          <Icon size={16} />
                        </div>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: '0.8rem', color: '#fff' }}>{s.label}</div>
                          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{s.description}</div>
                        </div>
                      </div>
                      <ArrowRight size={14} className={isSelected ? 'text-cyan' : 'text-muted'} />
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Cameras Matches */}
          {filteredCameras.length > 0 && (
            <div style={{ marginBottom: '8px' }}>
              <div style={{ fontSize: '0.62rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-cyan)', padding: '4px 8px', letterSpacing: '0.5px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Camera size={12} /> SENTINEL CCTV CAMERAS ({filteredCameras.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {filteredCameras.map((cam, idx) => {
                  const itemIdx = filteredShortcuts.length + idx;
                  const isSelected = selectedIndex === itemIdx;
                  return (
                    <div
                      key={cam.id}
                      onClick={() => handleSelect(itemIdx)}
                      className={`spotlight-result-item ${isSelected ? 'selected' : ''}`}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span className="clearance-dot" style={{ background: 'var(--accent-healthy)' }} />
                        <div>
                          <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#fff', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)', fontWeight: 700 }}>
                              {cam.camera_code}
                            </span>
                            <span>{cam.name}</span>
                          </div>
                          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                            District: {cam.district || 'Gujarat'} • 1080p 25FPS
                          </div>
                        </div>
                      </div>
                      <span className="badge-live" style={{ fontSize: '0.6rem', padding: '2px 6px', borderRadius: '3px', fontWeight: 700 }}>
                        LIVE FEED
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Watchlist Suspect Matches */}
          {sampleWatchlist.length > 0 && (
            <div>
              <div style={{ fontSize: '0.62rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-warning)', padding: '4px 8px', letterSpacing: '0.5px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Shield size={12} /> WATCHLIST SUSPECT MATCHES
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {sampleWatchlist.map((w, idx) => {
                  const itemIdx = filteredShortcuts.length + filteredCameras.length + idx;
                  const isSelected = selectedIndex === itemIdx;
                  return (
                    <div
                      key={w.plate}
                      onClick={() => handleSelect(itemIdx)}
                      className={`spotlight-result-item ${isSelected ? 'selected' : ''}`}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div
                          style={{
                            padding: '2px 6px',
                            borderRadius: '3px',
                            background: 'rgba(234, 179, 8, 0.15)',
                            border: '1px solid var(--accent-attention)',
                            color: 'var(--accent-attention)',
                            fontFamily: 'var(--font-mono)',
                            fontWeight: 700,
                            fontSize: '0.72rem',
                          }}
                        >
                          {w.plate}
                        </div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-primary)' }}>{w.reason}</div>
                      </div>
                      <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {w.district}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: '8px 16px',
            background: 'var(--bg-secondary)',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.68rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)',
          }}
        >
          <div style={{ display: 'flex', gap: '12px' }}>
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
          <span style={{ color: 'var(--accent-cyan)' }}>PHANTOM GLOBAL SEARCH</span>
        </div>
      </div>
    </div>
  );
};
