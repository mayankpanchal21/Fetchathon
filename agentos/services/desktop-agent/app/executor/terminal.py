import subprocess
import logging
from typing import Dict, Any, Optional
from ..policy import APPROVED_COMMAND_TEMPLATES, PolicyViolation
from ..config import settings, MONOREPO_ROOT

logger = logging.getLogger("agentos.executor.terminal")


def run_approved_command(command_id: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes an approved, predefined command template with structured arguments.
    Never accepts arbitrary shell string inputs.
    """
    if command_id not in APPROVED_COMMAND_TEMPLATES:
        raise PolicyViolation(
            f"Command ID '{command_id}' is not an approved command template. "
            f"Approved commands: {list(APPROVED_COMMAND_TEMPLATES.keys())}"
        )

    template = APPROVED_COMMAND_TEMPLATES[command_id]
    base_cmd = list(template["command_args"])
    args = arguments or {}

    # Determine execution working directory
    target_dir = settings.allowed_workspace
    if "directory" in args:
        from ..policy import validate_workspace_path
        target_dir = validate_workspace_path(args["directory"], allow_read_only_cwd=True)

    # Customize known templates with validated arguments
    if command_id == "python_script":
        script_name = args.get("script")
        if not script_name:
            raise PolicyViolation("Argument 'script' is required for python_script template.")
        from ..policy import validate_workspace_path
        script_path = validate_workspace_path(script_name, allow_read_only_cwd=True)
        base_cmd.append(str(script_path))

    elif command_id == "pytest":
        if "test_target" in args:
            base_cmd.append(args["test_target"])

    logger.info(f"Running approved command [{command_id}]: {base_cmd} in cwd={target_dir}")

    try:
        proc = subprocess.run(
            base_cmd,
            cwd=str(target_dir),
            capture_output=True,
            text=True,
            timeout=45
        )
        return {
            "command_id": command_id,
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-5000:],  # Truncate to last 5000 chars for safety
            "stderr": proc.stderr[-5000:],
            "success": proc.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {
            "command_id": command_id,
            "exit_code": -1,
            "stdout": "",
            "stderr": "Command execution timed out after 45 seconds.",
            "success": False
        }
    except Exception as e:
        logger.error(f"Error executing command template '{command_id}': {e}")
        return {
            "command_id": command_id,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "success": False
        }
