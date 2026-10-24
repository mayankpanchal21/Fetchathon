import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, TaskPlan } from '../lib/types';
import { VoiceButton } from './VoiceButton';
import { Send, StopCircle, Bot, User, Sparkles, Terminal, Globe, Camera, FolderPlus, CheckCircle2 } from 'lucide-react';

interface Props {
  messages: ChatMessage[];
  activeTask: TaskPlan | null;
  onSendCommand: (cmd: string) => void;
  onCancelActiveTask: () => void;
  loading: boolean;
}

const EXAMPLE_PROMPTS = [
  { label: 'Visit Website', text: 'Open Chrome and visit example.com.', icon: Globe },
  { label: 'Capture Screen', text: 'Take a screenshot and explain what is on my screen.', icon: Camera },
  { label: 'Create Folder', text: 'Create a folder called HackathonDemo in my Documents directory.', icon: FolderPlus },
  { label: 'Run Tests', text: 'Open Terminal and run the tests in my selected project.', icon: Terminal },
];

export const ChatPanel: React.FC<Props> = ({
  messages,
  activeTask,
  onSendCommand,
  onCancelActiveTask,
  loading,
}) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, activeTask]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSendCommand(input.trim());
    setInput('');
  };

  const handleVoiceTranscript = (transcript: string) => {
    setInput(transcript);
  };

  const isTaskRunning = activeTask && (activeTask.status === 'running' || activeTask.status === 'waiting_approval');

  return (
    <div className="flex-1 flex flex-col h-full bg-dark-950 border-r border-dark-800">
      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
            <div className="w-12 h-12 rounded-2xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-brand-primary mb-3">
              <Sparkles className="w-6 h-6" />
            </div>
            <h3 className="text-base font-semibold text-slate-200">
              AgentOS Desktop Operator
            </h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm">
              You speak. Your computer acts. Enter a command or click an example below to begin automation.
            </p>

            {/* Quick Example Chips */}
            <div className="mt-6 grid grid-cols-2 gap-2 max-w-md w-full">
              {EXAMPLE_PROMPTS.map((p, i) => {
                const Icon = p.icon;
                return (
                  <button
                    key={i}
                    onClick={() => onSendCommand(p.text)}
                    className="p-2.5 text-left bg-dark-900 hover:bg-dark-850 border border-dark-800 hover:border-dark-700 rounded-lg text-xs text-slate-300 transition-all flex items-start gap-2"
                  >
                    <Icon className="w-4 h-4 text-brand-primary mt-0.5 shrink-0" />
                    <div>
                      <span className="font-semibold block text-slate-200">{p.label}</span>
                      <span className="text-[11px] text-slate-500 line-clamp-1">{p.text}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 text-xs ${
                msg.sender === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {msg.sender !== 'user' && (
                <div className="w-7 h-7 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 shrink-0 mt-0.5">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-[80%] rounded-xl px-4 py-2.5 leading-relaxed ${
                  msg.sender === 'user'
                    ? 'bg-brand-primary text-white font-medium rounded-tr-none'
                    : 'bg-dark-900 border border-dark-800 text-slate-200 rounded-tl-none shadow-sm'
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.text}</div>
                <div
                  className={`mt-1 text-[10px] ${
                    msg.sender === 'user' ? 'text-blue-200/70' : 'text-slate-500'
                  }`}
                >
                  {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </div>
              </div>

              {msg.sender === 'user' && (
                <div className="w-7 h-7 rounded-lg bg-dark-800 border border-dark-700 flex items-center justify-center text-slate-300 shrink-0 mt-0.5">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Console */}
      <div className="p-3 bg-dark-900 border-t border-dark-800">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          {/* Microphone Voice Button */}
          <VoiceButton onTranscript={handleVoiceTranscript} disabled={loading} />

          {/* Text Input */}
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              loading
                ? 'Planning task with Fetch.ai ASI:One...'
                : 'Enter a desktop command (e.g. "Open Chrome and visit example.com")...'
            }
            disabled={loading}
            className="flex-1 bg-dark-950 border border-dark-750 focus:border-brand-primary rounded-lg px-4 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none transition-colors"
          />

          {/* Send Button */}
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="px-4 py-2 bg-brand-primary hover:bg-blue-600 disabled:opacity-50 disabled:pointer-events-none text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all shadow-md shadow-blue-950/50"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Send</span>
          </button>

          {/* Emergency Stop Button */}
          {isTaskRunning && (
            <button
              type="button"
              onClick={onCancelActiveTask}
              title="Stop task immediately (Emergency stop)"
              className="px-3 py-2 bg-rose-600/20 hover:bg-rose-600 text-rose-300 hover:text-white border border-rose-500/50 text-xs font-medium rounded-lg flex items-center gap-1.5 transition-all animate-pulse"
            >
              <StopCircle className="w-3.5 h-3.5" />
              <span>Stop Task</span>
            </button>
          )}
        </form>

        <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500 px-1">
          <span>You speak. Your computer acts.</span>
          <span>Security Sandbox Active: Allowed Workspace Only</span>
        </div>
      </div>
    </div>
  );
};
