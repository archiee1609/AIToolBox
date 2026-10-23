import base64
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Response
from app.schemas.voice import VoiceTranscribeRequest, VoiceTranscribeResponse, VoiceStatusResponse, VoiceSynthesizeRequest
from app.services.voice_service import voice_service

router = APIRouter(prefix="/voice", tags=["Voice & Speech"])


@router.get("/status", response_model=VoiceStatusResponse)
async def get_voice_status():
    """Returns availability and active status of speech recognition and voice input services."""
    stat = voice_service.get_status()
    stat["tts_supported"] = True
    return stat


@router.post("/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe_voice(
    audio_file: Optional[UploadFile] = File(None),
    audio_base64: Optional[str] = Form(None),
    language: str = Form("en-US"),
    engine: str = Form("auto"),
):
    """
    Transcribes audio bytes into plain text using high-performance speech recognition.
    Accepts:
      - Multipart audio file upload (`audio_file`)
      - Form field base64 encoded audio string (`audio_base64`)
    """
    raw_audio = b""

    if audio_file is not None:
        raw_audio = await audio_file.read()
    elif audio_base64:
        try:
            clean_b64 = audio_base64
            if "," in clean_b64:
                clean_b64 = clean_b64.split(",", 1)[1]
            raw_audio = base64.b64decode(clean_b64)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid base64 audio payload: {e}"
            )

    if not raw_audio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No audio payload provided. Supply either 'audio_file' or 'audio_base64'."
        )

    result = await voice_service.transcribe(
        audio_bytes=raw_audio,
        language=language,
        engine=engine
    )

    return VoiceTranscribeResponse(**result)


@router.post("/transcribe-json", response_model=VoiceTranscribeResponse)
async def transcribe_voice_json(payload: VoiceTranscribeRequest):
    """
    JSON endpoint for transcribing base64 audio payloads.
    """
    if not payload.audio_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field 'audio_base64' is required."
        )

    try:
        clean_b64 = payload.audio_base64
        if "," in clean_b64:
            clean_b64 = clean_b64.split(",", 1)[1]
        raw_audio = base64.b64decode(clean_b64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 audio payload: {e}"
        )

    result = await voice_service.transcribe(
        audio_bytes=raw_audio,
        language=payload.language,
        engine=payload.engine
    )

    return VoiceTranscribeResponse(**result)


@router.post("/synthesize")
async def synthesize_voice(payload: VoiceSynthesizeRequest):
    """
    Synthesizes text into spoken audio WAV stream for Audio Chat readouts.
    """
    if not payload.text or not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field 'text' cannot be empty."
        )

    wav_bytes = voice_service.synthesize_speech_wav(payload.text)
    if not wav_bytes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to synthesize audio."
        )

    return Response(content=wav_bytes, media_type="audio/wav")
