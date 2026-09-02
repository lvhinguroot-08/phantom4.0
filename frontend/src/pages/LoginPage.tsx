import React, { useState, useEffect, useRef } from 'react';
import {
  Shield,
  Lock,
  User,
  Eye,
  EyeOff,
  Cpu,
  Zap,
  Activity,
  Radio,
  Sparkles,
  KeyRound,
  Fingerprint,
  ChevronRight,
  AlertCircle,
  Camera,
  CheckCircle2,
  Terminal,
} from 'lucide-react';
import phantomEmblem from '../assets/branding/phantom-emblem.png';
import phantomWordmark from '../assets/branding/phantom-wordmark.png';
import {
  playAccessGrantedSound,
  playAccessDeniedSound,
  playHoverBlip,
  playWarpSound,
} from '../utils/audioSynth';

export interface LoginPageProps {
  onLoginSuccess: (userProfile?: any) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState<string>('admin');
  const [password, setPassword] = useState<string>('admin');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [authStep, setAuthStep] = useState<'idle' | 'scanning' | 'granted' | 'unlocked'>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [mousePos, setMousePos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [currentTime, setCurrentTime] = useState<string>('');
  const [terminalLogs, setTerminalLogs] = useState<string[]>([]);

  const containerRef = useRef<HTMLDivElement>(null);

  // Live IST Clock
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(
        now.toLocaleTimeString('en-IN', {
          timeZone: 'Asia/Kolkata',
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        }) + ' IST'
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Parallax 3D mouse tracking (crisp and subtle)
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current || authStep !== 'idle') return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    setMousePos({ x, y });
  };

  const handleLoginSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (isLoading || authStep !== 'idle') return;

    setErrorMessage(null);

    // Validate credentials (Default: admin / admin)
    const cleanUser = username.trim().toLowerCase();
    const cleanPass = password.trim();

    if (!cleanUser || !cleanPass) {
      playAccessDeniedSound();
      setErrorMessage('Please enter both username and security clearance key.');
      return;
    }

    if (cleanUser === 'admin' && cleanPass === 'admin') {
      setIsLoading(true);
      setAuthStep('scanning');
      playAccessGrantedSound();

      // Step 1: Terminal Log Sequence
      setTerminalLogs(['[INIT] INITIATING BIOMETRIC RETINA SCAN...']);

      setTimeout(() => {
        setTerminalLogs((prev) => [
          ...prev,
          '[OK] BIOMETRIC VERIFIED // DNA MATCH: 100%',
          '[AUTH] DECRYPTING POLICE SECURE CHANNELS...',
        ]);
        setAuthStep('granted');
      }, 350);

      setTimeout(() => {
        setTerminalLogs((prev) => [
          ...prev,
          '[GRID] 30 GUJARAT STATEWIDE NODES SYNCED',
          '[READY] ACCESS GRANTED // WELCOME COMMANDER',
        ]);
        setAuthStep('unlocked');
        playWarpSound();
      }, 700);

      // Step 2: Smooth transition into dashboard
      setTimeout(() => {
        onLoginSuccess({
          username: 'admin',
          full_name: 'Cmdr. Rajesh Patel',
          role: 'SYSTEM_ADMIN',
          department: 'Gujarat Police State Command & Control',
          badge_number: 'ADM-001',
          clearance_level: 5,
        });
      }, 1250);
    } else {
      setIsLoading(true);
      setTimeout(() => {
        setIsLoading(false);
        playAccessDeniedSound();
        setErrorMessage('Access Denied: Invalid tactical credentials. Default: admin / admin');
      }, 400);
    }
  };

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      style={{
        position: 'relative',
        width: '100vw',
        height: '100vh',
        overflow: 'hidden',
        background: 'radial-gradient(ellipse at 50% 40%, #0c1224 0%, #060913 55%, #020409 100%)',
        color: '#f8fafc',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'var(--font-body)',
        perspective: '1000px',
      }}
    >
      {/* 1. Tactical Vector Grid Pattern Background */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `
            linear-gradient(to right, rgba(168, 85, 247, 0.06) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(168, 85, 247, 0.06) 1px, transparent 1px)
          `,
          backgroundSize: '48px 48px',
          maskImage: 'radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0) 80%)',
          WebkitMaskImage: 'radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0) 80%)',
          transform: `translate(${mousePos.x * -12}px, ${mousePos.y * -12}px)`,
          transition: 'transform 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
          pointerEvents: 'none',
        }}
      />

      {/* 2. Top Status Banners */}
      <div
        style={{
          position: 'absolute',
          top: '20px',
          left: '24px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          zIndex: 20,
          opacity: authStep === 'unlocked' ? 0 : 1,
          transition: 'opacity 0.4s ease',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(10, 16, 32, 0.9)',
            border: '1px solid rgba(168, 85, 247, 0.3)',
            borderRadius: '6px',
            padding: '6px 14px',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.75rem',
            color: 'var(--accent-purple)',
            boxShadow: '0 0 15px rgba(168, 85, 247, 0.2)',
          }}
        >
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#22c55e', boxShadow: '0 0 10px #22c55e', display: 'inline-block' }} />
          <span>GUJARAT POLICE SENTINEL // ONLINE</span>
        </div>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          SECURE PROTOCOL v4.8
        </span>
      </div>

      <div
        style={{
          position: 'absolute',
          top: '20px',
          right: '24px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          zIndex: 20,
          opacity: authStep === 'unlocked' ? 0 : 1,
          transition: 'opacity 0.4s ease',
        }}
      >
        <div
          style={{
            background: 'rgba(10, 16, 32, 0.9)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '6px',
            padding: '6px 14px',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.78rem',
            color: '#f8fafc',
            letterSpacing: '1px',
          }}
        >
          {currentTime || '00:00:00 IST'}
        </div>
      </div>

      {/* 3. Central Ambient Holographic Aura & Scanner Ring */}
      <div
        style={{
          position: 'absolute',
          width: '520px',
          height: '520px',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          pointerEvents: 'none',
          zIndex: 1,
          transform: authStep === 'unlocked'
            ? 'scale(1.4) rotate(90deg)'
            : `scale(1) rotateX(${mousePos.y * -15}deg) rotateY(${mousePos.x * 15}deg)`,
          transition: 'all 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      >
        {/* Crisp Vector Outer Dash Ring */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '50%',
            border: '2px dashed rgba(168, 85, 247, 0.3)',
            animation: 'spin 22s linear infinite',
            boxShadow: '0 0 40px rgba(168, 85, 247, 0.12)',
          }}
        />

        {/* Dual Color Inner Reticle */}
        <div
          style={{
            position: 'absolute',
            inset: '35px',
            borderRadius: '50%',
            border: '1.5px solid rgba(56, 189, 248, 0.25)',
            borderTopColor: '#a855f7',
            borderBottomColor: '#38bdf8',
            animation: 'spin 14s linear infinite reverse',
          }}
        />

        {/* Glowing Central Radial Energy Dome */}
        <div
          style={{
            position: 'absolute',
            inset: '80px',
            borderRadius: '50%',
            background: authStep === 'granted' || authStep === 'unlocked'
              ? 'radial-gradient(circle, rgba(34, 197, 94, 0.25) 0%, rgba(10, 16, 32, 0) 70%)'
              : 'radial-gradient(circle, rgba(168, 85, 247, 0.18) 0%, rgba(10, 16, 32, 0) 70%)',
            transition: 'background 0.3s ease',
          }}
        />
      </div>

      {/* 4. Laser Scan Line Sweep (Activates during login) */}
      {(authStep === 'scanning' || authStep === 'granted') && (
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            height: '3px',
            background: 'linear-gradient(90deg, transparent, #38bdf8, #a855f7, transparent)',
            boxShadow: '0 0 20px #38bdf8, 0 0 40px #a855f7',
            zIndex: 30,
            animation: 'laserScan 0.7s ease-in-out infinite alternate',
            pointerEvents: 'none',
          }}
        />
      )}

      {/* 5. Main Card Interface */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          maxWidth: '460px',
          background: 'rgba(10, 16, 32, 0.88)',
          backdropFilter: 'blur(24px) saturate(180%)',
          WebkitBackdropFilter: 'blur(24px) saturate(180%)',
          border: authStep === 'granted' || authStep === 'unlocked'
            ? '1px solid rgba(34, 197, 94, 0.5)'
            : '1px solid rgba(168, 85, 247, 0.3)',
          borderRadius: '16px',
          padding: '36px 32px',
          boxShadow: authStep === 'granted' || authStep === 'unlocked'
            ? '0 25px 70px rgba(0, 0, 0, 0.85), 0 0 40px rgba(34, 197, 94, 0.3)'
            : '0 25px 70px rgba(0, 0, 0, 0.85), 0 0 35px rgba(168, 85, 247, 0.25)',
          zIndex: 20,
          transform: authStep === 'unlocked'
            ? 'scale(0.96) translateY(30px)'
            : `rotateX(${mousePos.y * 8}deg) rotateY(${mousePos.x * -8}deg)`,
          opacity: authStep === 'unlocked' ? 0 : 1,
          transition: 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.35s ease, border-color 0.3s ease, box-shadow 0.3s ease',
        }}
      >
        {/* Holographic Header Bar & Emblem */}
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              position: 'relative',
              marginBottom: '14px',
            }}
          >
            {/* Pulsing Iris Glow Ring */}
            <div
              style={{
                position: 'absolute',
                width: '84px',
                height: '84px',
                borderRadius: '50%',
                background: authStep === 'granted' || authStep === 'unlocked'
                  ? 'radial-gradient(circle, rgba(34, 197, 94, 0.4) 0%, transparent 70%)'
                  : 'radial-gradient(circle, rgba(168, 85, 247, 0.35) 0%, transparent 70%)',
                boxShadow: authStep === 'granted' || authStep === 'unlocked'
                  ? '0 0 25px rgba(34, 197, 94, 0.6)'
                  : '0 0 25px rgba(168, 85, 247, 0.5)',
                animation: 'pulse 2.5s infinite ease-in-out',
              }}
            />

            <img
              src={phantomEmblem}
              alt="PHANTOM Emblem"
              style={{
                width: '68px',
                height: '68px',
                objectFit: 'contain',
                zIndex: 2,
                filter: authStep === 'granted' || authStep === 'unlocked'
                  ? 'drop-shadow(0 0 15px rgba(34, 197, 94, 0.9))'
                  : 'drop-shadow(0 0 15px rgba(168, 85, 247, 0.8))',
                transition: 'filter 0.3s ease',
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '8px' }}>
            <img
              src={phantomWordmark}
              alt="PHANTOM 2.0"
              style={{
                height: '34px',
                objectFit: 'contain',
                filter: 'drop-shadow(0 0 12px rgba(168, 85, 247, 0.6))',
              }}
            />
          </div>

          <h2
            style={{
              margin: 0,
              fontSize: '0.96rem',
              fontWeight: 900,
              fontFamily: 'var(--font-heading)',
              letterSpacing: '2px',
              color: '#ffffff',
            }}
          >
            COMMAND ACCESS PORTAL
          </h2>
          <p
            style={{
              margin: '4px 0 0',
              fontSize: '0.78rem',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-tactical)',
              letterSpacing: '0.5px',
            }}
          >
            GUJARAT POLICE STATEWIDE CCTV & ANPR NETWORK
          </p>
        </div>

        {/* Live Terminal Decryption Box (When logging in) */}
        {authStep !== 'idle' ? (
          <div
            style={{
              padding: '16px',
              background: 'rgba(5, 9, 18, 0.95)',
              border: '1px solid rgba(34, 197, 94, 0.4)',
              borderRadius: '8px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              minHeight: '140px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.75rem',
              color: '#22c55e',
              boxShadow: 'inset 0 0 15px rgba(34, 197, 94, 0.1)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(34, 197, 94, 0.2)', paddingBottom: '6px' }}>
              <Terminal size={14} />
              <strong style={{ letterSpacing: '1px' }}>SENTINEL AUTHENTICATION ENGINE</strong>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '4px' }}>
              {terminalLogs.map((log, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ color: '#38bdf8' }}>&gt;</span>
                  <span>{log}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          /* Form Fields */
          <form onSubmit={handleLoginSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Username Input */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label
                style={{
                  fontSize: '0.74rem',
                  fontWeight: 700,
                  fontFamily: 'var(--font-tactical)',
                  letterSpacing: '0.8px',
                  color: 'var(--text-secondary)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <User size={13} style={{ color: 'var(--accent-purple)' }} />
                <span>OFFICER / COMMANDER ID</span>
              </label>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  background: 'rgba(7, 12, 24, 0.95)',
                  border: '1px solid rgba(168, 85, 247, 0.35)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  gap: '10px',
                  boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.5)',
                }}
              >
                <Shield size={16} style={{ color: 'var(--accent-purple)' }} />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter commander ID (admin)"
                  autoComplete="username"
                  disabled={isLoading}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#ffffff',
                    fontSize: '0.88rem',
                    fontFamily: 'var(--font-mono)',
                    outline: 'none',
                    flex: 1,
                  }}
                />
              </div>
            </div>

            {/* Password Input */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label
                style={{
                  fontSize: '0.74rem',
                  fontWeight: 700,
                  fontFamily: 'var(--font-tactical)',
                  letterSpacing: '0.8px',
                  color: 'var(--text-secondary)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <KeyRound size={13} style={{ color: 'var(--accent-purple)' }} />
                <span>CLEARANCE PASSCODE</span>
              </label>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  background: 'rgba(7, 12, 24, 0.95)',
                  border: '1px solid rgba(168, 85, 247, 0.35)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  gap: '10px',
                  boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.5)',
                }}
              >
                <Lock size={16} style={{ color: 'var(--accent-purple)' }} />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter passcode (admin)"
                  autoComplete="current-password"
                  disabled={isLoading}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#ffffff',
                    fontSize: '0.88rem',
                    fontFamily: 'var(--font-mono)',
                    outline: 'none',
                    flex: 1,
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    padding: 0,
                  }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Error Banner */}
            {errorMessage && (
              <div
                style={{
                  padding: '8px 12px',
                  borderRadius: '6px',
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.4)',
                  color: '#fca5a5',
                  fontSize: '0.78rem',
                  fontFamily: 'var(--font-mono)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <AlertCircle size={15} />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Quick Demo Credentials Pill */}
            <div
              onClick={() => {
                setUsername('admin');
                setPassword('admin');
                playHoverBlip();
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                background: 'rgba(168, 85, 247, 0.08)',
                border: '1px dashed rgba(168, 85, 247, 0.3)',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '0.72rem',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                transition: 'background 0.2s',
              }}
            >
              <span>DEFAULT CLEARANCE:</span>
              <strong style={{ color: 'var(--accent-purple)', fontFamily: 'var(--font-mono)' }}>
                admin / admin (Click to fill)
              </strong>
            </div>

            {/* High-Impact Action Button */}
            <button
              type="submit"
              disabled={isLoading}
              onMouseEnter={playHoverBlip}
              style={{
                marginTop: '8px',
                padding: '14px 24px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #a855f7 0%, #7c3aed 100%)',
                border: 'none',
                color: '#ffffff',
                fontSize: '0.88rem',
                fontWeight: 900,
                fontFamily: 'var(--font-tactical)',
                letterSpacing: '1.5px',
                cursor: isLoading ? 'default' : 'pointer',
                boxShadow: '0 0 25px rgba(168, 85, 247, 0.45)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '10px',
                transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
              }}
            >
              <Fingerprint size={18} />
              <span>AUTHENTICATE & ACCESS COMMAND CENTER</span>
              <ChevronRight size={18} />
            </button>
          </form>
        )}

        {/* Footer Security Badge */}
        <div
          style={{
            marginTop: '20px',
            paddingTop: '16px',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.68rem',
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Cpu size={12} style={{ color: 'var(--accent-purple)' }} />
            <span>CLEARANCE: LEVEL 5</span>
          </div>
          <div style={{ color: '#22c55e', fontWeight: 800 }}>
            ENCRYPTED TLS 1.3
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 0.8; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.12); }
        }
        @keyframes laserScan {
          0% { top: 15%; opacity: 0.3; }
          50% { opacity: 1; }
          100% { top: 85%; opacity: 0.3; }
        }
      `}</style>
    </div>
  );
};
