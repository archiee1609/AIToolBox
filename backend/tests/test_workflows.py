import pytest
from app.services.workflow_service import workflow_service
from app.schemas.automation import WorkflowCreate, WorkflowStep
from app.core.config import settings

@pytest.mark.asyncio
async def test_workflow_crud_and_preview():
    step1 = WorkflowStep(
        id="s1",
        action_type="read_files",
        parameters={"folder": "", "pattern": "*.txt"}
    )
    step2 = WorkflowStep(
        id="s2",
        action_type="write_file",
        parameters={"output_path": "summary.txt"},
        require_confirmation=True
    )

    wf_create = WorkflowCreate(
        name="Test Workflow",
        description="A test automation workflow",
        steps=[step1, step2],
        enabled=True
    )

    # Create
    wf = await workflow_service.create_workflow(wf_create)
    assert wf.id is not None
    assert wf.name == "Test Workflow"
    assert len(wf.steps) == 2

    # Preview
    preview = workflow_service.preview_workflow(wf)
    assert preview.valid is True
    assert len(preview.action_previews) == 2
    assert len(preview.sensitive_steps_requiring_approval) == 1

    # Clean up
    await workflow_service.delete_workflow(wf.id)
