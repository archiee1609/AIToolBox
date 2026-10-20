import os
import psutil
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.system import DiagnosticsReport, ServiceHealth
from app.services.ollama_service import ollama_service
from app.services.comfyui_service import comfyui_service
from app.database.connection import db

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])

@router.get("", response_model=DiagnosticsReport)
async def get_diagnostics():
    # Check Ollama
    ollama_health = await ollama_service.check_health()
    ollama_models = await ollama_service.list_models()
    model_names = [m.name for m in ollama_models]

    # Check ComfyUI
    comfy_status = await comfyui_service.check_status()

    # Check DB
    db_ok = True
    db_err = None
    try:
        row = await db.fetchone("SELECT 1 AS ok")
        if not row or row["ok"] != 1:
            db_ok = False
            db_err = "Unexpected response from SQLite test query"
    except Exception as e:
        db_ok = False
        db_err = str(e)

    # Check workspace
    ws_ok = settings.workspace_root.exists() and settings.workspace_root.is_dir()

    return DiagnosticsReport(
        app_name=settings.app_name,
        app_version=settings.app_version,
        backend_status="healthy" if db_ok and ws_ok else "degraded",
        ollama=ServiceHealth(
            name="Ollama",
            status="healthy" if ollama_health["reachable"] else "unavailable",
            endpoint=settings.ollama_base_url,
            details={"version": ollama_health["version"], "error": ollama_health["error"]}
        ),
        comfyui=ServiceHealth(
            name="ComfyUI",
            status="healthy" if comfy_status.is_reachable else "unavailable",
            endpoint=settings.comfyui_base_url,
            details={
                "version": comfy_status.version,
                "instructions": comfy_status.actionable_instructions
            }
        ),
        database=ServiceHealth(
            name="SQLite Database",
            status="healthy" if db_ok else "unavailable",
            endpoint=str(settings.db_path),
            details={"wal_mode": True, "error": db_err}
        ),
        workspace=ServiceHealth(
            name="Authorized Workspace",
            status="healthy" if ws_ok else "unavailable",
            endpoint=str(settings.workspace_root),
            details={"exists": ws_ok}
        ),
        installed_models=model_names,
        selected_model=settings.default_model,
        recent_errors=[]
    )
