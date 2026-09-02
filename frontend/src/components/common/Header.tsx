import React, { useState, useEffect, useRef } from 'react';
import {
  Search,
  Bell,
  LogOut,
  Shield,
  Clock,
  Volume2,
  VolumeX,
  Sun,
  Moon,
  Menu,
  X,
  Cpu,
  Radio,
  ChevronDown,
  Settings as SettingsIcon,
  Activity,
  Bot,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useRealtimeEvents } from '../../context/RealtimeEventContext';
import { useTheme } from '../../context/ThemeContext';
import { NotificationCenter } from './NotificationCenter';
import { ForensicAIModal } from './ForensicAIModal';
import { GlobalSearchModal } from './GlobalSearchModal';
import { Logo } from './Logo';
import { NavView } from './Sidebar';
import { Camera } from '../../types';

interface HeaderProps {
  onSearch?: (query: string) => void;
  onNavigate?: (view: NavView) => void;
  onSelectCamera?: (camera: Camera) => void;
  activeAlertCount?: number;
  isMobileMenuOpen?: boolean;
  onToggleMobileMenu?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onNavigate = () => {},
  onSelectCamera,
  activeAlertCount = 0,
  isMobileMenuOpen = false,
  onToggleMobileMenu,
}) => {
  const { theme, toggleTheme } = useTheme();
  const { unreadCount, isSoundEnabled, toggleSound } = useRealtimeEvents();
  const { user, operationalMode, logout } = useAuth();
  const [utcTime, setUtcTime] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isNotifOpen, setIsNotifOpen] = useState<boolean>(false);
  const [isForensicModalOpen, setIsForensicModalOpen] = useState<boolean>(false);
  const [isSearchModalOpen, setIsSearchModalOpen] = useState<boolean>(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState<boolean>(false);
  const profileDropdownRef = useRef<HTMLDivElement>(null);

  // UTC Precision Clock
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().replace('GMT', 'UTC'));
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  // Global Ctrl+K / Cmd+K listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsSearchModalOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Click outside to close profile dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        profileDropdownRef.current &&
        !profileDropdownRef.current.contains(event.target as Node)
      ) {
        setIsProfileDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <>
      <header className="top-command-bar" role="banner">
        {/* Left: Hamburger (Mobile) + Custom PHANTOM Brand Logo */}
        <div className="brand-section">
          {onToggleMobileMenu && (
            <button
              onClick={onToggleMobileMenu}
              className="mobile-nav-toggle-btn icon-btn"
              aria-label={isMobileMenuOpen ? 'Close Navigation Menu' : 'Open Navigation Menu'}
              title="Toggle Menu"
            >
              {isMobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          )}

          <div
            className="logo-badge cursor-pointer"
            onClick={() => onNavigate('dashboard')}
            title="Return to Dashboard"
            style={{ cursor: 'pointer' }}
          >
            <Logo size="md" />
          </div>

          <div className="op-mode-tag hide-on-mobile">
            <Shield size={12} style={{ color: 'var(--accent-purple)' }} />
            <span className="mode-label">MODE:</span>
            <span className="mode-val">{operationalMode}</span>
          </div>
        </div>

        {/* Center: UTC Clock & Live 30 Feeds Indicator */}
        <div className="telemetry-section hide-on-tablet">
          <div className="clock-badge" title="Coordinated Universal Time">
            <Clock size={13} style={{ color: 'var(--accent-purple)' }} />
            <span className="clock-text">{utcTime || 'UTC SYNCHRONIZING...'}</span>
          </div>

          <div className="status-pill status-online" title="All 30 Sentinel Feeds Transmitting">
            <Radio size={13} className="animate-pulse" style={{ color: 'var(--accent-healthy)' }} />
            <div className="pill-meta">
              <span className="pill-title">30/30 CCTV FEEDS</span>
              <span className="pill-sub">STATEWIDE GRID LIVE</span>
            </div>
          </div>
        </div>

        {/* Right: Search, Forensic AI, Sound, Notifications, Theme, User Profile */}
        <div className="actions-section">
          {/* Global Search Input Box */}
          <div
            onClick={() => setIsSearchModalOpen(true)}
            className="global-search-box hide-on-mobile"
            style={{ cursor: 'pointer' }}
            title="Open Global Surveillance Search (Ctrl+K)"
          >
            <Search size={14} className="search-icon" />
            <input
              type="text"
              readOnly
              placeholder="Search cameras, plates, incidents..."
              value={searchQuery}
              style={{ cursor: 'pointer' }}
            />
            <kbd className="search-kbd">Ctrl+K</kbd>
          </div>

          {/* Forensic AI Inspector Button */}
          <button
            onClick={() => setIsForensicModalOpen(true)}
            className="icon-btn highlight-btn"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'var(--accent-purple-dim)',
              border: '1px solid var(--border-medium)',
              color: 'var(--accent-purple)',
              padding: '6px 12px',
              borderRadius: 'var(--radius-sm)',
              fontWeight: 800,
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              cursor: 'pointer',
              width: 'auto',
            }}
            title="Open YOLO26 Forensic AI Inspector"
          >
            <Cpu size={14} className="animate-pulse" style={{ color: 'var(--accent-purple)' }} />
            <span className="hide-on-mobile">FORENSIC AI</span>
          </button>

          {/* Tactical Sound Toggle */}
          <button
            onClick={toggleSound}
            className={`icon-btn hide-on-mobile ${isSoundEnabled ? 'text-purple' : 'text-muted'}`}
            title={isSoundEnabled ? 'Sound Notifications ON' : 'Sound Notifications MUTED'}
            aria-label="Toggle Sound Notifications"
            style={{ color: isSoundEnabled ? 'var(--accent-purple)' : 'var(--text-muted)' }}
          >
            {isSoundEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
          </button>

          {/* Theme Switcher */}
          <button
            onClick={toggleTheme}
            className="icon-btn theme-toggle-btn"
            title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            aria-label="Toggle Theme Mode"
          >
            {theme === 'dark' ? (
              <Sun size={16} style={{ color: 'var(--accent-attention)' }} />
            ) : (
              <Moon size={16} style={{ color: 'var(--accent-purple)' }} />
            )}
          </button>

          {/* Notification Center Trigger */}
          <button
            onClick={() => setIsNotifOpen(true)}
            className="icon-btn relative"
            title="Threat Notification Center"
            aria-label="Notification Center"
          >
            <Bell size={16} />
            {(unreadCount > 0 || activeAlertCount > 0) && (
              <span className="alert-count-bubble animate-pulse">
                {unreadCount > 0 ? unreadCount : activeAlertCount}
              </span>
            )}
          </button>

          {/* Admin User Profile & Dropdown Menu */}
          <div className="relative" ref={profileDropdownRef} style={{ position: 'relative' }}>
            <div
              className="user-profile-badge"
              onClick={() => setIsProfileDropdownOpen((prev) => !prev)}
              style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
              title="Operator Identity & Menu"
            >
              <div
                className="user-avatar"
                style={{
                  background: 'linear-gradient(135deg, var(--accent-purple), var(--accent-blue))',
                  boxShadow: '0 0 10px var(--phantom-purple-dim)',
                  color: '#fff',
                }}
              >
                {user.full_name.substring(0, 2).toUpperCase()}
              </div>
              <div className="user-meta hide-on-mobile">
                <span className="user-name">{user.full_name}</span>
                <span className="user-role" style={{ color: 'var(--accent-purple)' }}>{user.role}</span>
              </div>
              <ChevronDown
                size={14}
                style={{
                  color: 'var(--text-muted)',
                  transform: isProfileDropdownOpen ? 'rotate(180deg)' : 'none',
                  transition: 'transform 0.2s ease',
                }}
              />
            </div>

            {/* Profile Dropdown Menu */}
            {isProfileDropdownOpen && (
              <div
                style={{
                  position: 'absolute',
                  right: 0,
                  top: '110%',
                  width: '260px',
                  background: 'var(--glass-bg)',
                  backdropFilter: 'var(--glass-blur)',
                  WebkitBackdropFilter: 'var(--glass-blur)',
                  border: '1px solid var(--border-medium)',
                  borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-3d)',
                  padding: '12px',
                  zIndex: 100,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                {/* User Identity Details */}
                <div
                  style={{
                    padding: '8px 10px',
                    background: 'var(--bg-tertiary)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                    {user.full_name}
                  </div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {user.department} • {user.badge_number}
                  </div>
                  <div
                    style={{
                      fontSize: '0.65rem',
                      color: 'var(--accent-purple)',
                      fontWeight: 800,
                      marginTop: '4px',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    ROLE: {user.role}
                  </div>
                </div>

                {/* Dropdown Navigation Actions */}
                <button
                  onClick={() => {
                    onNavigate('settings');
                    setIsProfileDropdownOpen(false);
                  }}
                  className="icon-btn"
                  style={{
                    width: '100%',
                    justifyContent: 'flex-start',
                    gap: '10px',
                    padding: '8px 10px',
                    height: 'auto',
                    fontSize: '0.78rem',
                    color: 'var(--text-primary)',
                  }}
                >
                  <SettingsIcon size={15} style={{ color: 'var(--accent-purple)' }} />
                  <span>System Settings</span>
                </button>

                <button
                  onClick={() => {
                    onNavigate('system_health');
                    setIsProfileDropdownOpen(false);
                  }}
                  className="icon-btn"
                  style={{
                    width: '100%',
                    justifyContent: 'flex-start',
                    gap: '10px',
                    padding: '8px 10px',
                    height: 'auto',
                    fontSize: '0.78rem',
                    color: 'var(--text-primary)',
                  }}
                >
                  <Activity size={15} style={{ color: 'var(--accent-blue)' }} />
                  <span>Stream & System Health</span>
                </button>

                <button
                  onClick={() => {
                    onNavigate('copilot');
                    setIsProfileDropdownOpen(false);
                  }}
                  className="icon-btn"
                  style={{
                    width: '100%',
                    justifyContent: 'flex-start',
                    gap: '10px',
                    padding: '8px 10px',
                    height: 'auto',
                    fontSize: '0.78rem',
                    color: 'var(--text-primary)',
                  }}
                >
                  <Bot size={15} style={{ color: 'var(--accent-healthy)' }} />
                  <span>AI Copilot Console</span>
                </button>

                <div style={{ height: '1px', background: 'var(--border-subtle)', margin: '4px 0' }} />

                {/* Logout Button */}
                <button
                  onClick={() => {
                    setIsProfileDropdownOpen(false);
                    logout();
                  }}
                  className="icon-btn"
                  style={{
                    width: '100%',
                    justifyContent: 'flex-start',
                    gap: '10px',
                    padding: '8px 10px',
                    height: 'auto',
                    fontSize: '0.78rem',
                    color: 'var(--accent-danger)',
                    borderColor: 'rgba(239, 68, 68, 0.3)',
                    background: 'rgba(239, 68, 68, 0.08)',
                    fontWeight: 700,
                  }}
                >
                  <LogOut size={15} />
                  <span>Lock Station & Logout</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Global Spotlight Search Modal */}
      <GlobalSearchModal
        isOpen={isSearchModalOpen}
        onClose={() => setIsSearchModalOpen(false)}
        onNavigate={onNavigate}
        onSelectCamera={onSelectCamera}
      />

      {/* Real-Time Notification Center Drawer */}
      <NotificationCenter isOpen={isNotifOpen} onClose={() => setIsNotifOpen(false)} />

      {/* YOLO26 Forensic AI Inspector Modal */}
      <ForensicAIModal
        isOpen={isForensicModalOpen}
        onClose={() => setIsForensicModalOpen(false)}
      />
    </>
  );
};
