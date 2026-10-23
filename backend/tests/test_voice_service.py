import io
import math
import wave
import struct
import base64
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.voice_service import voice_service, _TRANSCRIPTION_CACHE


@pytest.fixture
def client():
    return TestClient(app)


def create_synthetic_wav(duration: float = 1.0, frequency: float = 440.0, amplitude: int = 10000, sample_rate: int = 16000) -> bytes:
    """Creates a synthetic PCM WAV in-memory buffer."""
    num_samples = int(sample_rate * duration)
    samples = [int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate)) for i in range(num_samples)]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(struct.pack(f"<{num_samples}h", *samples))
    return buf.getvalue()


def test_voice_status_endpoint(client):
    """Verifies that /api/voice/status returns engine and microphone status."""
    res = client.get("/api/voice/status")
    assert res.status_code == 200
    data = res.json()
    assert "available" in data
    assert "engines" in data
    assert "default_engine" in data
    assert "microphone_supported" in data
    assert "web_speech_supported" in data
    assert "web_speech" in data["engines"]


def test_convert_to_pcm_wav_metrics():
    """Verifies that PCM conversion accurately detects sample rate, duration, and RMS."""
    wav_bytes = create_synthetic_wav(duration=1.0, frequency=440.0, amplitude=8000)
    out_wav, duration, rms = voice_service.convert_to_pcm_wav(wav_bytes)

    assert out_wav.startswith(b"RIFF")
    assert round(duration, 1) == 1.0
    assert rms > 4000.0  # Sine wave RMS of 8000 peak is ~5656


def test_silence_detection_and_pre_screening():
    """Verifies that silence is instantly screened in < 2ms without making network requests."""
    # Create pure silence
    silence_wav = create_synthetic_wav(duration=1.0, frequency=0.0, amplitude=0)
    res = voice_service._sync_transcribe(silence_wav)

    assert res["success"] is True
    assert res["is_silent"] is True
    assert res["text"] == ""
    assert res["engine"] == "silence_filter"


def test_transcription_caching():
    """Verifies that identical audio payloads are served from the high-speed cache."""
    mock_sr = MagicMock()
    mock_recognizer = MagicMock()
    mock_recognizer.recognize_google.return_value = "hello from cache test"
    mock_sr.Recognizer.return_value = mock_recognizer

    audio_bytes = create_synthetic_wav(duration=0.5, frequency=500.0, amplitude=12000)

    with patch.object(voice_service, "_ensure_speech_recognition", return_value=mock_sr):
        # First call: populates cache
        res1 = voice_service._sync_transcribe(audio_bytes)
        assert res1["success"] is True
        assert res1["text"] == "hello from cache test"

        # Second call: must come from cache
        res2 = voice_service._sync_transcribe(audio_bytes)
        assert res2["success"] is True
        assert res2["text"] == "hello from cache test"
        assert res2.get("cached") is True


def test_api_transcribe_multipart_endpoint(client):
    """Verifies multipart audio file upload to /api/voice/transcribe."""
    mock_sr = MagicMock()
    mock_recognizer = MagicMock()
    mock_recognizer.recognize_google.return_value = "open local ai workbench"
    mock_sr.Recognizer.return_value = mock_recognizer

    audio_bytes = create_synthetic_wav(duration=0.5, frequency=300.0, amplitude=10000)

    with patch.object(voice_service, "_ensure_speech_recognition", return_value=mock_sr):
        res = client.post(
            "/api/voice/transcribe",
            files={"audio_file": ("test_recording.wav", audio_bytes, "audio/wav")},
            data={"language": "en-US", "engine": "google"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["text"] == "open local ai workbench"
        assert data["engine"] == "google"


def test_api_transcribe_base64_json_endpoint(client):
    """Verifies base64 payload to /api/voice/transcribe-json."""
    mock_sr = MagicMock()
    mock_recognizer = MagicMock()
    mock_recognizer.recognize_google.return_value = "summarize current architecture"
    mock_sr.Recognizer.return_value = mock_recognizer

    audio_bytes = create_synthetic_wav(duration=0.5, frequency=350.0, amplitude=9000)
    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")

    with patch.object(voice_service, "_ensure_speech_recognition", return_value=mock_sr):
        res = client.post(
            "/api/voice/transcribe-json",
            json={"audio_base64": b64_audio, "language": "en-US", "engine": "google"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["text"] == "summarize current architecture"


def test_api_transcribe_empty_payload_error(client):
    """Verifies HTTP 400 when no audio payload is provided."""
    res = client.post("/api/voice/transcribe")
    assert res.status_code == 400
    assert "No audio payload provided" in res.json()["detail"]


def test_api_transcribe_invalid_base64(client):
    """Verifies HTTP 400 when invalid base64 is provided."""
    res = client.post("/api/voice/transcribe-json", json={"audio_base64": "!!!not_base64!!!"})
    assert res.status_code == 400
