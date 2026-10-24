import React from 'react';
import { DesktopStatus as DesktopStatusType } from '../lib/types';
import { Monitor, Cpu, Mic, ShieldAlert, CheckCircle2, Radio, Server, Bot } from 'lucide-react';

interface Props {
  status: DesktopStatusType | null;
  loading: boolean;
  onRefresh: () => void;
}

export const DesktopStatus: React.FC<Props> = ({ status, loading, onRefresh }) => {
  const isConnected = status?.backend_connected ?? false;
  const isASI1 = status?.asi1_configured ?? false;

  return (
    <div className="bg-dark-900 border-b border-dark-800 px-5 py-2.5 flex items-center justify-between text-xs text-slate-300">
      <div className="flex items-center gap-5 flex-wrap">
        {/* Backend Connectivity */}
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            {isConnected && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            )}
            <span
              className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                isConnected ? 'bg-emerald-500' : 'bg-rose-500'
              }`}
            ></span>
          </span>
          <span className="font-medium text-slate-200">
            {isConnected ? 'Local Backend Online' : 'Backend Disconnected'}
          </span>
          <span className="text-slate-500 font-mono">127.0.0.1:8000</span>
        </div>

        {/* Operating System */}
        <div className="flex items-center gap-1.5 text-slate-400">
          <Monitor className="w-3.5 h-3.5 text-slate-400" />
          <span>OS:</span>
          <span className="text-slate-200 font-medium">
            {status?.operating_system || 'Detecting...'}
          </span>
          {status?.architecture && (
            <span className="text-slate-500 font-mono">({status.architecture})</span>
          )}
        </div>

        {/* Screen Permission */}
        <div className="flex items-center gap-1.5 text-slate-400">
          <ShieldAlert className="w-3.5 h-3.5 text-slate-400" />
          <span>Screen:</span>
          <span
            className={`font-medium ${
              status?.screen_permission === 'granted' || status?.screen_permission === 'accessible'
                ? 'text-emerald-400'
                : 'text-amber-400'
            }`}
          >
            {status?.screen_permission || 'Checking...'}
          </span>
        </div>

        {/* Voice Engine */}
        <div className="flex items-center gap-1.5 text-slate-400">
          <Mic className="w-3.5 h-3.5 text-slate-400" />
          <span>Voice:</span>
          <span className="text-slate-200 font-medium">
            {status?.voice_info?.faster_whisper_available
              ? `faster-whisper (${status.voice_info.model_size})`
              : 'Web Speech API (Native)'}
          </span>
        </div>

        {/* Fetch.ai Agentverse Status */}
        <div className="flex items-center gap-1.5 text-slate-400">
          <Bot className="w-3.5 h-3.5 text-indigo-400" />
          <span>Fetch.ai Agent:</span>
          <span className="text-indigo-300 font-medium flex items-center gap-1">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
            uAgents Chat Protocol (Port 8001)
          </span>
        </div>
      </div>

      {/* Model Mode Pill */}
      <div className="flex items-center gap-2">
        <span
          className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium border flex items-center gap-1.5 ${
            isASI1
              ? 'bg-blue-950/60 text-blue-300 border-blue-800/80'
              : 'bg-amber-950/40 text-amber-300 border-amber-800/60'
          }`}
        >
          <Cpu className="w-3 h-3" />
          {isASI1 ? `Fetch.ai ${status?.asi1_model || 'asi1'}` : 'Local Rule Planner (Demo)'}
        </span>

        <button
          onClick={onRefresh}
          disabled={loading}
          className="text-slate-400 hover:text-slate-200 transition-colors p-1 rounded hover:bg-dark-800"
          title="Refresh status"
        >
          <Radio className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>
    </div>
  );
};
