import shutil
import logging
import subprocess
from typing import Dict, Any
from ..config import get_detected_os

logger = logging.getLogger("agentos.executor.applications")

# Known application name mappings per OS
APP_NAME_MAPPINGS_MAC = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "safari": "Safari",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "terminal": "Terminal",
    "finder": "Finder",
    "calculator": "Calculator",
    "textedit": "TextEdit",
    "notes": "Notes"
}

APP_NAME_MAPPINGS_WIN = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "vscode": "code",
    "vs code": "code",
    "code": "code",
    "notepad": "notepad.exe",
    "calculator": "calc.exe"
}


def open_application(app_name: str) -> Dict[str, Any]:
    if not app_name or not app_name.strip():
        raise ValueError("Application name cannot be empty.")

    clean_name = app_name.strip()
    os_info = get_detected_os()

    try:
        if os_info["is_mac"]:
            normalized_name = APP_NAME_MAPPINGS_MAC.get(clean_name.lower(), clean_name)
            # Use macOS 'open -a' command
            cmd = ["open", "-a", normalized_name]
            logger.info(f"Launching macOS app: {cmd}")
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if proc.returncode != 0:
                # If specific app name failed, try directly as bundle or fallback
                return {
                    "action": "open_application",
                    "app_name": clean_name,
                    "status": "warning",
                    "error": proc.stderr.strip() or f"Application '{normalized_name}' could not be opened. Verify installation.",
                    "platform": "macOS"
                }

        elif os_info["is_windows"]:
            normalized_name = APP_NAME_MAPPINGS_WIN.get(clean_name.lower(), clean_name)
            cmd = f'start "" "{normalized_name}"'
            logger.info(f"Launching Windows app: {cmd}")
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if proc.returncode != 0:
                return {
                    "action": "open_application",
                    "app_name": clean_name,
                    "status": "warning",
                    "error": proc.stderr.strip() or f"Application '{normalized_name}' could not be started.",
                    "platform": "Windows"
                }

        else:
            # Linux fallback
            cmd = ["xdg-open", clean_name]
            subprocess.Popen(cmd)

        return {
            "action": "open_application",
            "app_name": clean_name,
            "status": "success",
            "platform": os_info["os_name"]
        }

    except subprocess.TimeoutExpired:
        return {
            "action": "open_application",
            "app_name": clean_name,
            "status": "failed",
            "error": "Application launch timed out."
        }
    except Exception as e:
        logger.error(f"Failed to launch app '{clean_name}': {e}")
        return {
            "action": "open_application",
            "app_name": clean_name,
            "status": "failed",
            "error": str(e)
        }
