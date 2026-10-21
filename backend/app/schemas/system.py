from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ServiceHealth(BaseModel):
    name: str
    status: str # healthy, unavailable, degraded
    endpoint: str
    details: Dict[str, Any] = Field(default_factory=dict)

class DiagnosticsReport(BaseModel):
    app_name: str
    app_version: str
    backend_status: str
    ollama: ServiceHealth
    comfyui: ServiceHealth
    database: ServiceHealth
    workspace: ServiceHealth
    installed_models: List[str] = Field(default_factory=list)
    selected_model: Optional[str] = None
    recent_errors: List[str] = Field(default_factory=list)

class SystemSettings(BaseModel):
    ollama_base_url: str
    comfyui_base_url: str
    workspace_root: str
    default_model: str
    default_temperature: float
    default_context_length: int
    enable_web_search: bool
    theme: str = "dark"
    system_instruction: Optional[str] = None

class BackupResponse(BaseModel):
    filename: str
    backup_path: str
    size_bytes: int
    created_at: str

class RestoreRequest(BaseModel):
    backup_filename: str
    confirm: bool = False

class MemoryItem(BaseModel):
    id: str
    key: str
    content: str
    source_tool: Optional[str] = "custom" # chatgpt, claude, cursor, copilot, gemini, custom
    category: Optional[str] = "general" # rules, persona, snippet, instructions, context
    enabled: bool = True
    created_at: str
    updated_at: str

class ProjectMemoryItem(BaseModel):
    workspace_path: str
    instructions: str
    context_summary: str
    updated_at: str
