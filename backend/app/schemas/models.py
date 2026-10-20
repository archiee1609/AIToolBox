from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ModelCapabilities(BaseModel):
    text_generation: bool = True
    streaming: bool = True
    tool_calling: bool = False
    image_understanding: bool = False
    structured_output: bool = True
    reasoning_controls: bool = False

class ModelDetails(BaseModel):
    name: str
    model: str
    parameter_size: Optional[str] = None
    quantization_level: Optional[str] = None
    format: Optional[str] = None
    family: Optional[str] = None
    context_length: Optional[int] = None
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities)
    is_preferred: bool = False
    modified_at: Optional[str] = None
    size_bytes: Optional[int] = None

class ModelOptions(BaseModel):
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=0.9, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=40, ge=0)
    repeat_penalty: Optional[float] = Field(default=1.1, ge=0.0)
    seed: Optional[int] = None
    num_ctx: Optional[int] = Field(default=8192, ge=512)
    keep_alive: Optional[str] = "5m"
