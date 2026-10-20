import base64
import io
from PIL import Image
from fastapi import APIRouter, HTTPException
from app.core.config import settings
from app.core.logging import logger
from app.services.ollama_service import ollama_service
from app.schemas.image import VisionAnalyzeRequest, VisionAnalyzeResponse

router = APIRouter(prefix="/vision", tags=["Vision & Image Understanding"])

ALLOWED_IMAGE_FORMATS = ["JPEG", "PNG", "WEBP", "GIF"]

@router.post("/analyze", response_model=VisionAnalyzeResponse)
async def analyze_image(req: VisionAnalyzeRequest):
    model_name = req.model or settings.default_model

    # 1. Inspect model capability
    models = await ollama_service.list_models()
    selected_model_info = next((m for m in models if m.name == model_name or m.model == model_name), None)

    if selected_model_info and not selected_model_info.capabilities.image_understanding:
        return VisionAnalyzeResponse(
            model=model_name,
            response=f"The selected model '{model_name}' does not support visual inputs (image understanding). Please select a vision-capable model such as 'gemma4:12b'.",
            capability_supported=False
        )

    # 2. Validate and decode image data
    raw_b64 = req.image_data
    if "," in raw_b64 and "data:image" in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(raw_b64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {str(e)}")

    if len(image_bytes) > settings.max_attachment_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Image size exceeds maximum limit of {settings.max_attachment_size_bytes // (1024*1024)}MB."
        )

    # Validate image with Pillow
    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
        pil_img.verify()
        img_format = pil_img.format
        if img_format not in ALLOWED_IMAGE_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image format '{img_format}'. Supported formats: {', '.join(ALLOWED_IMAGE_FORMATS)}."
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image validation failed: {str(e)}")

    # 3. Call Ollama vision chat
    try:
        res = await ollama_service.chat(
            model=model_name,
            messages=[{
                "role": "user",
                "content": req.prompt or "Describe this image in detail.",
                "images": [raw_b64]
            }],
            options={"temperature": 0.3}
        )
        content = res.get("message", {}).get("content", "")
        return VisionAnalyzeResponse(
            model=model_name,
            response=content,
            capability_supported=True
        )
    except Exception as e:
        logger.exception(f"Vision analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Vision model inference failed: {str(e)}")
