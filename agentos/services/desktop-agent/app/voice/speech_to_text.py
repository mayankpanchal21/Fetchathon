import io
import os
import tempfile
import logging
from typing import Dict, Any, Optional
from ..config import settings

logger = logging.getLogger("agentos.voice")

_whisper_model = None


def get_voice_engine_info() -> Dict[str, Any]:
    has_faster_whisper = False
    try:
        import faster_whisper
        has_faster_whisper = True
    except ImportError:
        pass

    return {
        "configured_engine": settings.stt_engine,
        "model_size": settings.whisper_model_size,
        "faster_whisper_available": has_faster_whisper,
        "browser_speech_fallback_supported": True,
        "notes": "Browser native Web Speech API works directly with zero downloads. faster-whisper can be installed via 'pip install faster-whisper' for local offline speech-to-text."
    }


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    try:
        from faster_whisper import WhisperModel
        logger.info(f"Loading faster-whisper model: {settings.whisper_model_size} (CPU/device auto)")
        # Use cpu with int8 quantization for lightweight desktop usage
        _whisper_model = WhisperModel(settings.whisper_model_size, device="cpu", compute_type="int8")
        return _whisper_model
    except ImportError:
        raise RuntimeError("faster-whisper package is not installed. Use browser native speech fallback or install faster-whisper.")
    except Exception as e:
        logger.error(f"Failed to initialize faster-whisper: {e}")
        raise RuntimeError(f"Whisper initialization error: {e}")


def transcribe_audio_file(audio_bytes: bytes, filename: str = "voice_input.wav") -> Dict[str, Any]:
    """
    Transcribe uploaded audio file using local faster-whisper model.
    Falls back with detailed actionable diagnostics if whisper is unavailable.
    """
    info = get_voice_engine_info()
    if not info["faster_whisper_available"]:
        return {
            "transcript": "",
            "engine": "browser_fallback_recommended",
            "success": False,
            "error": "faster-whisper not installed on backend. Please use the browser microphone button with Web Speech API or install faster-whisper."
        }

    try:
        model = _get_whisper_model()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            segments, segment_info = model.transcribe(tmp_path, beam_size=5)
            transcript_text = " ".join([seg.text.strip() for seg in segments]).strip()
            return {
                "transcript": transcript_text,
                "language": segment_info.language,
                "language_probability": segment_info.language_probability,
                "engine": f"faster-whisper ({settings.whisper_model_size})",
                "success": True
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return {
            "transcript": "",
            "engine": "faster-whisper",
            "success": False,
            "error": str(e)
        }
