"""
analyzer.py — TaskAnalyzer: computes metrics, detects patterns, scores tasks
Showcases: classes, methods, type hints, list comprehensions, generators, property, staticmethod
"""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from typing import Dict, Generator, List, Optional, Tuple

from models import Priority, Status, Task, TaskCollection, TaskFilter


# ── Metric result types ───────────────────────────────────────────────────────

class MetricSnapshot:
    """Immutable snapshot of TaskCollection metrics at a point in time."""

    def __init__(
        self,
        total: int,
        by_status: Dict[str, int],
        by_priority: Dict[str, int],
        completion_rate: float,
        overdue_count: int,
        avg_age_days: float,
        priority_debt_score: float,
    ) -> None:
        self.total = total
        self.by_status = by_status
        self.by_priority = by_priority
        self.completion_rate = completion_rate
        self.overdue_count = overdue_count
        self.avg_age_days = avg_age_days
        self.priority_debt_score = priority_debt_score

    def __repr__(self) -> str:
        return (
            f"MetricSnapshot(total={self.total}, "
            f"completion={self.completion_rate:.1%}, "
            f"overdue={self.overdue_count})"
        )

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "by_status": self.by_status,
            "by_priority": self.by_priority,
            "completion_rate": self.completion_rate,
            "overdue_count": self.overdue_count,
            "avg_age_days": self.avg_age_days,
            "priority_debt_score": self.priority_debt_score,
        }


class HealthReport:
    """Human-readable health assessment of a task collection."""

    THRESHOLDS = {
        "critical_overdue": 10,
        "high_backlog": 50,
        "low_completion": 0.3,
    }

    def __init__(self, snapshot: MetricSnapshot) -> None:
        self.snapshot = snapshot
        self.warnings: List[str] = []
        self.recommendations: List[str] = []
        self._evaluate()

    def _evaluate(self) -> None:
        s = self.snapshot
        if s.overdue_count >= self.THRESHOLDS["critical_overdue"]:
            self.warnings.append(f"{s.overdue_count} overdue tasks — critical backlog!")
            self.recommendations.append("Triage overdue tasks immediately.")
        if s.completion_rate < self.THRESHOLDS["low_completion"]:
            self.warnings.append(f"Low completion rate: {s.completion_rate:.0%}")
            self.recommendations.append("Break large tasks into smaller subtasks.")
        if s.total >= self.THRESHOLDS["high_backlog"]:
            self.warnings.append(f"Large backlog: {s.total} total tasks")
            self.recommendations.append("Consider archiving or cancelling stale tasks.")

    @property
    def is_healthy(self) -> bool:
        return len(self.warnings) == 0

    def summary(self) -> str:
        status = "✅ Healthy" if self.is_healthy else "⚠️ Issues detected"
        lines = [status] + [f"  - {w}" for w in self.warnings]
        return "\n".join(lines)


# ── Core analyzer ─────────────────────────────────────────────────────────────

class TaskAnalyzer:
    """
    Computes metrics, ranks tasks, and detects quality patterns in a TaskCollection.
    """

    def __init__(self, collection: TaskCollection) -> None:
        self._collection = collection

    # ── Metrics ───────────────────────────────────────────────────────────

    def snapshot(self) -> MetricSnapshot:
        tasks = self._collection.all()
        if not tasks:
            return MetricSnapshot(0, {}, {}, 0.0, 0, 0.0, 0.0)

        by_status = Counter(t.status.value for t in tasks)
        by_priority = Counter(t.priority.name for t in tasks)
        done = by_status.get(Status.DONE.value, 0)
        completion_rate = done / len(tasks)
        overdue = sum(1 for t in tasks if t.is_overdue)
        ages = [t.age_days for t in tasks]
        avg_age = statistics.mean(ages) if ages else 0.0
        debt = self._priority_debt(tasks)

        return MetricSnapshot(
            total=len(tasks),
            by_status=dict(by_status),
            by_priority=dict(by_priority),
            completion_rate=completion_rate,
            overdue_count=overdue,
            avg_age_days=avg_age,
            priority_debt_score=debt,
        )

    def health_report(self) -> HealthReport:
        return HealthReport(self.snapshot())

    # ── Scoring ───────────────────────────────────────────────────────────

    def score(self, task: Task) -> float:
        """
        Composite urgency score: higher = should be done sooner.
        Factors: priority weight, age, overdue penalty, effort estimate.
        """
        base = task.priority.weight() * 10.0
        age_factor = math.log1p(task.age_days) * 2.0
        overdue_bonus = 20.0 if task.is_overdue else 0.0
        effort_penalty = task.estimate_effort() * 0.5
        return base + age_factor + overdue_bonus - effort_penalty

    def rank(self, top_n: Optional[int] = None) -> List[Tuple[Task, float]]:
        """Return tasks ranked by urgency score (descending)."""
        active = TaskFilter().with_status(*Status.active_states()).apply(self._collection.all())
        ranked = sorted(
            ((t, self.score(t)) for t in active),
            key=lambda pair: pair[1],
            reverse=True,
        )
        return ranked[:top_n] if top_n is not None else ranked

    # ── Pattern detection ─────────────────────────────────────────────────

    def find_blocked_chains(self) -> List[List[Task]]:
        """
        Detect tasks that are BLOCKED with subtasks also stuck.
        Returns chains (parent + blocked subtasks).
        """
        chains: List[List[Task]] = []
        for task in self._collection:
            if task.status == Status.BLOCKED:
                blocked_subs = [s for s in task._subtasks if s.status == Status.BLOCKED]
                if blocked_subs:
                    chains.append([task] + blocked_subs)
        return chains

    def stale_tasks(self, min_age_days: int = 30) -> List[Task]:
        """Return TODO tasks that haven't been updated in a long time."""
        return [
            t for t in self._collection
            if t.status == Status.TODO and t.age_days >= min_age_days
        ]

    def tag_distribution(self) -> Dict[str, int]:
        """Count tasks per tag."""
        dist: Dict[str, int] = defaultdict(int)
        for task in self._collection:
            for tag in task.tags:
                dist[tag.name] += 1
        return dict(dist)

    # ── Generators ────────────────────────────────────────────────────────

    def yield_critical(self) -> Generator[Task, None, None]:
        """Lazily yield CRITICAL priority tasks not yet done."""
        for task in self._collection:
            if task.priority == Priority.CRITICAL and not task.status.is_terminal():
                yield task

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _priority_debt(tasks: List[Task]) -> float:
        """
        Priority debt = sum of (weight * age_days) for all active high+ tasks.
        High value means important work has been sitting for too long.
        """
        debt = 0.0
        for task in tasks:
            if task.priority >= Priority.HIGH and not task.status.is_terminal():
                debt += task.priority.weight() * math.log1p(task.age_days)
        return round(debt, 2)

    def _normalise_score(self, raw: float, max_score: float) -> float:
        if max_score == 0:
            return 0.0
        return min(raw / max_score, 1.0)

    # ── Never-called method (dead code demo) ──────────────────────────────

    def _legacy_report(self) -> str:
        """Old plaintext report — replaced by HealthReport. Dead code."""
        snap = self.snapshot()
        return f"Total: {snap.total}, Done: {snap.by_status.get('done', 0)}"
