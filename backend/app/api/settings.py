import datetime
import uuid
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.database.connection import db
from app.services.backup_service import backup_service
from app.schemas.system import (
    SystemSettings,
    BackupResponse,
    RestoreRequest,
    MemoryItem,
    ProjectMemoryItem
)

router = APIRouter(prefix="/settings", tags=["Application Settings & Memory"])

@router.get("", response_model=SystemSettings)
async def get_settings():
    theme_row = await db.fetchone("SELECT value FROM user_preferences WHERE key = 'theme'")
    theme = theme_row["value"] if theme_row else "dark"
    sys_inst_row = await db.fetchone("SELECT value FROM user_preferences WHERE key = 'system_instruction'")
    sys_inst = sys_inst_row["value"] if sys_inst_row else "You are Local AI Workbench, an all-in-one expert assistant for coding, reasoning, reports, and data analysis."
    
    return SystemSettings(
        ollama_base_url=settings.ollama_base_url,
        comfyui_base_url=settings.comfyui_base_url,
        workspace_root=str(settings.workspace_root),
        default_model=settings.default_model,
        default_temperature=settings.default_temperature,
        default_context_length=settings.default_context_length,
        enable_web_search=settings.enable_web_search,
        theme=theme,
        system_instruction=sys_inst
    )

@router.patch("", response_model=SystemSettings)
async def update_settings(payload: Dict[str, Any]):
    if "ollama_base_url" in payload:
        settings.ollama_base_url = payload["ollama_base_url"].rstrip("/")
    if "comfyui_base_url" in payload:
        settings.comfyui_base_url = payload["comfyui_base_url"].rstrip("/")
    if "default_model" in payload:
        settings.default_model = payload["default_model"]
    if "default_temperature" in payload:
        settings.default_temperature = float(payload["default_temperature"])
    if "default_context_length" in payload:
        settings.default_context_length = int(payload["default_context_length"])
    if "enable_web_search" in payload:
        settings.enable_web_search = bool(payload["enable_web_search"])
    if "theme" in payload:
        await db.execute(
            """
            INSERT INTO user_preferences (key, value, updated_at)
            VALUES ('theme', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (payload["theme"],)
        )
    if "system_instruction" in payload:
        await db.execute(
            """
            INSERT INTO user_preferences (key, value, updated_at)
            VALUES ('system_instruction', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (str(payload["system_instruction"]),)
        )

    return await get_settings()

@router.get("/backups", response_model=List[BackupResponse])
async def list_backups():
    return backup_service.list_backups()

@router.post("/backups", response_model=BackupResponse)
async def create_backup():
    return await backup_service.create_backup()

@router.post("/restore")
async def restore_backup(req: RestoreRequest):
    try:
        return await backup_service.restore_backup(req.backup_filename, confirm=req.confirm)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/memories", response_model=List[MemoryItem])
async def list_memories():
    rows = await db.fetchall("SELECT * FROM user_memories ORDER BY updated_at DESC")
    return [
        MemoryItem(
            id=r["id"],
            key=r["key"],
            content=r["content"],
            source_tool=r["source_tool"] if "source_tool" in r.keys() and r["source_tool"] else "custom",
            category=r["category"] if "category" in r.keys() and r["category"] else "general",
            enabled=bool(r["enabled"]),
            created_at=r["created_at"],
            updated_at=r["updated_at"]
        )
        for r in rows
    ]

@router.post("/memories", response_model=MemoryItem)
async def create_memory(payload: Dict[str, Any]):
    mem_id = str(uuid.uuid4())
    now = datetime.datetime.now().isoformat()
    key = payload.get("key", "note").strip()
    content = payload.get("content", "").strip()
    source_tool = payload.get("source_tool", "custom")
    category = payload.get("category", "general")
    enabled = payload.get("enabled", True)

    await db.execute(
        """
        INSERT INTO user_memories (id, key, content, source_tool, category, enabled, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (mem_id, key, content, source_tool, category, 1 if enabled else 0, now, now)
    )

    return MemoryItem(
        id=mem_id,
        key=key,
        content=content,
        source_tool=source_tool,
        category=category,
        enabled=enabled,
        created_at=now,
        updated_at=now
    )

@router.put("/memories/{memory_id}", response_model=MemoryItem)
async def update_memory(memory_id: str, payload: Dict[str, Any]):
    existing = await db.fetchone("SELECT * FROM user_memories WHERE id = ?", (memory_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Memory not found.")

    now = datetime.datetime.now().isoformat()
    key = payload.get("key", existing["key"]).strip()
    content = payload.get("content", existing["content"]).strip()
    source_tool = payload.get("source_tool", existing["source_tool"] if "source_tool" in existing.keys() else "custom")
    category = payload.get("category", existing["category"] if "category" in existing.keys() else "general")
    enabled = payload.get("enabled", bool(existing["enabled"]))

    await db.execute(
        """
        UPDATE user_memories
        SET key = ?, content = ?, source_tool = ?, category = ?, enabled = ?, updated_at = ?
        WHERE id = ?
        """,
        (key, content, source_tool, category, 1 if enabled else 0, now, memory_id)
    )

    return MemoryItem(
        id=memory_id,
        key=key,
        content=content,
        source_tool=source_tool,
        category=category,
        enabled=enabled,
        created_at=existing["created_at"],
        updated_at=now
    )

@router.post("/memories/{memory_id}/toggle")
async def toggle_memory(memory_id: str):
    existing = await db.fetchone("SELECT * FROM user_memories WHERE id = ?", (memory_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Memory not found.")

    new_val = 0 if existing["enabled"] else 1
    now = datetime.datetime.now().isoformat()
    await db.execute("UPDATE user_memories SET enabled = ?, updated_at = ? WHERE id = ?", (new_val, now, memory_id))
    return {"id": memory_id, "enabled": bool(new_val)}

@router.post("/memories/import")
async def import_memories(payload: Dict[str, Any]):
    items = payload.get("items", [])
    now = datetime.datetime.now().isoformat()
    created_count = 0

    for item in items:
        key = item.get("key", "imported_rule").strip()
        content = item.get("content", "").strip()
        if not content:
            continue
        mem_id = str(uuid.uuid4())
        source = item.get("source_tool", "custom")
        cat = item.get("category", "general")
        await db.execute(
            """
            INSERT INTO user_memories (id, key, content, source_tool, category, enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (mem_id, key, content, source, cat, now, now)
        )
        created_count += 1

    return {"imported": created_count}

@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str):
    await db.execute("DELETE FROM user_memories WHERE id = ?", (memory_id,))
    return {"deleted": True, "id": memory_id}

@router.get("/project_context", response_model=ProjectMemoryItem)
async def get_project_context():
    ws_str = str(settings.workspace_root)
    row = await db.fetchone("SELECT * FROM project_memory WHERE workspace_path = ?", (ws_str,))
    if row:
        return ProjectMemoryItem(
            workspace_path=row["workspace_path"],
            instructions=row["instructions"] or "",
            context_summary=row["context_summary"] or "",
            updated_at=row["updated_at"]
        )
    return ProjectMemoryItem(
        workspace_path=ws_str,
        instructions="",
        context_summary="",
        updated_at=datetime.datetime.now().isoformat()
    )

@router.post("/project_context", response_model=ProjectMemoryItem)
async def update_project_context(payload: Dict[str, Any]):
    ws_str = str(settings.workspace_root)
    inst = payload.get("instructions", "")
    summary = payload.get("context_summary", "")
    now = datetime.datetime.now().isoformat()

    await db.execute(
        """
        INSERT INTO project_memory (workspace_path, instructions, context_summary, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(workspace_path) DO UPDATE SET
            instructions = excluded.instructions,
            context_summary = excluded.context_summary,
            updated_at = excluded.updated_at
        """,
        (ws_str, inst, summary, now)
    )

    return ProjectMemoryItem(
        workspace_path=ws_str,
        instructions=inst,
        context_summary=summary,
        updated_at=now
    )
