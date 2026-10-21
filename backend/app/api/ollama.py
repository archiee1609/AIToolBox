import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.services.ollama_service import ollama_service
from app.services.model_download_service import model_download_manager
from app.schemas.models import ModelDetails

router = APIRouter(prefix="/ollama", tags=["Ollama Integration"])

@router.get("/health")
async def get_ollama_health():
    return await ollama_service.check_health()

@router.get("/models", response_model=List[ModelDetails])
async def list_installed_models():
    models = await ollama_service.list_models()
    return models

@router.get("/models/{model_name:path}")
async def get_model_details(model_name: str):
    info = await ollama_service.get_model_info(model_name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' info not found on Ollama server.")
    return info

@router.post("/pull")
async def pull_model_endpoint(payload: Dict[str, Any]):
    """Installs / pulls a new Ollama model with real-time SSE progress streaming."""
    model_name = payload.get("name", "").strip()
    if not model_name:
        raise HTTPException(status_code=400, detail="Missing required parameter 'name' (model tag).")

    async def event_generator():
        try:
            async for chunk in ollama_service.pull_model(model_name):
                yield f"data: {json.dumps(chunk)}\n\n"
            yield f"data: {json.dumps({'status': 'success', 'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.delete("/models/{model_name:path}")
async def delete_model_endpoint(model_name: str):
    """Deletes an installed model from the Ollama library."""
    if not model_name:
        raise HTTPException(status_code=400, detail="Model name required.")
    try:
        return await ollama_service.delete_model(model_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/download/start")
async def start_background_download(payload: Dict[str, Any]):
    """Initiates a background model download task managed independently of HTTP streams."""
    model_name = payload.get("name", "").strip()
    if not model_name:
        raise HTTPException(status_code=400, detail="Missing parameter 'name'.")
    job = model_download_manager.start_download(model_name)
    return {"status": "started", "job": job.to_dict()}

@router.post("/download/stop")
async def stop_background_download(payload: Dict[str, Any]):
    """Stops or cancels an active background model download."""
    model_name = payload.get("name", "").strip()
    if not model_name:
        raise HTTPException(status_code=400, detail="Missing parameter 'name'.")
    stopped = model_download_manager.stop_download(model_name)
    return {"status": "stopped" if stopped else "not_found", "model": model_name}

@router.get("/download/status")
async def get_background_download_status(name: Optional[str] = None):
    """Gets status of active or specified model download job."""
    if name:
        job = model_download_manager.get_job(name)
    else:
        job = model_download_manager.get_active_or_latest_job()
    return {"job": job}

@router.get("/download/jobs")
async def list_background_download_jobs():
    """Lists all background model download jobs."""
    return {"jobs": model_download_manager.list_jobs()}

@router.delete("/download/job")
async def dismiss_background_download_job(name: Optional[str] = None):
    """Dismisses / clears a finished or stopped download job record."""
    model_download_manager.dismiss_job(name)
    return {"status": "dismissed", "model": name or "all"}

@router.post("/test")
async def test_model_inference(payload: Dict[str, Any]):
    model_name = payload.get("model", "gemma4:12b")
    prompt = payload.get("prompt", "Hello! Reply with 'OK'.")
    try:
        res = await ollama_service.chat(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1}
        )
        return {
            "model": model_name,
            "status": "success",
            "reply": res.get("message", {}).get("content", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
