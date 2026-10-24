import os
import platform
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

# Root repository resolution
APP_DIR = Path(__file__).resolve().parent
SERVICE_DIR = APP_DIR.parent
MONOREPO_ROOT = SERVICE_DIR.parent.parent

# Read .env if present
def load_env_file():
    env_paths = [
        MONOREPO_ROOT / ".env",
        SERVICE_DIR / ".env",
        Path.cwd() / ".env"
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

load_env_file()


class Settings(BaseModel):
    # Host & Port
    desktop_host: str = Field(default_factory=lambda: os.getenv("DESKTOP_HOST", "127.0.0.1"))
    desktop_port: int = Field(default_factory=lambda: int(os.getenv("DESKTOP_PORT", "8000")))
    device_pairing_token: str = Field(default_factory=lambda: os.getenv("DEVICE_PAIRING_TOKEN", "agentos-local-dev-token"))

    # ASI1 API Configuration
    asi1_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("ASI1_API_KEY", "").strip() or None)
    asi1_model: str = Field(default_factory=lambda: os.getenv("ASI1_MODEL", "asi1"))
    asi1_base_url: str = Field(default_factory=lambda: os.getenv("ASI1_BASE_URL", "https://api.asi1.ai/v1"))

    # Fetch.ai uAgent Configuration
    agent_name: str = Field(default_factory=lambda: os.getenv("AGENT_NAME", "AgentOS-Desktop-Worker"))
    agent_port: int = Field(default_factory=lambda: int(os.getenv("AGENT_PORT", "8001")))
    agent_seed_phrase: Optional[str] = Field(default_factory=lambda: os.getenv("AGENT_SEED_PHRASE", "").strip() or None)
    agent_mailbox_key: Optional[str] = Field(default_factory=lambda: os.getenv("AGENT_MAILBOX_KEY", "").strip() or None)
    relay_url: Optional[str] = Field(default_factory=lambda: os.getenv("RELAY_URL", "").strip() or None)

    # Workspace Sandbox
    allowed_workspace: Path = Field(default_factory=lambda: Path(os.getenv("ALLOWED_WORKSPACE", "./workspace")).resolve())

    # Speech to text
    stt_engine: str = Field(default_factory=lambda: os.getenv("STT_ENGINE", "browser"))
    whisper_model_size: str = Field(default_factory=lambda: os.getenv("WHISPER_MODEL_SIZE", "base"))

    # Execution limits
    max_task_steps: int = Field(default_factory=lambda: int(os.getenv("MAX_TASK_STEPS", "15")))
    max_task_duration_seconds: int = Field(default_factory=lambda: int(os.getenv("MAX_TASK_DURATION_SECONDS", "180")))
    max_step_retries: int = Field(default_factory=lambda: int(os.getenv("MAX_STEP_RETRIES", "2")))

    # Database
    db_path: Path = Field(default_factory=lambda: (SERVICE_DIR / "tasks.db").resolve())

    def ensure_directories(self):
        self.allowed_workspace.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()


def get_detected_os() -> Dict[str, Any]:
    sys_name = platform.system()
    release = platform.release()
    arch = platform.machine()
    is_mac = sys_name == "Darwin"
    is_windows = sys_name == "Windows"
    is_linux = sys_name == "Linux"

    return {
        "os_name": "macOS" if is_mac else ("Windows" if is_windows else sys_name),
        "raw_system": sys_name,
        "release": release,
        "architecture": arch,
        "is_mac": is_mac,
        "is_windows": is_windows,
        "is_linux": is_linux,
        "platform_string": f"{sys_name} {release} ({arch})"
    }


def check_screen_permission() -> str:
    """Detect screen recording permission on macOS if possible, or return platform default."""
    sys_info = get_detected_os()
    if not sys_info["is_mac"]:
        return "granted"  # Windows does not require TCC screen capture consent

    try:
        # Check using quartz CGPreflightScreenCaptureAccess if available
        import Quartz
        if hasattr(Quartz, "CGPreflightScreenCaptureAccess"):
            has_perm = Quartz.CGPreflightScreenCaptureAccess()
            return "granted" if has_perm else "denied_or_missing"
    except Exception:
        pass
    return "accessible"


def get_desktop_status() -> Dict[str, Any]:
    os_info = get_detected_os()
    return {
        "operating_system": os_info["os_name"],
        "platform_details": os_info["platform_string"],
        "architecture": os_info["architecture"],
        "backend_connected": True,
        "screen_permission": check_screen_permission(),
        "voice_engine": settings.stt_engine,
        "asi1_configured": bool(settings.asi1_api_key),
        "asi1_model": settings.asi1_model,
        "allowed_workspace": str(settings.allowed_workspace),
        "fetch_agent_paired": False, # Updated dynamically by manager
        "mode": "live_asi1" if settings.asi1_api_key else "local_demo_mode"
    }
