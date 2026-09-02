import React from 'react';
import {
  LayoutDashboard,
  Tv,
  Camera,
  Bot,
  Car,
  Shield,
  BellRing,
  FolderSearch,
  MapPin,
  Activity,
  Settings as SettingsIcon,
  X,
  Radio,
} from 'lucide-react';

export type NavView =
  | 'dashboard'
  | 'live_monitoring'
  | 'camera_registry'
  | 'copilot'
  | 'anpr'
  | 'watchlist'
  | 'alerts'
  | 'investigations'
  | 'map'
  | 'system_health'
  | 'settings';

interface SidebarProps {
  activeView: NavView;
  onNavigate: (view: NavView) => void;
  alertCount?: number;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

interface NavItem {
  id: NavView;
  label: string;
  icon: React.ElementType;
  badge?: string | number;
  badgeType?: 'live' | 'alert' | 'agent' | 'count';
}

interface NavSection {
  title: string;
  items: NavItem[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeView,
  onNavigate,
  alertCount = 0,
  isMobileOpen = false,
  onCloseMobile,
}) => {
  const sections: NavSection[] = [
    {
      title: 'COMMAND',
      items: [
        { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
        { id: 'live_monitoring', label: 'Live Monitoring', icon: Tv, badge: '30-LIVE', badgeType: 'live' },
        { id: 'camera_registry', label: 'Camera Registry', icon: Camera },
      ],
    },
    {
      title: 'INTELLIGENCE',
      items: [
        { id: 'copilot', label: 'AI Copilot', icon: Bot, badge: 'AI AGENT', badgeType: 'agent' },
        { id: 'anpr', label: 'ANPR & Vehicles', icon: Car },
        { id: 'watchlist', label: 'Watchlist', icon: Shield },
        {
          id: 'alerts',
          label: 'Alerts & Incidents',
          icon: BellRing,
          badge: alertCount > 0 ? alertCount : undefined,
          badgeType: 'alert',
        },
        { id: 'investigations', label: 'Investigations', icon: FolderSearch },
      ],
    },
    {
      title: 'OPERATIONS & SYSTEM',
      items: [
        { id: 'map', label: 'CCTV Map', icon: MapPin },
        { id: 'system_health', label: 'System Health', icon: Activity },
        { id: 'settings', label: 'Settings', icon: SettingsIcon },
      ],
    },
  ];

  return (
    <aside
      className={`global-sidebar ${isMobileOpen ? 'mobile-open' : ''}`}
      aria-label="Surveillance Navigation"
    >
      {/* Mobile Drawer Header */}
      <div className="mobile-sidebar-header">
        <div className="mobile-brand">
          <Radio size={18} className="text-cyan animate-pulse" />
          <span className="mobile-brand-name">PHANTOM C2</span>
        </div>
        {onCloseMobile && (
          <button
            onClick={onCloseMobile}
            className="mobile-close-btn icon-btn"
            aria-label="Close Navigation"
          >
            <X size={18} />
          </button>
        )}
      </div>

      <div className="sidebar-scroll">
        {sections.map((section) => (
          <div key={section.title} className="sidebar-section">
            <h3 className="section-title">{section.title}</h3>
            <ul className="nav-items-list">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeView === item.id;
                return (
                  <li key={item.id}>
                    <button
                      onClick={() => onNavigate(item.id)}
                      className={`nav-item-btn ${isActive ? 'active' : ''}`}
                      aria-current={isActive ? 'page' : undefined}
                    >
                      <Icon size={16} className="nav-icon" />
                      <span className="nav-label">{item.label}</span>

                      {item.badge !== undefined && (
                        <span className={`nav-badge badge-${item.badgeType || 'count'}`}>
                          {item.badge}
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>

      {/* Sidebar Footer Clearance Status */}
      <div className="sidebar-clearance-footer">
        <div className="clearance-indicator">
          <span className="clearance-dot"></span>
          <span className="clearance-text">CLEARANCE LEVEL 5 // ACTIVE</span>
        </div>
      </div>
    </aside>
  );
};
