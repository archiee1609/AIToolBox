from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.services.report_service import (
    report_service,
    ReportGenerateRequest,
    ReportGenerateResponse
)
from app.services.report_export_service import export_report_bundle, sanitize_filename

router = APIRouter(prefix="/reports", tags=["Reports & Document Generation"])


class ReportExportRequest(BaseModel):
    markdown: str = Field(..., description="Markdown report content")
    title: str = Field(default="Executive Report", description="Report title")
    format: str = Field(default="pdf", description="pdf, docx, xlsx, pptx, md, html, or zip")


class ReportBundleRequest(BaseModel):
    markdown: str = Field(..., description="Markdown report content")
    title: str = Field(default="Executive Report", description="Report title")


@router.post("/generate", response_model=ReportGenerateResponse)
async def generate_report_endpoint(req: ReportGenerateRequest):
    try:
        return await report_service.generate_report(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_report_endpoint(req: ReportExportRequest):
    """Converts markdown report text into downloadable PDF, DOCX, XLSX, PPTX, HTML, or ZIP binary files."""
    try:
        bundle = export_report_bundle(req.markdown, req.title)
        fmt = req.format.lower().strip()
        if fmt not in bundle:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{fmt}'. Choose from: {list(bundle.keys())}"
            )
        
        item = bundle[fmt]
        if "error" in item:
            raise HTTPException(status_code=500, detail=f"Failed to generate {fmt}: {item['error']}")
            
        return Response(
            content=item["bytes"],
            media_type=item["mime"],
            headers={"Content-Disposition": f'attachment; filename="{item["filename"]}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bundle")
async def bundle_report_endpoint(req: ReportBundleRequest):
    """Returns downloadable format metadata for a given markdown report."""
    try:
        bundle = export_report_bundle(req.markdown, req.title)
        meta = {}
        for fmt, item in bundle.items():
            meta[fmt] = {
                "name": item.get("name"),
                "filename": item.get("filename"),
                "mime": item.get("mime"),
                "icon": item.get("icon"),
                "size_kb": item.get("size_kb"),
                "available": "bytes" in item
            }
        return {"title": req.title, "formats": meta}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
