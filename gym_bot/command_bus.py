"""Command routing for task execution."""

from dataclasses import dataclass, field


@dataclass
class CommandContext:
    cfg: object
    payload: dict
    trigger_source: str
    task: object
    runtime_context: dict = field(default_factory=dict)


class CommandBus:
    def __init__(self):
        self._handlers: dict[str, object] = {}

    def register(self, command: str, handler):
        self._handlers[command] = handler

    def dispatch(self, command: str, context: CommandContext):
        if command not in self._handlers:
            raise KeyError(f"unknown command: {command}")
        return self._handlers[command](context)
