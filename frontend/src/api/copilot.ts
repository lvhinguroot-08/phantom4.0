import { apiClient } from './client';
import { ApiResponse } from '../types';

export interface CopilotStatusStep {
  id: string;
  label: string;
  status: 'completed' | 'in_progress' | 'failed' | 'pending';
  details?: string;
}

export interface CopilotUIAction {
  action_type:
    | 'OPEN_CAMERA'
    | 'OPEN_MONITORING'
    | 'FOCUS_CAMERA'
    | 'FULLSCREEN_CAMERA'
    | 'OPEN_MAP'
    | 'OPEN_ANPR'
    | 'RUN_DETECTION'
    | 'NAVIGATE'
    | 'FILTER_CAMERAS';
  payload: Record<string, any>;
}

export interface CopilotDataCard {
  title: string;
  type: 'CAMERA' | 'ANPR' | 'ALERT' | 'STATS';
  details: Record<string, string | number>;
}

export interface CopilotChatResponseData {
  query: string;
  detected_language: string;
  intent: string;
  text_response: string;
  status_steps: CopilotStatusStep[];
  ui_actions: CopilotUIAction[];
  data_card?: CopilotDataCard;
  opened_camera?: {
    id: string;
    camera_code: string;
    name: string;
    district: string;
    status: string;
    hls_url: string;
    webrtc_url?: string;
    rtsp_url?: string;
    fps?: number;
    resolution?: string;
  };
  detection_summary?: {
    total_detections: number;
    persons_detected: number;
    vehicles_detected: number;
    plates_detected: number;
    persons: any[];
    vehicles: any[];
    plates: any[];
  };
  session_id: string;
  requires_confirmation: boolean;
  confirmation_payload?: Record<string, any>;
  timestamp: string;
}

export interface CopilotTool {
  name: string;
  description: string;
  category: string;
  security_level: 'READ_ONLY' | 'UI_ACTION' | 'SENSITIVE';
  parameters: Record<string, any>;
  requires_confirmation: boolean;
}

export const copilotApi = {
  chat: async (params: {
    query: string;
    session_id?: string;
    current_route?: string;
    selected_camera_id?: string;
  }): Promise<ApiResponse<CopilotChatResponseData>> => {
    return apiClient<ApiResponse<CopilotChatResponseData>>('/copilot/chat', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  getHealth: async (): Promise<{ success: boolean; health: Record<string, any> }> => {
    return apiClient<{ success: boolean; health: Record<string, any> }>('/copilot/health');
  },

  getContext: async (): Promise<{ success: boolean; context: Record<string, any> }> => {
    return apiClient<{ success: boolean; context: Record<string, any> }>('/copilot/context');
  },

  getTools: async (): Promise<{ success: boolean; total_tools: number; tools: CopilotTool[] }> => {
    return apiClient<{ success: boolean; total_tools: number; tools: CopilotTool[] }>('/copilot/tools');
  },

  confirm: async (params: {
    confirmation_token: string;
    action_type: string;
    payload?: Record<string, any>;
  }): Promise<ApiResponse<any>> => {
    return apiClient<ApiResponse<any>>('/copilot/confirm', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },
};
