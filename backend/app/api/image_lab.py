import os
import asyncio
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.services.comfyui_service import comfyui_service, DEFAULT_COMFYUI_WORKFLOW, POPULAR_MODELS
from app.schemas.image import (
    ComfyUIStatusResponse,
    ImageGenerateRequest,
    ImageGenerateResponse,
    CheckpointDownloadRequest
)
from app.database.connection import db

router = APIRouter(prefix="/image_lab", tags=["Image Lab - Local Image Generation"])

@router.get("/status", response_model=ComfyUIStatusResponse)
async def get_comfyui_status():
    return await comfyui_service.check_status()

@router.post("/service/start")
async def start_comfyui_service():
    success = await comfyui_service.start_service()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to start ComfyUI service.")
    return {"status": "started", "service_url": comfyui_service.base_url}

@router.post("/service/stop")
async def stop_comfyui_service():
    stopped = await comfyui_service.stop_service()
    return {"status": "stopped" if stopped else "not_running"}

@router.get("/models/popular")
async def get_popular_models():
    return POPULAR_MODELS

@router.post("/models/download")
async def download_checkpoint_model(req: CheckpointDownloadRequest, background_tasks: BackgroundTasks):
    if req.model_key not in POPULAR_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown model key '{req.model_key}'.")
    background_tasks.add_task(comfyui_service.download_model_background, req.model_key)
    return {"status": "started", "model_key": req.model_key, "filename": POPULAR_MODELS[req.model_key]["filename"]}

@router.get("/workflow/default")
async def get_default_workflow():
    return DEFAULT_COMFYUI_WORKFLOW

@router.post("/generate", response_model=ImageGenerateResponse)
async def generate_image(req: ImageGenerateRequest):
    return await comfyui_service.generate_image(req)

@router.get("/history")
async def get_image_history(limit: int = Query(50, ge=1, le=100)):
    rows = await db.fetchall(
        """
        SELECT * FROM image_history
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,)
    )
    result = []
    for r in rows:
        fn = r["image_filename"]
        result.append({
            "id": r["id"],
            "prompt": r["prompt"],
            "negative_prompt": r["negative_prompt"],
            "model_checkpoint": r["model_checkpoint"],
            "seed": r["seed"],
            "width": r["width"],
            "height": r["height"],
            "image_filename": fn,
            "image_url": f"/api/image_lab/output/{fn}" if fn else None,
            "status": r["status"],
            "error": r["error"],
            "created_at": r["created_at"]
        })
    return result

@router.api_route("/output/{filename}", methods=["GET", "HEAD"])
async def get_generated_image_file(filename: str):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    
    file_path = settings.generated_images_dir / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Image file not found.")

    return FileResponse(file_path)
