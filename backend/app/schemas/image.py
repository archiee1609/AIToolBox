from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ImageGenerateRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = ""
    width: int = Field(default=512, ge=256, le=2048)
    height: int = Field(default=512, ge=256, le=2048)
    seed: Optional[int] = -1
    steps: Optional[int] = Field(default=20, ge=1, le=100)
    cfg_scale: Optional[float] = Field(default=7.0, ge=1.0, le=30.0)
    checkpoint: Optional[str] = None
    workflow_id: Optional[str] = "default"

class ImageGenerateResponse(BaseModel):
    id: str
    status: str # completed, success, failed, generating
    prompt: str
    image_filename: Optional[str] = None
    image_url: Optional[str] = None
    seed: Optional[int] = None
    error: Optional[str] = None
    created_at: str

class ComfyUIStatusResponse(BaseModel):
    is_reachable: bool
    is_installed: bool = False
    service_url: str
    version: Optional[str] = None
    queue_remaining: int = 0
    available_checkpoints: List[str] = Field(default_factory=list)
    actionable_instructions: Optional[str] = None
    download_progress: Optional[Dict[str, Any]] = None

class CheckpointDownloadRequest(BaseModel):
    model_key: str = "sd15" # sd15, sdturbo, dreamshaper

class VisionAnalyzeRequest(BaseModel):
    image_data: str # base64 data URI or raw base64
    prompt: str = "Describe this image in detail."
    model: Optional[str] = None

class VisionAnalyzeResponse(BaseModel):
    model: str
    response: str
    capability_supported: bool = True
