import pytest
from app.services.coding_agent_service import coding_agent_service
from app.core.config import settings

@pytest.mark.asyncio
async def test_compute_diff_and_apply_changes():
    # 1. Create a dummy file in workspace
    test_file = settings.workspace_root / "sample_code.py"
    test_file.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")

    # 2. Compute unified diff
    new_code = "def add(a, b):\n    return a + b\n"
    diff_res = coding_agent_service.compute_diff("sample_code.py", new_code)
    assert "-    return a - b" in diff_res.diff
    assert "+    return a + b" in diff_res.diff

    # 3. Create coding task
    task = await coding_agent_service.create_task("Fix subtraction bug in add function")
    assert task.status == "planning"

    # 4. Submit plan and diff
    await coding_agent_service.submit_plan_and_diff(
        task_id=task.id,
        plan="Change minus to plus operator",
        affected_files=["sample_code.py"],
        diff_content=diff_res.diff
    )

    # 5. Apply changes with approval
    apply_res = await coding_agent_service.apply_changes(
        task_id=task.id,
        file_changes=[{"path": "sample_code.py", "content": new_code}],
        approved=True
    )
    assert apply_res["status"] == "applied"

    # 6. Verify file content on disk
    updated_content = test_file.read_text(encoding="utf-8")
    assert "return a + b" in updated_content

    # Cleanup
    if test_file.exists():
        test_file.unlink()

def test_list_workspace_tree():
    tree = coding_agent_service.list_workspace_files()
    assert tree.workspace_root == str(settings.workspace_root)
    assert isinstance(tree.files, list)
