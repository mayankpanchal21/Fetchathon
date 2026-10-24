export interface TaskStep {
  step_id: number;
  tool: string;
  arguments: Record<string, any>;
  requires_approval: boolean;
  approval_reason?: string | null;
  status: 'pending' | 'waiting_approval' | 'running' | 'completed' | 'failed' | 'rejected' | 'skipped';
  result?: any;
  error?: string | null;
  verification_notes?: string | null;
}

export interface TaskVerification {
  verified: boolean;
  message: string;
  total_duration_sec?: number;
}

export interface TaskLog {
  timestamp: string;
  level: 'info' | 'warning' | 'error';
  step_id?: number | null;
  message: string;
}

export interface TaskPlan {
  task_id: string;
  user_request: string;
  goal: string;
  requires_approval: boolean;
  current_step_index: number;
  status: 'planned' | 'waiting_approval' | 'running' | 'completed' | 'failed' | 'cancelled';
  steps: TaskStep[];
  logs: TaskLog[];
  created_at: string;
  updated_at: string;
  verification_result?: TaskVerification | null;
  error_details?: string | null;
  planner_source?: string;
}

export interface DesktopStatus {
  operating_system: string;
  platform_details: string;
  architecture: string;
  backend_connected: boolean;
  screen_permission: string;
  voice_engine: string;
  asi1_configured: boolean;
  asi1_model: string;
  allowed_workspace: string;
  fetch_agent_paired: boolean;
  mode: 'live_asi1' | 'local_demo_mode';
  active_task_count: number;
  voice_info?: {
    configured_engine: string;
    model_size: string;
    faster_whisper_available: boolean;
    browser_speech_fallback_supported: boolean;
    notes: string;
  };
}

export interface ScreenPreview {
  saved_path: string;
  filename: string;
  width: number;
  height: number;
  base64_preview: string;
  captured_at: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent' | 'system';
  text: string;
  timestamp: string;
  task?: TaskPlan;
}
