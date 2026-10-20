import pytest
from app.services.tool_registry import tool_registry
from app.core.config import settings

@pytest.mark.asyncio
async def test_calculator_valid():
    res = await tool_registry.execute_tool("calculator", {"expression": "25 * 4 + 10"})
    assert res.status == "success"
    assert res.result["result"] == 110

@pytest.mark.asyncio
async def test_calculator_invalid_syntax():
    res = await tool_registry.execute_tool("calculator", {"expression": "import os"})
    assert res.status == "error"

@pytest.mark.asyncio
async def test_datetime_tool():
    res = await tool_registry.execute_tool("get_current_datetime", {})
    assert res.status == "success"
    assert "formatted" in res.result
    assert "date" in res.result

@pytest.mark.asyncio
async def test_validate_json_tool():
    valid_res = await tool_registry.execute_tool("validate_and_format_json", {"json_string": '{"name": "test", "val": 123}'})
    assert valid_res.status == "success"
    assert valid_res.result["valid"] is True

    invalid_res = await tool_registry.execute_tool("validate_and_format_json", {"json_string": '{bad json}'})
    assert invalid_res.status == "success"
    assert invalid_res.result["valid"] is False

@pytest.mark.asyncio
async def test_file_write_and_read_tools():
    # Write file
    write_res = await tool_registry.execute_tool(
        "write_workspace_file",
        {"path": "test_note.txt", "content": "Sample content for testing."},
        approved=True
    )
    assert write_res.status == "success"

    # Read file back
    read_res = await tool_registry.execute_tool(
        "read_workspace_file",
        {"path": "test_note.txt"}
    )
    assert read_res.status == "success"
    assert "Sample content for testing." in read_res.result["content"]

    # Search file
    search_res = await tool_registry.execute_tool(
        "search_workspace_files",
        {"pattern": "*test_note*"}
    )
    assert search_res.status == "success"
    assert len(search_res.result["matches"]) >= 1

    # Clean up test file
    test_file = settings.workspace_root / "test_note.txt"
    if test_file.exists():
        test_file.unlink()

@pytest.mark.asyncio
async def test_unregistered_tool():
    res = await tool_registry.execute_tool("nonexistent_tool", {})
    assert res.status == "error"
    assert "not registered" in res.error
