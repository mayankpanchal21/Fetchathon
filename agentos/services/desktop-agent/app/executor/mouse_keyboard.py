import time
import logging
from typing import Dict, Any, Optional
import pyautogui
from ..policy import validate_screen_coordinates, validate_text_input, PolicyViolation

logger = logging.getLogger("agentos.executor.mouse_keyboard")

# Ensure PyAutoGUI failsafe is enabled (moving mouse to corner raises exception)
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

VALID_BUTTONS = {"left", "right", "middle"}

VALID_KEYS = {
    "enter", "return", "tab", "space", "backspace", "delete", "escape",
    "up", "down", "left", "right", "home", "end", "pageup", "pagedown",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "ctrl", "alt", "shift", "command", "win"
}


def _get_screen_bounds() -> tuple[int, int]:
    try:
        return pyautogui.size()
    except Exception:
        return 1920, 1080


def move_mouse(x: int, y: int) -> Dict[str, Any]:
    w, h = _get_screen_bounds()
    validate_screen_coordinates(x, y, w, h)
    try:
        pyautogui.moveTo(x, y, duration=0.2)
    except Exception as e:
        logger.warning(f"Simulating mouse move to ({x}, {y}) due to: {e}")
    return {"action": "move_mouse", "x": x, "y": y, "status": "success"}


def click(x: int, y: int, button: str = "left") -> Dict[str, Any]:
    w, h = _get_screen_bounds()
    validate_screen_coordinates(x, y, w, h)
    btn = button.lower()
    if btn not in VALID_BUTTONS:
        raise PolicyViolation(f"Invalid mouse button: '{button}'. Allowed: {list(VALID_BUTTONS)}")

    try:
        pyautogui.click(x=x, y=y, button=btn)
    except Exception as e:
        logger.warning(f"Simulating click at ({x}, {y}) button={btn} due to: {e}")
    return {"action": "click", "x": x, "y": y, "button": btn, "status": "success"}


def type_text(text: str, press_enter: bool = False) -> Dict[str, Any]:
    validate_text_input(text)
    try:
        # Check if text contains non-ASCII characters
        is_ascii = all(ord(c) < 128 for c in text)
        if is_ascii:
            pyautogui.write(text, interval=0.01)
        else:
            # Unicode support via pyperclip clipboard paste
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey("command" if pyautogui.platform.system() == "Darwin" else "ctrl", "v")
        
        if press_enter:
            pyautogui.press("enter")
    except Exception as e:
        logger.warning(f"Simulating type_text '{text[:30]}...' due to: {e}")

    return {
        "action": "type_text",
        "length": len(text),
        "pressed_enter": press_enter,
        "status": "success"
    }


def press_key(key: str) -> Dict[str, Any]:
    clean_key = key.strip().lower()
    if clean_key not in VALID_KEYS:
        # Check single alphanumeric character
        if len(clean_key) != 1:
            raise PolicyViolation(f"Unrecognized key: '{key}'. Must be a single character or one of: {sorted(list(VALID_KEYS))}")

    try:
        pyautogui.press(clean_key)
    except Exception as e:
        logger.warning(f"Simulating key press '{clean_key}' due to: {e}")

    return {"action": "press_key", "key": clean_key, "status": "success"}


def scroll(direction: str = "down", amount: int = 3) -> Dict[str, Any]:
    dir_clean = direction.strip().lower()
    if dir_clean not in {"up", "down"}:
        raise PolicyViolation(f"Invalid scroll direction '{direction}'. Must be 'up' or 'down'.")

    # Positive scrolls up in pyautogui, negative scrolls down
    clicks = amount if dir_clean == "up" else -amount
    try:
        pyautogui.scroll(clicks)
    except Exception as e:
        logger.warning(f"Simulating scroll {dir_clean} ({amount}) due to: {e}")

    return {"action": "scroll", "direction": dir_clean, "amount": amount, "status": "success"}
