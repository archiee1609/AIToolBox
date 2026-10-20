import os
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
DATA_DIR = BASE_DIR / "data"
WORKSPACE_DIR = BASE_DIR / "workspace"
GENERATED_IMAGES_DIR = BASE_DIR / "generated_images"
BACKUP_DIR = DATA_DIR / "backups"

for d in [DATA_DIR, WORKSPACE_DIR, GENERATED_IMAGES_DIR, BACKUP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

class Settings(BaseModel):
    app_name: str = "Local AI Workbench"
    app_version: str = "1.0.0"
    host: str = "127.0.0.1"
    port: int = 8000
    
    # Endpoints
    ollama_base_url: str = Field(default=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    comfyui_base_url: str = Field(default=os.getenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188"))
    
    # File storage paths
    base_dir: Path = BASE_DIR
    data_dir: Path = DATA_DIR
    db_path: Path = DATA_DIR / "workbench.db"
    workspace_root: Path = WORKSPACE_DIR.resolve()
    generated_images_dir: Path = GENERATED_IMAGES_DIR.resolve()
    backup_dir: Path = BACKUP_DIR.resolve()
    
    # Limits & security
    max_attachment_size_bytes: int = 25 * 1024 * 1024 # 25MB
    max_tool_iterations: int = 10
    command_timeout_seconds: int = 60
    workflow_timeout_seconds: int = 300
    cors_origins: List[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]
    
    # Model defaults
    default_model: str = "gemma4:12b"
    default_temperature: float = 0.7
    default_context_length: int = 8192
    
    # Web search setting (explicit toggle, defaults to False for privacy)
    enable_web_search: bool = False

settings = Settings()
