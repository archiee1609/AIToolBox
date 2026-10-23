from typing import Optional, List
from pydantic import BaseModel, Field


class VoiceTranscribeRequest(BaseModel):
    audio_base64: Optional[str] = Field(None, description="Base64 encoded audio bytes (WAV, WebM, OGG, MP3)")
    language: str = Field("en-US", description="Language code for transcription e.g. 'en-US', 'es-ES', 'fr-FR', 'de-DE'")
    engine: str = Field("auto", description="Transcription engine to use: 'auto', 'google', 'whisper', 'offline'")


class VoiceTranscribeResponse(BaseModel):
    success: bool = Field(..., description="Whether transcription was successful or valid silence")
    text: str = Field("", description="Transcribed plain text from voice audio")
    duration_seconds: float = Field(0.0, description="Duration of processed audio in seconds")
    engine: str = Field("google", description="Engine utilized for speech-to-text")
    language: str = Field("en-US", description="Language code utilized")
    is_silent: bool = Field(False, description="True if input audio was detected as silence or below ambient threshold")
    error: Optional[str] = Field(None, description="Error message if transcription failed")


class VoiceSynthesizeRequest(BaseModel):
    text: str = Field(..., description="Text content to synthesize to spoken audio")
    voice: Optional[str] = Field("default", description="Voice profile identifier")


class VoiceStatusResponse(BaseModel):
    available: bool = Field(..., description="True if at least one speech transcription engine is active")
    engines: List[str] = Field(default_factory=list, description="List of available STT engines")
    default_engine: str = Field("google", description="Recommended/default engine")
    microphone_supported: bool = Field(True, description="Whether browser and client recording is supported")
    web_speech_supported: bool = Field(True, description="Whether HTML5 Web Speech API is enabled")
    tts_supported: bool = Field(True, description="Whether Text-to-Speech audio readout is available")
    details: str = Field("", description="Engine diagnostic info and status")
