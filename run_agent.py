"""
ASI:One Desktop Operator Agent (Official Fetch.ai uAgent Specification)
========================================================================
Built in accordance with the official ASI:One documentation (https://asi1.ai)
and Fetch.ai uAgents framework.

Capabilities:
- Fully Headless (NO FRONTEND)
- Auto-generates public HTTPS Endpoint URL for uagents & Agentverse
- Exposes ASI:One Agent Card (/.well-known/agent.json)
- Full physical macOS & Windows desktop control:
    * Applications (Google Chrome, VS Code, Notes, Calculator, Terminal)
    * Web Browser visible automation (Playwright headful)
    * Filesystem management (~/Desktop, ~/Documents)
    * Mouse, Keyboard, and Screen Capture (PyAutoGUI)
- ASI:One LLM Reasoning (https://api.asi1.ai/v1, model: asi1)

Usage:
    python run_agent.py
"""

import os
import sys
import time
import asyncio
import logging
import subprocess
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any, Optional, List

# Workspace and service paths
WORKSPACE_ROOT = Path(__file__).resolve().parent
AGENTOS_DIR = WORKSPACE_ROOT / "agentos"
DESKTOP_SERVICE_DIR = AGENTOS_DIR / "services" / "desktop-agent"

sys.path.insert(0, str(DESKTOP_SERVICE_DIR))

# Load .env
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

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [ASI1-Agent]: %(message)s"
)
logger = logging.getLogger("asi1.desktop_agent")

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

# Desktop Automation & Planning Engine
from app.config import get_detected_os, settings
from app.planner import create_task_plan, TaskPlan, TaskStepPlan
from app.executor.applications import open_application
from app.executor.mouse_keyboard import move_mouse, click, type_text, press_key, scroll
from app.executor.screen import get_screen_info, take_screenshot
from app.executor.files import list_files, search_files, create_directory, read_text_file, write_text_file
from app.executor.browser import browser_manager
from app.executor.terminal import run_approved_command

# Configuration
AGENT_NAME = os.getenv("AGENT_NAME", "ASI-One-Desktop-Operator")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8001"))
AGENT_SEED = os.getenv("AGENT_SEED_PHRASE", "asi1-fetchai-desktop-operator-seed-2026")
AGENT_MAILBOX_KEY = os.getenv("AGENT_MAILBOX_KEY", "").strip() or None


# =============================================================================
# Automatic Live Public HTTPS URL Generation (localtunnel / ngrok)
# =============================================================================
def generate_public_tunnel_url(port: int) -> Optional[str]:
    """Generates a live public HTTPS URL so other agents/Agentverse can connect."""
    # Check if user specified explicit AGENT_ENDPOINT in .env
    custom_endpoint = os.getenv("AGENT_ENDPOINT", "").strip()
    if custom_endpoint and not custom_endpoint.startswith("http://127.0.0.1"):
        return custom_endpoint.replace("/submit", "")

    # Try localtunnel via npx
    try:
        proc = subprocess.Popen(
            ["npx", "-y", "localtunnel", "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        for _ in range(30):
            line = proc.stdout.readline()
            if "your url is:" in line:
                url = line.split("your url is:")[1].strip()
                logger.info(f"Generated Live Public Tunnel URL: {url}")
                return url
            time.sleep(0.2)
    except Exception as e:
        logger.warning(f"Could not auto-start localtunnel: {e}")

    return None


PUBLIC_BASE_URL = generate_public_tunnel_url(AGENT_PORT) or f"http://127.0.0.1:{AGENT_PORT}"
AGENT_ENDPOINT = f"{PUBLIC_BASE_URL}/submit"

# Initialize Fetch.ai Agent
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

# Official Chat Protocol
chat_proto = Protocol(
    name=chat_protocol_spec.name,
    version=chat_protocol_spec.version,
)


# =============================================================================
# REST Models (Per ASI:One & Fetch.ai Specification)
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
    public_url: str
    endpoint_url: str
    operating_system: str
    architecture: str
    screen_resolution: str
    asi1_configured: bool
    asi1_model: str


class AgentSkill(Model):
    id: str
    name: str
    description: str


class AgentProvider(Model):
    organization: str
    url: str


class AgentCardResponse(Model):
    name: str
    description: str
    url: str
    version: str
    skills: List[AgentSkill]


# =============================================================================
# Desktop Execution Core
# =============================================================================
async def execute_step(step: TaskStepPlan) -> Dict[str, Any]:
    tool = step.tool
    args = step.arguments
    logger.info(f"Running step {step.step_id}: {tool}({args})")

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
    start_time = time.time()
    logger.info(f"Reasoning task with ASI:One: '{prompt}'")
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
        f"Model: {plan.planner_source}\n"
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
# Fetch.ai Chat Protocol Handlers
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
    logger.info(f"Incoming ChatMessage from {sender} (id: {msg.msg_id})")

    # Step 1: Immediate acknowledgement
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
                content=[TextContent(text="Empty desktop instruction received."), EndSessionContent()]
            )
        )
        return

    # Step 3: Execute on laptop
    result = await run_desktop_task(user_prompt)

    # Step 4: Return response
    icon = "✅" if result["status"] == "success" else "⚠️"
    reply_text = f"{icon} **ASI:One Desktop Execution Report:**\n\n{result['summary']}"

    await ctx.send(
        sender,
        ChatMessage(
            msg_id=uuid4(),
            timestamp=datetime.utcnow(),
            content=[TextContent(text=reply_text), EndSessionContent()]
        )
    )
    logger.info(f"Sent completion response to {sender}.")


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    logger.info(f"Received ack from {sender} for msg_id: {msg.acknowledged_msg_id}")


# =============================================================================
# REST Endpoints
# =============================================================================
@agent.on_rest_post("/api/task", TaskRequest, TaskResponse)
async def handle_rest_task(ctx: Context, req: TaskRequest) -> TaskResponse:
    """Direct task execution via HTTP POST."""
    logger.info(f"REST POST Task: '{req.prompt}'")
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


@agent.on_rest_get("/api/status", StatusResponse)
async def handle_rest_status(ctx: Context) -> StatusResponse:
    """Agent and host desktop status."""
    os_info = get_detected_os()
    screen = get_screen_info()
    return StatusResponse(
        agent_name=AGENT_NAME,
        agent_address=agent.address,
        public_url=PUBLIC_BASE_URL,
        endpoint_url=AGENT_ENDPOINT,
        operating_system=os_info["os_name"],
        architecture=os_info["architecture"],
        screen_resolution=f"{screen.get('width', 0)}x{screen.get('height', 0)}",
        asi1_configured=bool(settings.asi1_api_key),
        asi1_model=settings.asi1_model
    )


@agent.on_rest_get("/.well-known/agent.json", AgentCardResponse)
async def handle_agent_card(ctx: Context) -> AgentCardResponse:
    """Official ASI:One Agent Card Discovery Endpoint (https://asi1.ai/.well-known/agent.json)."""
    return AgentCardResponse(
        name="ASI:One Desktop Operator",
        description="Autonomous desktop operator powered by Fetch.ai ASI:One LLM. Controls native applications, web browser, mouse, keyboard, and files on macOS and Windows.",
        url=PUBLIC_BASE_URL,
        version="1.0.0",
        skills=[
            AgentSkill(id="desktop-applications", name="Application Management", description="Opens and coordinates desktop apps (Chrome, VS Code, Notes, Calculator, Terminal)."),
            AgentSkill(id="browser-navigation", name="Visible Web Navigation", description="Visibly opens Chrome/Chromium and navigates to target URLs."),
            AgentSkill(id="filesystem-management", name="Filesystem Management", description="Creates directories and manages files in ~/Desktop and ~/Documents."),
            AgentSkill(id="mouse-keyboard", name="Physical Mouse & Keyboard", description="Clicks, moves cursor, types text, and presses keys via PyAutoGUI."),
            AgentSkill(id="screen-inspection", name="Screen Capture & Info", description="Reads display geometry and takes full screenshots.")
        ]
    )


# =============================================================================
# Startup Banner & Info
# =============================================================================
@agent.on_event("startup")
async def on_startup(ctx: Context):
    os_info = get_detected_os()
    screen = get_screen_info()

    inspector_url = f"https://agentverse.ai/inspect/?uri={PUBLIC_BASE_URL}&address={agent.address}"

    print("\n" + "=" * 70)
    print("🤖 ASI:One Desktop Operator Agent (NO FRONTEND)")
    print("   Built with Fetch.ai uAgents & ASI:One LLM Reasoning")
    print("=" * 70)
    print(f"• Agent Name:            {AGENT_NAME}")
    print(f"• Agent Address:         {agent.address}")
    print(f"• Generated Endpoint:    {AGENT_ENDPOINT}  <-- [GIVE THIS IN UAGENT]")
    print(f"• Public Base URL:       {PUBLIC_BASE_URL}")
    print(f"• Agentverse Inspector:  {inspector_url}")
    print(f"• ASI:One Agent Card:    {PUBLIC_BASE_URL}/.well-known/agent.json")
    print(f"• Direct REST Task URL:  {PUBLIC_BASE_URL}/api/task")
    print(f"• Status URL:            {PUBLIC_BASE_URL}/api/status")
    print(f"• Operating System:      {os_info['os_name']} ({os_info['architecture']})")
    print(f"• Screen Canvas:         {screen.get('width')}x{screen.get('height')}")
    print(f"• ASI:One Model:         {settings.asi1_model} (Live API Active)")
    print("=" * 70)
    print("📋 Copy & Paste this Endpoint into Agentverse / uAgents:")
    print(f"   {AGENT_ENDPOINT}")
    print("=" * 70)
    print("💡 Or send a direct test task via curl:")
    print(f'   curl -X POST {PUBLIC_BASE_URL}/api/task \\')
    print('        -H "Content-Type: application/json" \\')
    print('        -d \'{"prompt": "Open Chrome and visit fetch.ai"}\'')
    print("=" * 70 + "\n")


# Attach Chat Protocol
agent.include(chat_proto, publish_manifest=True)


if __name__ == "__main__":
    agent.run()
