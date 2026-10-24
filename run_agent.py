"""
AgentOS — Standalone Fetch.ai uAgent for Desktop Automation (No Frontend)
=============================================================================
A self-contained Fetch.ai uAgent with a configurable endpoint URL for Agentverse,
ASI:One reasoning, and native cross-platform macOS & Windows desktop control.

Usage:
    python run_agent.py
"""

import os
import sys
import time
import asyncio
import logging
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add desktop-agent app directory to sys.path so executor modules resolve
WORKSPACE_ROOT = Path(__file__).resolve().parent
AGENTOS_DIR = WORKSPACE_ROOT / "agentos"
DESKTOP_SERVICE_DIR = AGENTOS_DIR / "services" / "desktop-agent"

sys.path.insert(0, str(DESKTOP_SERVICE_DIR))

# Load .env configuration
def load_env():
    env_paths = [
        AGENTOS_DIR / ".env",
        DESKTOP_SERVICE_DIR / ".env",
        WORKSPACE_ROOT / ".env"
    ]
    for p in env_paths:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
            break

load_env()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [AgentOS]: %(message)s"
)
logger = logging.getLogger("agentos.standalone_agent")

# uAgents Imports
from uagents import Agent, Context, Model
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
    EndSessionContent,
    chat_protocol_spec,
)
from uagents.protocol import Protocol

# Internal Desktop Engine Imports
from app.config import get_detected_os, settings
from app.planner import create_task_plan, TaskPlan, TaskStepPlan
from app.executor.applications import open_application
from app.executor.mouse_keyboard import move_mouse, click, type_text, press_key, scroll
from app.executor.screen import get_screen_info, take_screenshot
from app.executor.files import list_files, search_files, create_directory, read_text_file, write_text_file
from app.executor.browser import browser_manager
from app.executor.terminal import run_approved_command

# Configuration
AGENT_NAME = os.getenv("AGENT_NAME", "AgentOS-Desktop-Worker")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8000"))
AGENT_SEED = os.getenv("AGENT_SEED_PHRASE", "agentos-fetchai-desktop-operator-seed-2026")
AGENT_MAILBOX_KEY = os.getenv("AGENT_MAILBOX_KEY", "").strip() or None

# Configurable Agent Endpoint URL
DEFAULT_ENDPOINT = f"http://127.0.0.1:{AGENT_PORT}/submit"
AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT", DEFAULT_ENDPOINT).strip()

# Headless execution automatically approves user-directed desktop actions
AUTO_APPROVE = os.getenv("AUTO_APPROVE", "true").strip().lower() in ("true", "1", "yes")

# Initialize the Fetch.ai Agent
agent_kwargs = {
    "name": AGENT_NAME,
    "port": AGENT_PORT,
    "seed": AGENT_SEED,
    "endpoint": [AGENT_ENDPOINT],
}

if AGENT_MAILBOX_KEY:
    if AGENT_MAILBOX_KEY.lower() in ("true", "1", "yes"):
        agent_kwargs["mailbox"] = True
    else:
        mb_val = AGENT_MAILBOX_KEY if "@" in AGENT_MAILBOX_KEY else f"{AGENT_MAILBOX_KEY}@https://agentverse.ai"
        agent_kwargs["mailbox"] = mb_val
    agent_kwargs["publish_agent_details"] = True

agent = Agent(**agent_kwargs)

# Chat Protocol instance
chat_proto = Protocol(
    name=chat_protocol_spec.name,
    version=chat_protocol_spec.version,
)


# =============================================================================
# REST API Models (For HTTP Direct Access Without Frontend)
# =============================================================================
class TaskRequest(Model):
    prompt: str


class TaskResponse(Model):
    status: str
    goal: str
    planner_source: str
    steps_completed: int
    summary: str
    execution_time_sec: float
    platform: str


class StatusResponse(Model):
    agent_name: str
    agent_address: str
    endpoint_url: str
    operating_system: str
    architecture: str
    screen_resolution: str
    asi1_configured: bool
    asi1_model: str


# =============================================================================
# Execution Engine (Executes Steps on Real Laptop macOS & Windows)
# =============================================================================
async def execute_step(step: TaskStepPlan) -> Dict[str, Any]:
    tool = step.tool
    args = step.arguments
    logger.info(f"Executing step {step.step_id}: {tool}({args})")

    if tool == "get_screen_info":
        return get_screen_info()
    elif tool == "take_screenshot":
        return take_screenshot(output_name=args.get("output_name"))
    elif tool == "open_application":
        return open_application(app_name=args.get("app_name", ""), url=args.get("url"))
    elif tool == "click":
        return click(x=int(args.get("x", 0)), y=int(args.get("y", 0)), button=args.get("button", "left"))
    elif tool == "move_mouse":
        return move_mouse(x=int(args.get("x", 0)), y=int(args.get("y", 0)))
    elif tool == "type_text":
        return type_text(text=args.get("text", ""), press_enter=bool(args.get("press_enter", False)))
    elif tool == "press_key":
        return press_key(key=args.get("key", ""))
    elif tool == "scroll":
        return scroll(direction=args.get("direction", "down"), amount=int(args.get("amount", 3)))
    elif tool == "list_files":
        return list_files(directory=args.get("directory", "."))
    elif tool == "search_files":
        return search_files(directory=args.get("directory", "."), query=args.get("query", ""))
    elif tool == "create_directory":
        return create_directory(path=args.get("path", ""))
    elif tool == "read_text_file":
        return read_text_file(path=args.get("path", ""))
    elif tool == "write_text_file":
        return write_text_file(path=args.get("path", ""), content=args.get("content", ""))
    elif tool == "browser_open":
        return await browser_manager.browser_open(url=args.get("url"))
    elif tool == "browser_navigate":
        return await browser_manager.browser_navigate(url=args.get("url", ""))
    elif tool == "browser_get_page_content":
        return await browser_manager.browser_get_page_content()
    elif tool == "run_approved_command":
        return run_approved_command(command_id=args.get("command_id", ""), arguments=args.get("arguments"))
    else:
        raise ValueError(f"Unmapped tool: {tool}")


async def run_desktop_task(prompt: str) -> Dict[str, Any]:
    """Takes a natural language request, plans it via ASI:One, and executes it on the laptop."""
    start_time = time.time()
    logger.info(f"Generating plan for request: '{prompt}'")
    plan = create_task_plan(prompt)

    completed_steps = 0
    step_summaries = []

    for step in plan.steps:
        try:
            result = await execute_step(step)
            completed_steps += 1
            step_summaries.append(f"✓ Step {step.step_id} ({step.tool}): Success")
        except Exception as e:
            logger.error(f"Error in step {step.step_id} ({step.tool}): {e}")
            step_summaries.append(f"✗ Step {step.step_id} ({step.tool}): Failed ({e})")
            break

    elapsed = round(time.time() - start_time, 2)
    os_info = get_detected_os()

    summary_text = (
        f"Goal: {plan.goal}\n"
        f"Planner: {plan.planner_source}\n"
        f"Completed {completed_steps}/{len(plan.steps)} steps in {elapsed}s on {os_info['os_name']}.\n"
        + "\n".join(step_summaries)
    )

    return {
        "status": "success" if completed_steps == len(plan.steps) else "partial",
        "goal": plan.goal,
        "planner_source": plan.planner_source,
        "steps_completed": completed_steps,
        "total_steps": len(plan.steps),
        "summary": summary_text,
        "execution_time_sec": elapsed,
        "platform": os_info["os_name"]
    }


# =============================================================================
# Interface 1: Official Fetch.ai Chat Protocol Handlers
# =============================================================================
def extract_text_from_chat_msg(msg: ChatMessage) -> str:
    parts = []
    for item in msg.content:
        if isinstance(item, TextContent):
            parts.append(item.text)
        elif isinstance(item, dict) and item.get("type") == "text":
            parts.append(item.get("text", ""))
    return " ".join(parts).strip()


@chat_proto.on_message(ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    """Handles ChatMessage sent from other uAgents, Agentverse, or ASI:One chat."""
    logger.info(f"Received ChatMessage from {sender} (id: {msg.msg_id})")

    # Step 1: Send acknowledgement
    ack = ChatAcknowledgement(
        msg_id=uuid4(),
        acknowledged_msg_id=msg.msg_id,
        timestamp=datetime.utcnow()
    )
    await ctx.send(sender, ack)

    # Step 2: Extract prompt
    user_prompt = extract_text_from_chat_msg(msg)
    if not user_prompt:
        await ctx.send(
            sender,
            ChatMessage(
                msg_id=uuid4(),
                timestamp=datetime.utcnow(),
                content=[TextContent(text="Received empty command."), EndSessionContent()]
            )
        )
        return

    # Step 3: Execute on real laptop
    result = await run_desktop_task(user_prompt)

    # Step 4: Send formatted report back
    icon = "✅" if result["status"] == "success" else "⚠️"
    reply_text = f"{icon} **AgentOS Laptop Execution Report:**\n\n{result['summary']}"

    await ctx.send(
        sender,
        ChatMessage(
            msg_id=uuid4(),
            timestamp=datetime.utcnow(),
            content=[TextContent(text=reply_text), EndSessionContent()]
        )
    )
    logger.info(f"Replied to {sender} with execution summary.")


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    logger.info(f"Received ack from {sender} for msg_id: {msg.acknowledged_msg_id}")


# =============================================================================
# Interface 2: Direct REST POST API (/api/task)
# =============================================================================
@agent.on_rest_post("/api/task", TaskRequest, TaskResponse)
async def handle_rest_task(ctx: Context, req: TaskRequest) -> TaskResponse:
    """Execute a task via direct HTTP POST without needing frontend."""
    logger.info(f"Received REST POST task: '{req.prompt}'")
    res = await run_desktop_task(req.prompt)
    return TaskResponse(
        status=res["status"],
        goal=res["goal"],
        planner_source=res["planner_source"],
        steps_completed=res["steps_completed"],
        summary=res["summary"],
        execution_time_sec=res["execution_time_sec"],
        platform=res["platform"]
    )


# =============================================================================
# Interface 3: Direct REST GET API (/api/status)
# =============================================================================
@agent.on_rest_get("/api/status", StatusResponse)
async def handle_rest_status(ctx: Context) -> StatusResponse:
    """Get system and agent status."""
    os_info = get_detected_os()
    screen = get_screen_info()
    return StatusResponse(
        agent_name=AGENT_NAME,
        agent_address=agent.address,
        endpoint_url=AGENT_ENDPOINT,
        operating_system=os_info["os_name"],
        architecture=os_info["architecture"],
        screen_resolution=f"{screen.get('width', 0)}x{screen.get('height', 0)}",
        asi1_configured=bool(settings.asi1_api_key),
        asi1_model=settings.asi1_model
    )


# =============================================================================
# Startup Banner
# =============================================================================
@agent.on_event("startup")
async def on_startup(ctx: Context):
    os_info = get_detected_os()
    screen = get_screen_info()
    has_asi1 = bool(settings.asi1_api_key)

    print("\n" + "=" * 65)
    print("🤖 AgentOS — Fetch.ai Desktop Automation Agent (NO FRONTEND)")
    print("=" * 65)
    print(f"• Agent Name:     {AGENT_NAME}")
    print(f"• Agent Address:  {agent.address}")
    print(f"• Endpoint URL:   {AGENT_ENDPOINT}")
    print(f"• Listening Port: {AGENT_PORT}")
    print(f"• REST Task API:  http://127.0.0.1:{AGENT_PORT}/api/task")
    print(f"• Status API:     http://127.0.0.1:{AGENT_PORT}/api/status")
    print(f"• Operating Sys:  {os_info['os_name']} ({os_info['architecture']})")
    print(f"• Screen Canvas:  {screen.get('width')}x{screen.get('height')}")
    print(f"• ASI:One Model:  {settings.asi1_model} (Configured: {has_asi1})")
    if AGENT_MAILBOX_KEY:
        print(f"• Mailbox Status: Connected to Agentverse")
    else:
        print(f"• Network Mode:   Direct Endpoint Mode (Pass Endpoint URL to other agents/Agentverse)")
    print("=" * 65)
    print("💡 You can provide the Endpoint URL above in uAgents / Agentverse / DeltaV.")
    print("💡 Or send tasks via curl:")
    print(f'   curl -X POST http://127.0.0.1:{AGENT_PORT}/api/task \\')
    print('        -H "Content-Type: application/json" \\')
    print('        -d \'{"prompt": "Open Chrome and visit example.com"}\'')
    print("=" * 65 + "\n")


# Attach Chat Protocol
agent.include(chat_proto, publish_manifest=True)


if __name__ == "__main__":
    agent.run()
