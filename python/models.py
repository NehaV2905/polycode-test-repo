"""
models.py — Task domain model
Showcases: dataclasses, enums, type hints, properties, class methods, dunder methods
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Optional, List, Callable


# ── Enums ────────────────────────────────────────────────────────────────────

class Priority(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()

    def weight(self) -> int:
        weights = {
            Priority.LOW: 1,
            Priority.MEDIUM: 2,
            Priority.HIGH: 4,
            Priority.CRITICAL: 8,
        }
        return weights[self]

    def __lt__(self, other: Priority) -> bool:
        return self.weight() < other.weight()


class Status(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"

    @classmethod
    def active_states(cls) -> List[Status]:
        return [cls.TODO, cls.IN_PROGRESS, cls.BLOCKED]

    def is_terminal(self) -> bool:
        return self in (Status.DONE, Status.CANCELLED)


# ── Tag ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Tag:
    name: str
    color: str = "#888888"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Tag name cannot be empty")

    def __str__(self) -> str:
        return f"#{self.name}"


# ── Task ─────────────────────────────────────────────────────────────────────

@dataclass
class Task:
    title: str
    priority: Priority = Priority.MEDIUM
    status: Status = Status.TODO
    description: str = ""
    tags: List[Tag] = field(default_factory=list)
    due_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    _subtasks: List[Task] = field(default_factory=list, repr=False)

    # ── Derived properties ────────────────────────────────────────────────

    @property
    def is_overdue(self) -> bool:
        if self.due_date is None:
            return False
        return datetime.utcnow() > self.due_date and not self.status.is_terminal()

    @property
    def age_days(self) -> int:
        return (datetime.utcnow() - self.created_at).days

    @property
    def subtask_count(self) -> int:
        return len(self._subtasks)

    @property
    def completion_rate(self) -> float:
        if not self._subtasks:
            return 1.0 if self.status == Status.DONE else 0.0
        done = sum(1 for t in self._subtasks if t.status == Status.DONE)
        return done / len(self._subtasks)

    # ── Mutation ──────────────────────────────────────────────────────────

    def transition(self, new_status: Status) -> None:
        if self.status.is_terminal():
            raise ValueError(f"Cannot transition from terminal status {self.status}")
        self.status = new_status
        self.updated_at = datetime.utcnow()

    def add_subtask(self, subtask: Task) -> None:
        self._subtasks.append(subtask)
        self.updated_at = datetime.utcnow()

    def add_tag(self, tag: Tag) -> None:
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag_name: str) -> None:
        self.tags = [t for t in self.tags if t.name != tag_name]

    def estimate_effort(self) -> int:
        """Return a rough effort estimate (story points) based on heuristics."""
        base = self.priority.weight() * 2
        sub_penalty = self.subtask_count // 3
        overdue_penalty = 1 if self.is_overdue else 0
        return base + sub_penalty + overdue_penalty

    # ── Comparison & representation ────────────────────────────────────────

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Task):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"Task(id={self.id[:8]}, title={self.title!r}, status={self.status.value})"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority.name,
            "status": self.status.value,
            "description": self.description,
            "tags": [t.name for t in self.tags],
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "subtask_count": self.subtask_count,
            "completion_rate": self.completion_rate,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        return cls(
            id=data["id"],
            title=data["title"],
            priority=Priority[data["priority"]],
            status=Status(data["status"]),
            description=data.get("description", ""),
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
        )


# ── TaskFilter ────────────────────────────────────────────────────────────────

class TaskFilter:
    """Composable filter builder for querying task collections."""

    def __init__(self) -> None:
        self._predicates: List[Callable[[Task], bool]] = []

    def with_status(self, *statuses: Status) -> TaskFilter:
        self._predicates.append(lambda t: t.status in statuses)
        return self

    def with_priority(self, min_priority: Priority) -> TaskFilter:
        self._predicates.append(lambda t: t.priority >= min_priority)
        return self

    def with_tag(self, tag_name: str) -> TaskFilter:
        self._predicates.append(lambda t: any(tag.name == tag_name for tag in t.tags))
        return self

    def overdue_only(self) -> TaskFilter:
        self._predicates.append(lambda t: t.is_overdue)
        return self

    def apply(self, tasks: List[Task]) -> List[Task]:
        result = tasks
        for predicate in self._predicates:
            result = [t for t in result if predicate(t)]
        return result

    def count(self, tasks: List[Task]) -> int:
        return len(self.apply(tasks))


# ── TaskCollection ────────────────────────────────────────────────────────────

class TaskCollection:
    """An indexed, iterable bag of Tasks with bulk operations."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._index: dict[str, Task] = {}

    def add(self, task: Task) -> None:
        self._index[task.id] = task

    def get(self, task_id: str) -> Optional[Task]:
        return self._index.get(task_id)

    def remove(self, task_id: str) -> bool:
        return self._index.pop(task_id, None) is not None

    def all(self) -> List[Task]:
        return list(self._index.values())

    def filter(self, f: TaskFilter) -> List[Task]:
        return f.apply(self.all())

    def group_by_status(self) -> dict[Status, List[Task]]:
        groups: dict[Status, List[Task]] = {s: [] for s in Status}
        for task in self.all():
            groups[task.status].append(task)
        return groups

    def sort_by_priority(self, descending: bool = True) -> List[Task]:
        return sorted(self.all(), key=lambda t: t.priority.weight(), reverse=descending)

    def __len__(self) -> int:
        return len(self._index)

    def __iter__(self):
        return iter(self._index.values())

    def __contains__(self, task_id: str) -> bool:
        return task_id in self._index


# ── Intentionally unreachable code (for dead-code detection demo) ─────────────

def _legacy_task_builder(title: str, urgent: bool) -> Task:
    """Deprecated: Use Task() dataclass directly. Never called."""
    p = Priority.HIGH if urgent else Priority.LOW
    return Task(title=title, priority=p)


def _compute_score_v1(task: Task) -> float:
    """Old scoring algorithm — superseded by TaskAnalyzer.score(). Never called."""
    return task.priority.weight() * 10.0 - task.age_days * 0.5
