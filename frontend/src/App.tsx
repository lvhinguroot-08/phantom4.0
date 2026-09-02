import React, { useState } from 'react';
import { ThemeProvider } from './context/ThemeContext';
import { BackendStatusProvider } from './context/BackendStatusContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { RealtimeEventProvider } from './context/RealtimeEventContext';
import { Header } from './components/common/Header';
import { Sidebar, NavView } from './components/common/Sidebar';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { LiveMonitoringPage } from './pages/LiveMonitoringPage';
import { CameraRegistryPage } from './pages/CameraRegistryPage';
import { AICopilotPage } from './pages/AICopilotPage';
import { ANPRVehiclesPage } from './pages/ANPRVehiclesPage';
import { WatchlistPage } from './pages/WatchlistPage';
import { AlertsIncidentsPage } from './pages/AlertsIncidentsPage';
import { InvestigationsPage } from './pages/InvestigationsPage';
import { GISMapPage } from './pages/GISMapPage';
import { SystemHealthPage } from './pages/SystemHealthPage';
import { SettingsPage } from './pages/SettingsPage';

export const AppContent: React.FC = () => {
  const { isAuthenticated, login } = useAuth();
  const [activeView, setActiveView] = useState<NavView>('dashboard');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);

  const handleNavigate = (view: NavView) => {
    setActiveView(view);
    setIsMobileMenuOpen(false);
  };

  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={(profile) => login(profile)} />;
  }

  const renderActiveView = () => {
    switch (activeView) {
      case 'dashboard':
        return <DashboardPage />;
      case 'live_monitoring':
        return <LiveMonitoringPage />;
      case 'camera_registry':
        return <CameraRegistryPage />;
      case 'copilot':
        return <AICopilotPage onNavigate={handleNavigate} />;
      case 'anpr':
        return <ANPRVehiclesPage />;
      case 'watchlist':
        return <WatchlistPage />;
      case 'alerts':
        return <AlertsIncidentsPage />;
      case 'investigations':
        return <InvestigationsPage />;
      case 'map':
        return <GISMapPage />;
      case 'system_health':
        return <SystemHealthPage />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <DashboardPage />;
    }
  };

  return (
    <div className="command-center-app">
      {/* Top Command Bar */}
      <Header
        onNavigate={handleNavigate}
        isMobileMenuOpen={isMobileMenuOpen}
        onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
      />

      {/* Main Layout Body */}
      <div className="app-main-body">
        {/* Mobile Backdrop Overlay */}
        {isMobileMenuOpen && (
          <div
            className="mobile-sidebar-backdrop"
            onClick={() => setIsMobileMenuOpen(false)}
            aria-hidden="true"
          />
        )}

        {/* Global Multi-Section Sidebar */}
        <Sidebar
          activeView={activeView}
          onNavigate={handleNavigate}
          isMobileOpen={isMobileMenuOpen}
          onCloseMobile={() => setIsMobileMenuOpen(false)}
        />

        {/* Viewport Canvas */}
        <main className="app-viewport-content" role="main">
          {renderActiveView()}
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <BackendStatusProvider>
        <AuthProvider>
          <RealtimeEventProvider>
            <AppContent />
          </RealtimeEventProvider>
        </AuthProvider>
      </BackendStatusProvider>
    </ThemeProvider>
  );
};

export default App;
