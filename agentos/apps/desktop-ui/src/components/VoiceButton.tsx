import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Loader2 } from 'lucide-react';
import { api } from '../lib/api';

interface Props {
  onTranscript: (transcript: string) => void;
  disabled?: boolean;
}

export const VoiceButton: React.FC<Props> = ({ onTranscript, disabled = false }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [permissionError, setPermissionError] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    // Check if browser native Web Speech API is supported
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsRecording(true);
        setPermissionError(null);
      };

      recognition.onresult = (event: any) => {
        const text = event.results[0][0].transcript;
        if (text && text.trim()) {
          onTranscript(text.trim());
        }
      };

      recognition.onerror = (event: any) => {
        console.warn('SpeechRecognition error:', event.error);
        if (event.error === 'not-allowed') {
          setPermissionError('Microphone permission was denied.');
        } else if (event.error !== 'no-speech') {
          setPermissionError(`Speech error: ${event.error}`);
        }
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (_) {}
      }
    };
  }, [onTranscript]);

  const toggleRecording = async () => {
    setPermissionError(null);

    // If currently recording, stop
    if (isRecording) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (_) {}
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
      setIsRecording(false);
      return;
    }

    // Try Web Speech API first
    if (recognitionRef.current) {
      try {
        recognitionRef.current.start();
        return;
      } catch (err) {
        console.warn('Could not start Web Speech, falling back to backend audio recording', err);
      }
    }

    // Fallback: MediaRecorder sending audio blob to backend /api/v1/voice/transcribe
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        if (audioBlob.size > 0) {
          setIsProcessing(true);
          try {
            const res = await api.transcribeAudio(audioBlob);
            if (res.transcript) {
              onTranscript(res.transcript);
            } else if (res.error) {
              setPermissionError(res.error);
            }
          } catch (e: any) {
            setPermissionError(e.message || 'Audio upload transcription failed.');
          } finally {
            setIsProcessing(false);
          }
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err: any) {
      setPermissionError('Microphone access denied. You can still type your command below.');
      setIsRecording(false);
    }
  };

  return (
    <div className="relative inline-flex items-center">
      <button
        type="button"
        onClick={toggleRecording}
        disabled={disabled || isProcessing}
        title={isRecording ? 'Click to stop recording' : 'Speak command via microphone'}
        className={`relative p-2.5 rounded-lg border transition-all flex items-center justify-center ${
          isRecording
            ? 'bg-rose-500/20 border-rose-500 text-rose-300 ring-2 ring-rose-500/40 animate-pulse'
            : isProcessing
            ? 'bg-dark-800 border-dark-700 text-slate-400 cursor-wait'
            : 'bg-dark-850 hover:bg-dark-800 border-dark-700 text-slate-300 hover:text-white'
        }`}
      >
        {isProcessing ? (
          <Loader2 className="w-4 h-4 animate-spin text-brand-primary" />
        ) : isRecording ? (
          <>
            <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500"></span>
            </span>
            <MicOff className="w-4 h-4" />
          </>
        ) : (
          <Mic className="w-4 h-4" />
        )}
      </button>

      {permissionError && (
        <div className="absolute bottom-full mb-2 left-0 w-64 bg-rose-950/90 border border-rose-800 text-rose-200 text-[11px] p-2 rounded-lg shadow-xl z-30">
          {permissionError}
        </div>
      )}
    </div>
  );
};
