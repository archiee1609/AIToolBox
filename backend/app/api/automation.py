from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional

from app.services.workflow_service import workflow_service
from app.schemas.automation import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowRunResponse,
    WorkflowDryRunPreview
)

router = APIRouter(prefix="/automation", tags=["Workflow Automation Engine"])

@router.get("/workflows", response_model=List[WorkflowResponse])
async def list_workflows():
    return await workflow_service.list_workflows()

@router.post("/workflows", response_model=WorkflowResponse)
async def create_workflow(req: WorkflowCreate):
    return await workflow_service.create_workflow(req)

@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str):
    wf = await workflow_service.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return wf

@router.patch("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(workflow_id: str, req: WorkflowUpdate):
    wf = await workflow_service.update_workflow(workflow_id, req)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return wf

@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    await workflow_service.delete_workflow(workflow_id)
    return {"deleted": True, "id": workflow_id}

@router.post("/workflows/{workflow_id}/preview", response_model=WorkflowDryRunPreview)
async def preview_workflow(workflow_id: str):
    wf = await workflow_service.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return workflow_service.preview_workflow(wf)

@router.post("/workflows/{workflow_id}/run", response_model=WorkflowRunResponse)
async def run_workflow(workflow_id: str, payload: Optional[Dict[str, Any]] = None):
    confirmed = (payload or {}).get("confirmed", True)
    try:
        return await workflow_service.execute_workflow(
            workflow_id=workflow_id,
            triggered_by="user",
            confirmed_steps=confirmed
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/runs", response_model=List[WorkflowRunResponse])
async def list_runs(workflow_id: Optional[str] = None):
    return await workflow_service.list_runs(workflow_id)
