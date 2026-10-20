import difflib
import json
import os
import uuid
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.core.logging import logger
from app.core.security import resolve_and_validate_path, validate_file_size, SecurityError
from app.core.command_runner import run_command_safely
from app.database.connection import db
from app.schemas.coding import (
    WorkspaceFile,
    WorkspaceTree,
    ProposedFileChange,
    CodingTaskResponse,
    GitStatusResult
)

class CodingAgentService:
    def list_workspace_files(self, custom_root: Optional[str] = None) -> WorkspaceTree:
        """Inspects authorized workspace directory and returns tree structure."""
        root = resolve_and_validate_path(custom_root or settings.workspace_root)
        files_list: List[WorkspaceFile] = []

        for p in root.rglob("*"):
            # skip .git or node_modules or pycache
            parts = p.parts
            if any(part in [".git", "node_modules", "__pycache__", ".pytest_cache", ".venv", "venv"] for part in parts):
                continue

            rel_path = str(p.relative_to(root)).replace("\\", "/")
            stat = p.stat()
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            files_list.append(WorkspaceFile(
                name=p.name,
                path=rel_path,
                is_dir=p.is_dir(),
                size_bytes=stat.st_size if p.is_file() else 0,
                modified_at=mtime
            ))

        return WorkspaceTree(
            workspace_root=str(root),
            files=files_list
        )

    def read_file(self, rel_path: str, custom_root: Optional[str] = None) -> Dict[str, Any]:
        """Reads file within workspace boundary safely."""
        root = custom_root or settings.workspace_root
        target = resolve_and_validate_path(rel_path, workspace_root=root)
        validate_file_size(target)
        
        # Check binary vs text
        try:
            content = target.read_text(encoding="utf-8")
            return {
                "path": str(target.relative_to(resolve_and_validate_path(root))).replace("\\", "/"),
                "content": content,
                "size_bytes": len(content.encode("utf-8")),
                "is_binary": False
            }
        except UnicodeDecodeError:
            return {
                "path": str(target.relative_to(resolve_and_validate_path(root))).replace("\\", "/"),
                "content": "[Binary file content]",
                "size_bytes": target.stat().st_size,
                "is_binary": True
            }

    def compute_diff(self, file_path: str, new_content: str, custom_root: Optional[str] = None) -> ProposedFileChange:
        """Calculates a standard unified diff between current file content and proposed changes."""
        root = resolve_and_validate_path(custom_root or settings.workspace_root)
        target = resolve_and_validate_path(file_path, workspace_root=root, allow_creation=True)
        rel_str = str(target.relative_to(root)).replace("\\", "/")

        orig_content = ""
        if target.exists() and target.is_file():
            orig_content = target.read_text(encoding="utf-8", errors="replace")

        orig_lines = orig_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            orig_lines,
            new_lines,
            fromfile=f"a/{rel_str}",
            tofile=f"b/{rel_str}",
            lineterm=""
        ))
        diff_str = "".join(diff)

        explanation = f"Proposed update to {rel_str} ({len(new_lines)} lines)."
        if not orig_content:
            explanation = f"Proposed new file creation for {rel_str} ({len(new_lines)} lines)."

        return ProposedFileChange(
            path=rel_str,
            original_content=orig_content,
            new_content=new_content,
            diff=diff_str,
            explanation=explanation
        )

    async def create_task(self, task_description: str, workspace_path: Optional[str] = None) -> CodingTaskResponse:
        """Creates a tracked coding task."""
        task_id = str(uuid.uuid4())
        root = str(resolve_and_validate_path(workspace_path or settings.workspace_root))
        now = datetime.datetime.now().isoformat()

        await db.execute(
            """
            INSERT INTO coding_tasks (id, workspace_path, task_description, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (task_id, root, task_description, "planning", now)
        )

        return CodingTaskResponse(
            id=task_id,
            workspace_path=root,
            task_description=task_description,
            status="planning",
            created_at=now
        )

    async def submit_plan_and_diff(
        self,
        task_id: str,
        plan: str,
        affected_files: List[str],
        diff_content: str
    ) -> None:
        """Updates task with proposed plan, affected files, and diff awaiting approval."""
        await db.execute(
            """
            UPDATE coding_tasks
            SET plan = ?, affected_files_json = ?, diff_content = ?, status = 'awaiting_approval'
            WHERE id = ?
            """,
            (plan, json.dumps(affected_files), diff_content, task_id)
        )

    async def apply_changes(
        self,
        task_id: str,
        file_changes: List[Dict[str, str]], # [{"path": rel_path, "content": new_content}]
        approved: bool = True
    ) -> Dict[str, Any]:
        """Applies approved changes to workspace files and records task completion."""
        task = await db.fetchone("SELECT * FROM coding_tasks WHERE id = ?", (task_id,))
        if not task:
            raise ValueError(f"Task {task_id} not found.")

        if not approved:
            await db.execute("UPDATE coding_tasks SET status = 'rejected' WHERE id = ?", (task_id,))
            return {"status": "rejected", "message": "Code changes were rejected by user."}

        root = resolve_and_validate_path(task["workspace_path"])
        applied_files = []

        for change in file_changes:
            rel_path = change["path"]
            content = change["content"]
            target = resolve_and_validate_path(rel_path, workspace_root=root, allow_creation=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            applied_files.append(rel_path)

        now = datetime.datetime.now().isoformat()
        await db.execute(
            """
            UPDATE coding_tasks
            SET status = 'applied', completed_at = ?
            WHERE id = ?
            """,
            (now, task_id)
        )

        return {
            "status": "applied",
            "applied_files": applied_files,
            "completed_at": now
        }

    async def run_test_suite(
        self,
        task_id: str,
        command: str = "pytest"
    ) -> Dict[str, Any]:
        """Executes test runner on workspace and updates task record."""
        task = await db.fetchone("SELECT * FROM coding_tasks WHERE id = ?", (task_id,))
        if not task:
            raise ValueError(f"Task {task_id} not found.")

        root = task["workspace_path"]
        result = await run_command_safely(command, cwd=root, timeout=60, approved=True)

        # Update command logs
        logs = json.loads(task["command_logs_json"] or "[]")
        logs.append(result.to_dict())

        new_status = "completed" if result.exit_code == 0 else "failed"
        await db.execute(
            """
            UPDATE coding_tasks
            SET status = ?, command_logs_json = ?
            WHERE id = ?
            """,
            (new_status, json.dumps(logs), task_id)
        )

        return result.to_dict()

    async def get_git_status(self, custom_root: Optional[str] = None) -> GitStatusResult:
        """Inspects git status in the workspace if initialized."""
        root = resolve_and_validate_path(custom_root or settings.workspace_root)
        if not (root / ".git").exists():
            return GitStatusResult(is_git_repo=False, clean=True)

        status_res = await run_command_safely("git status --porcelain", cwd=root, timeout=15)
        diff_res = await run_command_safely("git diff", cwd=root, timeout=15)
        branch_res = await run_command_safely("git rev-parse --abbrev-ref HEAD", cwd=root, timeout=15)

        lines = [line.strip() for line in status_res.stdout.splitlines() if line.strip()]
        modified = [line[3:] for line in lines if not line.startswith("??")]
        untracked = [line[3:] for line in lines if line.startswith("??")]

        return GitStatusResult(
            is_git_repo=True,
            branch=branch_res.stdout.strip() if branch_res.exit_code == 0 else "main",
            clean=len(lines) == 0,
            modified=modified,
            untracked=untracked,
            diff=diff_res.stdout
        )

coding_agent_service = CodingAgentService()
