from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.ollama import router as ollama_router
from app.api.chat import router as chat_router
from app.api.tools import router as tools_router
from app.api.vision import router as vision_router
from app.api.image_lab import router as image_lab_router
from app.api.coding import router as coding_router
from app.api.automation import router as automation_router
from app.api.settings import router as settings_router
from app.api.reports import router as reports_router
from app.api.voice import router as voice_router

api_router = APIRouter(prefix="/api")

api_router.include_router(health_router)
api_router.include_router(ollama_router)
api_router.include_router(chat_router)
api_router.include_router(tools_router)
api_router.include_router(vision_router)
api_router.include_router(image_lab_router)
api_router.include_router(coding_router)
api_router.include_router(automation_router)
api_router.include_router(settings_router)
api_router.include_router(reports_router)
api_router.include_router(voice_router)
