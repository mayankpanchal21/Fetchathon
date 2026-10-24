import { DesktopStatus, TaskPlan, ScreenPreview } from './types';

const API_BASE_URL = 'http://127.0.0.1:8000';
let deviceToken = localStorage.getItem('agentos_token') || 'agentos-local-dev-token';

export const setDeviceToken = (token: string) => {
  deviceToken = token;
  localStorage.setItem('agentos_token', token);
};

export const getDeviceToken = () => deviceToken;

const headers = () => ({
  'Content-Type': 'application/json',
  'X-Device-Token': deviceToken,
});

export const api = {
  async getStatus(): Promise<DesktopStatus> {
    const res = await fetch(`${API_BASE_URL}/api/v1/desktop/status`, {
      headers: headers(),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch desktop status`);
    return res.json();
  },

  async getScreen(): Promise<ScreenPreview> {
    const res = await fetch(`${API_BASE_URL}/api/v1/desktop/screen`, {
      headers: headers(),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to capture desktop screen`);
    return res.json();
  },

  async submitTask(request: string): Promise<TaskPlan> {
    const res = await fetch(`${API_BASE_URL}/api/v1/tasks`, {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({ request }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to submit task (HTTP ${res.status})`);
    }
    return res.json();
  },

  async getTask(taskId: string): Promise<TaskPlan> {
    const res = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}`, {
      headers: headers(),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Task not found`);
    return res.json();
  },

  async getTasks(): Promise<TaskPlan[]> {
    const res = await fetch(`${API_BASE_URL}/api/v1/tasks`, {
      headers: headers(),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch tasks`);
    return res.json();
  },

  async approveStep(taskId: string, stepId?: number): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}/approve`, {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({ step_id: stepId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to approve step');
    }
  },

  async rejectStep(taskId: string, stepId?: number, reason?: string): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}/reject`, {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({ step_id: stepId, reason }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to reject step');
    }
  },

  async cancelTask(taskId: string): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}/cancel`, {
      method: 'POST',
      headers: headers(),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to cancel task`);
  },

  async transcribeAudio(audioBlob: Blob): Promise<{ transcript: string; engine: string; success: boolean; error?: string }> {
    const formData = new FormData();
    formData.append('file', audioBlob, 'recording.wav');

    const res = await fetch(`${API_BASE_URL}/api/v1/voice/transcribe`, {
      method: 'POST',
      headers: {
        'X-Device-Token': deviceToken,
      },
      body: formData,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Audio transcription failed`);
    return res.json();
  }
};
