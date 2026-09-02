import React, { useState } from 'react';
import {
  FolderSearch,
  Search,
  Car,
  MapPin,
  Clock,
  Shield,
  ShieldAlert,
  ArrowRight,
  FileText,
  Download,
  CheckCircle2,
  Cpu,
  Sparkles,
  Zap,
} from 'lucide-react';

interface CaseTrajectory {
  time: string;
  camera: string;
  district: string;
  speed: string;
  confidence: string;
}

export const InvestigationsPage: React.FC = () => {
  const [query, setQuery] = useState<string>('');
  const [isInvestigating, setIsInvestigating] = useState<boolean>(false);
  const [activeCase, setActiveCase] = useState<any>({
    caseId: 'CASE-GJ-2026-089',
    suspectPlate: 'GJ 01 AB 1234',
    suspectVehicle: 'Silver Hyundai i20 (2023 Model)',
    investigator: 'Inspector R. K. Jadeja (Crime Branch AHM)',
    incidentType: 'Armed Robbery & High-Speed Highway Escape',
    status: 'ACTIVE PURSUIT',
    aiConfidence: 96.8,
    trajectories: [
      { time: '14:02:15', camera: '01 Chiman bhai Bridge (CAM01)', district: 'Ahmedabad', speed: '58 km/h', confidence: '98.2%' },
      { time: '14:09:40', camera: '04 Paldi Circle (CAM04)', district: 'Ahmedabad', speed: '64 km/h', confidence: '96.5%' },
      { time: '14:18:22', camera: '02 Janpath Crossroads (CAM02)', district: 'Ahmedabad', speed: '48 km/h', confidence: '97.1%' },
      { time: '14:27:05', camera: '05 Visat teen Rasta (CAM05)', district: 'Ahmedabad', speed: '52 km/h', confidence: '95.4%' },
    ],
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsInvestigating(true);
    setTimeout(() => {
      setIsInvestigating(false);
    }, 600);
  };

  const quickPresets = [
    'Locate black Scorpio GJ-05-CD-5678 last seen near Paldi Circle',
    'Track Silver Hyundai i20 GJ-01-AB-1234 on Chiman bhai Bridge',
    'Find Tata 407 Truck near Junagadh Timbavadi Gate',
  ];

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
            <FolderSearch size={24} />
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
              FORENSIC CASE INVESTIGATION & TIMELINE
            </h1>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
              Multi-Camera Geospatial Trajectory Reconstruction, Chronological Vehicle Timeline & Evidence Compilation
            </p>
          </div>
        </div>

        <button
          onClick={() => alert('Exporting Official Forensic Case PDF Report with Cryptographic Signatures...')}
          className="icon-btn highlight-btn"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 22px',
            height: 'auto',
            width: 'auto',
            borderRadius: 'var(--radius-md)',
            background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-blue))',
            border: 'none',
            color: '#070b14',
            fontFamily: 'var(--font-heading)',
            fontSize: '0.88rem',
            fontWeight: 900,
            cursor: 'pointer',
          }}
        >
          <Download size={17} />
          <span>EXPORT CASE DOSSIER</span>
        </button>
      </div>

      {/* Prominent Investigation Search Bar */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(13, 21, 39, 0.9), rgba(19, 31, 56, 0.85))',
          border: '1px solid var(--border-medium)',
          borderRadius: 'var(--radius-lg)',
          padding: '20px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
          boxShadow: 'var(--card-shadow)',
        }}
      >
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '12px' }}>
          <input
            type="text"
            placeholder="Enter natural language case query or vehicle plate (e.g. 'Track red Swift near Ahmedabad toll')..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{
              flex: 1,
              padding: '14px 20px',
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-medium)',
              borderRadius: 'var(--radius-md)',
              color: '#fff',
              fontSize: '1rem',
              outline: 'none',
              fontFamily: 'var(--font-body)',
            }}
          />

          <button
            type="submit"
            disabled={isInvestigating}
            className="icon-btn highlight-btn"
            style={{
              padding: '14px 26px',
              height: 'auto',
              width: 'auto',
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-blue))',
              border: 'none',
              color: '#070b14',
              fontFamily: 'var(--font-heading)',
              fontSize: '0.9rem',
              fontWeight: 900,
              cursor: 'pointer',
            }}
          >
            <Search size={18} />
            <span>{isInvestigating ? 'ANALYZING...' : 'RECONSTRUCT'}</span>
          </button>
        </form>

        {/* Quick Presets */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>PRESETS:</span>
          {quickPresets.map((preset, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQuery(preset);
              }}
              style={{
                padding: '6px 12px',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--accent-cyan)',
                fontSize: '0.78rem',
                cursor: 'pointer',
              }}
            >
              {preset}
            </button>
          ))}
        </div>
      </div>

      {/* Main Case Dossier Split View */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '20px' }}>
        {/* Left: Case Summary Card */}
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-lg)',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            boxShadow: 'var(--card-shadow)',
          }}
        >
          <div style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
            <span
              style={{
                fontSize: '0.72rem',
                fontFamily: 'var(--font-mono)',
                fontWeight: 800,
                color: 'var(--accent-cyan)',
                background: 'var(--accent-cyan-dim)',
                padding: '3px 8px',
                borderRadius: '3px',
              }}
            >
              {activeCase.caseId}
            </span>
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.2rem', fontWeight: 900, color: '#fff', margin: '8px 0 0 0' }}>
              {activeCase.suspectPlate}
            </h2>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              {activeCase.suspectVehicle}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.82rem' }}>
            <div>
              <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>INCIDENT TYPE:</span>
              <div style={{ color: '#fff', fontWeight: 700, marginTop: '2px' }}>{activeCase.incidentType}</div>
            </div>

            <div>
              <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>LEAD INVESTIGATOR:</span>
              <div style={{ color: 'var(--text-primary)', marginTop: '2px' }}>{activeCase.investigator}</div>
            </div>

            <div>
              <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>AI MATCH CONFIDENCE:</span>
              <div style={{ color: 'var(--accent-healthy)', fontWeight: 800, fontSize: '1.1rem', marginTop: '2px' }}>
                {activeCase.aiConfidence}% HIGH ACCURACY
              </div>
            </div>
          </div>

          <div style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid var(--border-subtle)' }}>
            <button
              onClick={() => alert(`Patrol Interceptor dispatched to intercept ${activeCase.suspectPlate}`)}
              className="icon-btn highlight-btn"
              style={{
                width: '100%',
                padding: '12px',
                height: 'auto',
                borderRadius: 'var(--radius-md)',
                background: 'var(--accent-danger)',
                color: '#fff',
                fontFamily: 'var(--font-heading)',
                fontSize: '0.88rem',
                fontWeight: 900,
                border: 'none',
                justifyContent: 'center',
                gap: '8px',
                cursor: 'pointer',
              }}
            >
              <Zap size={16} />
              <span>DISPATCH PATROL INTERCEPTOR</span>
            </button>
          </div>
        </div>

        {/* Right: Chronological CCTV Trajectory Waypoints Timeline */}
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            boxShadow: 'var(--card-shadow)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
            <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.1rem', fontWeight: 900, color: '#fff', margin: 0 }}>
              RECONSTRUCTED VEHICLE TRAJECTORY TIMELINE
            </h3>
            <span className="badge-live" style={{ fontSize: '0.72rem', padding: '3px 8px', borderRadius: '3px' }}>
              4 SIGHTINGS CORRELATED
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {activeCase.trajectories.map((traj: CaseTrajectory, idx: number) => (
              <div
                key={idx}
                style={{
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '16px 20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '14px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '50%',
                      background: 'rgba(0, 240, 255, 0.15)',
                      border: '1px solid var(--accent-cyan)',
                      color: 'var(--accent-cyan)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 800,
                      fontSize: '0.85rem',
                    }}
                  >
                    #{idx + 1}
                  </div>

                  <div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#fff' }}>{traj.camera}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                      District: {traj.district} • Speed: <b style={{ color: 'var(--text-primary)' }}>{traj.speed}</b>
                    </div>
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.88rem', fontFamily: 'var(--font-mono)', fontWeight: 800, color: 'var(--accent-cyan)' }}>
                    {traj.time}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--accent-healthy)', fontWeight: 700, marginTop: '2px' }}>
                    {traj.confidence} Match
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
