from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ToolParameterProperty(BaseModel):
    type: str
    description: str
    enum: Optional[list] = None

class ToolParametersSchema(BaseModel):
    type: str = "object"
    properties: Dict[str, Any]
    required: Optional[list] = Field(default_factory=list)

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    requires_approval: bool = False
    category: str = "general" # general, filesystem, project, git, web
    is_external: bool = False # true if calls out to internet

class ToolExecutionRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    conversation_id: Optional[str] = None
    approved: bool = False

class ToolExecutionResponse(BaseModel):
    tool_name: str
    status: str # success, error, blocked, requires_approval
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: int = 0
    requires_approval: bool = False
    confirmation_message: Optional[str] = None
