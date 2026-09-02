import React, { useState, useMemo } from 'react';
import {
  Car,
  Search,
  Filter,
  Shield,
  ShieldAlert,
  Clock,
  MapPin,
  Camera,
  CheckCircle2,
  AlertTriangle,
  Download,
  Eye,
  X,
  Gauge,
  Sparkles,
  Layers,
} from 'lucide-react';

interface ANPRDetection {
  id: string;
  plate: string;
  vehicle_type: string;
  vehicle_color: string;
  vehicle_make: string;
  confidence: number;
  camera_code: string;
  camera_name: string;
  district: string;
  timestamp: string;
  speed_kmph: number;
  is_watchlist_hit: boolean;
  watchlist_category?: 'STOLEN' | 'WANTED' | 'BOLO' | 'REVOKED';
  watchlist_notes?: string;
  image_url?: string;
}

export const ANPRVehiclesPage: React.FC = () => {
  const [searchPlate, setSearchPlate] = useState<string>('');
  const [watchlistOnly, setWatchlistOnly] = useState<boolean>(false);
  const [districtFilter, setDistrictFilter] = useState<string>('ALL');
  const [vehicleTypeFilter, setVehicleTypeFilter] = useState<string>('ALL');
  const [selectedDetection, setSelectedDetection] = useState<ANPRDetection | null>(null);

  // Mock Statewide ANPR Log with realistic Gujarat Data
  const [detections] = useState<ANPRDetection[]>([
    {
      id: 'anpr-001',
      plate: 'GJ 01 AB 1234',
      vehicle_type: 'CAR / HATCHBACK',
      vehicle_color: 'SILVER',
      vehicle_make: 'HYUNDAI I20',
      confidence: 96.8,
      camera_code: 'CAM01',
      camera_name: '01 Chiman bhai Bridge',
      district: 'Ahmedabad',
      timestamp: '2026-09-01 16:38:12',
      speed_kmph: 58,
      is_watchlist_hit: true,
      watchlist_category: 'STOLEN',
      watchlist_notes: 'Stolen vehicle - FIR #492/2026 registered at Ahmedabad East',
    },
    {
      id: 'anpr-002',
      plate: 'GJ 05 CD 5678',
      vehicle_type: 'SUV',
      vehicle_color: 'WHITE',
      vehicle_make: 'MAHINDRA SCORPIO',
      confidence: 98.4,
      camera_code: 'CAM04',
      camera_name: '04 Paldi Circle',
      district: 'Ahmedabad',
      timestamp: '2026-09-01 16:35:45',
      speed_kmph: 64,
      is_watchlist_hit: true,
      watchlist_category: 'WANTED',
      watchlist_notes: 'High-speed reckless driving suspect - Paldi Toll Alert',
    },
    {
      id: 'anpr-003',
      plate: 'GJ 06 KL 3456',
      vehicle_type: 'SEDAN',
      vehicle_color: 'BLACK',
      vehicle_make: 'HONDA CITY',
      confidence: 94.1,
      camera_code: 'CAM08',
      camera_name: '08 Kalupur Railway Station Road',
      district: 'Ahmedabad',
      timestamp: '2026-09-01 16:32:10',
      speed_kmph: 38,
      is_watchlist_hit: false,
    },
    {
      id: 'anpr-004',
      plate: 'GJ 11 XY 9012',
      vehicle_type: 'COMMERCIAL TRUCK',
      vehicle_color: 'YELLOW / BLUE',
      vehicle_make: 'TATA 407',
      confidence: 97.2,
      camera_code: 'CAM09',
      camera_name: '09 Timbavadi Gate',
      district: 'Junagadh',
      timestamp: '2026-09-01 16:29:50',
      speed_kmph: 45,
      is_watchlist_hit: true,
      watchlist_category: 'BOLO',
      watchlist_notes: 'Unauthorized overweight cargo during restricted hours',
    },
    {
      id: 'anpr-005',
      plate: 'GJ 27 MN 7890',
      vehicle_type: 'MOTORCYCLE',
      vehicle_color: 'RED',
      vehicle_make: 'HERO SPLENDOR',
      confidence: 91.5,
      camera_code: 'CAM05',
      camera_name: '05 Visat teen Rasta',
      district: 'Ahmedabad',
      timestamp: '2026-09-01 16:24:18',
      speed_kmph: 42,
      is_watchlist_hit: false,
    },
    {
      id: 'anpr-006',
      plate: 'GJ 03 PQ 4567',
      vehicle_type: 'CAR / HATCHBACK',
      vehicle_color: 'WHITE',
      vehicle_make: 'MARUTI SWIFT',
      confidence: 95.8,
      camera_code: 'CAM19',
      camera_name: '19 Madhuram Bypass Road',
      district: 'Junagadh',
      timestamp: '2026-09-01 16:20:05',
      speed_kmph: 72,
      is_watchlist_hit: false,
    },
    {
      id: 'anpr-007',
      plate: 'GJ 18 ZZ 8899',
      vehicle_type: 'LUXURY SUV',
      vehicle_color: 'GREY',
      vehicle_make: 'TOYOTA FORTUNER',
      confidence: 99.1,
      camera_code: 'CAM11',
      camera_name: '11 Tri Mandir Adalaj Tollnaka',
      district: 'Gandhinagar',
      timestamp: '2026-09-01 16:15:30',
      speed_kmph: 88,
      is_watchlist_hit: true,
      watchlist_category: 'REVOKED',
      watchlist_notes: 'Expired commercial permit & pending court challans',
    },
    {
      id: 'anpr-008',
      plate: 'GJ 21 EF 6789',
      vehicle_type: 'VAN',
      vehicle_color: 'WHITE',
      vehicle_make: 'MARUTI ECCO',
      confidence: 93.7,
      camera_code: 'CAM17',
      camera_name: '17 Tower Road Junction',
      district: 'Navsari',
      timestamp: '2026-09-01 16:10:22',
      speed_kmph: 35,
      is_watchlist_hit: false,
    },
  ]);

  const filteredDetections = useMemo(() => {
    return detections.filter((d) => {
      if (watchlistOnly && !d.is_watchlist_hit) return false;
      if (districtFilter !== 'ALL' && d.district !== districtFilter) return false;
      if (vehicleTypeFilter !== 'ALL' && !d.vehicle_type.includes(vehicleTypeFilter)) return false;
      if (searchPlate.trim()) {
        const query = searchPlate.toLowerCase().replace(/\s+/g, '');
        const plateNorm = d.plate.toLowerCase().replace(/\s+/g, '');
        if (!plateNorm.includes(query) && !d.vehicle_make.toLowerCase().includes(query)) {
          return false;
        }
      }
      return true;
    });
  }, [detections, searchPlate, watchlistOnly, districtFilter, vehicleTypeFilter]);

  const totalHits = detections.filter((d) => d.is_watchlist_hit).length;

  return (
    <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner & Header */}
      <div
        style={{
          background: 'var(--glass-bg)',
          backdropFilter: 'var(--glass-blur)',
          WebkitBackdropFilter: 'var(--glass-blur)',
          border: '1px solid var(--border-medium)',
          borderRadius: 'var(--radius-lg)',
          padding: '18px 24px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          boxShadow: 'var(--card-shadow)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
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
              <Car size={24} />
            </div>
            <div>
              <h1
                style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize: '1.3rem',
                  fontWeight: 900,
                  color: '#fff',
                  letterSpacing: '1.5px',
                  margin: 0,
                }}
              >
                ANPR & VEHICLE INTELLIGENCE VAULT
              </h1>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
                High-speed OCR Plate Recognition, Vahan National Registry Cross-Verification & Real-time Velocity Ingest
              </p>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              color: 'var(--accent-danger)',
              fontFamily: 'var(--font-mono)',
              fontWeight: 800,
              fontSize: '0.85rem',
            }}
          >
            <ShieldAlert size={18} className="animate-pulse" />
            <span>{totalHits} ACTIVE WATCHLIST HITS DETECTED</span>
          </div>
        </div>
      </div>

      {/* DEDICATED HIGH-IMPACT SEARCH & FILTER SECTION */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(13, 21, 39, 0.9), rgba(19, 31, 56, 0.85))',
          border: '1px solid var(--border-medium)',
          borderRadius: 'var(--radius-lg)',
          padding: '20px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          boxShadow: 'var(--card-shadow)',
        }}
      >
        {/* Top Search Input Row */}
        <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ flex: 1, minWidth: '320px', position: 'relative' }}>
            <Search size={20} className="text-cyan" style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="SEARCH VEHICLE PLATE (e.g. 'GJ01AB1234') OR MAKE (e.g. 'Scorpio', 'Hyundai')..."
              value={searchPlate}
              onChange={(e) => setSearchPlate(e.target.value)}
              style={{
                width: '100%',
                padding: '14px 20px 14px 50px',
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-medium)',
                borderRadius: 'var(--radius-md)',
                color: '#fff',
                fontSize: '1rem',
                fontWeight: 700,
                fontFamily: 'var(--font-mono)',
                letterSpacing: '1px',
                outline: 'none',
                boxShadow: 'inset 0 2px 6px rgba(0,0,0,0.5)',
              }}
            />
          </div>

          {/* Watchlist Toggle Button */}
          <button
            onClick={() => setWatchlistOnly(!watchlistOnly)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '14px 22px',
              borderRadius: 'var(--radius-md)',
              border: watchlistOnly ? '1px solid var(--accent-attention)' : '1px solid var(--border-medium)',
              background: watchlistOnly ? 'rgba(234, 179, 8, 0.2)' : 'var(--bg-tertiary)',
              color: watchlistOnly ? 'var(--accent-attention)' : 'var(--text-secondary)',
              fontFamily: 'var(--font-heading)',
              fontSize: '0.88rem',
              fontWeight: 800,
              letterSpacing: '0.5px',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              boxShadow: watchlistOnly ? '0 0 16px rgba(234, 179, 8, 0.3)' : 'none',
            }}
          >
            <Shield size={18} />
            <span>WATCHLIST HITS ONLY ({totalHits})</span>
          </button>

          {/* Search Action Button */}
          <button
            onClick={() => {}}
            className="icon-btn highlight-btn"
            style={{
              padding: '14px 28px',
              height: 'auto',
              width: 'auto',
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-blue))',
              border: 'none',
              color: '#070b14',
              fontFamily: 'var(--font-heading)',
              fontSize: '0.92rem',
              fontWeight: 900,
              letterSpacing: '1px',
              cursor: 'pointer',
              boxShadow: '0 4px 20px var(--accent-cyan-dim)',
            }}
          >
            <Search size={18} />
            <span>SEARCH PLATE</span>
          </button>
        </div>

        {/* Secondary Filter Dropdowns */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-primary)', padding: '8px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <MapPin size={15} className="text-cyan" />
            <span style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>DISTRICT:</span>
            <select
              value={districtFilter}
              onChange={(e) => setDistrictFilter(e.target.value)}
              style={{ background: 'transparent', color: '#fff', border: 'none', outline: 'none', fontSize: '0.85rem', fontFamily: 'var(--font-mono)', fontWeight: 700 }}
            >
              <option value="ALL" style={{ background: '#0a101d' }}>ALL DISTRICTS</option>
              <option value="Ahmedabad" style={{ background: '#0a101d' }}>Ahmedabad</option>
              <option value="Junagadh" style={{ background: '#0a101d' }}>Junagadh</option>
              <option value="Gandhinagar" style={{ background: '#0a101d' }}>Gandhinagar</option>
              <option value="Navsari" style={{ background: '#0a101d' }}>Navsari</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-primary)', padding: '8px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <Car size={15} className="text-purple" />
            <span style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>VEHICLE TYPE:</span>
            <select
              value={vehicleTypeFilter}
              onChange={(e) => setVehicleTypeFilter(e.target.value)}
              style={{ background: 'transparent', color: '#fff', border: 'none', outline: 'none', fontSize: '0.85rem', fontFamily: 'var(--font-mono)', fontWeight: 700 }}
            >
              <option value="ALL" style={{ background: '#0a101d' }}>ALL TYPES</option>
              <option value="CAR" style={{ background: '#0a101d' }}>Cars & Sedans</option>
              <option value="SUV" style={{ background: '#0a101d' }}>SUVs</option>
              <option value="TRUCK" style={{ background: '#0a101d' }}>Commercial Trucks</option>
              <option value="MOTORCYCLE" style={{ background: '#0a101d' }}>Motorcycles</option>
            </select>
          </div>

          <span style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginLeft: 'auto' }}>
            Showing {filteredDetections.length} matched vehicle detections
          </span>
        </div>
      </div>

      {/* SCALED-UP ANPR DETECTIONS TABLE */}
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
          boxShadow: 'var(--card-shadow)',
        }}
      >
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem', fontFamily: 'var(--font-body)' }}>
            <thead>
              <tr style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-medium)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px' }}>
                <th style={{ padding: '16px 20px' }}>License Plate</th>
                <th style={{ padding: '16px 20px' }}>Vehicle Spec</th>
                <th style={{ padding: '16px 20px' }}>OCR Accuracy</th>
                <th style={{ padding: '16px 20px' }}>Camera Node & Junction</th>
                <th style={{ padding: '16px 20px' }}>Speed</th>
                <th style={{ padding: '16px 20px' }}>Timestamp</th>
                <th style={{ padding: '16px 20px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredDetections.map((det) => (
                <tr
                  key={det.id}
                  style={{
                    borderBottom: '1px solid var(--border-subtle)',
                    background: det.is_watchlist_hit ? 'rgba(239, 68, 68, 0.06)' : 'transparent',
                    transition: 'background 0.15s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = det.is_watchlist_hit ? 'rgba(239, 68, 68, 0.12)' : 'var(--bg-card-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = det.is_watchlist_hit ? 'rgba(239, 68, 68, 0.06)' : 'transparent')}
                >
                  {/* Indian RTO Number Plate Badge */}
                  <td style={{ padding: '16px 20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div
                        style={{
                          background: '#fef08a',
                          color: '#000',
                          border: '2px solid #000',
                          borderRadius: '4px',
                          padding: '4px 10px',
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 900,
                          fontSize: '0.95rem',
                          letterSpacing: '1.5px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                        }}
                      >
                        <span style={{ fontSize: '0.65rem', background: '#000', color: '#fff', padding: '1px 3px', borderRadius: '2px', fontWeight: 800 }}>IND</span>
                        <span>{det.plate}</span>
                      </div>

                      {det.is_watchlist_hit && (
                        <span
                          style={{
                            background: 'var(--accent-danger)',
                            color: '#fff',
                            fontSize: '0.65rem',
                            fontFamily: 'var(--font-mono)',
                            fontWeight: 800,
                            padding: '2px 6px',
                            borderRadius: '3px',
                          }}
                        >
                          {det.watchlist_category || 'SUSPECT'}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Vehicle Spec */}
                  <td style={{ padding: '16px 20px' }}>
                    <div style={{ fontWeight: 700, color: '#fff', fontSize: '0.88rem' }}>{det.vehicle_make}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                      {det.vehicle_type} • {det.vehicle_color}
                    </div>
                  </td>

                  {/* OCR Confidence */}
                  <td style={{ padding: '16px 20px' }}>
                    <span
                      style={{
                        color: det.confidence > 95 ? 'var(--accent-healthy)' : 'var(--accent-attention)',
                        fontWeight: 800,
                        fontFamily: 'var(--font-mono)',
                        fontSize: '0.85rem',
                      }}
                    >
                      {det.confidence}%
                    </span>
                  </td>

                  {/* Location & Camera */}
                  <td style={{ padding: '16px 20px' }}>
                    <div style={{ color: '#fff', fontWeight: 600, fontSize: '0.85rem' }}>{det.camera_name}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                      {det.camera_code} • {det.district}
                    </div>
                  </td>

                  {/* Speed */}
                  <td style={{ padding: '16px 20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: det.speed_kmph > 70 ? 'var(--accent-danger)' : 'var(--text-primary)' }}>
                      <Gauge size={14} className={det.speed_kmph > 70 ? 'text-danger' : 'text-cyan'} />
                      <span>{det.speed_kmph} km/h</span>
                    </div>
                  </td>

                  {/* Timestamp */}
                  <td style={{ padding: '16px 20px', fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {det.timestamp}
                  </td>

                  {/* Actions */}
                  <td style={{ padding: '16px 20px', textAlign: 'right' }}>
                    <button
                      onClick={() => setSelectedDetection(det)}
                      className="icon-btn highlight-btn"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '6px 14px',
                        height: 'auto',
                        width: 'auto',
                        borderRadius: 'var(--radius-sm)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '0.75rem',
                        fontWeight: 800,
                        cursor: 'pointer',
                      }}
                    >
                      <Eye size={14} />
                      <span>DOSSIER</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Vehicle Dossier & Trajectory Modal */}
      {selectedDetection && (
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
              maxWidth: '750px',
              padding: '24px',
              boxShadow: 'var(--shadow-3d)',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Car size={22} className="text-cyan" />
                <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.2rem', fontWeight: 900, color: '#fff', margin: 0 }}>
                  VEHICLE FORENSIC DOSSIER // {selectedDetection.plate}
                </h2>
              </div>
              <button onClick={() => setSelectedDetection(null)} className="icon-btn" style={{ width: '32px', height: '32px' }}>
                <X size={16} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div style={{ padding: '14px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>VEHICLE SPECIFICATIONS</div>
                <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#fff', marginTop: '4px' }}>{selectedDetection.vehicle_make}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  Type: <b>{selectedDetection.vehicle_type}</b> • Color: <b>{selectedDetection.vehicle_color}</b>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--accent-healthy)', fontWeight: 700, marginTop: '8px' }}>
                  OCR Precision: {selectedDetection.confidence}% Match
                </div>
              </div>

              <div style={{ padding: '14px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>DETECTION TELEMETRY</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-cyan)', marginTop: '4px' }}>
                  {selectedDetection.camera_name} ({selectedDetection.camera_code})
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  District: <b>{selectedDetection.district}</b> • Speed: <b>{selectedDetection.speed_kmph} km/h</b>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: '8px' }}>
                  Captured: {selectedDetection.timestamp}
                </div>
              </div>
            </div>

            {selectedDetection.is_watchlist_hit && (
              <div style={{ padding: '14px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid var(--accent-danger)', borderRadius: 'var(--radius-md)', color: '#fff' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 800, color: 'var(--accent-danger)' }}>
                  <ShieldAlert size={18} />
                  <span>ALERT: {selectedDetection.watchlist_category} VEHICLE HOTLIST HIT</span>
                </div>
                <div style={{ fontSize: '0.82rem', marginTop: '6px', color: '#fca5a5' }}>
                  {selectedDetection.watchlist_notes}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
              <button onClick={() => setSelectedDetection(null)} className="icon-btn" style={{ padding: '8px 18px', width: 'auto', height: 'auto' }}>
                CLOSE
              </button>
              <button
                onClick={() => alert(`Dispatch alert issued for ${selectedDetection.plate} across ${selectedDetection.district} Patrol Grid.`)}
                className="icon-btn highlight-btn"
                style={{
                  padding: '8px 22px',
                  width: 'auto',
                  height: 'auto',
                  background: 'var(--accent-danger)',
                  color: '#fff',
                  fontWeight: 800,
                  border: 'none',
                }}
              >
                DISPATCH INTERCEPTOR
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
