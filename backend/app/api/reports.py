from fastapi import APIRouter, HTTPException
from app.services.report_service import (
    report_service,
    ReportGenerateRequest,
    ReportGenerateResponse
)

router = APIRouter(prefix="/reports", tags=["Reports & Document Generation"])

@router.post("/generate", response_model=ReportGenerateResponse)
async def generate_report_endpoint(req: ReportGenerateRequest):
    try:
        return await report_service.generate_report(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
