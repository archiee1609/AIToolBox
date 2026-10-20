from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class WorkspaceFile(BaseModel):
    name: str
    path: str # relative to workspace
    is_dir: bool
    size_bytes: int = 0
    modified_at: str

class WorkspaceTree(BaseModel):
    workspace_root: str
    files: List[WorkspaceFile]

class FileReadRequest(BaseModel):
    path: str # relative to workspace

class FileReadResponse(BaseModel):
    path: str
    content: str
    size_bytes: int
    is_binary: bool = False

class ProposedFileChange(BaseModel):
    path: str # relative to workspace
    original_content: Optional[str] = None
    new_content: str
    diff: str
    explanation: str

class CodingTaskCreate(BaseModel):
    task_description: str
    workspace_path: Optional[str] = None

class CodingTaskResponse(BaseModel):
    id: str
    workspace_path: str
    task_description: str
    status: str # planning, awaiting_approval, applied, rejected, testing, completed, failed
    plan: Optional[str] = None
    affected_files: List[str] = Field(default_factory=list)
    diff_content: Optional[str] = None
    command_logs: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str
    completed_at: Optional[str] = None

class FileChangeItem(BaseModel):
    path: str
    content: str

class ApplyChangeRequest(BaseModel):
    approved: bool = True
    file_changes: List[FileChangeItem] = Field(default_factory=list)

class RunCommandRequest(BaseModel):
    command: str
    cwd: Optional[str] = None
    approved: bool = True

class GitStatusResult(BaseModel):
    is_git_repo: bool
    branch: Optional[str] = None
    clean: bool = True
    modified: List[str] = Field(default_factory=list)
    untracked: List[str] = Field(default_factory=list)
    diff: Optional[str] = ""
