import shutil
import logging
import subprocess
from typing import Dict, Any, Optional
from ..config import get_detected_os

logger = logging.getLogger("agentos.executor.applications")

# Known application name mappings per OS
APP_NAME_MAPPINGS_MAC = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "browser": "Google Chrome",
    "google": "Google Chrome",
    "safari": "Safari",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "editor": "Visual Studio Code",
    "terminal": "Terminal",
    "finder": "Finder",
    "calculator": "Calculator",
    "calc": "Calculator",
    "textedit": "TextEdit",
    "notes": "Notes",
    "settings": "System Settings",
    "preferences": "System Settings"
}

APP_NAME_MAPPINGS_WIN = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "browser": "chrome.exe",
    "edge": "msedge.exe",
    "msedge": "msedge.exe",
    "vscode": "code",
    "vs code": "code",
    "code": "code",
    "notepad": "notepad.exe",
    "editor": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "terminal": "cmd.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe"
}


def open_application(app_name: str, url: Optional[str] = None) -> Dict[str, Any]:
    if not app_name or not app_name.strip():
        raise ValueError("Application name cannot be empty.")

    clean_name = app_name.strip()
    os_info = get_detected_os()

    try:
        if os_info["is_mac"]:
            normalized_name = APP_NAME_MAPPINGS_MAC.get(clean_name.lower(), clean_name)
            # Use macOS 'open -a' command
            cmd = ["open", "-a", normalized_name]
            if url:
                cmd.append(url)
            logger.info(f"Launching macOS app: {cmd}")
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if proc.returncode != 0:
                # If specific app name failed, fallback to default handler
                if url:
                    subprocess.run(["open", url], check=False)
                return {
                    "action": "open_application",
                    "app_name": clean_name,
                    "url": url,
                    "status": "warning",
                    "error": proc.stderr.strip() or f"Application '{normalized_name}' could not be opened. Fallback triggered.",
                    "platform": "macOS"
                }

        elif os_info["is_windows"]:
            normalized_name = APP_NAME_MAPPINGS_WIN.get(clean_name.lower(), clean_name)
            target = f'"{url}"' if url else ""
            cmd = f'start "" "{normalized_name}" {target}'.strip()
            logger.info(f"Launching Windows app: {cmd}")
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if proc.returncode != 0:
                if url:
                    subprocess.run(f'start {url}', shell=True, check=False)
                return {
                    "action": "open_application",
                    "app_name": clean_name,
                    "url": url,
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
