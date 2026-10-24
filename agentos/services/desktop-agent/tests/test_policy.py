import pytest
from pathlib import Path
from app.policy import (
    REGISTERED_TOOLS,
    validate_tool_name,
    validate_workspace_path,
    validate_screen_coordinates,
    validate_text_input,
    check_step_approval_requirement,
    PolicyViolation
)
from app.config import settings


def test_registered_tools_allowlist():
    assert "get_screen_info" in REGISTERED_TOOLS
    assert "browser_navigate" in REGISTERED_TOOLS
    assert "run_approved_command" in REGISTERED_TOOLS

    # Valid tool passes
    validate_tool_name("take_screenshot")

    # Unknown tool fails
    with pytest.raises(PolicyViolation) as exc_info:
        validate_tool_name("rm_rf_root")
    assert "not in the approved desktop tool registry" in str(exc_info.value)


def test_workspace_path_restrictions(tmp_path):
    orig_ws = settings.allowed_workspace
    try:
        settings.allowed_workspace = tmp_path
        # Inside workspace is allowed
        inside = validate_workspace_path("subfolder/file.txt")
        assert inside == (tmp_path / "subfolder/file.txt").resolve()

        # Path traversal outside workspace is blocked
        with pytest.raises(PolicyViolation) as exc_info:
            validate_workspace_path("../../../outside.txt")
        assert "outside the allowed sandbox" in str(exc_info.value)

        # Empty path is blocked
        with pytest.raises(PolicyViolation):
            validate_workspace_path("")
    finally:
        settings.allowed_workspace = orig_ws


def test_screen_coordinates_validation():
    # Valid coordinates
    validate_screen_coordinates(100, 200, 1920, 1080)

    # Negative coordinates
    with pytest.raises(PolicyViolation):
        validate_screen_coordinates(-5, 200, 1920, 1080)

    # Out of bounds coordinates
    with pytest.raises(PolicyViolation) as exc_info:
        validate_screen_coordinates(2000, 500, 1920, 1080)
    assert "fall outside detected screen boundaries" in str(exc_info.value)


def test_text_input_length_limit():
    validate_text_input("hello world")
    huge_text = "a" * 6000
    with pytest.raises(PolicyViolation):
        validate_text_input(huge_text, max_chars=5000)


def test_approval_required_operations():
    # Safe operations do not require approval
    appr, _ = check_step_approval_requirement("get_screen_info", {})
    assert appr is False

    appr, _ = check_step_approval_requirement("browser_navigate", {"url": "https://example.com"})
    assert appr is False

    # Risky operations DO require approval
    appr, reason = check_step_approval_requirement("write_text_file", {"path": "test.txt", "content": "hi"})
    assert appr is True
    assert "File write/overwrite requested" in reason

    appr, reason = check_step_approval_requirement("run_approved_command", {"command_id": "pytest"})
    assert appr is True
    assert "Terminal command execution requested" in reason

    appr, reason = check_step_approval_requirement("open_application", {"app_name": "Terminal"})
    assert appr is True
    assert "sensitive system application" in reason
