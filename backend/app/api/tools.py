from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from app.services.tool_registry import tool_registry
from app.schemas.tools import ToolDefinition, ToolExecutionRequest, ToolExecutionResponse
from app.database.connection import db

router = APIRouter(prefix="/tools", tags=["AI Tools Registry"])

@router.get("", response_model=List[ToolDefinition])
async def list_tools():
    return tool_registry.get_all_definitions()

@router.post("/execute", response_model=ToolExecutionResponse)
async def execute_tool(req: ToolExecutionRequest):
    res = await tool_registry.execute_tool(
        name=req.tool_name,
        arguments=req.arguments,
        conversation_id=req.conversation_id,
        approved=req.approved
    )
    return res

@router.get("/history")
async def get_tool_history(limit: int = Query(50, ge=1, le=200)):
    rows = await db.fetchall(
        """
        SELECT * FROM tools_log
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,)
    )
    return rows
