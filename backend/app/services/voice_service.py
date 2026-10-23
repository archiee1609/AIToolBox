import io
import math
import struct
import wave
import time
import hashlib
from typing import Dict, Any, Optional, Tuple, List
import asyncio

from app.core.logging import logger

# Time-to-live for identical audio payload caching (60 seconds)
_CACHE_TTL_SECONDS = 60.0
_TRANSCRIPTION_CACHE: Dict[str, Tuple[Dict[str, Any], float]] = {}


class VoiceService:
    """
    High-performance audio processing and speech-to-text service.
    Features:
      - Resampling any container format (WebM, OGG, MP3, WAV, FLAC) to 16kHz mono PCM.
      - Fast silence pre-screening to eliminate API round-trips for empty recordings.
      - Non-blocking asynchronous execution via thread pool.
      - SHA256 audio hash caching for instant re-queries.
      - Cross-platform support across Windows, macOS, and Linux.
    """

    def __init__(self):
        self._sr = None
        self._av = None
        self._initialized = False

    def _ensure_speech_recognition(self):
        """Lazy-loads speech_recognition to prevent startup latency."""
        if self._sr is None:
            try:
                import speech_recognition as sr
                self._sr = sr
            except ImportError:
                logger.warning("speech_recognition library not available. Install via pip install SpeechRecognition")
                self._sr = None
        return self._sr

    def _ensure_pyav(self):
        """Lazy-loads PyAV for universal audio decoding."""
        if self._av is None:
            try:
                import av
                self._av = av
            except ImportError:
                self._av = None
        return self._av

    def get_supported_engines(self) -> List[str]:
        """Returns list of active speech-to-text engines."""
        sr = self._ensure_speech_recognition()
        engines = ["web_speech"]  # Browser-native Web Speech API always supported
        if sr is not None:
            engines.append("google")
            # Check for local whisper
            try:
                import whisper  # noqa: F401
                engines.append("whisper")
            except ImportError:
                pass
        return engines

    def get_status(self) -> Dict[str, Any]:
        """Provides diagnostic health information for voice services."""
        engines = self.get_supported_engines()
        sr = self._ensure_speech_recognition()
        av = self._ensure_pyav()
        return {
            "available": len(engines) > 0,
            "engines": engines,
            "default_engine": "google" if "google" in engines else "web_speech",
            "microphone_supported": True,
            "web_speech_supported": True,
            "details": f"SpeechRecognition: {'Available' if sr else 'Missing'}, PyAV Decoder: {'Available' if av else 'Missing'}"
        }

    def convert_to_pcm_wav(self, audio_bytes: bytes) -> Tuple[bytes, float, float]:
        """
        Converts arbitrary audio bytes (WebM, OGG, MP3, WAV) into 16kHz mono 16-bit PCM WAV.
        Returns: (wav_bytes, duration_seconds, rms_energy)
        """
        if not audio_bytes:
            return b"", 0.0, 0.0

        # 1. Fast path: Check if already a standard PCM WAV
        if audio_bytes.startswith(b"RIFF") and b"WAVE" in audio_bytes[:16]:
            try:
                with wave.open(io.BytesIO(audio_bytes), "rb") as w:
                    rate = w.getframerate()
                    channels = w.getnchannels()
                    sampwidth = w.getsampwidth()
                    frames_count = w.getnframes()
                    duration = round(frames_count / float(rate), 3) if rate > 0 else 0.0

                    # If already 16kHz mono 16-bit PCM, compute RMS directly
                    if rate == 16000 and channels == 1 and sampwidth == 2:
                        frames = w.readframes(frames_count)
                        rms = self._compute_rms_from_pcm16(frames)
                        return audio_bytes, duration, rms
            except Exception:
                pass  # Fall through to universal decoder

        # 2. Universal decoding via PyAV
        av = self._ensure_pyav()
        if av is not None:
            try:
                inp = io.BytesIO(audio_bytes)
                container = av.open(inp)
                stream = next((s for s in container.streams if s.type == "audio"), None)
                if stream is not None:
                    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
                    out_buf = io.BytesIO()
                    raw_pcm = bytearray()

                    with wave.open(out_buf, "wb") as wav_out:
                        wav_out.setnchannels(1)
                        wav_out.setsampwidth(2)
                        wav_out.setframerate(16000)

                        for frame in container.decode(stream):
                            for resampled_frame in resampler.resample(frame):
                                pcm_chunk = resampled_frame.to_ndarray().tobytes()
                                raw_pcm.extend(pcm_chunk)
                                wav_out.writeframes(pcm_chunk)

                    wav_bytes = out_buf.getvalue()
                    total_samples = len(raw_pcm) // 2
                    duration = round(total_samples / 16000.0, 3)
                    rms = self._compute_rms_from_pcm16(bytes(raw_pcm))
                    return wav_bytes, duration, rms
            except Exception as e:
                logger.warning(f"PyAV audio decoding fallback failed: {e}")

        # 3. Fallback: return raw bytes with basic length check
        return audio_bytes, 0.0, 1000.0

    @staticmethod
    def _compute_rms_from_pcm16(pcm_data: bytes) -> float:
        """Calculates Root-Mean-Square (RMS) amplitude of 16-bit PCM samples."""
        if not pcm_data or len(pcm_data) < 2:
            return 0.0
        sample_count = len(pcm_data) // 2
        try:
            samples = struct.unpack(f"<{sample_count}h", pcm_data[:sample_count * 2])
            if not samples:
                return 0.0
            sum_squares = sum(s * s for s in samples)
            return round(math.sqrt(sum_squares / sample_count), 2)
        except Exception:
            return 0.0

    def _sync_transcribe(self, audio_bytes: bytes, language: str = "en-US", engine: str = "auto") -> Dict[str, Any]:
        """Synchronous speech recognition worker executed in a background thread."""
        sr = self._ensure_speech_recognition()
        if sr is None:
            return {
                "success": False,
                "text": "",
                "duration_seconds": 0.0,
                "engine": engine,
                "language": language,
                "is_silent": False,
                "error": "SpeechRecognition library is not installed in the backend environment."
            }

        # 1. Resample and measure audio
        wav_bytes, duration, rms = self.convert_to_pcm_wav(audio_bytes)

        # 2. Fast silence screening (< 180 RMS is silence or background ambient hum)
        if duration > 0.0 and rms < 180.0:
            return {
                "success": True,
                "text": "",
                "duration_seconds": duration,
                "engine": "silence_filter",
                "language": language,
                "is_silent": True,
                "error": None
            }

        # 3. Cache check based on audio hash
        audio_hash = hashlib.sha256(audio_bytes).hexdigest()
        now = time.time()
        if audio_hash in _TRANSCRIPTION_CACHE:
            cached_result, cached_ts = _TRANSCRIPTION_CACHE[audio_hash]
            if now - cached_ts < _CACHE_TTL_SECONDS:
                return {**cached_result, "cached": True}

        # 4. Perform speech recognition
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True

        try:
            with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
                audio_data = recognizer.record(source)

            # Choose engine
            target_engine = engine.lower()
            if target_engine in ["auto", "google"]:
                text = recognizer.recognize_google(audio_data, language=language)
                active_engine = "google"
            elif target_engine == "whisper":
                text = recognizer.recognize_whisper(audio_data, model="base")
                active_engine = "whisper"
            elif target_engine == "sphinx":
                text = recognizer.recognize_sphinx(audio_data)
                active_engine = "sphinx"
            else:
                text = recognizer.recognize_google(audio_data, language=language)
                active_engine = "google"

            result = {
                "success": True,
                "text": text.strip(),
                "duration_seconds": duration,
                "engine": active_engine,
                "language": language,
                "is_silent": False,
                "error": None
            }
            # Cache positive result
            _TRANSCRIPTION_CACHE[audio_hash] = (result, now)
            return result

        except sr.UnknownValueError:
            # Valid audio, but no intelligible speech detected (e.g. cough, noise, silent murmur)
            return {
                "success": True,
                "text": "",
                "duration_seconds": duration,
                "engine": engine,
                "language": language,
                "is_silent": True,
                "error": None
            }
        except sr.RequestError as re:
            return {
                "success": False,
                "text": "",
                "duration_seconds": duration,
                "engine": engine,
                "language": language,
                "is_silent": False,
                "error": f"Speech recognition service unreachable: {re}"
            }
        except Exception as e:
            return {
                "success": False,
                "text": "",
                "duration_seconds": duration,
                "engine": engine,
                "language": language,
                "is_silent": False,
                "error": str(e)
            }

    def synthesize_speech_wav(self, text: str) -> bytes:
        """Synthesizes text into offline PCM WAV audio bytes for audio chat responses."""
        if not text or not text.strip():
            return b""
        try:
            import pyttsx3
            import tempfile
            import re
            import os

            engine = pyttsx3.init()
            try:
                engine.setProperty("rate", 175)
            except Exception:
                pass

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                tmp_path = tf.name

            # Strip markdown formatting and code blocks for crisp speech
            clean = re.sub(r"```.*?```", "code block omitted", text, flags=re.DOTALL)
            clean = re.sub(r"[*#_`~>|\[\]()]", " ", clean)
            clean = " ".join(clean.split())[:1200]

            engine.save_to_file(clean, tmp_path)
            engine.runAndWait()

            with open(tmp_path, "rb") as f:
                wav_bytes = f.read()

            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

            return wav_bytes
        except Exception as e:
            logger.warning(f"Voice synthesis failed: {e}")
            return b""

    async def transcribe(self, audio_bytes: bytes, language: str = "en-US", engine: str = "auto") -> Dict[str, Any]:
        """Asynchronously transcribes audio without blocking the FastAPI event loop."""
        return await asyncio.to_thread(self._sync_transcribe, audio_bytes, language, engine)


voice_service = VoiceService()
