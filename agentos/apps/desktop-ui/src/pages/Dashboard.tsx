import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api, getDeviceToken, setDeviceToken } from '../lib/api';
import { TaskPlan, DesktopStatus as DesktopStatusType, ChatMessage } from '../lib/types';
import { DesktopStatus } from '../components/DesktopStatus';
import { ChatPanel } from '../components/ChatPanel';
import { TaskTimeline } from '../components/TaskTimeline';
import { ApprovalDialog } from '../components/ApprovalDialog';
import {
  Cpu,
  History,
  Settings,
  Plus,
  Bot,
  ExternalLink,
  Shield,
  Layers,
  Key,
  FolderLock,
  RefreshCw
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  const [status, setStatus] = useState<DesktopStatusType | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [tasks, setTasks] = useState<TaskPlan[]>([]);
  const [activeTask, setActiveTask] = useState<TaskPlan | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [tokenInput, setTokenInput] = useState(getDeviceToken());
  const [viewHistoryModal, setViewHistoryModal] = useState(false);

  const activePollingRef = useRef<number | null>(null);

  // Load status and recent tasks
  const refreshStatus = useCallback(async () => {
    setStatusLoading(true);
    try {
      const s = await api.getStatus();
      setStatus(s);
    } catch (e) {
      console.error('Failed to load status:', e);
      setStatus(null);
    } finally {
      setStatusLoading(false);
    }
  }, []);

  const loadTasks = useCallback(async () => {
    try {
      const list = await api.getTasks();
      setTasks(list);
    } catch (e) {
      console.error('Failed to load tasks:', e);
    }
  }, []);

  useEffect(() => {
    refreshStatus();
    loadTasks();
    const interval = window.setInterval(refreshStatus, 10000);
    return () => window.clearInterval(interval);
  }, [refreshStatus, loadTasks]);

  // Polling active task status
  useEffect(() => {
    if (!activeTask || activeTask.status === 'completed' || activeTask.status === 'failed' || activeTask.status === 'cancelled') {
      if (activePollingRef.current) {
        window.clearInterval(activePollingRef.current);
        activePollingRef.current = null;
      }
      return;
    }

    const poll = async () => {
      try {
        const updated = await api.getTask(activeTask.task_id);
        setActiveTask(updated);

        // If completed or failed, update tasks list
        if (updated.status === 'completed' || updated.status === 'failed' || updated.status === 'cancelled') {
          loadTasks();
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              sender: 'agent',
              text:
                updated.status === 'completed'
                  ? `✅ Goal achieved: ${updated.goal}\n${updated.verification_result?.message || 'All steps verified successfully.'}`
                  : `⚠️ Task ${updated.status}: ${updated.error_details || 'Task ended.'}`,
              timestamp: new Date().toISOString(),
              task: updated,
            },
          ]);
        }
      } catch (e) {
        console.error('Error polling task:', e);
      }
    };

    activePollingRef.current = window.setInterval(poll, 1000);
    return () => {
      if (activePollingRef.current) {
        window.clearInterval(activePollingRef.current);
        activePollingRef.current = null;
      }
    };
  }, [activeTask, loadTasks]);

  // Submit user command
  const handleSendCommand = async (command: string) => {
    setLoading(true);
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: command,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const plan = await api.submitTask(command);
      setActiveTask(plan);
      loadTasks();

      const agentMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'agent',
        text: `Plan created with ${plan.steps.length} steps (${plan.planner_source || 'ASI:One'}):\n${plan.steps
          .map((s) => `• Step ${s.step_id}: ${s.tool}`)
          .join('\n')}`,
        timestamp: new Date().toISOString(),
        task: plan,
      };
      setMessages((prev) => [...prev, agentMsg]);
    } catch (e: any) {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'system',
        text: `Error submitting task: ${e.message}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  // Approval handlers
  const handleApproveStep = async () => {
    if (!activeTask) return;
    try {
      await api.approveStep(activeTask.task_id);
      const updated = await api.getTask(activeTask.task_id);
      setActiveTask(updated);
    } catch (e: any) {
      alert(`Approval error: ${e.message}`);
    }
  };

  const handleRejectStep = async () => {
    if (!activeTask) return;
    try {
      await api.rejectStep(activeTask.task_id, undefined, 'User declined authorization');
      const updated = await api.getTask(activeTask.task_id);
      setActiveTask(updated);
    } catch (e: any) {
      alert(`Reject error: ${e.message}`);
    }
  };

  const handleCancelActiveTask = async () => {
    if (!activeTask) return;
    try {
      await api.cancelTask(activeTask.task_id);
      const updated = await api.getTask(activeTask.task_id);
      setActiveTask(updated);
      loadTasks();
    } catch (e: any) {
      alert(`Cancel error: ${e.message}`);
    }
  };

  const pendingStep =
    activeTask?.status === 'waiting_approval' && activeTask.steps
      ? activeTask.steps[activeTask.current_step_index] || null
      : null;

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-dark-950 text-slate-100">
      {/* 1. Sidebar */}
      <aside className="w-64 bg-dark-900 border-r border-dark-800 flex flex-col justify-between shrink-0">
        <div>
          {/* Logo */}
          <div className="p-4 border-b border-dark-800 flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold shadow-lg shadow-blue-900/40">
              ⚡
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-sm tracking-tight text-white">AgentOS</span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 bg-blue-950 text-blue-300 rounded border border-blue-800/80">
                  v1.0
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Fetch.ai Desktop Operator</p>
            </div>
          </div>

          {/* New Task Action */}
          <div className="p-3">
            <button
              onClick={() => {
                setActiveTask(null);
                setMessages([]);
              }}
              className="w-full py-2 px-3 bg-brand-primary hover:bg-blue-600 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-2 shadow-sm transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>New Task Session</span>
            </button>
          </div>

          {/* Recent Tasks List */}
          <div className="px-3 py-2">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-400 px-2 mb-2">
              <span className="flex items-center gap-1.5">
                <History className="w-3.5 h-3.5" />
                <span>Recent Tasks</span>
              </span>
              <button
                onClick={() => setViewHistoryModal(true)}
                className="text-[11px] text-blue-400 hover:text-blue-300"
              >
                View all ({tasks.length})
              </button>
            </div>

            <div className="space-y-1 overflow-y-auto max-h-[300px]">
              {tasks.length === 0 ? (
                <div className="p-3 text-[11px] text-slate-500 text-center italic">
                  No prior task history
                </div>
              ) : (
                tasks.slice(0, 8).map((t) => (
                  <button
                    key={t.task_id}
                    onClick={() => setActiveTask(t)}
                    className={`w-full text-left p-2 rounded-lg text-xs transition-colors flex flex-col gap-0.5 ${
                      activeTask?.task_id === t.task_id
                        ? 'bg-dark-800 text-slate-200 border border-dark-700'
                        : 'hover:bg-dark-850 text-slate-400 border border-transparent'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-slate-300 truncate max-w-[130px]">
                        {t.goal}
                      </span>
                      <span
                        className={`text-[9px] px-1.5 py-0.2 rounded font-mono ${
                          t.status === 'completed'
                            ? 'text-emerald-400 bg-emerald-950/60'
                            : t.status === 'failed'
                            ? 'text-rose-400 bg-rose-950/60'
                            : t.status === 'cancelled'
                            ? 'text-slate-400 bg-dark-800'
                            : 'text-amber-400 bg-amber-950/60'
                        }`}
                      >
                        {t.status}
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Fetch.ai Agent Connection Card */}
        <div className="p-3 border-t border-dark-800 space-y-2">
          <div className="bg-dark-950 p-2.5 rounded-lg border border-dark-800 text-xs">
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold text-indigo-300 flex items-center gap-1.5">
                <Bot className="w-3.5 h-3.5" />
                Fetch.ai uAgent
              </span>
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
            </div>
            <p className="text-[11px] text-slate-400">
              Protocol: <span className="font-mono text-slate-300">AgentChatProtocol</span>
            </p>
            <p className="text-[11px] text-slate-400">
              Port: <span className="font-mono text-slate-300">8001 (Loopback)</span>
            </p>
          </div>

          <button
            onClick={() => setSettingsOpen(true)}
            className="w-full py-1.5 px-3 bg-dark-800 hover:bg-dark-750 text-slate-300 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-colors"
          >
            <Settings className="w-3.5 h-3.5" />
            <span>Settings & Security</span>
          </button>
        </div>
      </aside>

      {/* 2. Main Workspace */}
      <main className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Status Bar */}
        <DesktopStatus
          status={status}
          loading={statusLoading}
          onRefresh={refreshStatus}
        />

        {/* Content Split Pane */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left: Chat & Command Panel */}
          <div className="w-1/2 flex flex-col h-full">
            <ChatPanel
              messages={messages}
              activeTask={activeTask}
              onSendCommand={handleSendCommand}
              onCancelActiveTask={handleCancelActiveTask}
              loading={loading}
            />
          </div>

          {/* Right: Real-time Task Timeline & Observation */}
          <div className="w-1/2 flex flex-col h-full bg-dark-900 border-l border-dark-800 overflow-hidden">
            <TaskTimeline task={activeTask} />
          </div>
        </div>
      </main>

      {/* 3. Approval Modal */}
      <ApprovalDialog
        isOpen={Boolean(pendingStep)}
        taskId={activeTask?.task_id || ''}
        step={pendingStep}
        onApprove={handleApproveStep}
        onReject={handleRejectStep}
        onCancelTask={handleCancelActiveTask}
      />

      {/* 4. Settings Modal */}
      {settingsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-md bg-dark-900 border border-dark-700 rounded-xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-dark-800 pb-3">
              <h3 className="font-semibold text-sm text-white flex items-center gap-2">
                <Settings className="w-4 h-4 text-brand-primary" />
                AgentOS Configuration
              </h3>
              <button
                onClick={() => setSettingsOpen(false)}
                className="text-slate-400 hover:text-white text-xs"
              >
                Close
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Local Device Pairing Token</label>
                <div className="flex gap-2">
                  <input
                    type="password"
                    value={tokenInput}
                    onChange={(e) => setTokenInput(e.target.value)}
                    className="flex-1 bg-dark-950 border border-dark-700 rounded-lg px-3 py-1.5 font-mono text-slate-200"
                  />
                  <button
                    onClick={() => {
                      setDeviceToken(tokenInput);
                      alert('Device pairing token saved.');
                    }}
                    className="px-3 py-1.5 bg-brand-primary hover:bg-blue-600 text-white rounded-lg font-medium"
                  >
                    Save
                  </button>
                </div>
              </div>

              <div className="bg-dark-950 p-3 rounded-lg border border-dark-800 space-y-1">
                <span className="text-slate-400 font-semibold block">Fetch.ai ASI:One LLM Status:</span>
                <p className="text-slate-300">
                  Model: <span className="font-mono text-blue-400">{status?.asi1_model || 'asi1'}</span>
                </p>
                <p className="text-slate-300">
                  Endpoint: <span className="font-mono text-blue-400">https://api.asi1.ai/v1</span>
                </p>
                <p className="text-slate-400 text-[11px] mt-1">
                  {status?.asi1_configured
                    ? 'ASI1 API key active. Live reasoning enabled.'
                    : 'No API key set. Running in deterministic Local Demo Mode.'}
                </p>
              </div>

              <div className="bg-dark-950 p-3 rounded-lg border border-dark-800 space-y-1">
                <span className="text-slate-400 font-semibold block">Filesystem Sandbox:</span>
                <p className="text-slate-400 font-mono text-[11px] break-all">
                  {status?.allowed_workspace || './workspace'}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5. Full History Modal */}
      {viewHistoryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-2xl bg-dark-900 border border-dark-700 rounded-xl shadow-2xl p-6 flex flex-col max-h-[85vh]">
            <div className="flex items-center justify-between border-b border-dark-800 pb-3 mb-4">
              <h3 className="font-semibold text-sm text-white flex items-center gap-2">
                <History className="w-4 h-4 text-brand-primary" />
                Persistent Task Audit History ({tasks.length})
              </h3>
              <button
                onClick={() => setViewHistoryModal(false)}
                className="text-slate-400 hover:text-white text-xs"
              >
                Close
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 pr-1">
              {tasks.map((t) => (
                <div
                  key={t.task_id}
                  onClick={() => {
                    setActiveTask(t);
                    setViewHistoryModal(false);
                  }}
                  className="p-3 bg-dark-950 hover:bg-dark-850 border border-dark-800 rounded-lg cursor-pointer transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-xs text-slate-200">{t.goal}</span>
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded font-medium ${
                        t.status === 'completed'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : t.status === 'failed'
                          ? 'bg-rose-950 text-rose-400 border border-rose-800'
                          : 'bg-dark-800 text-slate-300'
                      }`}
                    >
                      {t.status}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 italic">"{t.user_request}"</p>
                  <div className="mt-2 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                    <span>Steps: {t.steps.length}</span>
                    <span>Created: {new Date(t.created_at).toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
