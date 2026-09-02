import React, { useState, useEffect, useMemo } from 'react';
import { Camera } from '../types';
import { camerasApi } from '../api/cameras';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingState, EmptyState } from '../components/common/LoadingError';
import { useBackendStatus } from '../context/BackendStatusContext';
import { CameraPlayer } from '../components/camera/CameraPlayer';
import {
  Search,
  Filter,
  RefreshCw,
  MapPin,
  Building,
  Radio,
  Cpu,
  Plus,
  UploadCloud,
  Eye,
  Video,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  X,
  ChevronLeft,
  ChevronRight,
  Shield,
  Layers,
} from 'lucide-react';

export const CameraRegistryPage: React.FC = () => {
  const { isConnected } = useBackendStatus();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [districtFilter, setDistrictFilter] = useState<string>('ALL');

  // Modals
  const [selectedLiveCam, setSelectedLiveCam] = useState<Camera | null>(null);
  const [showOnboardModal, setShowOnboardModal] = useState<boolean>(false);
  const [showBulkImportModal, setShowBulkImportModal] = useState<boolean>(false);

  // Form states for manual onboarding
  const [onboardForm, setOnboardForm] = useState({
    camera_code: '',
    name: '',
    department_name: 'Gujarat Police / Smart City',
    district: 'Ahmedabad',
    city: 'Ahmedabad',
    latitude: 23.0225,
    longitude: 72.5714,
    camera_type: 'ANPR',
    stream_url: '',
    protocol: 'HLS',
  });
  const [onboardSubmitting, setOnboardSubmitting] = useState<boolean>(false);

  // Bulk import state
  const [bulkCsvText, setBulkCsvText] = useState<string>(
    `camera_code,name,district,city,latitude,longitude,camera_type,stream_url\nCAM-VAL-101,Vapi Toll Plaza Gate 1,Valsad,Vapi,20.3712,72.9106,ANPR,/api/v1/streams/cam01/live.mp4\nCAM-NAV-202,Navsari Tower Road Junction,Navsari,Navsari,20.9467,72.9520,PTZ,/api/v1/streams/cam02/live.mp4`
  );
  const [bulkSubmitting, setBulkSubmitting] = useState<boolean>(false);
  const [bulkSuccess, setBulkSuccess] = useState<boolean>(false);

  // Pagination
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 12;

  const fetchCameras = async () => {
    setIsLoading(true);
    try {
      const loadedCams = await camerasApi.fetchDirectCorp8Catalog();
      setCameras(loadedCams);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCameras();
  }, []);

  const districts = useMemo(() => {
    return Array.from(new Set(cameras.map((c) => c.district).filter(Boolean))).sort();
  }, [cameras]);

  const filteredCameras = useMemo(() => {
    return cameras.filter((cam) => {
      if (statusFilter !== 'ALL' && cam.status !== statusFilter) return false;
      if (districtFilter !== 'ALL' && cam.district !== districtFilter) return false;
      if (search.trim()) {
        const query = search.toLowerCase();
        const matchCode = cam.camera_code?.toLowerCase().includes(query);
        const matchName = cam.name?.toLowerCase().includes(query);
        const matchDistrict = cam.district?.toLowerCase().includes(query);
        const matchCity = cam.city?.toLowerCase().includes(query);
        if (!matchCode && !matchName && !matchDistrict && !matchCity) return false;
      }
      return true;
    });
  }, [cameras, statusFilter, districtFilter, search]);

  const totalPages = Math.ceil(filteredCameras.length / pageSize) || 1;
  const paginatedCameras = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredCameras.slice(start, start + pageSize);
  }, [filteredCameras, currentPage, pageSize]);

  const handleOnboardSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setOnboardSubmitting(true);
    setTimeout(() => {
      const newCam: Camera = {
        id: `cam-${Date.now()}`,
        camera_code: onboardForm.camera_code.toUpperCase(),
        name: onboardForm.name,
        district: onboardForm.district,
        city: onboardForm.city,
        latitude: onboardForm.latitude,
        longitude: onboardForm.longitude,
        camera_type: onboardForm.camera_type as any,
        status: 'ONLINE',
        is_ptz_capable: onboardForm.camera_type === 'PTZ',
        ai_enabled: true,
      };
      setCameras((prev) => [newCam, ...prev]);
      setOnboardSubmitting(false);
      setShowOnboardModal(false);
      setOnboardForm({
        camera_code: '',
        name: '',
        department_name: 'Gujarat Police / Smart City',
        district: 'Ahmedabad',
        city: 'Ahmedabad',
        latitude: 23.0225,
        longitude: 72.5714,
        camera_type: 'ANPR',
        stream_url: '',
        protocol: 'HLS',
      });
    }, 600);
  };

  const handleBulkImportSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setBulkSubmitting(true);
    setTimeout(() => {
      setBulkSubmitting(false);
      setBulkSuccess(true);
      setTimeout(() => {
        setBulkSuccess(false);
        setShowBulkImportModal(false);
      }, 1500);
    }, 800);
  };

  return (
    <div className="registry-page-container" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
      {/* Top Header & Prominent Action Buttons */}
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
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
              STATEWIDE CAMERA REGISTRY
            </h1>
            <span
              className="badge-live"
              style={{
                fontSize: '0.75rem',
                padding: '4px 10px',
                borderRadius: 'var(--radius-sm)',
                fontWeight: 800,
                fontFamily: 'var(--font-mono)',
              }}
            >
              {cameras.length} NODES REGISTERED
            </span>
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
            Master inventory of Gujarat Police surveillance nodes, RTSP streaming endpoints, and PostGIS coordinates
          </p>
        </div>

        {/* Scaled Up Professional Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Professional Bulk Import Button */}
          <button
            onClick={() => setShowBulkImportModal(true)}
            className="icon-btn"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 18px',
              height: 'auto',
              width: 'auto',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(168, 85, 247, 0.15)',
              border: '1px solid rgba(168, 85, 247, 0.45)',
              color: '#c084fc',
              fontFamily: 'var(--font-heading)',
              fontSize: '0.82rem',
              fontWeight: 800,
              letterSpacing: '0.5px',
              cursor: 'pointer',
              boxShadow: '0 4px 14px rgba(168, 85, 247, 0.2)',
            }}
          >
            <UploadCloud size={17} />
            <span>BULK CSV IMPORT</span>
          </button>

          {/* Scaled-Up Register Camera Button */}
          <button
            onClick={() => setShowOnboardModal(true)}
            className="icon-btn highlight-btn"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 20px',
              height: 'auto',
              width: 'auto',
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-blue))',
              border: 'none',
              color: '#070b14',
              fontFamily: 'var(--font-heading)',
              fontSize: '0.85rem',
              fontWeight: 900,
              letterSpacing: '0.5px',
              cursor: 'pointer',
              boxShadow: '0 4px 18px var(--accent-cyan-dim)',
            }}
          >
            <Plus size={18} />
            <span>REGISTER CAMERA</span>
          </button>

          <button
            onClick={fetchCameras}
            className="icon-btn"
            style={{ width: '42px', height: '42px', borderRadius: 'var(--radius-md)' }}
            title="Refresh Camera Table"
          >
            <RefreshCw size={17} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Scaled-Up Search & Filter Bar */}
      <div
        style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '14px 20px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: '280px' }}>
          <Search size={18} className="text-cyan" />
          <input
            type="text"
            placeholder="Search by Camera Code, Junction, District, or City..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setCurrentPage(1);
            }}
            style={{
              width: '100%',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '8px 14px',
              color: '#fff',
              fontSize: '0.85rem',
              outline: 'none',
              fontFamily: 'var(--font-body)',
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* District Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-tertiary)', padding: '6px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <MapPin size={14} className="text-cyan" />
            <select
              value={districtFilter}
              onChange={(e) => {
                setDistrictFilter(e.target.value);
                setCurrentPage(1);
              }}
              style={{ background: 'transparent', color: '#fff', border: 'none', outline: 'none', fontSize: '0.82rem', fontFamily: 'var(--font-mono)', fontWeight: 600 }}
            >
              <option value="ALL" style={{ background: '#0a101d' }}>ALL DISTRICTS ({cameras.length})</option>
              {districts.map((d) => (
                <option key={d} value={d} style={{ background: '#0a101d' }}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-tertiary)', padding: '6px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <Radio size={14} className="text-healthy" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
              style={{ background: 'transparent', color: '#fff', border: 'none', outline: 'none', fontSize: '0.82rem', fontFamily: 'var(--font-mono)', fontWeight: 600 }}
            >
              <option value="ALL" style={{ background: '#0a101d' }}>ALL STATUSES</option>
              <option value="ONLINE" style={{ background: '#0a101d' }}>ONLINE</option>
              <option value="OFFLINE" style={{ background: '#0a101d' }}>OFFLINE</option>
            </select>
          </div>
        </div>
      </div>

      {/* Scaled-Up Professional Camera Table */}
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          overflow: 'hidden',
          boxShadow: 'var(--card-shadow)',
        }}
      >
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.82rem', fontFamily: 'var(--font-body)' }}>
            <thead>
              <tr style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-medium)', fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                <th style={{ padding: '14px 18px' }}>Camera Code</th>
                <th style={{ padding: '14px 18px' }}>Location / Junction</th>
                <th style={{ padding: '14px 18px' }}>District</th>
                <th style={{ padding: '14px 18px' }}>Type</th>
                <th style={{ padding: '14px 18px' }}>Coordinates (Lat, Lng)</th>
                <th style={{ padding: '14px 18px' }}>Status</th>
                <th style={{ padding: '14px 18px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} style={{ padding: '40px', textAlign: 'center' }}>
                    <LoadingState message="Loading statewide camera inventory..." />
                  </td>
                </tr>
              ) : paginatedCameras.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: '40px', textAlign: 'center' }}>
                    <EmptyState title="No Cameras Found" message="No surveillance nodes match your search query." />
                  </td>
                </tr>
              ) : (
                paginatedCameras.map((cam) => (
                  <tr
                    key={cam.id}
                    style={{
                      borderBottom: '1px solid var(--border-subtle)',
                      transition: 'background 0.15s ease',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-card-hover)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td style={{ padding: '14px 18px', fontFamily: 'var(--font-mono)', fontWeight: 800, color: 'var(--accent-cyan)', fontSize: '0.85rem' }}>
                      {cam.camera_code}
                    </td>
                    <td style={{ padding: '14px 18px', color: '#fff', fontWeight: 600, fontSize: '0.85rem' }}>
                      {cam.name}
                    </td>
                    <td style={{ padding: '14px 18px', color: 'var(--text-secondary)' }}>
                      {cam.district || 'Gujarat'}
                    </td>
                    <td style={{ padding: '14px 18px' }}>
                      <span style={{ padding: '2px 8px', borderRadius: '3px', background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border-subtle)', fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-primary)' }}>
                        {cam.camera_type || 'ANPR'}
                      </span>
                    </td>
                    <td style={{ padding: '14px 18px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                      {cam.latitude?.toFixed(4)}, {cam.longitude?.toFixed(4)}
                    </td>
                    <td style={{ padding: '14px 18px' }}>
                      <StatusBadge status={cam.status} />
                    </td>
                    <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                      <button
                        onClick={() => setSelectedLiveCam(cam)}
                        className="icon-btn highlight-btn"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '6px 12px',
                          height: 'auto',
                          width: 'auto',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '0.72rem',
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 700,
                          cursor: 'pointer',
                        }}
                      >
                        <Eye size={13} />
                        <span>LIVE STREAM</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div
          style={{
            padding: '12px 20px',
            background: 'var(--bg-secondary)',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.78rem',
            color: 'var(--text-muted)',
          }}
        >
          <div>
            Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, filteredCameras.length)} of {filteredCameras.length} cameras
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="icon-btn"
              style={{ width: '32px', height: '32px', opacity: currentPage === 1 ? 0.4 : 1 }}
            >
              <ChevronLeft size={16} />
            </button>
            <span style={{ color: '#fff', fontWeight: 700 }}>
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="icon-btn"
              style={{ width: '32px', height: '32px', opacity: currentPage === totalPages ? 0.4 : 1 }}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Live Stream Preview Modal */}
      {selectedLiveCam && (
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
              maxWidth: '900px',
              overflow: 'hidden',
              boxShadow: 'var(--shadow-3d)',
            }}
          >
            <div style={{ padding: '14px 20px', background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span className="clearance-dot" style={{ background: 'var(--accent-healthy)' }} />
                <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '0.92rem', color: '#fff' }}>
                  {selectedLiveCam.camera_code} - {selectedLiveCam.name}
                </span>
              </div>
              <button onClick={() => setSelectedLiveCam(null)} className="icon-btn" style={{ width: '30px', height: '30px' }}>
                <X size={16} />
              </button>
            </div>
            <div style={{ aspectRatio: '16/9', background: '#000' }}>
              <CameraPlayer camera={selectedLiveCam} status={selectedLiveCam.status} fps={25} quality="EXCELLENT" />
            </div>
          </div>
        </div>
      )}

      {/* Register Camera (Onboarding) Modal */}
      {showOnboardModal && (
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
              maxWidth: '650px',
              padding: '24px',
              boxShadow: 'var(--shadow-3d)',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.1rem', fontWeight: 900, color: '#fff', margin: 0 }}>
                REGISTER NEW SURVEILLANCE NODE
              </h2>
              <button onClick={() => setShowOnboardModal(false)} className="icon-btn" style={{ width: '30px', height: '30px' }}>
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleOnboardSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>CAMERA CODE *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. CAM-AHM-401"
                    value={onboardForm.camera_code}
                    onChange={(e) => setOnboardForm({ ...onboardForm, camera_code: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', color: '#fff', outline: 'none', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>LOCATION / JUNCTION NAME *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. SG Highway Iskcon Bridge"
                    value={onboardForm.name}
                    onChange={(e) => setOnboardForm({ ...onboardForm, name: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', color: '#fff', outline: 'none' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>DISTRICT</label>
                  <select
                    value={onboardForm.district}
                    onChange={(e) => setOnboardForm({ ...onboardForm, district: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', color: '#fff', outline: 'none' }}
                  >
                    <option value="Ahmedabad">Ahmedabad</option>
                    <option value="Junagadh">Junagadh</option>
                    <option value="Surat">Surat</option>
                    <option value="Vadodara">Vadodara</option>
                    <option value="Rajkot">Rajkot</option>
                    <option value="Gandhinagar">Gandhinagar</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>CAMERA TYPE</label>
                  <select
                    value={onboardForm.camera_type}
                    onChange={(e) => setOnboardForm({ ...onboardForm, camera_type: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', color: '#fff', outline: 'none' }}
                  >
                    <option value="ANPR">ANPR (Plate Recognition)</option>
                    <option value="PTZ">PTZ (Pan-Tilt-Zoom)</option>
                    <option value="FIXED">FIXED</option>
                    <option value="THERMAL">THERMAL</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button type="button" onClick={() => setShowOnboardModal(false)} className="icon-btn" style={{ padding: '8px 16px', width: 'auto', height: 'auto' }}>
                  CANCEL
                </button>
                <button
                  type="submit"
                  disabled={onboardSubmitting}
                  className="icon-btn highlight-btn"
                  style={{
                    padding: '8px 20px',
                    width: 'auto',
                    height: 'auto',
                    background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-blue))',
                    color: '#070b14',
                    fontWeight: 900,
                    border: 'none',
                  }}
                >
                  {onboardSubmitting ? 'REGISTERING...' : 'CONFIRM NODE'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Professional Bulk CSV Import Modal */}
      {showBulkImportModal && (
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
              maxWidth: '700px',
              padding: '24px',
              boxShadow: 'var(--shadow-3d)',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <UploadCloud size={22} className="text-purple" />
                <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.1rem', fontWeight: 900, color: '#fff', margin: 0 }}>
                  BULK CSV CAMERA ONBOARDING
                </h2>
              </div>
              <button onClick={() => setShowBulkImportModal(false)} className="icon-btn" style={{ width: '30px', height: '30px' }}>
                <X size={16} />
              </button>
            </div>

            {bulkSuccess ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--accent-healthy)', fontFamily: 'var(--font-heading)', fontWeight: 800 }}>
                <CheckCircle2 size={36} style={{ margin: '0 auto 12px auto' }} />
                <span>ALL CAMERA NODES IMPORTED & SYNCED SUCCESSFULLY!</span>
              </div>
            ) : (
              <form onSubmit={handleBulkImportSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: 0 }}>
                  Paste CSV content containing `camera_code, name, district, city, latitude, longitude, camera_type, stream_url`:
                </p>

                <textarea
                  rows={6}
                  value={bulkCsvText}
                  onChange={(e) => setBulkCsvText(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px',
                    background: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    color: '#fff',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.72rem',
                    outline: 'none',
                    resize: 'none',
                  }}
                />

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                  <button type="button" onClick={() => setShowBulkImportModal(false)} className="icon-btn" style={{ padding: '8px 16px', width: 'auto', height: 'auto' }}>
                    CANCEL
                  </button>
                  <button
                    type="submit"
                    disabled={bulkSubmitting}
                    className="icon-btn"
                    style={{
                      padding: '8px 20px',
                      width: 'auto',
                      height: 'auto',
                      background: 'rgba(168, 85, 247, 0.25)',
                      border: '1px solid rgba(168, 85, 247, 0.6)',
                      color: '#c084fc',
                      fontWeight: 800,
                    }}
                  >
                    {bulkSubmitting ? 'PROCESSING CSV...' : 'START BULK IMPORT'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
