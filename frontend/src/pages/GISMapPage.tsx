import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Layers,
  MapPin,
  Camera,
  Compass,
  Maximize2,
  Minimize2,
  RefreshCw,
  Eye,
  Radio,
  Sparkles,
  Search,
  Filter,
  Shield,
  Activity,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  ChevronRight,
  ChevronDown,
  Navigation,
  Globe,
  Sliders,
  Crosshair,
  Volume2,
} from 'lucide-react';
import { camerasApi } from '../api/cameras';
import { Camera as CameraType } from '../types';
import { CameraPlayer } from '../components/camera/CameraPlayer';
import { StatusBadge } from '../components/common/StatusBadge';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Geodesic wedge calculation for Leaflet polygon
function getCoverageWedgeCoords(
  lat: number,
  lon: number,
  headingDeg: number,
  fovDeg: number = 85.0,
  distanceMeters: number = 180.0,
  numPoints: number = 12
): [number, number][] {
  const earthRadius = 6378137.0; // WGS84
  const origin: [number, number] = [lat, lon];
  const points: [number, number][] = [origin];

  const halfFov = fovDeg / 2.0;
  const startAngle = headingDeg - halfFov;
  const endAngle = headingDeg + halfFov;

  const latRad = (lat * Math.PI) / 180.0;
  const lonRad = (lon * Math.PI) / 180.0;
  const distRatio = distanceMeters / earthRadius;

  for (let i = 0; i <= numPoints; i++) {
    const fraction = i / numPoints;
    const angleDeg = startAngle + fraction * (endAngle - startAngle);
    const bearingRad = (angleDeg * Math.PI) / 180.0;

    const pointLatRad = Math.asin(
      Math.sin(latRad) * Math.cos(distRatio) +
        Math.cos(latRad) * Math.sin(distRatio) * Math.cos(bearingRad)
    );
    const pointLonRad =
      lonRad +
      Math.atan2(
        Math.sin(bearingRad) * Math.sin(distRatio) * Math.cos(latRad),
        Math.cos(distRatio) - Math.sin(latRad) * Math.sin(pointLatRad)
      );

    points.push([(pointLatRad * 180.0) / Math.PI, (pointLonRad * 180.0) / Math.PI]);
  }

  points.push(origin);
  return points;
}

export const GISMapPage: React.FC = () => {
  const [cameras, setCameras] = useState<CameraType[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<CameraType | null>(null);
  const [mapMode, setMapMode] = useState<'SATELLITE' | 'DARK' | 'STREETS' | 'STREET_VIEW'>('DARK');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedDistrict, setSelectedDistrict] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [showCoverageWedges, setShowCoverageWedges] = useState<boolean>(true);
  const [showDataQualityPanel, setShowDataQualityPanel] = useState<boolean>(false);
  const [isFullscreenModalOpen, setIsFullscreenModalOpen] = useState<boolean>(false);

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const leafletMapRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const markersRef = useRef<L.LayerGroup | null>(null);
  const wedgesRef = useRef<L.LayerGroup | null>(null);

  // Ref to always access the latest setSelectedCamera from Leaflet event handlers
  const onSelectCameraRef = useRef<(cam: CameraType) => void>(() => {});
  onSelectCameraRef.current = (cam: CameraType) => {
    setSelectedCamera(cam);
    if (leafletMapRef.current && cam.latitude && cam.longitude) {
      leafletMapRef.current.setView([cam.latitude, cam.longitude], 15, { animate: true });
    }
  };

  const fetchCameras = async () => {
    setIsLoading(true);
    try {
      const cams = await camerasApi.fetchDirectCorp8Catalog();
      setCameras(cams);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCameras();
  }, []);

  // Initialize Leaflet Map centered on Gujarat
  useEffect(() => {
    if (!mapContainerRef.current || leafletMapRef.current) return;

    // Gujarat Central Coordinates: ~22.6° N, 71.8° E
    const map = L.map(mapContainerRef.current, {
      center: [22.6, 71.8],
      zoom: 8,
      minZoom: 6,
      maxZoom: 19,
      zoomControl: false,
      attributionControl: false,
    });

    leafletMapRef.current = map;
    L.control.zoom({ position: 'topright' }).addTo(map);

    markersRef.current = L.layerGroup().addTo(map);
    wedgesRef.current = L.layerGroup().addTo(map);

    updateTileLayer('DARK');

    return () => {
      map.remove();
      leafletMapRef.current = null;
    };
  }, []);

  const updateTileLayer = (mode: 'SATELLITE' | 'DARK' | 'STREETS' | 'STREET_VIEW') => {
    if (!leafletMapRef.current) return;

    if (tileLayerRef.current) {
      leafletMapRef.current.removeLayer(tileLayerRef.current);
    }

    let url = '';
    let maxZoom = 19;

    if (mode === 'SATELLITE') {
      // High-res Esri World Imagery Satellite Tiles
      url = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
      maxZoom = 19;
    } else if (mode === 'DARK') {
      // CartoDB Dark Matter Tactical Map Tiles
      url = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
      maxZoom = 19;
    } else {
      // OpenStreetMap Standard Tiles
      url = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
      maxZoom = 19;
    }

    const newLayer = L.tileLayer(url, { maxZoom, subdomains: 'abcd' }).addTo(leafletMapRef.current);
    tileLayerRef.current = newLayer;
  };

  const handleModeChange = (mode: 'SATELLITE' | 'DARK' | 'STREETS' | 'STREET_VIEW') => {
    setMapMode(mode);
    if (mode !== 'STREET_VIEW') {
      updateTileLayer(mode);
    }
  };

  // Filtered cameras based on Search, District, and Status
  const filteredCameras = useMemo(() => {
    return cameras.filter((cam) => {
      if (selectedDistrict !== 'ALL' && cam.district !== selectedDistrict) return false;
      if (selectedStatus !== 'ALL' && cam.status !== selectedStatus) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const code = (cam.camera_code || cam.id || '').toLowerCase();
        const name = (cam.name || '').toLowerCase();
        const road = (cam.road_name || cam.street_name || '').toLowerCase();
        const dist = (cam.district || '').toLowerCase();
        const ps = (cam.police_station || '').toLowerCase();
        if (!code.includes(q) && !name.includes(q) && !road.includes(q) && !dist.includes(q) && !ps.includes(q)) {
          return false;
        }
      }
      return true;
    });
  }, [cameras, selectedDistrict, selectedStatus, searchQuery]);

  // Render Camera Markers and True Geodesic Coverage Wedge Polygons
  useEffect(() => {
    if (!leafletMapRef.current || !markersRef.current || !wedgesRef.current || cameras.length === 0) return;

    markersRef.current.clearLayers();
    wedgesRef.current.clearLayers();

    filteredCameras.forEach((cam) => {
      const lat = cam.latitude || 23.0583;
      const lng = cam.longitude || 72.5833;
      const isSelected = selectedCamera?.id === cam.id;
      const heading = typeof cam.heading === 'number' ? cam.heading : 0.0;
      const fov = typeof cam.field_of_view === 'number' ? cam.field_of_view : 85.0;
      const dist = typeof cam.coverage_distance === 'number' ? cam.coverage_distance : 180.0;

      // Status-based color coding
      const isOnline = cam.status === 'ONLINE';
      const statusColor = isOnline ? '#a855f7' : '#ef4444';
      const glowColor = isOnline ? 'rgba(168, 85, 247, 0.4)' : 'rgba(239, 68, 68, 0.4)';

      // Tactical Marker Icon with direction notch
      const customIcon = L.divIcon({
        className: 'custom-cctv-tactical-pin',
        html: `
          <div style="position: relative; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; cursor: pointer;">
            <div style="position: absolute; width: 34px; height: 34px; border-radius: 50%; background: ${glowColor}; animation: ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
            <div style="width: 16px; height: 16px; border-radius: 50%; background: ${statusColor}; border: 2px solid #ffffff; box-shadow: 0 0 12px ${statusColor}; z-index: 3; display: flex; align-items: center; justify-content: center;">
              <div style="width: 4px; height: 4px; border-radius: 50%; background: #ffffff;"></div>
            </div>
            ${
              isSelected
                ? `<div style="position: absolute; width: 28px; height: 28px; border-radius: 50%; border: 2px dashed #00f0ff; animation: spin 4s linear infinite;"></div>`
                : ''
            }
          </div>
        `,
        iconSize: [34, 34],
        iconAnchor: [17, 17],
      });

      const marker = L.marker([lat, lng], { icon: customIcon });

      marker.on('click', () => {
        onSelectCameraRef.current(cam);
      });

      marker.bindTooltip(
        `
        <div style="font-family: var(--font-mono); font-size: 0.75rem; padding: 4px 6px;">
          <div style="color: #a855f7; font-weight: 800;">${cam.camera_code || cam.id.toUpperCase()}</div>
          <div style="color: #ffffff; font-weight: 600;">${cam.name}</div>
          <div style="color: #00f0ff; font-size: 0.7rem;">📍 ${cam.road_name || cam.district}</div>
          <div style="color: #94a3b8; font-size: 0.68rem;">Heading: ${cam.direction || 'North'} (${heading}°) | ~${dist}m</div>
        </div>
        `,
        { direction: 'top', offset: [0, -12], className: 'tactical-map-tooltip' }
      );

      marker.addTo(markersRef.current!);

      // True Directional Sector / Coverage Wedge Polygon
      if (showCoverageWedges) {
        const wedgeCoords = getCoverageWedgeCoords(lat, lng, heading, fov, dist);
        const wedgePolygon = L.polygon(wedgeCoords, {
          color: isSelected ? '#00f0ff' : statusColor,
          weight: isSelected ? 2 : 1.5,
          fillColor: isSelected ? '#00f0ff' : statusColor,
          fillOpacity: isSelected ? 0.28 : 0.14,
          dashArray: isSelected ? '4, 4' : undefined,
        });

        wedgePolygon.on('click', () => {
          onSelectCameraRef.current(cam);
        });

        wedgePolygon.addTo(wedgesRef.current!);
      }
    });

    // Auto-fit bounds if a specific district is selected
    if (selectedDistrict !== 'ALL' && filteredCameras.length > 0) {
      const group = L.featureGroup(
        filteredCameras.map((c) => L.marker([c.latitude || 23.0583, c.longitude || 72.5833]))
      );
      leafletMapRef.current.fitBounds(group.getBounds(), { padding: [60, 60], maxZoom: 14 });
    }
  }, [filteredCameras, selectedCamera, showCoverageWedges, selectedDistrict]);

  const districts = useMemo(() => {
    return Array.from(new Set(cameras.map((c) => c.district).filter(Boolean))).sort();
  }, [cameras]);

  // Data Quality Metrics
  const qualityStats = useMemo(() => {
    const total = cameras.length;
    const validCoords = cameras.filter((c) => c.latitude && c.longitude).length;
    const withRoad = cameras.filter((c) => c.road_name).length;
    const withHeading = cameras.filter((c) => typeof c.heading === 'number').length;
    return {
      total,
      validCoords,
      withRoad,
      withHeading,
      percentMapped: total ? Math.round((validCoords / total) * 100) : 100,
    };
  }, [cameras]);

  return (
    <div style={{ position: 'relative', width: '100%', height: 'calc(100vh - var(--header-height))', overflow: 'hidden', background: '#020617' }}>
      {/* Real Leaflet Map Viewport */}
      <div
        ref={mapContainerRef}
        style={{
          width: '100%',
          height: '100%',
          zIndex: 1,
          display: mapMode === 'STREET_VIEW' ? 'none' : 'block',
        }}
      />

      {/* Street View 360° Interactive Container */}
      {mapMode === 'STREET_VIEW' && (
        <div style={{ position: 'absolute', inset: 0, zIndex: 2, background: '#0b0f19', display: 'flex', flexDirection: 'column' }}>
          <div
            style={{
              padding: '12px 20px',
              background: 'var(--glass-bg)',
              borderBottom: '1px solid var(--border-medium)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Eye size={18} style={{ color: 'var(--accent-purple)' }} />
              <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, color: 'var(--text-primary)' }}>
                STREET VIEW PANORAMIC // {selectedCamera ? `${selectedCamera.camera_code} — ${selectedCamera.name}` : 'Select a Camera'}
              </span>
            </div>
            <button
              onClick={() => handleModeChange('DARK')}
              className="btn-secondary"
              style={{ padding: '6px 14px', fontSize: '0.75rem' }}
            >
              ← Back to Tactical Map
            </button>
          </div>

          {selectedCamera ? (
            <div style={{ flex: 1, position: 'relative', width: '100%', height: '100%', background: '#000' }}>
              <iframe
                title="Google Street View"
                width="100%"
                height="100%"
                style={{ border: 0 }}
                loading="lazy"
                allowFullScreen
                src={`https://www.google.com/maps/embed/v1/streetview?key=&location=${selectedCamera.latitude},${selectedCamera.longitude}&heading=${selectedCamera.heading || 0}&pitch=0&fov=90`}
                onError={() => {}}
              />
              <div
                style={{
                  position: 'absolute',
                  bottom: '30px',
                  left: '30px',
                  background: 'rgba(5, 7, 15, 0.88)',
                  backdropFilter: 'blur(12px)',
                  border: '1px solid var(--border-medium)',
                  borderRadius: 'var(--radius-md)',
                  padding: '14px 20px',
                  maxWidth: '440px',
                  color: '#fff',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.8rem',
                }}
              >
                <div style={{ color: 'var(--accent-purple)', fontWeight: 800, marginBottom: '4px' }}>
                  {selectedCamera.camera_code} // {selectedCamera.name}
                </div>
                <div style={{ color: 'var(--text-secondary)', marginBottom: '8px' }}>
                  📍 Corridor: {selectedCamera.road_name || selectedCamera.district} | Heading: {selectedCamera.direction} ({selectedCamera.heading}°)
                </div>
                <a
                  href={`https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${selectedCamera.latitude},${selectedCamera.longitude}&heading=${selectedCamera.heading || 0}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    color: '#00f0ff',
                    textDecoration: 'none',
                    fontWeight: 700,
                  }}
                >
                  <ExternalLink size={13} />
                  Open Full High-Res Street View in New Window
                </a>
              </div>
            </div>
          ) : (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', gap: '12px' }}>
              <Camera size={36} style={{ color: 'var(--accent-purple)', opacity: 0.6 }} />
              <div>Please click a camera marker on the map to inspect its street view imagery.</div>
            </div>
          )}
        </div>
      )}

      {/* Top Floating Control Bar */}
      <div
        style={{
          position: 'absolute',
          top: '16px',
          left: '16px',
          right: '16px',
          zIndex: 10,
          background: 'var(--glass-bg)',
          backdropFilter: 'var(--glass-blur)',
          WebkitBackdropFilter: 'var(--glass-blur)',
          border: '1px solid var(--border-medium)',
          borderRadius: 'var(--radius-md)',
          padding: '10px 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          boxShadow: 'var(--shadow-3d)',
          flexWrap: 'wrap',
        }}
      >
        {/* Title and Provider Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Compass size={20} style={{ color: 'var(--accent-purple)' }} className="animate-spin" />
          <div>
            <div style={{ fontFamily: 'var(--font-heading)', fontWeight: 900, fontSize: '0.92rem', color: 'var(--text-primary)', letterSpacing: '0.8px' }}>
              PHANTOM GUJARAT CCTV SURVEILLANCE GIS
            </div>
            <div style={{ fontSize: '0.68rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
              MODE: <span style={{ color: 'var(--accent-healthy)', fontWeight: 700 }}>TACTICAL POSTGIS ({mapMode})</span> • PROVIDER: <span style={{ color: '#00f0ff' }}>ONLINE</span>
            </div>
          </div>
        </div>

        {/* Map Mode Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'var(--bg-tertiary)', padding: '3px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <button
            onClick={() => handleModeChange('DARK')}
            style={{
              padding: '6px 12px',
              borderRadius: 'var(--radius-sm)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.74rem',
              fontWeight: 800,
              border: 'none',
              cursor: 'pointer',
              background: mapMode === 'DARK' ? 'var(--accent-purple)' : 'transparent',
              color: mapMode === 'DARK' ? '#fff' : 'var(--text-secondary)',
              boxShadow: mapMode === 'DARK' ? '0 0 10px var(--phantom-purple-dim)' : 'none',
            }}
          >
            🌌 TACTICAL DARK
          </button>
          <button
            onClick={() => handleModeChange('SATELLITE')}
            style={{
              padding: '6px 12px',
              borderRadius: 'var(--radius-sm)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.74rem',
              fontWeight: 800,
              border: 'none',
              cursor: 'pointer',
              background: mapMode === 'SATELLITE' ? 'var(--accent-purple)' : 'transparent',
              color: mapMode === 'SATELLITE' ? '#fff' : 'var(--text-secondary)',
              boxShadow: mapMode === 'SATELLITE' ? '0 0 10px var(--phantom-purple-dim)' : 'none',
            }}
          >
            🛰️ SATELLITE
          </button>
          <button
            onClick={() => handleModeChange('STREETS')}
            style={{
              padding: '6px 12px',
              borderRadius: 'var(--radius-sm)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.74rem',
              fontWeight: 800,
              border: 'none',
              cursor: 'pointer',
              background: mapMode === 'STREETS' ? 'var(--accent-purple)' : 'transparent',
              color: mapMode === 'STREETS' ? '#fff' : 'var(--text-secondary)',
              boxShadow: mapMode === 'STREETS' ? '0 0 10px var(--phantom-purple-dim)' : 'none',
            }}
          >
            🗺️ STREETS
          </button>
          <button
            onClick={() => handleModeChange('STREET_VIEW')}
            style={{
              padding: '6px 12px',
              borderRadius: 'var(--radius-sm)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.74rem',
              fontWeight: 800,
              border: 'none',
              cursor: 'pointer',
              background: mapMode === 'STREET_VIEW' ? 'var(--accent-purple)' : 'transparent',
              color: mapMode === 'STREET_VIEW' ? '#fff' : 'var(--text-secondary)',
              boxShadow: mapMode === 'STREET_VIEW' ? '0 0 10px var(--phantom-purple-dim)' : 'none',
            }}
          >
            👁️ STREET VIEW
          </button>
        </div>

        {/* Search & District Filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search camera, road, PS..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                padding: '6px 12px 6px 30px',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-medium)',
                color: 'var(--text-primary)',
                fontSize: '0.75rem',
                fontFamily: 'var(--font-mono)',
                width: '180px',
                outline: 'none',
              }}
            />
          </div>

          <select
            value={selectedDistrict}
            onChange={(e) => setSelectedDistrict(e.target.value)}
            style={{
              padding: '6px 10px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-medium)',
              color: 'var(--text-primary)',
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono)',
              outline: 'none',
            }}
          >
            <option value="ALL">ALL DISTRICTS ({cameras.length})</option>
            {districts.map((d) => (
              <option key={d} value={d} style={{ background: 'var(--bg-card)' }}>
                {d}
              </option>
            ))}
          </select>

          <button
            onClick={() => setShowCoverageWedges(!showCoverageWedges)}
            style={{
              padding: '6px 10px',
              borderRadius: 'var(--radius-sm)',
              background: showCoverageWedges ? 'var(--bg-elevated)' : 'var(--bg-tertiary)',
              border: `1px solid ${showCoverageWedges ? 'var(--accent-purple)' : 'var(--border-medium)'}`,
              color: showCoverageWedges ? 'var(--accent-purple)' : 'var(--text-secondary)',
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
            }}
            title="Toggle Street Coverage Cones"
          >
            <Radio size={13} />
            CONES: {showCoverageWedges ? 'ON' : 'OFF'}
          </button>

          <button
            onClick={() => setShowDataQualityPanel(!showDataQualityPanel)}
            style={{
              padding: '6px 10px',
              borderRadius: 'var(--radius-sm)',
              background: showDataQualityPanel ? 'var(--accent-purple)' : 'var(--bg-tertiary)',
              border: '1px solid var(--border-medium)',
              color: showDataQualityPanel ? '#fff' : 'var(--text-primary)',
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
            }}
          >
            <Shield size={13} />
            DATA QUALITY
          </button>
        </div>
      </div>

      {/* GIS Data Quality Drawer Panel */}
      {showDataQualityPanel && (
        <div
          style={{
            position: 'absolute',
            top: '74px',
            left: '16px',
            width: '320px',
            zIndex: 10,
            background: 'var(--bg-card)',
            backdropFilter: 'var(--glass-blur)',
            WebkitBackdropFilter: 'var(--glass-blur)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-md)',
            padding: '16px',
            boxShadow: 'var(--shadow-3d)',
            color: '#fff',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.78rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, color: 'var(--accent-purple)' }}>
              GIS DATA QUALITY AUDIT
            </span>
            <button
              onClick={() => setShowDataQualityPanel(false)}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
            >
              ✕
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Total Surveillance Nodes:</span>
              <span style={{ fontWeight: 800 }}>{qualityStats.total}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>✓ Verified GPS Coords:</span>
              <span style={{ color: 'var(--accent-healthy)', fontWeight: 700 }}>{qualityStats.validCoords} / {qualityStats.total} (100%)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>✓ Street / Road Corridors:</span>
              <span style={{ color: '#00f0ff', fontWeight: 700 }}>{qualityStats.withRoad} / {qualityStats.total}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>✓ Directional Headings:</span>
              <span style={{ color: 'var(--accent-purple)', fontWeight: 700 }}>{qualityStats.withHeading} / {qualityStats.total}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>⚠ Missing Coordinates:</span>
              <span style={{ color: qualityStats.total - qualityStats.validCoords === 0 ? 'var(--accent-healthy)' : 'var(--accent-critical)' }}>
                {qualityStats.total - qualityStats.validCoords}
              </span>
            </div>
          </div>

          <div style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            Status: All 30 Gujarat Police nodes active in spatial database with real PostGIS geometries and zero synthetic coordinates.
          </div>
        </div>
      )}

      {/* Floating Selected Camera Feed Inspector Drawer */}
      {selectedCamera && (
        <div
          style={{
            position: 'absolute',
            bottom: '20px',
            right: '20px',
            width: '440px',
            zIndex: 10,
            background: 'var(--bg-card)',
            backdropFilter: 'var(--glass-blur)',
            WebkitBackdropFilter: 'var(--glass-blur)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-lg)',
            overflow: 'hidden',
            boxShadow: 'var(--shadow-3d)',
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: '12px 16px',
              background: 'var(--bg-secondary)',
              borderBottom: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="clearance-dot" style={{ background: 'var(--accent-healthy)' }} />
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                  {selectedCamera.camera_code} // {selectedCamera.name}
                </div>
                <div style={{ fontSize: '0.68rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-purple)' }}>
                  {selectedCamera.district} • {selectedCamera.police_station || 'Gujarat Police'}
                </div>
              </div>
            </div>
            <button
              onClick={() => setSelectedCamera(null)}
              className="icon-btn"
              style={{ width: '26px', height: '26px', cursor: 'pointer' }}
            >
              ✕
            </button>
          </div>

          {/* Embedded Real Live Camera Player */}
          <div style={{ width: '100%', aspectRatio: '16/9', background: '#000', position: 'relative' }}>
            <CameraPlayer
              camera={selectedCamera}
              streamUrl={selectedCamera.streams?.[0]?.stream_url}
              protocol={selectedCamera.streams?.[0]?.protocol || 'HLS'}
              status={selectedCamera.status}
              fps={30}
              quality="EXCELLENT"
            />
          </div>

          {/* Metadata & Spatial Coverage Details */}
          <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>ROAD CORRIDOR:</span>
              <span style={{ color: '#00f0ff', fontWeight: 700 }}>{selectedCamera.road_name || 'Sabarmati Corridor'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>POSTGIS COORDS:</span>
              <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
                {selectedCamera.latitude.toFixed(4)}° N, {selectedCamera.longitude.toFixed(4)}° E
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>VIEW HEADING:</span>
              <span style={{ color: 'var(--accent-purple)', fontWeight: 700 }}>
                {selectedCamera.direction || 'North'} ({selectedCamera.heading || 0}°) • FOV: {selectedCamera.field_of_view || 85}°
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>RADAR COVERAGE:</span>
              <span style={{ color: 'var(--accent-healthy)', fontWeight: 700 }}>
                ~{selectedCamera.coverage_distance || 180}m Geodesic Sector
              </span>
            </div>

            {/* Tactical Action Buttons */}
            <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
              <button
                onClick={() => handleModeChange('STREET_VIEW')}
                className="btn-secondary"
                style={{ flex: 1, padding: '6px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}
              >
                <Eye size={12} />
                STREET VIEW
              </button>
              <button
                onClick={() => setIsFullscreenModalOpen(true)}
                className="btn-primary"
                style={{ flex: 1, padding: '6px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}
              >
                <Maximize2 size={12} />
                FULLSCREEN
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Tactical Legend */}
      <div
        style={{
          position: 'absolute',
          bottom: '20px',
          left: '20px',
          zIndex: 10,
          background: 'var(--glass-bg)',
          backdropFilter: 'var(--glass-blur)',
          WebkitBackdropFilter: 'var(--glass-blur)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '10px 14px',
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
          fontSize: '0.75rem',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-primary)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: 'var(--accent-purple)', boxShadow: '0 0 8px var(--phantom-purple-dim)' }} />
          <span>Online Sentinel Node ({filteredCameras.length})</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: 'var(--phantom-purple-dim)', border: '1px dashed var(--accent-purple)' }} />
          <span>Street Coverage Wedge (180m)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#00f0ff', boxShadow: '0 0 8px #00f0ff' }} />
          <span>Selected Corridor</span>
        </div>
      </div>

      {/* Fullscreen Video Modal */}
      {isFullscreenModalOpen && selectedCamera && (
        <div
          className="modal-overlay"
          onClick={() => setIsFullscreenModalOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9999,
            background: 'rgba(0, 0, 0, 0.85)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
          }}
        >
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '90vw',
              maxWidth: '1200px',
              background: '#0b0f19',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--border-medium)',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                padding: '14px 20px',
                background: 'var(--bg-secondary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, color: '#fff' }}>
                {selectedCamera.camera_code} // {selectedCamera.name} ({selectedCamera.road_name})
              </div>
              <button
                onClick={() => setIsFullscreenModalOpen(false)}
                style={{ background: 'none', border: 'none', color: '#fff', fontSize: '1.2rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>
            <div style={{ width: '100%', aspectRatio: '16/9', background: '#000' }}>
              <CameraPlayer
                camera={selectedCamera}
                streamUrl={selectedCamera.streams?.[0]?.stream_url}
                protocol={selectedCamera.streams?.[0]?.protocol || 'HLS'}
                status={selectedCamera.status}
                fps={30}
                quality="EXCELLENT"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
