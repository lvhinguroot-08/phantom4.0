import React, { useState } from 'react';
import {
  Settings as SettingsIcon,
  Sliders,
  Tv,
  Volume2,
  VolumeX,
  Shield,
  CheckCircle2,
  Save,
  Cpu,
  RefreshCw,
  Bell,
  Sparkles,
  Lock,
  Radio,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  // AI Parameters
  const [yoloConfidence, setYoloConfidence] = useState<number>(85);
  const [anprConfidence, setAnprConfidence] = useState<number>(90);
  const [maxBoxes, setMaxBoxes] = useState<number>(50);

  // Streaming Parameters
  const [streamProfile, setStreamProfile] = useState<'1080P' | '720P' | 'LOW'>('1080P');
  const [hlsBufferSeconds, setHlsBufferSeconds] = useState<number>(2);

  // Audio & Dispatch Protocols
  const [audioSiren, setAudioSiren] = useState<boolean>(true);
  const [autoDispatch, setAutoDispatch] = useState<boolean>(true);
  const [nightInfrared, setNightInfrared] = useState<boolean>(true);

  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedSuccess(true);
    setTimeout(() => {
      setSavedSuccess(false);
    }, 2500);
  };

  return (
    <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '1400px', margin: '0 auto' }}>
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
            <SettingsIcon size={24} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="clearance-dot" style={{ background: 'var(--accent-healthy)' }} />
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
                C2 COMMAND SYSTEM CONFIGURATION & PROTOCOLS
              </h1>
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
              Fine-tune YOLO-26 neural inference, video transcoding profiles, audible alert sirens, and dispatch triggers
            </p>
          </div>
        </div>

        <button
          onClick={handleSave}
          className="icon-btn highlight-btn"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 24px',
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
            boxShadow: '0 4px 18px var(--accent-cyan-dim)',
          }}
        >
          <Save size={18} />
          <span>SAVE & APPLY CONFIGURATION</span>
        </button>
      </div>

      {savedSuccess && (
        <div
          style={{
            padding: '16px 20px',
            background: 'rgba(34, 197, 94, 0.15)',
            border: '1px solid var(--accent-healthy)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--accent-healthy)',
            fontFamily: 'var(--font-heading)',
            fontSize: '0.88rem',
            fontWeight: 800,
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <CheckCircle2 size={20} />
          <span>SYSTEM CONFIGURATION SAVED & DEPLOYED ACROSS 30 CCTV STREAM PIPELINES!</span>
        </div>
      )}

      {/* Main Settings Sections Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px' }}>
        {/* Section 1: AI Neural Inference & Detection Sliders */}
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-lg)',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
            boxShadow: 'var(--card-shadow)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
            <Cpu size={22} className="text-cyan" />
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.1rem', fontWeight: 900, color: '#fff', margin: 0 }}>
              AI NEURAL INFERENCE THRESHOLDS
            </h2>
          </div>

          {/* YOLO Slider */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff' }}>YOLO-26 Object Detection Confidence</label>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '0.95rem', color: 'var(--accent-cyan)' }}>
                {yoloConfidence}%
              </span>
            </div>
            <input
              type="range"
              min={50}
              max={99}
              value={yoloConfidence}
              onChange={(e) => setYoloConfidence(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--accent-cyan)', cursor: 'pointer', height: '6px' }}
            />
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Higher values reduce false positives in dense traffic and night surveillance.
            </span>
          </div>

          {/* ANPR OCR Slider */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff' }}>ANPR License Plate OCR Accuracy</label>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '0.95rem', color: 'var(--accent-healthy)' }}>
                {anprConfidence}%
              </span>
            </div>
            <input
              type="range"
              min={60}
              max={99}
              value={anprConfidence}
              onChange={(e) => setAnprConfidence(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--accent-healthy)', cursor: 'pointer', height: '6px' }}
            />
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Strictness threshold before triggering a hotlist alert against the Vahan RTO database.
            </span>
          </div>

          {/* Max Bounding Boxes */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff' }}>Max Simultaneous Object Tracks / Frame</label>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '0.95rem', color: '#c084fc' }}>
                {maxBoxes} Objects
              </span>
            </div>
            <input
              type="range"
              min={10}
              max={120}
              value={maxBoxes}
              onChange={(e) => setMaxBoxes(Number(e.target.value))}
              style={{ width: '100%', accentColor: '#c084fc', cursor: 'pointer', height: '6px' }}
            />
          </div>
        </div>

        {/* Section 2: Video Streaming Profiles */}
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-lg)',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
            boxShadow: 'var(--card-shadow)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
            <Tv size={22} className="text-cyan" />
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.1rem', fontWeight: 900, color: '#fff', margin: 0 }}>
              VIDEO RESOLUTION & STREAM BUFFER
            </h2>
          </div>

          {/* Stream Profile Cards */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <label style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff' }}>Select Default Stream Profile:</label>

            {[
              { id: '1080P', title: '1080p FHD (High Precision)', sub: '1920x1080 @ 25 FPS • Full Quality for HQ Control Room Wall' },
              { id: '720P', title: '720p HD (Balanced)', sub: '1280x720 @ 25 FPS • Recommended for 30-Camera Grid Multi-View' },
              { id: 'LOW', title: 'Low Bandwidth Mode', sub: '640x360 @ 15 FPS • Optimized for Mobile / Satellite Patrol' },
            ].map((prof) => {
              const isSelected = streamProfile === prof.id;
              return (
                <div
                  key={prof.id}
                  onClick={() => setStreamProfile(prof.id as any)}
                  style={{
                    padding: '14px 18px',
                    borderRadius: 'var(--radius-md)',
                    background: isSelected ? 'var(--accent-cyan-dim)' : 'var(--bg-tertiary)',
                    border: isSelected ? '1px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 800, fontSize: '0.88rem', color: isSelected ? 'var(--accent-cyan)' : '#fff' }}>
                      {prof.title}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      {prof.sub}
                    </div>
                  </div>

                  <span
                    style={{
                      width: '16px',
                      height: '16px',
                      borderRadius: '50%',
                      border: isSelected ? '5px solid var(--accent-cyan)' : '2px solid var(--text-muted)',
                      background: isSelected ? '#070b14' : 'transparent',
                    }}
                  />
                </div>
              );
            })}
          </div>

          {/* Buffer Length Slider */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff' }}>HLS Live Ingest Buffer</label>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '0.95rem', color: 'var(--accent-cyan)' }}>
                {hlsBufferSeconds} Seconds (Ultra-Low Latency)
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={10}
              value={hlsBufferSeconds}
              onChange={(e) => setHlsBufferSeconds(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--accent-cyan)', cursor: 'pointer', height: '6px' }}
            />
          </div>
        </div>

        {/* Section 3: Audio Siren & Dispatch Protocols */}
        <div
          style={{
            gridColumn: 'span 2',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-lg)',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
            boxShadow: 'var(--card-shadow)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
            <Bell size={22} className="text-danger" />
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.1rem', fontWeight: 900, color: '#fff', margin: 0 }}>
              LAW ENFORCEMENT AUDIBLE SIRENS & DISPATCH PROTOCOLS
            </h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
            {/* Toggle 1: Audio Siren */}
            <div
              onClick={() => setAudioSiren(!audioSiren)}
              style={{
                padding: '16px 20px',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
              }}
            >
              <div>
                <div style={{ fontWeight: 800, fontSize: '0.88rem', color: '#fff' }}>Tactical Audio Siren</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>Play 880Hz alert on CRITICAL hits</div>
              </div>

              {/* Big Glowing Toggle Switch */}
              <div
                style={{
                  width: '50px',
                  height: '26px',
                  borderRadius: '13px',
                  background: audioSiren ? 'var(--accent-cyan)' : 'rgba(255,255,255,0.1)',
                  position: 'relative',
                  transition: 'background 0.2s ease',
                }}
              >
                <div
                  style={{
                    width: '20px',
                    height: '20px',
                    borderRadius: '50%',
                    background: audioSiren ? '#070b14' : '#64748b',
                    position: 'absolute',
                    top: '3px',
                    left: audioSiren ? '27px' : '3px',
                    transition: 'left 0.2s ease',
                  }}
                />
              </div>
            </div>

            {/* Toggle 2: Auto Dispatch */}
            <div
              onClick={() => setAutoDispatch(!autoDispatch)}
              style={{
                padding: '16px 20px',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
              }}
            >
              <div>
                <div style={{ fontWeight: 800, fontSize: '0.88rem', color: '#fff' }}>Automated Interceptor Alert</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>Broadcast to nearby Highway Patrol</div>
              </div>

              <div
                style={{
                  width: '50px',
                  height: '26px',
                  borderRadius: '13px',
                  background: autoDispatch ? 'var(--accent-healthy)' : 'rgba(255,255,255,0.1)',
                  position: 'relative',
                  transition: 'background 0.2s ease',
                }}
              >
                <div
                  style={{
                    width: '20px',
                    height: '20px',
                    borderRadius: '50%',
                    background: autoDispatch ? '#070b14' : '#64748b',
                    position: 'absolute',
                    top: '3px',
                    left: autoDispatch ? '27px' : '3px',
                    transition: 'left 0.2s ease',
                  }}
                />
              </div>
            </div>

            {/* Toggle 3: Night Vision */}
            <div
              onClick={() => setNightInfrared(!nightInfrared)}
              style={{
                padding: '16px 20px',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
              }}
            >
              <div>
                <div style={{ fontWeight: 800, fontSize: '0.88rem', color: '#fff' }}>Night Infrared Enhancement</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>Auto histogram equalization in low light</div>
              </div>

              <div
                style={{
                  width: '50px',
                  height: '26px',
                  borderRadius: '13px',
                  background: nightInfrared ? '#c084fc' : 'rgba(255,255,255,0.1)',
                  position: 'relative',
                  transition: 'background 0.2s ease',
                }}
              >
                <div
                  style={{
                    width: '20px',
                    height: '20px',
                    borderRadius: '50%',
                    background: nightInfrared ? '#070b14' : '#64748b',
                    position: 'absolute',
                    top: '3px',
                    left: nightInfrared ? '27px' : '3px',
                    transition: 'left 0.2s ease',
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
