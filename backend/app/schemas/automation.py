from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class WorkflowStep(BaseModel):
    id: str
    action_type: str # read_files, extract_info, llm_transform, write_file, run_test
    parameters: Dict[str, Any] = Field(default_factory=dict)
    require_confirmation: bool = False

class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    steps: List[WorkflowStep]
    enabled: bool = True
    timeout_seconds: Optional[int] = 300
    max_iterations: Optional[int] = 10

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[WorkflowStep]] = None
    enabled: Optional[bool] = None
    timeout_seconds: Optional[int] = None
    max_iterations: Optional[int] = None

class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    enabled: bool
    timeout_seconds: int
    max_iterations: int
    created_at: str
    updated_at: str

class WorkflowRunResponse(BaseModel):
    id: str
    workflow_id: str
    status: str # running, completed, failed, cancelled
    triggered_by: str
    logs: List[Dict[str, Any]]
    result: Dict[str, Any]
    error: Optional[str] = None
    duration_ms: int = 0
    created_at: str

class WorkflowDryRunPreview(BaseModel):
    workflow_id: Optional[str] = None
    workflow_name: str
    valid: bool
    validation_errors: List[str] = Field(default_factory=list)
    action_previews: List[Dict[str, Any]] = Field(default_factory=list)
    sensitive_steps_requiring_approval: List[str] = Field(default_factory=list)
