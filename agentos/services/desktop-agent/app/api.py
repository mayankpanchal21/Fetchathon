from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, Query, UploadFile, File, status
from pydantic import BaseModel, Field

from .config import settings, get_desktop_status
from .executor.screen import take_screenshot
from .task_manager import task_manager
from .voice.speech_to_text import transcribe_audio_file, get_voice_engine_info

router = APIRouter()


# ----------------------------------------------------
# Request and Response Models
# ----------------------------------------------------

class CreateTaskRequest(BaseModel):
    request: str = Field(..., min_length=2, max_length=1000, description="User voice or text command")


class ApproveTaskRequest(BaseModel):
    step_id: Optional[int] = Field(None, description="Step ID to approve. Defaults to current pending step.")


class RejectTaskRequest(BaseModel):
    step_id: Optional[int] = Field(None, description="Step ID to reject. Defaults to current pending step.")
    reason: Optional[str] = Field("Rejected by user", description="Reason for rejecting action")


# ----------------------------------------------------
# Security Dependency
# ----------------------------------------------------

def verify_device_token(
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    token: Optional[str] = Query(None)
):
    """
    Validates token for state-changing desktop operations.
    Protects against malicious cross-site scripting (CSRF) or unauthorized loopback calls.
    """
    provided = x_device_token or token
    expected = settings.device_pairing_token
    # If device pairing token is configured, enforce match
    if expected and provided != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Device-Token header. Desktop control requires authentication."
        )
    return True


# ----------------------------------------------------
# Endpoints
# ----------------------------------------------------

@router.get("/health")
def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "agentos-desktop-service",
        "timestamp": datetime.utcnow().isoformat(),
        "mode": "live_asi1" if settings.asi1_api_key else "local_demo_mode"
    }


@router.get("/api/v1/desktop/status")
def desktop_status() -> Dict[str, Any]:
    status_data = get_desktop_status()
    status_data["voice_info"] = get_voice_engine_info()
    status_data["active_task_count"] = len(task_manager.active_tasks)
    return status_data


@router.get("/api/v1/desktop/screen")
def desktop_screen() -> Dict[str, Any]:
    """Capture current desktop screen with metadata and preview."""
    return take_screenshot()


@router.post("/api/v1/tasks", dependencies=[Depends(verify_device_token)])
async def create_task(req: CreateTaskRequest) -> Dict[str, Any]:
    """Create and schedule an autonomous task from a user prompt."""
    plan = await task_manager.submit_task(req.request)
    return plan.model_dump()


@router.get("/api/v1/tasks/{task_id}")
def get_task_detail(task_id: str) -> Dict[str, Any]:
    """Retrieve detailed state, logs, and verification for a task."""
    plan = task_manager.get_task(task_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Task with ID '{task_id}' not found.")
    return plan.model_dump()


@router.post("/api/v1/tasks/{task_id}/approve", dependencies=[Depends(verify_device_token)])
async def approve_task(task_id: str, req: ApproveTaskRequest = ApproveTaskRequest()) -> Dict[str, Any]:
    """Approve a paused step in a task waiting for user authorization."""
    success = await task_manager.approve_step(task_id, req.step_id)
    if not success:
        raise HTTPException(status_code=400, detail="Could not approve step. Check if task exists and is waiting for approval.")
    return {"task_id": task_id, "approved": True, "message": "Step approved. Resuming execution."}


@router.post("/api/v1/tasks/{task_id}/reject", dependencies=[Depends(verify_device_token)])
async def reject_task(task_id: str, req: RejectTaskRequest = RejectTaskRequest()) -> Dict[str, Any]:
    """Reject a proposed action in a task."""
    success = await task_manager.reject_step(task_id, req.step_id, reason=req.reason)
    if not success:
        raise HTTPException(status_code=400, detail="Could not reject step. Check if task exists.")
    return {"task_id": task_id, "rejected": True, "reason": req.reason}


@router.post("/api/v1/tasks/{task_id}/cancel", dependencies=[Depends(verify_device_token)])
async def cancel_task(task_id: str) -> Dict[str, Any]:
    """Emergency stop button: immediately cancels active execution."""
    success = await task_manager.cancel_task(task_id)
    return {"task_id": task_id, "cancelled": success, "message": "Task stopped immediately."}


@router.get("/api/v1/tasks")
def list_tasks(limit: int = 50) -> List[Dict[str, Any]]:
    """Get persistent task history (completed, failed, cancelled, planned)."""
    return task_manager.list_all_tasks(limit=limit)


@router.post("/api/v1/voice/transcribe", dependencies=[Depends(verify_device_token)])
async def transcribe_voice(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Transcribe audio recording from user microphone."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio payload is empty.")
    result = transcribe_audio_file(audio_bytes, filename=file.filename or "recording.wav")
    return result
