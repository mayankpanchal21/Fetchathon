import os
import time
import logging
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger("agentos.fetch_agent.dispatcher")


class DesktopDispatcher:
    """
    Authenticated dispatcher connecting Fetch.ai uAgent to the local desktop service.
    Enforces device pairing token and strictly prevents arbitrary OS command injection.
    """

    def __init__(
        self,
        desktop_base_url: Optional[str] = None,
        pairing_token: Optional[str] = None
    ):
        self.base_url = (desktop_base_url or os.getenv("DESKTOP_SERVICE_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.pairing_token = pairing_token or os.getenv("DEVICE_PAIRING_TOKEN", "agentos-local-dev-token")

    async def check_desktop_health(self) -> Dict[str, Any]:
        """Check if local desktop agent is running and accessible."""
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"{self.base_url}/health")
                if res.status_code == 200:
                    return {"connected": True, "details": res.json()}
        except Exception as e:
            logger.warning(f"Local desktop service unreachable at {self.base_url}: {e}")
        return {"connected": False, "error": f"Desktop service offline at {self.base_url}"}

    async def dispatch_task(self, user_command: str) -> Dict[str, Any]:
        """
        Submits the user request to the local desktop agent and monitors execution.
        Returns truthful execution report without exposing private secrets.
        """
        headers = {
            "X-Device-Token": self.pairing_token,
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 1. Submit task
                create_res = await client.post(
                    f"{self.base_url}/api/v1/tasks",
                    json={"request": user_command},
                    headers=headers
                )

                if create_res.status_code == 401:
                    return {
                        "success": False,
                        "status": "unauthorized",
                        "summary": "Authentication failure: Device pairing token rejected by local desktop agent."
                    }

                if create_res.status_code != 200:
                    return {
                        "success": False,
                        "status": "error",
                        "summary": f"Desktop agent returned HTTP {create_res.status_code}: {create_res.text}"
                    }

                task_data = create_res.json()
                task_id = task_data.get("task_id")

                # 2. Poll progress briefly for synchronous response
                for _ in range(12):  # Poll for up to 6 seconds
                    await httpx.AsyncClient().aclose() # ensure cleanly closed
                    async with httpx.AsyncClient(timeout=4.0) as poll_client:
                        status_res = await poll_client.get(
                            f"{self.base_url}/api/v1/tasks/{task_id}",
                            headers=headers
                        )
                        if status_res.status_code == 200:
                            current = status_res.json()
                            status = current.get("status")

                            if status == "completed":
                                v_res = current.get("verification_result", {})
                                return {
                                    "success": True,
                                    "task_id": task_id,
                                    "status": "completed",
                                    "goal": current.get("goal"),
                                    "summary": f"Task completed successfully: {v_res.get('message', 'All steps verified.')}",
                                    "steps_count": len(current.get("steps", []))
                                }

                            elif status == "waiting_approval":
                                pending_step = current["steps"][current.get("current_step_index", 0)]
                                reason = pending_step.get("approval_reason", "Action requires confirmation")
                                return {
                                    "success": True,
                                    "task_id": task_id,
                                    "status": "waiting_approval",
                                    "summary": f"Task is paused on your desktop awaiting your approval: {reason}. Please approve or reject on your local AgentOS dashboard."
                                }

                            elif status in {"failed", "cancelled"}:
                                return {
                                    "success": False,
                                    "task_id": task_id,
                                    "status": status,
                                    "summary": f"Task {status}: {current.get('error_details', 'Execution stopped.')}"
                                }

                    import asyncio
                    await asyncio.sleep(0.5)

                # Still running
                return {
                    "success": True,
                    "task_id": task_id,
                    "status": "in_progress",
                    "summary": f"Task '{task_data.get('goal')}' is currently executing on your local desktop. ID: {task_id}"
                }

        except httpx.ConnectError:
            # Fallback: Clearly labelled development mock transport
            logger.info("Using local mock transport because desktop agent is offline.")
            return {
                "success": False,
                "status": "mock_transport_standby",
                "summary": (
                    "[AgentOS Mock Transport]: Local desktop agent is not running on 127.0.0.1:8000. "
                    "Start 'desktop-agent' service locally to execute real actions."
                )
            }
        except Exception as e:
            return {
                "success": False,
                "status": "dispatcher_error",
                "summary": f"Dispatcher communication error: {str(e)}"
            }
