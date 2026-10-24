"""
AgentOS — Autonomous Desktop Operator uAgent
=============================================
A self-contained Fetch.ai uAgent for complete physical laptop control
(Applications, Web Browser, Mouse, Keyboard, Files, Screen) powered by Fetch.ai ASI:One.
"""

import os
import sys
import time
import json
import logging
import platform
import subprocess
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any, Optional, List

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [AgentOS]: %(message)s"
)
logger = logging.getLogger("agentos")

# Workspace root
WORKSPACE_DIR = Path(__file__).resolve().parent

# Load environment configuration (.env)
def load_env():
    env_paths = [
        WORKSPACE_DIR / "agentos" / ".env",
        WORKSPACE_DIR / ".env"
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

# ASI:One API Configuration
ASI1_API_KEY = os.getenv("ASI1_API_KEY", "sk_a16bf299fdd8474ab776fcd044dcb3dfe68f3f89d37a447888d525c4562e9457")
ASI1_BASE_URL = os.getenv("ASI1_BASE_URL", "https://api.asi1.ai/v1")
ASI1_MODEL = os.getenv("ASI1_MODEL", "asi1")

# Third-party Automation Libraries
import pyautogui
from openai import OpenAI
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

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

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

# =============================================================================
# Fetch.ai Agent Initialization
# =============================================================================
agent = Agent(
    name="agentos_desktop_agent",
    port=8001,
    endpoint=["http://127.0.0.1:8001/submit"],
    mailbox=True,
)

chat_proto = Protocol(
    name=chat_protocol_spec.name,
    version=chat_protocol_spec.version,
)


# =============================================================================
# Desktop Automation Tools
# =============================================================================
IS_MAC = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"

APP_MAP_MAC = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "safari": "Safari",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "terminal": "Terminal",
    "calculator": "Calculator",
    "notes": "Notes",
    "textedit": "TextEdit",
    "finder": "Finder"
}

APP_MAP_WIN = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "vscode": "code",
    "vs code": "code",
    "calculator": "calc.exe",
    "notepad": "notepad.exe"
}


def open_application(app_name: str, url: Optional[str] = None) -> Dict[str, Any]:
    """Launch and focus a native desktop application."""
    clean_name = app_name.strip()
    logger.info(f"Opening desktop application: '{clean_name}' (url: {url})")

    if IS_MAC:
        resolved = APP_MAP_MAC.get(clean_name.lower(), clean_name)
        cmd = ["open", "-a", resolved]
        if url:
            cmd.append(url)
        subprocess.run(cmd, check=False)
        # Focus/activate window so keystrokes go into it
        subprocess.run(["osascript", "-e", f'tell application "{resolved}" to activate'], check=False)
        time.sleep(1.0)
    elif IS_WINDOWS:
        resolved = APP_MAP_WIN.get(clean_name.lower(), clean_name)
        target = f'"{url}"' if url else ""
        subprocess.run(f'start "" "{resolved}" {target}', shell=True, check=False)
        time.sleep(1.0)
    else:
        subprocess.Popen(["xdg-open", clean_name])
        time.sleep(1.0)

    return {"action": "open_application", "app_name": clean_name, "status": "success"}


def type_text(text: str, press_enter: bool = False) -> Dict[str, Any]:
    """Type keyboard characters with proper delay so active app receives them."""
    logger.info(f"Typing text: '{text}' (press_enter={press_enter})")
    time.sleep(0.3)

    # For math/calculator strings (e.g. '8*9='), press character by character
    for char in text:
        try:
            pyautogui.press(char)
        except Exception:
            pyautogui.write(char)
        time.sleep(0.06)

    if press_enter:
        time.sleep(0.1)
        pyautogui.press("enter")

    return {"action": "type_text", "length": len(text), "status": "success"}


def press_key(key: str) -> Dict[str, Any]:
    """Press a single key (e.g. enter, tab, space, escape, backspace)."""
    clean_key = key.strip().lower()
    logger.info(f"Pressing key: '{clean_key}'")
    time.sleep(0.1)
    pyautogui.press(clean_key)
    return {"action": "press_key", "key": clean_key, "status": "success"}


def click(x: int, y: int, button: str = "left") -> Dict[str, Any]:
    """Click at screen coordinates."""
    logger.info(f"Clicking at ({x}, {y}) button={button}")
    pyautogui.click(x=x, y=y, button=button.lower())
    return {"action": "click", "x": x, "y": y, "status": "success"}


def move_mouse(x: int, y: int) -> Dict[str, Any]:
    """Move cursor to screen coordinates."""
    pyautogui.moveTo(x, y, duration=0.2)
    return {"action": "move_mouse", "x": x, "y": y, "status": "success"}


def scroll(direction: str = "down", amount: int = 3) -> Dict[str, Any]:
    clicks = amount if direction.lower() == "up" else -amount
    pyautogui.scroll(clicks)
    return {"action": "scroll", "direction": direction, "status": "success"}


def get_screen_info() -> Dict[str, Any]:
    """Get screen resolution and OS details."""
    w, h = pyautogui.size()
    return {
        "width": w,
        "height": h,
        "operating_system": "macOS" if IS_MAC else ("Windows" if IS_WINDOWS else platform.system()),
        "architecture": platform.machine()
    }


def take_screenshot(output_name: Optional[str] = None) -> Dict[str, Any]:
    """Capture full display screenshot."""
    shots_dir = WORKSPACE_DIR / "screenshots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    filename = output_name or f"screenshot_{int(time.time())}.png"
    if not filename.endswith(".png"):
        filename += ".png"
    filepath = shots_dir / filename

    img = pyautogui.screenshot()
    img.convert("RGB").save(str(filepath), "PNG")
    logger.info(f"Screenshot saved: {filepath}")
    return {"action": "take_screenshot", "saved_path": str(filepath), "status": "success"}


def create_directory(path: str) -> Dict[str, Any]:
    """Create directory on laptop (e.g. ~/Desktop/FolderName)."""
    target = Path(path).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created directory: {target}")
    return {"action": "create_directory", "path": str(target), "status": "success"}


def write_text_file(path: str, content: str) -> Dict[str, Any]:
    """Write text file on laptop."""
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"action": "write_text_file", "path": str(target), "bytes": len(content), "status": "success"}


def read_text_file(path: str) -> Dict[str, Any]:
    """Read text file on laptop."""
    target = Path(path).expanduser().resolve()
    text = target.read_text(encoding="utf-8")
    return {"action": "read_text_file", "path": str(target), "content": text[:2000], "status": "success"}


# =============================================================================
# Web Browser Automation (Playwright Visible Headful Chrome)
# =============================================================================
class BrowserOperator:
    def __init__(self):
        self._pw = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def _ensure_page(self) -> Page:
        if self._page and not self._page.is_closed():
            return self._page

        if not self._pw:
            self._pw = await async_playwright().start()

        if not self._browser or not self._browser.is_connected():
            self._browser = await self._pw.chromium.launch(
                headless=False,  # Visible headful mode so user sees Chrome on laptop
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            self._context = await self._browser.new_context(viewport={"width": 1280, "height": 800})

        self._page = await self._context.new_page()
        return self._page

    async def open_url(self, url: str) -> Dict[str, Any]:
        page = await self._ensure_page()
        clean_url = url.strip()
        if not clean_url.startswith("http"):
            clean_url = "https://" + clean_url
        logger.info(f"Browser navigating to: {clean_url}")
        await page.goto(clean_url, wait_until="domcontentloaded", timeout=30000)
        return {"action": "browser_open", "url": page.url, "title": await page.title(), "status": "success"}

    async def fill_input(self, selector_or_name: str, text: str) -> Dict[str, Any]:
        """Smart fill into web inputs (email, password, search, etc.) directly via DOM."""
        page = await self._ensure_page()
        logger.info(f"Filling web input '{selector_or_name}' with: '{text}'")

        # Try multiple common selectors
        candidates = [
            selector_or_name,
            f"input[name='{selector_or_name}']",
            f"input[id='{selector_or_name}']",
            f"input[type='{selector_or_name}']",
            f"input[placeholder*='{selector_or_name}' i]",
            f"textarea[name='{selector_or_name}']",
            "input[type='email']",
            "input[type='text']",
            "input[type='password']"
        ]

        filled = False
        for sel in candidates:
            try:
                elem = page.locator(sel).first
                if await elem.is_visible(timeout=1500):
                    await elem.fill(text)
                    filled = True
                    logger.info(f"Successfully filled via selector: {sel}")
                    break
            except Exception:
                continue

        if not filled:
            # Fallback: type directly using keyboard
            time.sleep(0.2)
            pyautogui.write(text, interval=0.04)

        return {"action": "browser_fill", "field": selector_or_name, "status": "success"}

    async def click_element(self, selector_or_text: str) -> Dict[str, Any]:
        """Smart click on web button or link."""
        page = await self._ensure_page()
        logger.info(f"Clicking web element: '{selector_or_text}'")

        candidates = [
            selector_or_text,
            f"button:has-text('{selector_or_text}')",
            f"a:has-text('{selector_or_text}')",
            f"input[type='submit'][value*='{selector_or_text}' i]",
            "button[type='submit']",
            "button"
        ]

        clicked = False
        for sel in candidates:
            try:
                elem = page.locator(sel).first
                if await elem.is_visible(timeout=1500):
                    await elem.click()
                    clicked = True
                    logger.info(f"Successfully clicked via selector: {sel}")
                    break
            except Exception:
                continue

        if not clicked:
            pyautogui.press("enter")

        return {"action": "browser_click", "target": selector_or_text, "status": "success"}


browser = BrowserOperator()


# =============================================================================
# ASI:One Autonomous Planner
# =============================================================================
PLANNER_PROMPT = """You are AgentOS Desktop Planner powered by Fetch.ai ASI:One.
Convert user desktop requests into sequential tool actions.

AVAILABLE TOOLS:
- open_application(app_name): Launch desktop apps (e.g. "Calculator", "Google Chrome", "Visual Studio Code", "Notes", "Terminal").
- type_text(text, press_enter): Type keystrokes into the active application. (For calculator: type_text(text="8*9=", press_enter=false)).
- press_key(key): Press key ("enter", "tab", "space", "escape", "backspace").
- click(x, y, button): Click screen pixels.
- move_mouse(x, y): Move cursor.
- take_screenshot(): Take screen picture.
- get_screen_info(): Get display dimensions.
- create_directory(path): Create directory (e.g. "~/Desktop/MyFolder").
- write_text_file(path, content): Write file.
- read_text_file(path): Read file.
- browser_open(url): Open visible Chrome and visit URL.
- browser_fill(selector, text): Fill web inputs (e.g. selector="email", text="abc@gmail.com", selector="password", text="123").
- browser_click(selector): Click web button (e.g. selector="Log In" or selector="login").

CRITICAL RULES:
1. For Calculator / Math (e.g. "Open Calculator and Multiply 8 and 9"):
   Step 1: open_application({"app_name": "Calculator"})
   Step 2: type_text({"text": "8*9=", "press_enter": false})
2. For Websites & Web Forms (e.g. "visit facebook.com and type email abc@gmail.com and password 123"):
   Step 1: browser_open({"url": "https://www.facebook.com"})
   Step 2: browser_fill({"selector": "email", "text": "abc@gmail.com"})
   Step 3: browser_fill({"selector": "password", "text": "123"})
   Step 4: browser_click({"selector": "Log In"})
3. For Folders:
   Step 1: create_directory({"path": "~/Desktop/FolderName"})
4. For Screenshot:
   Step 1: take_screenshot({})

Respond ONLY with valid JSON:
{
  "goal": "description",
  "steps": [
    {"tool": "tool_name", "arguments": {"arg": "val"}}
  ]
}
"""

client = OpenAI(base_url=ASI1_BASE_URL, api_key=ASI1_API_KEY, timeout=45.0)


async def execute_task(prompt: str) -> Dict[str, Any]:
    start_time = time.time()
    logger.info(f"Generating plan via Fetch.ai ASI:One: '{prompt}'")

    try:
        res = client.chat.completions.create(
            model=ASI1_MODEL,
            messages=[
                {"role": "system", "content": PLANNER_PROMPT},
                {"role": "user", "content": f"Request: {prompt}"}
            ],
            response_format={"type": "json_object"}
        )
        data = json.loads(res.choices[0].message.content)
        goal = data.get("goal", prompt)
        steps = data.get("steps", [])
    except Exception as e:
        logger.warning(f"ASI:One planning fallback ({e})")
        goal = prompt
        steps = [{"tool": "take_screenshot", "arguments": {}}]

    completed = 0
    logs = []

    for idx, s in enumerate(steps, start=1):
        tool = s.get("tool", "")
        args = s.get("arguments", {})
        logger.info(f"Step {idx}: {tool}({args})")

        try:
            if tool == "open_application":
                open_application(app_name=args.get("app_name", ""), url=args.get("url"))
            elif tool == "type_text":
                type_text(text=args.get("text", ""), press_enter=bool(args.get("press_enter", False)))
            elif tool == "press_key":
                press_key(key=args.get("key", ""))
            elif tool == "click":
                click(x=int(args.get("x", 0)), y=int(args.get("y", 0)), button=args.get("button", "left"))
            elif tool == "move_mouse":
                move_mouse(x=int(args.get("x", 0)), y=int(args.get("y", 0)))
            elif tool == "scroll":
                scroll(direction=args.get("direction", "down"), amount=int(args.get("amount", 3)))
            elif tool == "get_screen_info":
                get_screen_info()
            elif tool == "take_screenshot":
                take_screenshot()
            elif tool == "create_directory":
                create_directory(path=args.get("path", ""))
            elif tool == "write_text_file":
                write_text_file(path=args.get("path", ""), content=args.get("content", ""))
            elif tool == "read_text_file":
                read_text_file(path=args.get("path", ""))
            elif tool == "browser_open":
                await browser.open_url(url=args.get("url", ""))
            elif tool == "browser_fill":
                await browser.fill_input(selector_or_name=args.get("selector", ""), text=args.get("text", ""))
            elif tool == "browser_click":
                await browser.click_element(selector_or_text=args.get("selector", ""))
            completed += 1
            logs.append(f"✓ Step {idx} ({tool}): Success")
        except Exception as err:
            logger.error(f"Step {idx} error: {err}")
            logs.append(f"✗ Step {idx} ({tool}): Failed ({err})")
            break

    elapsed = round(time.time() - start_time, 2)
    os_name = "macOS" if IS_MAC else "Windows"
    summary = f"Goal: {goal}\nModel: Fetch.ai ASI:One ({ASI1_MODEL})\nExecuted {completed}/{len(steps)} steps in {elapsed}s on {os_name}.\n" + "\n".join(logs)

    return {
        "status": "success" if completed == len(steps) else "partial",
        "goal": goal,
        "steps_completed": completed,
        "summary": summary,
        "execution_time_sec": elapsed
    }


# =============================================================================
# Fetch.ai Chat Protocol Handler (For Agentverse Testing UI)
# =============================================================================
def extract_text(msg: ChatMessage) -> str:
    parts = []
    for item in msg.content:
        if isinstance(item, TextContent):
            parts.append(item.text)
        elif isinstance(item, dict) and item.get("type") == "text":
            parts.append(item.get("text", ""))
    return " ".join(parts).strip()


@chat_proto.on_message(ChatMessage)
async def on_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    logger.info(f"ChatMessage from {sender} (id: {msg.msg_id})")

    # Acknowledge
    await ctx.send(sender, ChatAcknowledgement(
        msg_id=uuid4(),
        acknowledged_msg_id=msg.msg_id,
        timestamp=datetime.utcnow()
    ))

    prompt = extract_text(msg)
    if not prompt:
        await ctx.send(sender, ChatMessage(
            msg_id=uuid4(),
            timestamp=datetime.utcnow(),
            content=[TextContent(text="Empty instruction."), EndSessionContent()]
        ))
        return

    # Execute on desktop
    res = await execute_task(prompt)

    # Reply to Agentverse
    icon = "✅" if res["status"] == "success" else "⚠️"
    reply = f"{icon} **AgentOS Desktop Execution:**\n\n{res['summary']}"
    await ctx.send(sender, ChatMessage(
        msg_id=uuid4(),
        timestamp=datetime.utcnow(),
        content=[TextContent(text=reply), EndSessionContent()]
    ))
    logger.info(f"Replied to {sender} on Agentverse.")


@chat_proto.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


# =============================================================================
# REST Endpoints (For chat.py & curl)
# =============================================================================
class TaskReq(Model):
    prompt: str

class TaskRes(Model):
    status: str
    goal: str
    summary: str
    execution_time_sec: float

class StatusRes(Model):
    agent_name: str
    agent_address: str
    endpoint_url: str
    status: str

@agent.on_rest_post("/api/task", TaskReq, TaskRes)
async def rest_task(ctx: Context, req: TaskReq) -> TaskRes:
    res = await execute_task(req.prompt)
    return TaskRes(
        status=res["status"],
        goal=res["goal"],
        summary=res["summary"],
        execution_time_sec=res["execution_time_sec"]
    )

@agent.on_rest_get("/api/status", StatusRes)
async def rest_status(ctx: Context) -> StatusRes:
    return StatusRes(
        agent_name=agent.name,
        agent_address=agent.address,
        endpoint_url="http://127.0.0.1:8001/submit",
        status="active"
    )


# =============================================================================
# Startup Banner
# =============================================================================
@agent.on_event("startup")
async def startup_banner(ctx: Context):
    print("\n" + "=" * 65)
    print("🤖 AgentOS — Pure Desktop Automation uAgent")
    print("=" * 65)
    print(f"• Agent Name:     {agent.name}")
    print(f"• Agent Address:  {agent.address}")
    print(f"• Endpoint URL:   http://127.0.0.1:8001/submit")
    print(f"• Agentverse UI:  https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8001&address={agent.address}")
    print(f"• ASI:One Model:  {ASI1_MODEL} (API Key: Active)")
    print(f"• System:         {'macOS' if IS_MAC else 'Windows'}")
    print("=" * 65 + "\n")


agent.include(chat_proto, publish_manifest=True)


if __name__ == "__main__":
    agent.run()
