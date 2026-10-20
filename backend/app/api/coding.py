import json
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.services.coding_agent_service import coding_agent_service
from app.schemas.coding import (
    WorkspaceTree,
    FileReadRequest,
    FileReadResponse,
    ProposedFileChange,
    CodingTaskCreate,
    CodingTaskResponse,
    ApplyChangeRequest,
    GitStatusResult
)
from app.database.connection import db

router = APIRouter(prefix="/coding", tags=["Coding Agent"])

@router.get("/workspace/tree", response_model=WorkspaceTree)
async def get_workspace_tree(workspace: Optional[str] = None):
    try:
        return coding_agent_service.list_workspace_files(workspace)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/workspace/read", response_model=FileReadResponse)
async def read_workspace_file(req: FileReadRequest):
    try:
        data = coding_agent_service.read_file(req.path)
        return FileReadResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/diff", response_model=ProposedFileChange)
async def compute_file_diff(payload: Dict[str, Any]):
    path = payload.get("path")
    new_content = payload.get("new_content", "")
    if not path:
        raise HTTPException(status_code=400, detail="Path is required.")
    try:
        return coding_agent_service.compute_diff(path, new_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tasks", response_model=List[CodingTaskResponse])
async def list_coding_tasks(limit: int = Query(20, ge=1, le=100)):
    rows = await db.fetchall(
        "SELECT * FROM coding_tasks ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )
    result = []
    for r in rows:
        result.append(CodingTaskResponse(
            id=r["id"],
            workspace_path=r["workspace_path"],
            task_description=r["task_description"],
            status=r["status"],
            plan=r["plan"],
            affected_files=json.loads(r["affected_files_json"] or "[]"),
            diff_content=r["diff_content"],
            command_logs=json.loads(r["command_logs_json"] or "[]"),
            created_at=r["created_at"],
            completed_at=r["completed_at"]
        ))
    return result

@router.post("/tasks", response_model=CodingTaskResponse)
async def create_coding_task(req: CodingTaskCreate):
    try:
        return await coding_agent_service.create_task(req.task_description, req.workspace_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/tasks/{task_id}/plan")
async def submit_task_plan(task_id: str, payload: Dict[str, Any]):
    plan = payload.get("plan", "")
    affected_files = payload.get("affected_files", [])
    diff_content = payload.get("diff_content", "")
    await coding_agent_service.submit_plan_and_diff(task_id, plan, affected_files, diff_content)
    return {"status": "awaiting_approval", "task_id": task_id}

@router.post("/tasks/{task_id}/apply")
async def apply_task_changes(task_id: str, req: ApplyChangeRequest):
    file_changes = [{"path": fc.path, "content": fc.content} for fc in req.file_changes]
    try:
        res = await coding_agent_service.apply_changes(task_id, file_changes, approved=req.approved)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/tasks/{task_id}/run_tests")
async def run_task_tests(task_id: str, payload: Dict[str, Any]):
    command = payload.get("command", "pytest")
    try:
        res = await coding_agent_service.run_test_suite(task_id, command)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/git/status", response_model=GitStatusResult)
async def get_workspace_git_status():
    return await coding_agent_service.get_git_status()
