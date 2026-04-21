"""Persistence layer for task execution records."""

import json
from pathlib import Path

from runtime_paths import ensure_runtime_dirs, resolve_tasks_path
from task_models import TaskRecord


class TaskRepository:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else resolve_tasks_path()

    def list(self, limit: int | None = None) -> list[TaskRecord]:
        tasks = self._load_all()
        tasks.sort(key=lambda item: item.created_at, reverse=True)
        if limit is not None:
            tasks = tasks[:limit]
        return tasks

    def latest(self, command: str | None = None) -> TaskRecord | None:
        for task in self.list():
            if command is None or task.command == command:
                return task
        return None

    def get(self, task_id: str) -> TaskRecord | None:
        for task in self._load_all():
            if task.id == task_id:
                return task
        return None

    def find_running(self, command: str | None = None) -> list[TaskRecord]:
        running = []
        for task in self._load_all():
            if task.status != "running":
                continue
            if command and task.command != command:
                continue
            running.append(task)
        return running

    def create(
        self,
        command: str,
        trigger_source: str,
        payload: dict | None = None,
        metadata: dict | None = None,
    ) -> TaskRecord:
        task = TaskRecord.create(
            command=command,
            trigger_source=trigger_source,
            payload=payload,
            metadata=metadata,
        )
        tasks = self._load_all()
        tasks.append(task)
        self._write_all(tasks)
        return task

    def save(self, task: TaskRecord) -> TaskRecord:
        tasks = self._load_all()
        for idx, existing in enumerate(tasks):
            if existing.id == task.id:
                tasks[idx] = task
                break
        else:
            tasks.append(task)
        self._write_all(tasks)
        return task

    def _load_all(self) -> list[TaskRecord]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text())
        except Exception:
            return []
        if not isinstance(raw, list):
            return []
        return [TaskRecord.from_dict(item) for item in raw if isinstance(item, dict)]

    def _write_all(self, tasks: list[TaskRecord]):
        ensure_runtime_dirs()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps([task.to_dict() for task in tasks], indent=2)
        )
