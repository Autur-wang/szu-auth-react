"""Task execution orchestration over the command bus."""

import time

from auth_service import AuthService
from booking_service import BookingService
from command_bus import CommandBus, CommandContext
from observability import (
    emit_event,
    reset_context,
    set_task_context,
    set_trigger_source,
)
from policy_engine import PolicyEngine
from task_repository import TaskRepository


class TaskService:
    def __init__(
        self,
        cfg,
        repository: TaskRepository | None = None,
        policy: PolicyEngine | None = None,
        bus: CommandBus | None = None,
    ):
        self.cfg = cfg
        self.repository = repository or TaskRepository()
        self.policy = policy or PolicyEngine()
        self.bus = bus or CommandBus()
        self._register_default_handlers()

    def run(
        self,
        command: str,
        payload: dict | None = None,
        trigger_source: str = "manual",
        metadata: dict | None = None,
        runtime_context: dict | None = None,
    ):
        payload = payload or {}
        task = self.repository.create(
            command=command,
            trigger_source=trigger_source,
            payload=payload,
            metadata=metadata,
        )
        emit_event(
            "task.created",
            task_id=task.id,
            trigger_source=trigger_source,
            command=command,
            payload=payload,
        )
        decision = self.policy.evaluate_task(self.repository, command)
        if not decision.allowed:
            task.status = "rejected"
            task.error = decision.reason
            task.finished_at = time.time()
            emit_event(
                "task.rejected",
                level="warning",
                task_id=task.id,
                trigger_source=trigger_source,
                command=command,
                reason=decision.reason,
            )
            return self.repository.save(task)

        task.status = "running"
        task.started_at = time.time()
        self.repository.save(task)
        task_token = set_task_context(task.id)
        src_token = set_trigger_source(trigger_source)
        emit_event(
            "task.started",
            task_id=task.id,
            trigger_source=trigger_source,
            command=command,
        )
        context = CommandContext(
            cfg=self.cfg,
            payload=payload,
            trigger_source=trigger_source,
            task=task,
            runtime_context=runtime_context or {},
        )

        try:
            task.result = self.bus.dispatch(command, context)
            task.status = "succeeded"
            emit_event(
                "task.succeeded",
                task_id=task.id,
                trigger_source=trigger_source,
                command=command,
            )
        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
            emit_event(
                "task.failed",
                level="error",
                task_id=task.id,
                trigger_source=trigger_source,
                command=command,
                error=str(exc),
            )
        finally:
            task.finished_at = time.time()
            self.repository.save(task)
            emit_event(
                "task.finished",
                task_id=task.id,
                trigger_source=trigger_source,
                command=command,
                status=task.status,
                duration_ms=round((task.finished_at - task.started_at) * 1000, 2),
            )
            reset_context(task_token)
            reset_context(src_token)
        return task

    def list_tasks(self, limit: int = 20) -> list[dict]:
        return [task.to_dict() for task in self.repository.list(limit=limit)]

    def latest_task(self, command: str | None = None) -> dict | None:
        task = self.repository.latest(command=command)
        return task.to_dict() if task else None

    def get_task(self, task_id: str) -> dict | None:
        task = self.repository.get(task_id)
        return task.to_dict() if task else None

    def _register_default_handlers(self):
        if self.bus._handlers:
            return
        self.bus.register("auth.login", self._handle_auth_login)
        self.bus.register("auth.ensure_cookie", self._handle_auth_ensure_cookie)
        self.bus.register("booking.query", self._handle_booking_query)
        self.bus.register("booking.run", self._handle_booking_run)

    def _resolve_auth_service(self, context: CommandContext) -> AuthService:
        auth_service = context.runtime_context.get("auth_service")
        if auth_service is not None:
            return auth_service
        return AuthService(context.cfg)

    def _resolve_session(self, context: CommandContext):
        session = context.runtime_context.get("session")
        if session is not None:
            return session
        return self._resolve_auth_service(context).login_verified()

    def _resolve_date(self, booking_service: BookingService, payload: dict) -> str:
        date = payload.get("date")
        return date or booking_service.resolve_target_date()

    def _handle_auth_login(self, context: CommandContext):
        auth_service = self._resolve_auth_service(context)
        auth_service.login_verified()
        return {
            "message": "登录成功",
            "cookie_status": auth_service.cookie_status(),
        }

    def _handle_auth_ensure_cookie(self, context: CommandContext):
        auth_service = self._resolve_auth_service(context)
        if auth_service.has_valid_cached_session():
            return {
                "message": "Cookie 缓存有效",
                "source": "cache",
                "cookie_status": auth_service.cookie_status(),
            }
        if auth_service.try_headless_login():
            return {
                "message": "Headless 登录成功",
                "source": "headless",
                "cookie_status": auth_service.cookie_status(),
            }
        raise RuntimeError("需要人工登录")

    def _handle_booking_query(self, context: CommandContext):
        session = self._resolve_session(context)
        booking_service = BookingService(context.cfg, session)
        date = self._resolve_date(booking_service, context.payload)
        venues = booking_service.query_preferred_venues(date)
        return {
            "date": date,
            "venue_count": len(venues),
            "venues": [
                {
                    "wid": venue.wid,
                    "display": venue.display,
                    "venue_name": venue.venue_name,
                    "begin_hour": venue.begin_hour,
                    "end_hour": venue.end_hour,
                }
                for venue in venues
            ],
        }

    def _handle_booking_run(self, context: CommandContext):
        session = self._resolve_session(context)
        booking_service = BookingService(context.cfg, session)
        date = self._resolve_date(booking_service, context.payload)
        result = booking_service.run_for_date(
            date,
            skip_wait=bool(context.payload.get("now")),
        )
        if not result.result:
            raise RuntimeError(result.message)
        return {
            "date": result.date,
            "advance_ms": result.advance_ms,
            "venue_count": len(result.venues),
            "message": result.message,
            "result": result.result.display if result.result else None,
        }
