import React from 'react';
import { TaskPlan, TaskStep } from '../lib/types';
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  PauseCircle,
  Loader2,
  ChevronRight,
  Terminal,
  Globe,
  FileCode,
  Shield,
  Search,
  Monitor
} from 'lucide-react';

interface Props {
  task: TaskPlan | null;
  onSelectStep?: (step: TaskStep) => void;
}

export const TaskTimeline: React.FC<Props> = ({ task }) => {
  if (!task) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
        <Monitor className="w-12 h-12 mb-3 text-dark-700" />
        <p className="text-sm font-medium text-slate-400">No active execution</p>
        <p className="text-xs text-slate-600 mt-1 max-w-xs">
          Submit a command via text or microphone to observe structured planning and real-time execution.
        </p>
      </div>
    );
  }

  const getToolIcon = (tool: string) => {
    if (tool.startsWith('browser_')) return <Globe className="w-4 h-4 text-blue-400" />;
    if (tool.includes('command')) return <Terminal className="w-4 h-4 text-amber-400" />;
    if (tool.includes('file') || tool.includes('directory')) return <FileCode className="w-4 h-4 text-emerald-400" />;
    if (tool.includes('search')) return <Search className="w-4 h-4 text-purple-400" />;
    return <Monitor className="w-4 h-4 text-slate-400" />;
  };

  const getStatusBadge = (status: TaskStep['status']) => {
    switch (status) {
      case 'completed':
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium text-emerald-400 bg-emerald-950/40 border border-emerald-800/60 px-2 py-0.5 rounded-full">
            <CheckCircle2 className="w-3 h-3" />
            Verified
          </span>
        );
      case 'running':
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium text-blue-400 bg-blue-950/40 border border-blue-800/60 px-2 py-0.5 rounded-full animate-pulse">
            <Loader2 className="w-3 h-3 animate-spin" />
            Executing
          </span>
        );
      case 'waiting_approval':
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium text-amber-400 bg-amber-950/40 border border-amber-800/60 px-2 py-0.5 rounded-full animate-pulse">
            <PauseCircle className="w-3 h-3" />
            Awaiting Approval
          </span>
        );
      case 'failed':
      case 'rejected':
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium text-rose-400 bg-rose-950/40 border border-rose-800/60 px-2 py-0.5 rounded-full">
            <AlertCircle className="w-3 h-3" />
            {status}
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium text-slate-400 bg-dark-900 border border-dark-800 px-2 py-0.5 rounded-full">
            <Clock className="w-3 h-3" />
            Pending
          </span>
        );
    }
  };

  return (
    <div className="h-full flex flex-col bg-dark-900">
      {/* Task Header */}
      <div className="p-4 border-b border-dark-800 bg-dark-950/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-dark-800 text-slate-400">
              {task.task_id.slice(0, 8)}
            </span>
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                task.status === 'completed'
                  ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800'
                  : task.status === 'running'
                  ? 'bg-blue-950/60 text-blue-400 border border-blue-800'
                  : task.status === 'waiting_approval'
                  ? 'bg-amber-950/60 text-amber-400 border border-amber-800'
                  : 'bg-dark-800 text-slate-300 border border-dark-700'
              }`}
            >
              {task.status.toUpperCase()}
            </span>
          </div>
          {task.planner_source && (
            <span className="text-[11px] text-slate-400 font-mono truncate max-w-[220px]">
              {task.planner_source}
            </span>
          )}
        </div>

        <h4 className="text-sm font-semibold text-slate-100 mt-2 line-clamp-1">
          {task.goal}
        </h4>
        <p className="text-xs text-slate-400 mt-0.5 italic">
          "{task.user_request}"
        </p>

        {/* Progress bar */}
        <div className="mt-3">
          <div className="flex justify-between text-[11px] text-slate-400 mb-1">
            <span>Progress: {task.current_step_index + (task.status === 'completed' ? 1 : 0)} of {task.steps.length} steps</span>
            <span>
              {Math.round(
                ((task.current_step_index + (task.status === 'completed' ? 1 : 0)) / Math.max(task.steps.length, 1)) * 100
              )}%
            </span>
          </div>
          <div className="w-full bg-dark-800 h-1.5 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                task.status === 'failed' ? 'bg-rose-500' : 'bg-brand-primary'
              }`}
              style={{
                width: `${Math.min(
                  100,
                  ((task.current_step_index + (task.status === 'completed' ? 1 : 0)) / Math.max(task.steps.length, 1)) * 100
                )}%`,
              }}
            ></div>
          </div>
        </div>
      </div>

      {/* Steps List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {task.steps.map((step, idx) => (
          <div
            key={step.step_id}
            className={`p-3 rounded-lg border transition-all ${
              step.status === 'running'
                ? 'bg-dark-850 border-blue-600/60 shadow-lg shadow-blue-950/20'
                : step.status === 'waiting_approval'
                ? 'bg-amber-950/20 border-amber-600/50 shadow-lg shadow-amber-950/20'
                : step.status === 'completed'
                ? 'bg-dark-950 border-dark-800 hover:border-dark-700'
                : 'bg-dark-950/50 border-dark-850 opacity-60'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-dark-800 rounded-md">
                  {getToolIcon(step.tool)}
                </div>
                <div>
                  <span className="font-mono text-xs font-semibold text-slate-200">
                    {step.tool}
                  </span>
                  <span className="text-[10px] text-slate-500 ml-2">Step #{step.step_id}</span>
                </div>
              </div>
              {getStatusBadge(step.status)}
            </div>

            {/* Arguments preview */}
            {step.arguments && Object.keys(step.arguments).length > 0 && (
              <div className="mt-2 text-[11px] font-mono text-slate-400 bg-dark-900 p-2 rounded border border-dark-800/80 truncate">
                {Object.entries(step.arguments).map(([k, v]) => (
                  <span key={k} className="mr-3">
                    <span className="text-slate-500">{k}:</span>{' '}
                    <span className="text-slate-300">
                      {typeof v === 'string' ? `"${v}"` : JSON.stringify(v)}
                    </span>
                  </span>
                ))}
              </div>
            )}

            {/* Verification Note */}
            {step.verification_notes && (
              <div className="mt-2 flex items-start gap-1.5 text-[11px] text-emerald-300/90 bg-emerald-950/20 px-2 py-1 rounded border border-emerald-900/30">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <span>{step.verification_notes}</span>
              </div>
            )}

            {/* Step Error */}
            {step.error && (
              <div className="mt-2 text-[11px] text-rose-300 bg-rose-950/30 px-2 py-1 rounded border border-rose-900/40">
                Error: {step.error}
              </div>
            )}
          </div>
        ))}

        {/* Verification Report */}
        {task.verification_result && (
          <div className="mt-4 p-3 bg-emerald-950/30 border border-emerald-800/60 rounded-lg text-xs text-emerald-200">
            <div className="flex items-center gap-1.5 font-semibold text-emerald-300">
              <Shield className="w-4 h-4" />
              <span>Final Task Verification:</span>
            </div>
            <p className="mt-1 text-emerald-200/90">
              {task.verification_result.message}
            </p>
            {task.verification_result.total_duration_sec !== undefined && (
              <p className="mt-0.5 text-[11px] text-emerald-400/80">
                Total duration: {task.verification_result.total_duration_sec}s
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
