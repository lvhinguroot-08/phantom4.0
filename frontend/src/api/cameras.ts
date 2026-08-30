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

  // Dynamic Sentinel Ingest Discovery (Zero hardcoded IDs, locations, or counts)
  fetchDirectCorp8Catalog: async (): Promise<Camera[]> => {
    try {
      const res = await apiClient<PaginatedResponse<Camera>>('/cameras?page_size=50');
      if (res && res.data && res.data.length > 0) {
        return res.data;
      }
    } catch {
      // Backend request fallback to direct catalogue probe
    }

    try {
      const directRes = await fetch('/api/v1/sentinel/status');
      if (directRes.ok) {
        const payload = await directRes.json();
        if (payload.data && payload.data.cameras) {
          return payload.data.cameras;
        }
      }
    } catch {
      // Fallback handled smoothly by UI
    }

    return [];
  },
};
