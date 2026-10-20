import asyncio
import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

from app.core.config import settings
from app.core.logging import logger
from app.core.security import evaluate_command_safety, CommandPolicyError

class CommandResult:
    def __init__(
        self,
        command: str,
        cwd: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        duration_ms: int,
        approved: bool = True
    ):
        self.command = command
        self.cwd = cwd
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration_ms = duration_ms
        self.approved = approved

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "cwd": self.cwd,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "approved": self.approved,
            "success": self.exit_code == 0
        }

async def run_command_safely(
    command: Union[str, List[str]],
    cwd: Optional[Union[str, Path]] = None,
    timeout: Optional[int] = None,
    approved: bool = False,
    record_audit: bool = True
) -> CommandResult:
    """
    Executes a command safely within the authorized workspace.
    Validates safety, enforces timeouts, captures output, and logs to audit trail.
    """
    cmd_str = command if isinstance(command, str) else " ".join(command)
    work_dir = Path(cwd or settings.workspace_root).resolve()
    actual_timeout = timeout or settings.command_timeout_seconds

    # Validate security policy
    is_safe, reason = evaluate_command_safety(cmd_str, work_dir)
    if not is_safe:
        logger.warning(f"Command execution blocked by security policy: {reason} | Command: {cmd_str}")
        raise CommandPolicyError(f"Security validation failed: {reason}")

    start_time = time.time()
    logger.info(f"Executing command safely: '{cmd_str}' in cwd '{work_dir}'")

    try:
        # Use asyncio create_subprocess_shell with proper shell execution for Windows commands
        proc = await asyncio.create_subprocess_shell(
            cmd_str,
            cwd=str(work_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            # Windows specific flags to prevent popups
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(),
            timeout=float(actual_timeout)
        )
        
        exit_code = proc.returncode if proc.returncode is not None else -1
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        
    except asyncio.TimeoutError:
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Command timed out after {actual_timeout}s: '{cmd_str}'")
        result = CommandResult(
            command=cmd_str,
            cwd=str(work_dir),
            exit_code=124,
            stdout="",
            stderr=f"Command execution timed out after {actual_timeout} seconds.",
            duration_ms=duration_ms,
            approved=approved
        )
        return result
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.exception(f"Unexpected error running command '{cmd_str}': {e}")
        return CommandResult(
            command=cmd_str,
            cwd=str(work_dir),
            exit_code=1,
            stdout="",
            stderr=f"Command execution failed: {str(e)}",
            duration_ms=duration_ms,
            approved=approved
        )

    duration_ms = int((time.time() - start_time) * 1000)
    result = CommandResult(
        command=cmd_str,
        cwd=str(work_dir),
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_ms=duration_ms,
        approved=approved
    )

    # Audit logging will be handled directly or called by caller with DB
    return result
