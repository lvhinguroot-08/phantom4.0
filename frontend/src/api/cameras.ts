import { apiClient } from './client';
import {
  Camera,
  CameraCoverage,
  ApiResponse,
  PaginatedResponse,
  StreamSessionResponse,
  StreamHealthTelemetry,
} from '../types';

export interface CameraListParams {
  page?: number;
  page_size?: number;
  department_id?: string;
  district?: string;
  status?: string;
  search?: string;
}

export const camerasApi = {
  list: (params: CameraListParams = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.append('page', String(params.page));
    if (params.page_size) query.append('page_size', String(params.page_size));
    if (params.department_id) query.append('department_id', params.department_id);
    if (params.district) query.append('district', params.district);
    if (params.status) query.append('status', params.status);
    if (params.search) query.append('search', params.search);

    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiClient<PaginatedResponse<Camera>>(`/cameras${qs}`);
  },

  getById: (id: string) => apiClient<ApiResponse<Camera>>(`/cameras/${id}`),

  create: (data: any) =>
    apiClient<ApiResponse<Camera>>('/cameras', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: any) =>
    apiClient<ApiResponse<Camera>>(`/cameras/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    apiClient<ApiResponse<{ message: string }>>(`/cameras/${id}`, {
      method: 'DELETE',
    }),

  getCoverage: () => apiClient<ApiResponse<CameraCoverage>>('/cameras/coverage'),

  getNearby: (lat: number, lng: number, radiusMeters: number = 5000) =>
    apiClient<ApiResponse<Camera[]>>(
      `/cameras/nearby?latitude=${lat}&longitude=${lng}&radius_meters=${radiusMeters}`
    ),

  getBBox: (params: { min_lat: number; min_lon: number; max_lat: number; max_lon: number; district?: string; status?: string; limit?: number }) => {
    const q = new URLSearchParams({
      min_lat: String(params.min_lat),
      min_lon: String(params.min_lon),
      max_lat: String(params.max_lat),
      max_lon: String(params.max_lon),
    });
    if (params.district) q.append('district', params.district);
    if (params.status) q.append('status', params.status);
    if (params.limit) q.append('limit', String(params.limit));
    return apiClient<ApiResponse<any[]>>(`/cameras/bbox?${q.toString()}`);
  },

  getCorridor: (params: { start_lat: number; start_lon: number; end_lat: number; end_lon: number; buffer_meters?: number; limit?: number }) => {
    const q = new URLSearchParams({
      start_lat: String(params.start_lat),
      start_lon: String(params.start_lon),
      end_lat: String(params.end_lat),
      end_lon: String(params.end_lon),
    });
    if (params.buffer_meters) q.append('buffer_meters', String(params.buffer_meters));
    if (params.limit) q.append('limit', String(params.limit));
    return apiClient<ApiResponse<any[]>>(`/cameras/corridor?${q.toString()}`);
  },

  getCoverageGaps: (params: { district?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.district) q.append('district', params.district);
    const qs = q.toString() ? `?${q.toString()}` : '';
    return apiClient<ApiResponse<any>>(`/cameras/coverage-gaps${qs}`);
  },

  bulkImport: (rows: any[]) =>
    apiClient<ApiResponse<any>>('/cameras/bulk-import', {
      method: 'POST',
      body: JSON.stringify(rows),
    }),

  getStream: (cameraId: string, protocol: string = 'HLS') =>
    apiClient<ApiResponse<StreamSessionResponse>>(`/cameras/${cameraId}/stream?protocol=${protocol}`),

  getStreamHealth: (cameraId: string) =>
    apiClient<ApiResponse<StreamHealthTelemetry>>(`/cameras/${cameraId}/health`),

  syncExternalCameras: () =>
    apiClient<ApiResponse<{ synced_count: number; cameras: unknown[] }>>('/cameras/sync', {
      method: 'POST',
    }),

  getSentinelHealth: () =>
    apiClient<ApiResponse<{
      sentinel_connection: string;
      catalogue_state: string;
      base_url: string;
      total_discovered_cameras: number;
      live_cameras: number;
      offline_cameras: number;
      connecting_cameras: number;
      reconnecting_cameras: number;
      ai_active_cameras: number;
      last_sync: string | null;
      last_error: string | null;
      reconnect_attempt: number;
    }>>('/cameras/health/sentinel'),

  // Dynamic Sentinel Ingest Discovery (Official Sentinel Camera Grid HLS Feeds)
  fetchDirectCorp8Catalog: async (): Promise<Camera[]> => {
    const resolveAuthoritativeCameraId = (c: any, idx: number): string => {
      const rawId = String(c.id || c.camera_id || c.camera_code || '').trim().toLowerCase();
      if (/^cam\d+$/.test(rawId)) {
        return rawId;
      }
      const m = rawId.match(/^cam-(\d+)$/);
      if (m) {
        return `cam${m[1].padStart(2, '0')}`;
      }
      if (/^\d+$/.test(rawId)) {
        return `cam${rawId.padStart(2, '0')}`;
      }
      return rawId || `cam${String(idx + 1).padStart(2, '0')}`;
    };

    try {
      const sampleRes = await fetch('/api/sample-cameras');
      if (sampleRes.ok) {
        const payload = await sampleRes.json();
        const rawCams = Array.isArray(payload) ? payload : (payload.cameras || payload.data?.cameras || []);
        if (rawCams && rawCams.length > 0) {
          return rawCams.map((c: any, idx: number) => {
            const streamId = resolveAuthoritativeCameraId(c, idx);
            const camCode = c.camera_code || `CAM-${streamId.replace(/\D/g, '').padStart(3, '0')}`;
            const hlsUrl = `https://cctv.corp8.cloud/${streamId}/index.m3u8`;
            return {
              id: streamId,
              sample_id: streamId,
              camera_code: camCode,
              name: c.name || `Camera ${camCode}`,
              district: c.district || 'Ahmedabad',
              city: c.city || c.district || 'Ahmedabad',
              state: c.state || 'Gujarat',
              status: c.status || 'ONLINE',
              connectivity_status: c.status || 'ONLINE',
              camera_type: c.camera_type || 'ANPR',
              ownership: 'Gujarat Police',
              fps: c.fps || 25,
              resolution: c.resolution || '1080p',
              latitude: Number(c.latitude) || 23.0583,
              longitude: Number(c.longitude) || 72.5833,
              road_name: c.road_name || c.street_name || 'Gujarat Corridor',
              street_name: c.street_name || c.road_name || 'Gujarat Corridor',
              police_station: c.police_station || 'Gujarat Police Station',
              direction: c.direction || 'North',
              heading: typeof c.heading === 'number' ? c.heading : 0.0,
              field_of_view: typeof c.field_of_view === 'number' ? c.field_of_view : 85.0,
              coverage_distance: typeof c.coverage_distance === 'number' ? c.coverage_distance : 180.0,
              coverage_polygon: c.coverage_polygon || null,
              has_valid_location: c.has_valid_location !== false,
              streams: [
                {
                  id: `stream_${streamId}`,
                  camera_id: streamId,
                  protocol: 'HLS' as const,
                  stream_url: hlsUrl,
                  resolution: '1080p',
                  fps: 25,
                  is_active: true,
                },
              ],
            };
          });
        }
      }
    } catch {
      // Fallback handled smoothly by backend fetch
    }

    try {
      const res = await apiClient<PaginatedResponse<Camera>>('/cameras?page_size=50');
      if (res && res.data && res.data.length > 0) {
        return res.data.map((c: Camera, idx: number) => {
          const streamId = resolveAuthoritativeCameraId(c, idx);
          const camCode = c.camera_code || `CAM-${streamId.replace(/\D/g, '').padStart(3, '0')}`;
          const hlsUrl = `https://cctv.corp8.cloud/${streamId}/index.m3u8`;
          return {
            ...c,
            id: streamId,
            sample_id: streamId,
            camera_code: camCode,
            status: c.status || 'ONLINE',
            connectivity_status: c.status || 'ONLINE',
            streams: [
              {
                id: `stream_${streamId}`,
                camera_id: streamId,
                protocol: 'HLS' as const,
                stream_url: hlsUrl,
                resolution: '1080p',
                fps: 25,
                codec: 'H264',
                is_primary: true,
                is_active: true,
              },
            ],
          };
        });
      }
    } catch {
      // Backend request fallback
    }

    return [];
  },
};
