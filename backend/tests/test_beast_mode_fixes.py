import ast
import io
import pytest
from pathlib import Path
from app.services.ollama_service import OllamaGenerateResponse
from app.services.document_service import extract_file_data, process_uploaded_files
from app.services.coding_agent_service import CodingAgentService
from app.services.tool_registry import safe_eval_math
from app.core.security import resolve_and_validate_path, PathTraversalError


def test_ollama_generate_response_compatibility():
    """Verify OllamaGenerateResponse seamlessly supports .response, str(), dict access, and string operations."""
    raw_dict = {
        "model": "deepseek-r1:8b",
        "response": "Here is the architectural review.\n1. Scalability\n2. Modularity",
        "total_duration": 4500000000
    }
    resp = OllamaGenerateResponse(raw_dict["response"], raw=raw_dict)

    # 1. Direct attribute access (used in streamlit_app.py)
    assert resp.response == raw_dict["response"]

    # 2. String subclass behaviors
    assert isinstance(resp, str)
    assert str(resp) == raw_dict["response"]
    assert f"Summary: {resp}" == f"Summary: {raw_dict['response']}"
    assert resp.startswith("Here is")

    # 3. Dict-style access
    assert resp["response"] == raw_dict["response"]
    assert resp["model"] == "deepseek-r1:8b"
    assert resp.get("total_duration") == 4500000000
    assert resp.get("non_existent", "default_val") == "default_val"


def test_document_service_binary_and_spreadsheet_protection():
    """Verify binary files and spreadsheets are parsed safely without injecting corrupt unicode."""
    # 1. Null-byte binary file
    binary_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"
    res_bin = extract_file_data("payload.bin", binary_bytes)
    assert res_bin["type"] == "binary"
    assert "binary contents omitted" in res_bin["text"]

    # 2. Corrupted / non-pdf file with .pdf extension shouldn't crash
    corrupt_pdf = b"%PDF-1.4\ncorrupted bytes\x00\xff\xfe"
    res_pdf = extract_file_data("damaged.pdf", corrupt_pdf)
    assert res_pdf["type"] == "document"
    assert "text" in res_pdf

    # 3. Spreadsheet mock
    res_xls = extract_file_data("sheet.xlsx", b"not-a-valid-zip-file")
    assert res_xls["type"] == "document"
    assert "Spreadsheet" in res_xls["text"] or "openpyxl" in res_xls["text"]


def test_safe_eval_math_bounds():
    """Verify exponential complexity and division by zero are guarded against DoS."""
    # Normal math
    node_normal = ast.parse("2 + 3 * 4", mode="eval").body
    assert safe_eval_math(node_normal) == 14

    # Exponent too large
    node_huge_exp = ast.parse("2 ** 99999", mode="eval").body
    with pytest.raises(ValueError, match="Exponent or base too large"):
        safe_eval_math(node_huge_exp)

    # Division by zero
    node_zero_div = ast.parse("100 / 0", mode="eval").body
    with pytest.raises(ZeroDivisionError):
        safe_eval_math(node_zero_div)


def test_security_url_encoded_path_traversal(tmp_path):
    """Verify URL-encoded and double-encoded path traversal attacks are rejected."""
    workspace = tmp_path / "sandbox"
    workspace.mkdir()

    # Percent-encoded ..%2f..%2f
    with pytest.raises(PathTraversalError):
        resolve_and_validate_path("..%2f..%2fWindows%2fSystem32", workspace_root=workspace)

    # Double percent-encoded %252e%252e
    with pytest.raises(PathTraversalError):
        resolve_and_validate_path("%252e%252e%252fsecret.txt", workspace_root=workspace)

    # Encoded null byte
    with pytest.raises(PathTraversalError):
        resolve_and_validate_path("file.txt%00.png", workspace_root=workspace)


def test_coding_agent_stat_resilience(tmp_path, monkeypatch):
    """Verify CodingAgentService.list_workspace_files ignores files that raise OSError during iteration."""
    workspace = tmp_path / "code_ws"
    workspace.mkdir()
    f1 = workspace / "valid.py"
    f1.write_text("x = 1", encoding="utf-8")
    f2 = workspace / "ghost.py"
    f2.write_text("y = 2", encoding="utf-8")

    agent = CodingAgentService()

    # Monkeypatch Path.stat to raise OSError on ghost.py simulating broken symlink/concurrent deletion
    orig_stat = Path.stat
    def mock_stat(self, *args, **kwargs):
        if self.name == "ghost.py":
            raise OSError("Simulated broken symlink / file deleted concurrently")
        return orig_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", mock_stat)

    tree = agent.list_workspace_files(custom_root=str(workspace))
    file_names = [f.name for f in tree.files]
    assert "valid.py" in file_names
    assert "ghost.py" not in file_names
