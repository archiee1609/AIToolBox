import os
import urllib.parse
from pathlib import Path
from typing import Union, Optional, Tuple
from app.core.config import settings
from app.core.logging import logger

BLOCKED_COMMAND_SUBSTRINGS = [
    # Windows destructive system commands
    "format ",
    "diskpart",
    "reg delete",
    "reg add",
    "bcdedit",
    "shutdown",
    "net user",
    "takeown",
    "icacls /grant",
    "del /f /s /q c:\\",
    "del /f /s /q %windir%",
    "rmdir /s /q c:\\",
    "rmdir /s /q %windir%",
    
    # Linux & macOS destructive filesystem commands
    "rm -rf /",
    "rm -fr /",
    "rm -rf /*",
    "rm -fr /*",
    "rm -rf ~",
    "rm -fr ~",
    "chmod -r 777 /",
    "chmod 777 /",
    "chown -r ",
    "reboot",
    "poweroff",
    "init 0",
    "init 6",
    "halt",
    
    # Raw disk & fork bomb operations
    "wipefs",
    "mkfs",
    ":(){ :|:& };:", # fork bomb
    "dd if=",
]

class SecurityError(Exception):
    pass

class PathTraversalError(SecurityError):
    pass

class CommandPolicyError(SecurityError):
    pass

def resolve_and_validate_path(
    target_path: Union[str, Path],
    workspace_root: Optional[Union[str, Path]] = None,
    allow_creation: bool = False
) -> Path:
    """
    Validates that target_path resolves strictly within workspace_root.
    Resolves symlinks, prevents relative escapes and null bytes.
    """
    root = Path(workspace_root or settings.workspace_root).resolve()
    
    if isinstance(target_path, str):
        # Decode URL / percent-encoded sequences (e.g. %2e%2e%2f or double-encoded %252e)
        unquoted = urllib.parse.unquote(target_path)
        if "%" in unquoted:
            unquoted = urllib.parse.unquote(unquoted)
        if "\0" in unquoted:
            raise PathTraversalError("Null byte detected in path.")
        p = Path(unquoted)
    else:
        p = target_path

    # If relative, anchor to root
    if not p.is_absolute():
        p = root / p
        
    resolved = p.resolve()
    
    # Strict boundary check
    try:
        resolved.relative_to(root)
    except ValueError:
        raise PathTraversalError(f"Access denied: path '{resolved}' escapes workspace root '{root}'.")
        
    # If file doesn't exist and creation is not allowed
    if not allow_creation and not resolved.exists():
        # verify parent exists and is inside root
        if not resolved.parent.exists():
            raise FileNotFoundError(f"Path does not exist: {resolved}")
            
    return resolved

def validate_file_size(file_path: Path, max_bytes: Optional[int] = None) -> int:
    max_limit = max_bytes or settings.max_attachment_size_bytes
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    size = file_path.stat().st_size
    if size > max_limit:
        raise SecurityError(
            f"File '{file_path.name}' size ({size} bytes) exceeds maximum permitted limit ({max_limit} bytes)."
        )
    return size

def evaluate_command_safety(
    command: str,
    cwd: Union[str, Path],
    workspace_root: Optional[Union[str, Path]] = None
) -> Tuple[bool, str]:
    """
    Evaluates whether a command is safe to execute in the specified cwd.
    Returns (is_safe, reason).
    """
    if not command or not command.strip():
        return False, "Command cannot be empty."

    # Validate cwd is inside workspace
    try:
        resolved_cwd = resolve_and_validate_path(cwd, workspace_root=workspace_root)
        if not resolved_cwd.is_dir():
            return False, f"Working directory does not exist or is not a directory: {resolved_cwd}"
    except Exception as e:
        return False, f"Invalid working directory: {str(e)}"

    cmd_lower = command.lower().strip()
    
    # Check blocked destructive system operations
    for blocked in BLOCKED_COMMAND_SUBSTRINGS:
        if blocked in cmd_lower:
            return False, f"Command contains blocked high-risk pattern: '{blocked}'"

    # Block administrative privilege escalation attempts (Windows RunAs & POSIX sudo/su/doas)
    escalation_patterns = [
        "runas",
        "start-process -verb runas",
        "sudo ",
        "su -",
        "su ",
        "doas ",
        "pkexec "
    ]
    if any(pat in cmd_lower for pat in escalation_patterns) or cmd_lower in ["sudo", "su", "doas", "pkexec"]:
        return False, "Privilege escalation (Administrator / sudo / su / root) is strictly forbidden."

    return True, "Command passed security checks."
