"""Task domain models for command execution."""

import time
import uuid
from dataclasses import asdict, dataclass, field


@dataclass
class TaskRecord:
    id: str
    command: str
    trigger_source: str
    status: str = "queued"
    payload: dict = field(default_factory=dict)
    result: dict | None = None
    error: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: float = 0
    finished_at: float = 0

    @classmethod
    def create(
        cls,
        command: str,
        trigger_source: str,
        payload: dict | None = None,
        metadata: dict | None = None,
    ) -> "TaskRecord":
        return cls(
            id=uuid.uuid4().hex,
            command=command,
            trigger_source=trigger_source,
            payload=payload or {},
            metadata=metadata or {},
        )

    @classmethod
    def from_dict(cls, data: dict) -> "TaskRecord":
        known = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

    def to_dict(self) -> dict:
        return asdict(self)
