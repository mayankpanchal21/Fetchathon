import pytest
from app.planner import create_task_plan, _local_deterministic_plan, TaskPlan, TaskStepPlan
from app.policy import PolicyViolation


def test_deterministic_browser_planning():
    plan = _local_deterministic_plan("Open Chrome and visit example.com")
    assert isinstance(plan, TaskPlan)
    assert len(plan.steps) >= 2
    assert plan.steps[0].tool == "open_application"
    assert "Chrome" in plan.steps[0].arguments["app_name"]
    assert plan.steps[1].tool == "browser_navigate"
    assert "example.com" in plan.steps[1].arguments["url"]


def test_deterministic_folder_creation_planning():
    plan = _local_deterministic_plan("Create a folder called HackathonDemo in my Documents directory")
    assert isinstance(plan, TaskPlan)
    assert len(plan.steps) >= 1
    assert plan.steps[0].tool == "create_directory"
    assert "Documents/HackathonDemo" in plan.steps[0].arguments["path"]
    assert plan.requires_approval is True


def test_approval_propagation_in_planner():
    plan = create_task_plan("Open Terminal and run the tests in my selected project")
    assert isinstance(plan, TaskPlan)
    # Terminal or command execution requires approval
    assert plan.requires_approval is True
    assert plan.status == "waiting_approval"


def test_reject_unknown_tool_in_step():
    with pytest.raises(PolicyViolation):
        TaskStepPlan(step_id=1, tool="malicious_tool", arguments={})
