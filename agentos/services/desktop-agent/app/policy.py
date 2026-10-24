import os
import re
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Set
from .config import settings

# Registered Tools allowlist
REGISTERED_TOOLS: Set[str] = {
    "get_screen_info",
    "take_screenshot",
    "open_application",
    "click",
    "move_mouse",
    "type_text",
    "press_key",
    "scroll",
    "list_files",
    "search_files",
    "create_directory",
    "read_text_file",
    "write_text_file",
    "browser_open",
    "browser_navigate",
    "browser_get_page_content",
    "run_approved_command",
}

# Approved Command Templates (LLM can NEVER execute raw arbitrary commands)
APPROVED_COMMAND_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "pytest": {
        "description": "Run pytest suite inside the workspace or tests directory",
        "command_args": ["pytest", "-v"],
        "allowed_in_dir": True,
    },
    "npm_test": {
        "description": "Run npm test script inside frontend directory",
        "command_args": ["npm", "test"],
        "allowed_in_dir": True,
    },
    "git_status": {
        "description": "Inspect git status of current repository",
        "command_args": ["git", "status", "--short"],
        "allowed_in_dir": False,
    },
    "python_script": {
        "description": "Run verified python script within the allowed workspace",
        "command_args": ["python3"],
        "allowed_in_dir": True,
    }
}

class PolicyViolation(Exception):
    """Raised when an operation violates security boundaries or permissions."""
    pass


def validate_tool_name(tool_name: str) -> None:
    if tool_name not in REGISTERED_TOOLS:
        raise PolicyViolation(
            f"Tool '{tool_name}' is not in the approved desktop tool registry. "
            f"Available tools: {sorted(list(REGISTERED_TOOLS))}"
        )


ALLOWED_USER_ROOTS = [
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path.home() / "Downloads",
    Path.home(),
]


def validate_workspace_path(path_str: str, allow_read_only_cwd: bool = False) -> Path:
    """
    Enforces that filesystem paths resolve within the configured workspace
    or user-permitted personal folders (Documents, Desktop, Downloads).
    Prevents path traversal to sensitive system directories (/etc, C:\\Windows, etc.).
    """
    if not path_str or not path_str.strip():
        raise PolicyViolation("Path argument cannot be empty.")

    target = Path(path_str).expanduser()
    if not target.is_absolute():
        target = (settings.allowed_workspace / target).resolve()
    else:
        target = target.resolve()

    workspace = settings.allowed_workspace.resolve()

    # 1. Allowed if inside configured workspace
    try:
        target.relative_to(workspace)
        return target
    except ValueError:
        pass

    # 2. Allowed if inside project repository
    if allow_read_only_cwd:
        try:
            from .config import MONOREPO_ROOT
            target.relative_to(MONOREPO_ROOT.resolve())
            return target
        except ValueError:
            pass

    # 3. Allowed if inside user personal folders (Documents, Desktop, Downloads)
    for user_root in ALLOWED_USER_ROOTS:
        try:
            target.relative_to(user_root.resolve())
            return target
        except ValueError:
            pass

    raise PolicyViolation(
        f"Path '{path_str}' resolves to '{target}' which is outside the allowed sandbox. "
        f"Filesystem access is restricted to the workspace and personal folders (Documents, Desktop)."
    )


def validate_screen_coordinates(x: int, y: int, max_w: int, max_h: int) -> None:
    if x < 0 or x >= max_w or y < 0 or y >= max_h:
        raise PolicyViolation(
            f"Coordinates ({x}, {y}) fall outside detected screen boundaries (width: {max_w}, height: {max_h})."
        )


def validate_text_input(text: str, max_chars: int = 5000) -> None:
    if len(text) > max_chars:
        raise PolicyViolation(f"Input text exceeds maximum allowed length ({max_chars} characters).")


def check_step_approval_requirement(tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Determines whether a proposed step requires human approval.
    Destructive or state-modifying operations require approval.
    """
    if tool_name == "write_text_file":
        target = arguments.get("path", "unknown")
        return True, f"File write/overwrite requested for: '{target}'"

    if tool_name == "run_approved_command":
        cmd_id = arguments.get("command_id", "unknown")
        return True, f"Terminal command execution requested: template '{cmd_id}'"

    if tool_name == "create_directory":
        path_str = arguments.get("path", "")
        try:
            target = validate_workspace_path(path_str)
            try:
                target.relative_to(settings.allowed_workspace.resolve())
                return False, None
            except ValueError:
                return True, f"Creating directory in user folder: '{target}'"
        except PolicyViolation:
            return True, f"Creating directory outside standard workspace: '{path_str}'"

    if tool_name == "open_application":
        app_name = arguments.get("app_name", "").lower()
        risky_apps = ["terminal", "iterm", "cmd", "powershell", "system preferences", "settings", "keychain"]
        if any(r in app_name for r in risky_apps):
            return True, f"Opening sensitive system application: '{arguments.get('app_name')}'"
        return False, None

    # Mouse clicks and keyboard typing in default desktop use do not require approval
    # unless marked explicitly by the planner
    return False, None
