import pytest
from pathlib import Path
from app.core.config import settings
from app.core.security import (
    resolve_and_validate_path,
    validate_file_size,
    evaluate_command_safety,
    PathTraversalError,
    SecurityError
)

def test_resolve_valid_path_in_workspace(tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    f = sub / "test.txt"
    f.write_text("hello", encoding="utf-8")

    res = resolve_and_validate_path("subdir/test.txt", workspace_root=tmp_path)
    assert res == f.resolve()

def test_reject_path_traversal_parent_escape(tmp_path):
    with pytest.raises(PathTraversalError):
        resolve_and_validate_path("../outside.txt", workspace_root=tmp_path)

def test_reject_null_bytes(tmp_path):
    with pytest.raises(PathTraversalError):
        resolve_and_validate_path("test\0evil.txt", workspace_root=tmp_path)

def test_reject_absolute_path_outside_workspace(tmp_path):
    outside = Path("C:/Windows/System32/calc.exe")
    with pytest.raises(PathTraversalError):
        resolve_and_validate_path(str(outside), workspace_root=tmp_path)

def test_validate_file_size_limit(tmp_path):
    f = tmp_path / "large.bin"
    f.write_bytes(b"x" * 1000)

    # Allow 2000 bytes
    size = validate_file_size(f, max_bytes=2000)
    assert size == 1000

    # Reject 500 bytes limit
    with pytest.raises(SecurityError):
        validate_file_size(f, max_bytes=500)

def test_command_safety_allowed(tmp_path):
    is_safe, reason = evaluate_command_safety("pytest", cwd=tmp_path, workspace_root=tmp_path)
    assert is_safe is True

def test_command_safety_blocked_system_destructive(tmp_path):
    is_safe, reason = evaluate_command_safety("format c: /fs:ntfs", cwd=tmp_path, workspace_root=tmp_path)
    assert is_safe is False
    assert "blocked" in reason.lower()

def test_command_safety_blocked_privilege_escalation(tmp_path):
    is_safe, reason = evaluate_command_safety("runas /user:Administrator cmd.exe", cwd=tmp_path, workspace_root=tmp_path)
    assert is_safe is False
    assert "privilege escalation" in reason.lower()

def test_command_safety_blocked_invalid_cwd(tmp_path):
    is_safe, reason = evaluate_command_safety("dir", cwd="C:/Windows/System32")
    assert is_safe is False
