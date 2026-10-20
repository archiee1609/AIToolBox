import asyncio
import datetime
import json
import re
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.core.logging import logger
from app.core.security import resolve_and_validate_path, validate_file_size, SecurityError
from app.core.command_runner import run_command_safely
from app.database.connection import db
from app.services.ollama_service import ollama_service
from app.schemas.automation import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowRunResponse,
    WorkflowDryRunPreview,
    WorkflowStep
)

# In-memory dictionary of running workflow cancel tokens
ACTIVE_WORKFLOW_TASKS: Dict[str, asyncio.Task] = {}

class WorkflowService:
    async def create_workflow(self, req: WorkflowCreate) -> WorkflowResponse:
        workflow_id = str(uuid.uuid4())
        now = datetime.datetime.now().isoformat()
        steps_json = json.dumps([s.model_dump() for s in req.steps])

        await db.execute(
            """
            INSERT INTO workflows (id, name, description, steps_json, enabled, timeout_seconds, max_iterations, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                workflow_id,
                req.name,
                req.description or "",
                steps_json,
                1 if req.enabled else 0,
                req.timeout_seconds or 300,
                req.max_iterations or 10,
                now,
                now
            )
        )

        return await self.get_workflow(workflow_id)

    async def get_workflow(self, workflow_id: str) -> Optional[WorkflowResponse]:
        row = await db.fetchone("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
        if not row:
            return None
        
        steps_raw = json.loads(row["steps_json"] or "[]")
        steps = [WorkflowStep(**s) for s in steps_raw]

        return WorkflowResponse(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            steps=steps,
            enabled=bool(row["enabled"]),
            timeout_seconds=row["timeout_seconds"],
            max_iterations=row["max_iterations"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    async def list_workflows(self) -> List[WorkflowResponse]:
        rows = await db.fetchall("SELECT * FROM workflows ORDER BY updated_at DESC")
        result = []
        for row in rows:
            steps_raw = json.loads(row["steps_json"] or "[]")
            steps = [WorkflowStep(**s) for s in steps_raw]
            result.append(WorkflowResponse(
                id=row["id"],
                name=row["name"],
                description=row["description"] or "",
                steps=steps,
                enabled=bool(row["enabled"]),
                timeout_seconds=row["timeout_seconds"],
                max_iterations=row["max_iterations"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            ))
        return result

    async def update_workflow(self, workflow_id: str, req: WorkflowUpdate) -> Optional[WorkflowResponse]:
        existing = await self.get_workflow(workflow_id)
        if not existing:
            return None

        now = datetime.datetime.now().isoformat()
        name = req.name if req.name is not None else existing.name
        desc = req.description if req.description is not None else existing.description
        enabled = req.enabled if req.enabled is not None else existing.enabled
        timeout_s = req.timeout_seconds if req.timeout_seconds is not None else existing.timeout_seconds
        max_iters = req.max_iterations if req.max_iterations is not None else existing.max_iterations

        steps_json = json.dumps([s.model_dump() for s in (req.steps if req.steps is not None else existing.steps)])

        await db.execute(
            """
            UPDATE workflows
            SET name = ?, description = ?, steps_json = ?, enabled = ?, timeout_seconds = ?, max_iterations = ?, updated_at = ?
            WHERE id = ?
            """,
            (name, desc, steps_json, 1 if enabled else 0, timeout_s, max_iters, now, workflow_id)
        )
        return await self.get_workflow(workflow_id)

    async def delete_workflow(self, workflow_id: str) -> bool:
        await db.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
        return True

    def preview_workflow(self, workflow: WorkflowResponse) -> WorkflowDryRunPreview:
        """Performs static validation and dry-run preview of workflow steps."""
        errors: List[str] = []
        previews: List[Dict[str, Any]] = []
        requires_approval: List[str] = []

        if not workflow.steps:
            errors.append("Workflow has no steps defined.")

        for i, step in enumerate(workflow.steps):
            step_preview = {
                "step_index": i + 1,
                "action_type": step.action_type,
                "summary": "",
                "requires_confirmation": step.require_confirmation
            }

            if step.action_type == "read_files":
                folder = step.parameters.get("folder", "")
                pattern = step.parameters.get("pattern", "*")
                step_preview["summary"] = f"Scan folder '{folder}' for files matching '{pattern}'."
            elif step.action_type == "extract_info":
                field = step.parameters.get("regex_pattern", "all text")
                step_preview["summary"] = f"Extract text matching pattern '{field}' from input."
            elif step.action_type == "llm_transform":
                prompt_preview = step.parameters.get("prompt", "")[:60]
                model = step.parameters.get("model", settings.default_model)
                step_preview["summary"] = f"Prompt model '{model}' with '{prompt_preview}...' to process data."
            elif step.action_type == "write_file":
                output_file = step.parameters.get("output_path", "")
                step_preview["summary"] = f"Save transformed result to workspace file '{output_file}'."
                requires_approval.append(f"Step {i+1} (write_file: {output_file})")
            elif step.action_type == "run_test":
                cmd = step.parameters.get("command", "pytest")
                step_preview["summary"] = f"Execute test command: '{cmd}'."
                requires_approval.append(f"Step {i+1} (run_test: {cmd})")
            else:
                errors.append(f"Unknown action_type '{step.action_type}' in step {i+1}.")

            previews.append(step_preview)

        return WorkflowDryRunPreview(
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            valid=len(errors) == 0,
            validation_errors=errors,
            action_previews=previews,
            sensitive_steps_requiring_approval=requires_approval
        )

    async def execute_workflow(
        self,
        workflow_id: str,
        triggered_by: str = "user",
        confirmed_steps: bool = False
    ) -> WorkflowRunResponse:
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found.")
        if not workflow.enabled:
            raise ValueError(f"Workflow '{workflow.name}' is currently disabled.")

        run_id = str(uuid.uuid4())
        now = datetime.datetime.now().isoformat()
        start_time = time.time()

        await db.execute(
            """
            INSERT INTO workflow_runs (id, workflow_id, status, triggered_by, logs_json, result_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, workflow_id, "running", triggered_by, "[]", "{}", now)
        )

        logs: List[Dict[str, Any]] = []
        context: Dict[str, Any] = {"workflow_id": workflow_id, "run_id": run_id}
        error_msg: Optional[str] = None
        status = "completed"

        async def _log_step(step_name: str, message: str, detail: Any = None):
            logs.append({
                "timestamp": datetime.datetime.now().isoformat(),
                "step": step_name,
                "message": message,
                "detail": detail
            })
            await db.execute(
                "UPDATE workflow_runs SET logs_json = ? WHERE id = ?",
                (json.dumps(logs), run_id)
            )

        try:
            await _log_step("init", f"Starting workflow '{workflow.name}' with {len(workflow.steps)} steps.")

            for i, step in enumerate(workflow.steps):
                if i >= workflow.max_iterations:
                    raise RuntimeError(f"Workflow reached maximum iterations limit ({workflow.max_iterations}).")

                # Check confirmation requirement
                if step.require_confirmation and not confirmed_steps:
                    raise RuntimeError(f"Step {i+1} ({step.action_type}) requires explicit confirmation approval.")

                await _log_step(f"step_{i+1}", f"Executing action '{step.action_type}'")

                if step.action_type == "read_files":
                    folder = step.parameters.get("folder", "")
                    pattern = step.parameters.get("pattern", "*")
                    target_dir = resolve_and_validate_path(folder) if folder else settings.workspace_root
                    
                    collected = []
                    for f in target_dir.glob(pattern):
                        if f.is_file():
                            validate_file_size(f)
                            text = f.read_text(encoding="utf-8", errors="replace")
                            collected.append({
                                "filename": f.name,
                                "path": str(f.relative_to(settings.workspace_root)),
                                "content": text
                            })
                    context["files"] = collected
                    context["current_text"] = "\n\n".join([f["content"] for f in collected])
                    await _log_step(f"step_{i+1}", f"Read {len(collected)} files matching pattern '{pattern}'.")

                elif step.action_type == "extract_info":
                    pattern_str = step.parameters.get("regex_pattern")
                    raw_text = context.get("current_text", "")
                    if pattern_str:
                        matches = re.findall(pattern_str, raw_text)
                        context["extracted"] = matches
                        context["current_text"] = "\n".join(matches) if isinstance(matches[0] if matches else "", str) else json.dumps(matches)
                        await _log_step(f"step_{i+1}", f"Extracted {len(matches)} matches using regex.")
                    else:
                        context["extracted"] = raw_text
                        await _log_step(f"step_{i+1}", "Passed through full text content.")

                elif step.action_type == "llm_transform":
                    prompt = step.parameters.get("prompt", "Summarize this content:")
                    input_text = context.get("current_text", "")
                    model = step.parameters.get("model", settings.default_model)
                    full_prompt = f"{prompt}\n\n[INPUT DATA]:\n{input_text[:12000]}"
                    
                    llm_res = await ollama_service.chat(
                        model=model,
                        messages=[{"role": "user", "content": full_prompt}],
                        options={"temperature": 0.3}
                    )
                    out_content = llm_res.get("message", {}).get("content", "")
                    context["llm_output"] = out_content
                    context["current_text"] = out_content
                    await _log_step(f"step_{i+1}", f"LLM transformation completed using model '{model}'.")

                elif step.action_type == "write_file":
                    out_path = step.parameters.get("output_path", "workflow_output.txt")
                    target_file = resolve_and_validate_path(out_path, allow_creation=True)
                    content_to_write = context.get("current_text", "")
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    target_file.write_text(content_to_write, encoding="utf-8")
                    context["saved_file"] = str(target_file.relative_to(settings.workspace_root))
                    await _log_step(f"step_{i+1}", f"Successfully wrote {len(content_to_write)} characters to '{out_path}'.")

                elif step.action_type == "run_test":
                    test_cmd = step.parameters.get("command", "pytest")
                    cmd_res = await run_command_safely(test_cmd, cwd=settings.workspace_root, timeout=60, approved=True)
                    context["test_result"] = cmd_res.to_dict()
                    await _log_step(f"step_{i+1}", f"Test command '{test_cmd}' finished with exit code {cmd_res.exit_code}.")
                    if cmd_res.exit_code != 0:
                        raise RuntimeError(f"Test suite failed with exit code {cmd_res.exit_code}: {cmd_res.stderr}")

            await _log_step("finish", "Workflow execution completed successfully.")

        except asyncio.CancelledError:
            status = "cancelled"
            error_msg = "Workflow execution was cancelled by user."
            await _log_step("cancelled", error_msg)
        except Exception as e:
            status = "failed"
            error_msg = str(e)
            logger.exception(f"Workflow {workflow_id} failed: {e}")
            await _log_step("error", f"Failure: {error_msg}")

        duration_ms = int((time.time() - start_time) * 1000)
        await db.execute(
            """
            UPDATE workflow_runs
            SET status = ?, result_json = ?, error = ?, duration_ms = ?
            WHERE id = ?
            """,
            (status, json.dumps(context, default=str), error_msg, duration_ms, run_id)
        )

        return WorkflowRunResponse(
            id=run_id,
            workflow_id=workflow_id,
            status=status,
            triggered_by=triggered_by,
            logs=logs,
            result=context,
            error=error_msg,
            duration_ms=duration_ms,
            created_at=now
        )

    async def list_runs(self, workflow_id: Optional[str] = None) -> List[WorkflowRunResponse]:
        query = "SELECT * FROM workflow_runs"
        params = ()
        if workflow_id:
            query += " WHERE workflow_id = ?"
            params = (workflow_id,)
        query += " ORDER BY created_at DESC LIMIT 50"

        rows = await db.fetchall(query, params)
        res = []
        for r in rows:
            res.append(WorkflowRunResponse(
                id=r["id"],
                workflow_id=r["workflow_id"],
                status=r["status"],
                triggered_by=r["triggered_by"],
                logs=json.loads(r["logs_json"] or "[]"),
                result=json.loads(r["result_json"] or "{}"),
                error=r["error"],
                duration_ms=r["duration_ms"],
                created_at=r["created_at"]
            ))
        return res

workflow_service = WorkflowService()
