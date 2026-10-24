import re
import json
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

from .llm.asi1_client import ASI1Client, ModelTier, ModelConfigError
from .policy import (
    REGISTERED_TOOLS,
    validate_tool_name,
    check_step_approval_requirement,
    PolicyViolation
)

logger = logging.getLogger("agentos.planner")


class TaskStepPlan(BaseModel):
    step_id: int
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    status: str = "pending"  # pending, waiting_approval, running, completed, failed, rejected
    result: Optional[Any] = None
    error: Optional[str] = None
    verification_notes: Optional[str] = None

    @field_validator("tool")
    def check_tool_valid(cls, v: str) -> str:
        validate_tool_name(v)
        return v


class TaskPlan(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_request: str
    goal: str
    requires_approval: bool = False
    current_step_index: int = 0
    status: str = "planned"  # planned, waiting_approval, running, completed, failed, cancelled
    steps: List[TaskStepPlan]
    logs: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    verification_result: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    planner_source: str = "Local Rule Planner (Demo Mode)"

    def add_log(self, message: str, level: str = "info", step_id: Optional[int] = None):
        self.logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "step_id": step_id,
            "message": message
        })
        self.updated_at = datetime.utcnow().isoformat()


PLANNER_SYSTEM_PROMPT = """You are AgentOS Planner, an autonomous AI desktop operator powered by Fetch.ai's ASI:One model.
Transform the user's desktop request into a validated, structured sequence of tool actions.

REGISTERED TOOLS:
- get_screen_info(): Get current display resolution and OS details.
- take_screenshot(): Capture current screen image.
- open_application(app_name): Launch desktop app (e.g. Chrome, VS Code, Terminal).
- click(x, y, button): Click at coordinates.
- move_mouse(x, y): Move cursor to coordinates.
- type_text(text, press_enter): Type keyboard characters.
- press_key(key): Press specific key (enter, escape, tab, etc).
- scroll(direction, amount): Scroll 'up' or 'down'.
- list_files(directory): List directory contents in workspace.
- search_files(directory, query): Find files matching name/extension.
- create_directory(path): Create directory in workspace.
- read_text_file(path): Read text file contents in workspace.
- write_text_file(path, content): Create or overwrite file in workspace.
- browser_open(url): Open browser via Playwright.
- browser_navigate(url): Navigate to specific URL.
- browser_get_page_content(): Extract page text and title.
- run_approved_command(command_id, arguments): Run approved template ('pytest', 'npm_test', 'git_status', 'python_script').

SAFETY RULES:
1. ONLY select tools from the registered list above.
2. NEVER output arbitrary shell scripts or destructive disk commands.
3. Keep plans focused, efficient, and sequential (maximum 10 steps).

OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching this schema:
{
  "goal": "Brief description of the objective",
  "steps": [
    {
      "step_id": 1,
      "tool": "tool_name",
      "arguments": { "arg_name": "value" }
    }
  ]
}
"""


def _local_deterministic_plan(user_request: str) -> TaskPlan:
    """
    Deterministic rule-based planner for local development and offline demo mode
    when ASI1_API_KEY is not yet supplied.
    """
    req_lower = user_request.lower().strip()
    steps: List[TaskStepPlan] = []
    goal = f"Execute desktop request: {user_request}"

    # 1. Browser navigation / Open website
    if any(k in req_lower for k in ["visit", "navigate", "open chrome", "browse", "website", "url", ".com", ".org", "http"]):
        url_match = re.search(r'(https?://[^\s]+|[a-zA-Z0-9-]+\.(?:com|org|io|net|edu|ai|app)[^\s]*)', user_request)
        target_url = url_match.group(0) if url_match else "https://example.com"
        if not target_url.startswith("http"):
            target_url = "https://" + target_url
        goal = f"Open Chrome and navigate to {target_url}"
        # Launches the real system Google Chrome / browser with target URL
        steps.append(TaskStepPlan(step_id=1, tool="open_application", arguments={"app_name": "Google Chrome", "url": target_url}))
        steps.append(TaskStepPlan(step_id=2, tool="browser_navigate", arguments={"url": target_url}))
        steps.append(TaskStepPlan(step_id=3, tool="browser_get_page_content", arguments={}))

    # 2. Screenshot
    elif any(k in req_lower for k in ["screenshot", "screen capture", "what is on my screen"]):
        goal = "Capture screen and analyze display context"
        steps.append(TaskStepPlan(step_id=1, tool="get_screen_info", arguments={}))
        steps.append(TaskStepPlan(step_id=2, tool="take_screenshot", arguments={}))

    # 3. Create folder / directory
    elif any(k in req_lower for k in ["create a folder", "make a folder", "create folder", "mkdir", "create directory"]):
        # Extract folder name: prioritize 'called <name>' or 'named <name>'
        name_match = re.search(r'(?:called|named)\s+([a-zA-Z0-9_-]+)', user_request, re.IGNORECASE)
        if not name_match:
            name_match = re.search(r'(?:folder|directory)\s+([a-zA-Z0-9_-]+)', user_request, re.IGNORECASE)
        folder_name = name_match.group(1) if name_match else "HackathonDemo"

        # Check if user explicitly asked for Documents or Desktop on their laptop
        if "document" in req_lower:
            target_path = f"~/Documents/{folder_name}"
            goal = f"Create directory '{folder_name}' in user Documents directory"
        elif "desktop" in req_lower:
            target_path = f"~/Desktop/{folder_name}"
            goal = f"Create directory '{folder_name}' on user Desktop"
        else:
            target_path = folder_name
            goal = f"Create directory '{folder_name}' in workspace"

        steps.append(TaskStepPlan(step_id=1, tool="create_directory", arguments={"path": target_path}))
        steps.append(TaskStepPlan(step_id=2, tool="list_files", arguments={"directory": target_path}))

    # 4. Open VS Code or inspect
    elif any(k in req_lower for k in ["vs code", "vscode", "code"]):
        goal = "Open Visual Studio Code and inspect project files"
        steps.append(TaskStepPlan(step_id=1, tool="open_application", arguments={"app_name": "Visual Studio Code"}))
        steps.append(TaskStepPlan(step_id=2, tool="list_files", arguments={"directory": "."}))

    # 5. Open Terminal and run tests
    elif any(k in req_lower for k in ["run tests", "pytest", "test my project", "run the tests", "test"]):
        goal = "Open Terminal and execute test suite"
        steps.append(TaskStepPlan(step_id=1, tool="open_application", arguments={"app_name": "Terminal"}))
        steps.append(TaskStepPlan(step_id=2, tool="run_approved_command", arguments={"command_id": "pytest"}))

    # 6. Find / search file
    elif any(k in req_lower for k in ["find a file", "search for", "find file", "where is"]):
        words = user_request.split()
        query = words[-1] if words else "test"
        query = query.strip("?\"'.,")
        goal = f"Search files matching '{query}'"
        steps.append(TaskStepPlan(step_id=1, tool="search_files", arguments={"directory": ".", "query": query}))

    # 7. Write file
    elif any(k in req_lower for k in ["write file", "save file", "create file"]):
        filename = "demo.txt"
        words = user_request.split()
        for w in words:
            if "." in w and len(w) > 3:
                filename = w.strip("?\"'.,")
                break
        goal = f"Write text content to '{filename}'"
        steps.append(TaskStepPlan(
            step_id=1,
            tool="write_text_file",
            arguments={"path": filename, "content": "Created autonomously by AgentOS."}
        ))

    # Fallback: Safe screen inspection
    else:
        goal = f"Inspect system state for request: {user_request}"
        steps.append(TaskStepPlan(step_id=1, tool="get_screen_info", arguments={}))
        steps.append(TaskStepPlan(step_id=2, tool="take_screenshot", arguments={}))

    # Apply policy and approval inspection
    requires_approval = False
    for step in steps:
        req_appr, reason = check_step_approval_requirement(step.tool, step.arguments)
        step.requires_approval = req_appr
        step.approval_reason = reason
        if req_appr:
            requires_approval = True

    plan = TaskPlan(
        user_request=user_request,
        goal=goal,
        requires_approval=requires_approval,
        steps=steps,
        status="waiting_approval" if requires_approval else "planned",
        planner_source="Local Rule Planner (Configure ASI1_API_KEY for live Fetch.ai ASI:One reasoning)"
    )
    plan.add_log(f"Generated task plan with {len(steps)} steps.", level="info")
    return plan


def create_task_plan(user_request: str) -> TaskPlan:
    """
    Generate and validate a structured TaskPlan using Fetch.ai ASI:One API
    with seamless local deterministic fallback.
    """
    client = ASI1Client()

    if not client.is_configured:
        logger.info("ASI1_API_KEY not present; using local deterministic planner.")
        return _local_deterministic_plan(user_request)

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": f"User Request: {user_request}"}
    ]

    try:
        raw_json_str = client.complete(messages, response_format={"type": "json_object"})
        data = json.loads(raw_json_str)
        goal = data.get("goal", user_request)
        raw_steps = data.get("steps", [])

        if not raw_steps:
            raise ValueError("ASI:One returned plan with 0 steps.")

        validated_steps: List[TaskStepPlan] = []
        overall_requires_approval = False

        for idx, s in enumerate(raw_steps, start=1):
            tool = s.get("tool", "")
            args = s.get("arguments", {})

            # Check tool allowlist
            validate_tool_name(tool)

            # Check approval requirements
            req_appr, reason = check_step_approval_requirement(tool, args)
            if req_appr:
                overall_requires_approval = True

            validated_steps.append(TaskStepPlan(
                step_id=idx,
                tool=tool,
                arguments=args,
                requires_approval=req_appr,
                approval_reason=reason
            ))

        plan = TaskPlan(
            user_request=user_request,
            goal=goal,
            requires_approval=overall_requires_approval,
            steps=validated_steps,
            status="waiting_approval" if overall_requires_approval else "planned",
            planner_source=f"Fetch.ai ASI:One ({client.default_model})"
        )
        plan.add_log(f"Generated validated plan with {len(validated_steps)} steps via ASI:One.", level="info")
        return plan

    except Exception as e:
        logger.warning(f"ASI:One planning failed ({e}); falling back to local deterministic planner.")
        fallback = _local_deterministic_plan(user_request)
        fallback.add_log(f"Notice: Live ASI:One planning encountered error ({e}); used local planner fallback.", level="warning")
        return fallback
