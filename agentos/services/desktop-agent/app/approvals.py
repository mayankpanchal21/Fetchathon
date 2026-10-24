import asyncio
import logging
from enum import Enum
from typing import Dict, Optional, Any
from pydantic import BaseModel

logger = logging.getLogger("agentos.approvals")

class ApprovalDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalRequest(BaseModel):
    task_id: str
    step_id: int
    tool: str
    arguments: Dict[str, Any]
    reason: str
    status: ApprovalDecision = ApprovalDecision.PENDING
    decision_reason: Optional[str] = None


class ApprovalEngine:
    def __init__(self):
        self._pending_requests: Dict[str, ApprovalRequest] = {}
        self._events: Dict[str, asyncio.Event] = {}

    def _key(self, task_id: str, step_id: int) -> str:
        return f"{task_id}:{step_id}"

    def register_approval_request(
        self,
        task_id: str,
        step_id: int,
        tool: str,
        arguments: Dict[str, Any],
        reason: str
    ) -> ApprovalRequest:
        key = self._key(task_id, step_id)
        req = ApprovalRequest(
            task_id=task_id,
            step_id=step_id,
            tool=tool,
            arguments=arguments,
            reason=reason,
            status=ApprovalDecision.PENDING
        )
        self._pending_requests[key] = req
        self._events[key] = asyncio.Event()
        logger.info(f"Registered approval request for task {task_id} step {step_id}: {reason}")
        return req

    def get_request(self, task_id: str, step_id: int) -> Optional[ApprovalRequest]:
        return self._pending_requests.get(self._key(task_id, step_id))

    def get_pending_request_for_task(self, task_id: str) -> Optional[ApprovalRequest]:
        for req in self._pending_requests.values():
            if req.task_id == task_id and req.status == ApprovalDecision.PENDING:
                return req
        return None

    def approve(self, task_id: str, step_id: int) -> bool:
        key = self._key(task_id, step_id)
        req = self._pending_requests.get(key)
        if not req:
            return False
        req.status = ApprovalDecision.APPROVED
        if key in self._events:
            self._events[key].set()
        logger.info(f"Approved action for task {task_id} step {step_id}")
        return True

    def reject(self, task_id: str, step_id: int, reason: Optional[str] = None) -> bool:
        key = self._key(task_id, step_id)
        req = self._pending_requests.get(key)
        if not req:
            return False
        req.status = ApprovalDecision.REJECTED
        req.decision_reason = reason or "Rejected by user"
        if key in self._events:
            self._events[key].set()
        logger.info(f"Rejected action for task {task_id} step {step_id}: {req.decision_reason}")
        return True

    def cancel_all_for_task(self, task_id: str):
        for key, req in list(self._pending_requests.items()):
            if req.task_id == task_id and req.status == ApprovalDecision.PENDING:
                req.status = ApprovalDecision.CANCELLED
                req.decision_reason = "Task cancelled by emergency stop"
                if key in self._events:
                    self._events[key].set()

    async def wait_for_decision(self, task_id: str, step_id: int, timeout: float = 300.0) -> ApprovalDecision:
        key = self._key(task_id, step_id)
        if key not in self._events:
            return ApprovalDecision.REJECTED
        try:
            await asyncio.wait_for(self._events[key].wait(), timeout=timeout)
            req = self._pending_requests.get(key)
            return req.status if req else ApprovalDecision.REJECTED
        except asyncio.TimeoutError:
            req = self._pending_requests.get(key)
            if req:
                req.status = ApprovalDecision.REJECTED
                req.decision_reason = "Approval timed out after 300s"
            return ApprovalDecision.REJECTED


approval_engine = ApprovalEngine()
