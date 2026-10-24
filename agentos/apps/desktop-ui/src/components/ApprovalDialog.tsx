import React from 'react';
import { TaskStep } from '../lib/types';
import { AlertTriangle, ShieldCheck, XCircle, StopCircle } from 'lucide-react';

interface Props {
  isOpen: boolean;
  taskId: string;
  step: TaskStep | null;
  onApprove: () => void;
  onReject: () => void;
  onCancelTask: () => void;
  loading?: boolean;
}

export const ApprovalDialog: React.FC<Props> = ({
  isOpen,
  taskId,
  step,
  onApprove,
  onReject,
  onCancelTask,
  loading = false,
}) => {
  if (!isOpen || !step) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="approval-title"
        className="w-full max-w-lg bg-dark-900 border border-amber-600/50 rounded-xl shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="bg-amber-950/40 border-b border-amber-800/40 px-6 py-4 flex items-center gap-3">
          <div className="p-2 bg-amber-500/20 text-amber-400 rounded-lg">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h3 id="approval-title" className="text-base font-semibold text-amber-200">
              Action Approval Required
            </h3>
            <p className="text-xs text-amber-300/80">
              AgentOS paused for your consent before executing a sensitive desktop action.
            </p>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4 text-sm text-slate-300">
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Reason for confirmation:
            </span>
            <p className="mt-1 text-slate-200 font-medium bg-dark-950 p-3 rounded-lg border border-dark-800">
              {step.approval_reason || 'This operation modifies system state or files.'}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="bg-dark-950 p-3 rounded-lg border border-dark-800">
              <span className="text-slate-500 block">Proposed Tool:</span>
              <span className="font-mono text-blue-400 font-medium text-sm mt-0.5 block">
                {step.tool}
              </span>
            </div>
            <div className="bg-dark-950 p-3 rounded-lg border border-dark-800">
              <span className="text-slate-500 block">Step ID:</span>
              <span className="font-mono text-slate-300 font-medium text-sm mt-0.5 block">
                Step #{step.step_id}
              </span>
            </div>
          </div>

          {step.arguments && Object.keys(step.arguments).length > 0 && (
            <div>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Arguments:
              </span>
              <pre className="mt-1 p-3 bg-dark-950 rounded-lg border border-dark-800 text-xs font-mono text-slate-300 overflow-x-auto max-h-36">
                {JSON.stringify(step.arguments, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="bg-dark-950 px-6 py-4 border-t border-dark-800 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={onCancelTask}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-rose-400 hover:text-rose-300 hover:bg-rose-950/30 rounded-lg border border-transparent hover:border-rose-900 transition-colors"
          >
            <StopCircle className="w-4 h-4" />
            Cancel Entire Task
          </button>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={onReject}
              disabled={loading}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-slate-300 hover:text-white bg-dark-800 hover:bg-dark-700 rounded-lg border border-dark-700 transition-colors"
            >
              <XCircle className="w-4 h-4" />
              Reject Action
            </button>
            <button
              type="button"
              onClick={onApprove}
              disabled={loading}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg shadow-lg shadow-emerald-900/30 transition-colors"
            >
              <ShieldCheck className="w-4 h-4" />
              Approve Once
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
