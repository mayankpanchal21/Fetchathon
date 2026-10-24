import io
import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw
import pyautogui
from ..config import settings, get_detected_os

logger = logging.getLogger("agentos.executor.screen")

SCREENSHOTS_DIR = settings.allowed_workspace / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def get_screen_info() -> Dict[str, Any]:
    """Retrieve screen dimensions and display metrics."""
    try:
        width, height = pyautogui.size()
    except Exception as e:
        logger.warning(f"Could not read display size from pyautogui ({e}). Falling back to 1920x1080.")
        width, height = 1920, 1080

    os_info = get_detected_os()
    return {
        "width": width,
        "height": height,
        "operating_system": os_info["os_name"],
        "architecture": os_info["architecture"],
        "timestamp": datetime.utcnow().isoformat()
    }


def take_screenshot(output_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Capture a screenshot, save it safely within the workspace screenshots directory,
    and return metadata with base64 preview.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    filename = output_name or f"screenshot_{timestamp}.png"
    if not filename.endswith(".png"):
        filename += ".png"

    save_path = SCREENSHOTS_DIR / filename

    try:
        # Capture screenshot
        img = pyautogui.screenshot()
    except Exception as e:
        logger.warning(f"PyAutoGUI screenshot failed or headless display: {e}. Generating clean status canvas.")
        # Create a fallback image for headless/sandbox environments
        img = Image.new("RGB", (1280, 800), color=(24, 24, 27))
        draw = ImageDraw.Draw(img)
        draw.text((40, 40), "AgentOS Desktop Operator - Display Context", fill=(255, 255, 255))
        draw.text((40, 80), f"Timestamp: {datetime.utcnow().isoformat()}", fill=(160, 160, 160))
        draw.text((40, 120), f"OS: {get_detected_os()['platform_string']}", fill=(160, 160, 160))

    # Save to disk
    img.save(save_path, format="PNG")

    # Generate a thumbnail for fast base64 UI transmission (max width 600)
    thumb = img.copy()
    thumb.thumbnail((600, 375))
    if thumb.mode in ("RGBA", "P"):
        thumb = thumb.convert("RGB")
    buf = io.BytesIO()
    thumb.save(buf, format="JPEG", quality=75)
    b64_preview = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {
        "saved_path": str(save_path),
        "filename": filename,
        "width": img.width,
        "height": img.height,
        "base64_preview": f"data:image/jpeg;base64,{b64_preview}",
        "captured_at": datetime.utcnow().isoformat()
    }
