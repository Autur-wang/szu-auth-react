"""Tests for task_repository.py — task persistence."""

from task_repository import TaskRepository


class TestTaskRepository:
    def test_create_and_list(self, tmp_path):
        repo = TaskRepository(tmp_path / "tasks.json")
        repo.create("booking.run", "manual", {"now": True})

        tasks = repo.list()
        assert len(tasks) == 1
        assert tasks[0].command == "booking.run"

    def test_save_updates_task(self, tmp_path):
        repo = TaskRepository(tmp_path / "tasks.json")
        task = repo.create("auth.login", "manual")
        task.status = "succeeded"
        repo.save(task)

        latest = repo.latest("auth.login")
        assert latest is not None
        assert latest.status == "succeeded"

    def test_find_running(self, tmp_path):
        repo = TaskRepository(tmp_path / "tasks.json")
        task = repo.create("booking.run", "manual")
        task.status = "running"
        repo.save(task)

        running = repo.find_running("booking.run")
        assert len(running) == 1

    def test_get_by_id(self, tmp_path):
        repo = TaskRepository(tmp_path / "tasks.json")
        task = repo.create("auth.login", "manual")

        found = repo.get(task.id)

        assert found is not None
        assert found.id == task.id
