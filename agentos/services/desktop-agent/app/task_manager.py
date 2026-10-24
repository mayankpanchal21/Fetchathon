import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Set
from .config import settings
from .planner import TaskPlan, TaskStepPlan, create_task_plan
from .approvals import approval_engine, ApprovalDecision
from .database import db
from .executor import (
    get_screen_info,
    take_screenshot,
    click,
    move_mouse,
    type_text,
    press_key,
    scroll,
    open_application,
    list_files,
    search_files,
    create_directory,
    read_text_file,
    write_text_file,
    run_approved_command,
    browser_manager
)

logger = logging.getLogger("agentos.task_manager")


class TaskManager:
    def __init__(self):
        self.active_tasks: Dict[str, TaskPlan] = {}
        self.cancelled_tasks: Set[str] = set()
        self._running_coroutines: Dict[str, asyncio.Task] = {}

    def get_task(self, task_id: str) -> Optional[TaskPlan]:
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        saved = db.get_task(task_id)
        if saved:
            plan = TaskPlan(**saved)
            self.active_tasks[task_id] = plan
            return plan
        return None

    def list_all_tasks(self, limit: int = 50) -> list[Dict[str, Any]]:
        return db.list_tasks(limit=limit)

    async def submit_task(self, user_request: str) -> TaskPlan:
        # Create structured plan
        plan = create_task_plan(user_request)
        self.active_tasks[plan.task_id] = plan
        db.save_task(plan.model_dump())

        # Start background executor loop
        coro = asyncio.create_task(self._run_task_lifecycle(plan))
        self._running_coroutines[plan.task_id] = coro
        return plan

    async def approve_step(self, task_id: str, step_id: Optional[int] = None) -> bool:
        plan = self.get_task(task_id)
        if not plan:
            return False

        target_step_id = step_id or (plan.steps[plan.current_step_index].step_id if plan.current_step_index < len(plan.steps) else 1)
        ok = approval_engine.approve(task_id, target_step_id)
        if ok:
            plan.add_log(f"Step {target_step_id} approved by user.", level="info")
            db.save_task(plan.model_dump())
        return ok

    async def reject_step(self, task_id: str, step_id: Optional[int] = None, reason: Optional[str] = None) -> bool:
        plan = self.get_task(task_id)
        if not plan:
            return False

        target_step_id = step_id or (plan.steps[plan.current_step_index].step_id if plan.current_step_index < len(plan.steps) else 1)
        ok = approval_engine.reject(task_id, target_step_id, reason=reason)
        if ok:
            plan.add_log(f"Step {target_step_id} rejected: {reason or 'User rejected'}", level="warning")
            db.save_task(plan.model_dump())
        return ok

    async def cancel_task(self, task_id: str) -> bool:
        """Emergency stop mechanism."""
        self.cancelled_tasks.add(task_id)
        approval_engine.cancel_all_for_task(task_id)

        plan = self.get_task(task_id)
        if plan:
            plan.status = "cancelled"
            plan.error_details = "Task stopped by emergency cancellation."
            plan.add_log("Task stopped immediately by user emergency stop.", level="warning")
            db.save_task(plan.model_dump())

        if task_id in self._running_coroutines:
            self._running_coroutines[task_id].cancel()
            del self._running_coroutines[task_id]

        logger.warning(f"Task {task_id} successfully cancelled by emergency stop.")
        return True

    async def _execute_step_action(self, step: TaskStepPlan) -> Dict[str, Any]:
        """Dispatch step to registered tool."""
        tool = step.tool
        args = step.arguments

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

    def _verify_step_outcome(self, step: TaskStepPlan, result: Dict[str, Any]) -> tuple[bool, str]:
        """Independent verification of step outcome."""
        tool = step.tool
        if tool == "create_directory":
            verified = result.get("verified", False)
            return verified, "Directory verified on filesystem." if verified else "Directory not verified."
        elif tool == "write_text_file":
            verified = result.get("verified", False)
            return verified, f"File verified written ({result.get('bytes_written', 0)} bytes)."
        elif tool == "browser_navigate":
            verified = result.get("verified", False)
            title = result.get("title", "")
            return verified, f"Browser navigated successfully. Page title: '{title}'"
        elif tool == "take_screenshot":
            has_bytes = bool(result.get("saved_path"))
            return has_bytes, f"Screenshot verified at {result.get('saved_path')}"
        elif tool == "run_approved_command":
            success = result.get("success", False)
            return success, f"Command exited with code {result.get('exit_code', -1)}"
        return True, "Action completed without error."

    async def _run_task_lifecycle(self, plan: TaskPlan):
        start_time = time.time()
        logger.info(f"Starting execution lifecycle for task {plan.task_id}: {plan.goal}")
        plan.status = "running"
        plan.add_log(f"Execution started for task: {plan.goal}", level="info")
        db.save_task(plan.model_dump())

        try:
            for idx, step in enumerate(plan.steps):
                plan.current_step_index = idx

                # 1. Emergency stop check
                if plan.task_id in self.cancelled_tasks:
                    plan.status = "cancelled"
                    plan.add_log("Task cancelled by emergency stop.", level="warning")
                    db.save_task(plan.model_dump())
                    return

                # 2. Maximum task duration check
                if time.time() - start_time > settings.max_task_duration_seconds:
                    plan.status = "failed"
                    plan.error_details = f"Exceeded maximum task duration ({settings.max_task_duration_seconds}s)."
                    plan.add_log("Task timed out.", level="error")
                    db.save_task(plan.model_dump())
                    return

                # 3. Check and wait for approval if required
                if step.requires_approval:
                    step.status = "waiting_approval"
                    plan.status = "waiting_approval"
                    reason = step.approval_reason or f"Action '{step.tool}' requires approval."
                    plan.add_log(f"Step {step.step_id} paused for approval: {reason}", level="warning", step_id=step.step_id)
                    approval_engine.register_approval_request(
                        task_id=plan.task_id,
                        step_id=step.step_id,
                        tool=step.tool,
                        arguments=step.arguments,
                        reason=reason
                    )
                    db.save_task(plan.model_dump())

                    # Wait for UI decision
                    decision = await approval_engine.wait_for_decision(plan.task_id, step.step_id)
                    if decision != ApprovalDecision.APPROVED:
                        step.status = "rejected" if decision == ApprovalDecision.REJECTED else "cancelled"
                        plan.status = "failed" if decision == ApprovalDecision.REJECTED else "cancelled"
                        plan.error_details = f"Step {step.step_id} was {decision.value}."
                        plan.add_log(f"Task stopped: {plan.error_details}", level="warning", step_id=step.step_id)
                        db.save_task(plan.model_dump())
                        return

                # 4. Execute step
                step.status = "running"
                plan.status = "running"
                plan.add_log(f"Executing step {step.step_id}: {step.tool}", level="info", step_id=step.step_id)
                db.save_task(plan.model_dump())

                retries = 0
                step_success = False
                last_error = None

                while retries <= settings.max_step_retries and not step_success:
                    try:
                        result = await self._execute_step_action(step)
                        step.result = result

                        # 5. Verify outcome
                        verified, note = self._verify_step_outcome(step, result)
                        step.verification_notes = note

                        if verified:
                            step_success = True
                            step.status = "completed"
                            plan.add_log(f"Step {step.step_id} succeeded. Verification: {note}", level="info", step_id=step.step_id)
                        else:
                            retries += 1
                            last_error = f"Verification failed: {note}"
                            plan.add_log(f"Step {step.step_id} verification failed (retry {retries}/{settings.max_step_retries}): {note}", level="warning", step_id=step.step_id)
                            await asyncio.sleep(0.5)

                    except Exception as e:
                        retries += 1
                        last_error = str(e)
                        logger.error(f"Error on step {step.step_id} (attempt {retries}): {e}")
                        plan.add_log(f"Step {step.step_id} failed attempt {retries}: {e}", level="error", step_id=step.step_id)
                        await asyncio.sleep(0.5)

                if not step_success:
                    step.status = "failed"
                    step.error = last_error
                    plan.status = "failed"
                    plan.error_details = f"Step {step.step_id} ({step.tool}) failed: {last_error}"
                    plan.add_log(f"Task aborted: {plan.error_details}", level="error", step_id=step.step_id)
                    db.save_task(plan.model_dump())
                    return

                db.save_task(plan.model_dump())

            # All steps completed!
            plan.status = "completed"
            plan.verification_result = {
                "verified": True,
                "message": f"Successfully completed all {len(plan.steps)} planned steps.",
                "total_duration_sec": round(time.time() - start_time, 2)
            }
            plan.add_log(f"Task completed successfully in {plan.verification_result['total_duration_sec']}s.", level="info")
            db.save_task(plan.model_dump())
            logger.info(f"Task {plan.task_id} completed successfully.")

        except asyncio.CancelledError:
            plan.status = "cancelled"
            plan.add_log("Task cancelled.", level="warning")
            db.save_task(plan.model_dump())
        except Exception as e:
            logger.exception(f"Unexpected error in task lifecycle {plan.task_id}: {e}")
            plan.status = "failed"
            plan.error_details = str(e)
            plan.add_log(f"Fatal task error: {e}", level="error")
            db.save_task(plan.model_dump())


task_manager = TaskManager()
