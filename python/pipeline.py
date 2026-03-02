"""
pipeline.py — Async pipeline, decorators, lambdas
Showcases: async/await, decorators, lambda expressions, functools, context manager, typing protocols
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable, List, Protocol, TypeVar

from models import Priority, Status, Task, TaskCollection
from analyzer import TaskAnalyzer, MetricSnapshot

T = TypeVar("T")
logger = logging.getLogger(__name__)


# ── Protocols ─────────────────────────────────────────────────────────────────

class Processor(Protocol):
    """Anything that can process a task asynchronously."""
    async def process(self, task: Task) -> Task:
        ...


class Sink(Protocol):
    """Anything that can accept processed tasks."""
    async def accept(self, task: Task) -> None:
        ...


# ── Decorators ────────────────────────────────────────────────────────────────

def retry(max_attempts: int = 3, delay: float = 0.5):
    """Decorator: retry an async function up to max_attempts times on exception."""
    def decorator(fn: Callable):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    logger.warning("Attempt %d/%d failed: %s", attempt, max_attempts, exc)
                    await asyncio.sleep(delay * attempt)
            raise RuntimeError(f"All {max_attempts} attempts failed") from last_exc
        return wrapper
    return decorator


def timed(fn: Callable):
    """Decorator: log execution time of an async function."""
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        start = time.monotonic()
        result = await fn(*args, **kwargs)
        elapsed = time.monotonic() - start
        logger.debug("%s completed in %.3fs", fn.__name__, elapsed)
        return result
    return wrapper


def validate_tasks(fn: Callable):
    """Decorator: ensure no None tasks are passed to process methods."""
    @functools.wraps(fn)
    async def wrapper(self, task: Task, *args, **kwargs):
        if task is None:
            raise ValueError("Task cannot be None")
        return await fn(self, task, *args, **kwargs)
    return wrapper


# ── Context manager ───────────────────────────────────────────────────────────

@asynccontextmanager
async def pipeline_scope(name: str) -> AsyncGenerator[dict, None]:
    """Context manager tracking pipeline run stats."""
    stats: dict = {"name": name, "start": time.monotonic(), "processed": 0, "errors": 0}
    logger.info("Pipeline '%s' started", name)
    try:
        yield stats
    finally:
        elapsed = time.monotonic() - stats["start"]
        logger.info(
            "Pipeline '%s' finished: %d processed, %d errors in %.2fs",
            name, stats["processed"], stats["errors"], elapsed,
        )


# ── Concrete processors ───────────────────────────────────────────────────────

class PriorityEscalator:
    """Escalates overdue tasks to CRITICAL priority."""

    @validate_tasks
    @timed
    async def process(self, task: Task) -> Task:
        if task.is_overdue and task.priority != Priority.CRITICAL:
            task.priority = Priority.CRITICAL
            logger.info("Escalated task %s to CRITICAL", task.id[:8])
        return task


class NormalizationProcessor:
    """Strips leading/trailing whitespace from title and description."""

    @validate_tasks
    async def process(self, task: Task) -> Task:
        task.title = task.title.strip()
        task.description = task.description.strip()
        return task


class StatusValidator:
    """Marks tasks as DONE if completion_rate is 1.0."""

    @validate_tasks
    async def process(self, task: Task) -> Task:
        if task.completion_rate >= 1.0 and task.status != Status.DONE:
            task.transition(Status.DONE)
        return task


# ── Sinks ─────────────────────────────────────────────────────────────────────

class CollectionSink:
    """Writes processed tasks back into a TaskCollection."""

    def __init__(self, collection: TaskCollection) -> None:
        self._collection = collection

    async def accept(self, task: Task) -> None:
        self._collection.add(task)


class LoggingSink:
    """Logs each task to stdout (useful for debugging)."""

    async def accept(self, task: Task) -> None:
        logger.debug("Processed: %r", task)


# ── Pipeline ──────────────────────────────────────────────────────────────────

class AnalysisPipeline:
    """
    Async pipeline: tasks flow through a list of Processors, then into Sinks.
    Supports batch processing with concurrency control.
    """

    def __init__(
        self,
        processors: List[Processor],
        sinks: List[Sink],
        concurrency: int = 4,
    ) -> None:
        self._processors = processors
        self._sinks = sinks
        self._semaphore = asyncio.Semaphore(concurrency)

    async def _run_task(self, task: Task, stats: dict) -> None:
        async with self._semaphore:
            try:
                for processor in self._processors:
                    task = await processor.process(task)
                for sink in self._sinks:
                    await sink.accept(task)
                stats["processed"] += 1
            except Exception as exc:
                stats["errors"] += 1
                logger.error("Pipeline error on task %s: %s", task.id[:8], exc)

    @retry(max_attempts=2)
    async def run_batch(self, tasks: List[Task]) -> MetricSnapshot:
        """Run all tasks through the pipeline concurrently, return final metrics."""
        output_collection = TaskCollection("pipeline_output")
        self._sinks.append(CollectionSink(output_collection))

        async with pipeline_scope("batch") as stats:
            coros = [self._run_task(t, stats) for t in tasks]
            await asyncio.gather(*coros)

        return TaskAnalyzer(output_collection).snapshot()


# ── Lambda-heavy orchestration ────────────────────────────────────────────────

def build_pipeline(source: TaskCollection) -> AnalysisPipeline:
    """
    Factory using lambdas/higher-order functions to wire up the pipeline.
    Demonstrates: lambda, map, filter, functools.reduce.
    """
    all_tasks = source.all()

    # Lambda-based filters
    is_actionable = lambda t: not t.status.is_terminal()
    has_title = lambda t: bool(t.title.strip())
    filtered = list(filter(lambda t: is_actionable(t) and has_title(t), all_tasks))

    # Map to annotate
    score_fn = lambda t: t.estimate_effort()
    _ = list(map(score_fn, filtered))   # eagerly compute scores (side-effect: caches)

    # Reduce to build priority-ordered list (demo of functools.reduce)
    sorter = functools.reduce(
        lambda acc, t: acc + [t],
        sorted(filtered, key=lambda t: t.priority.weight(), reverse=True),
        [],
    )
    _ = sorter  # consumed downstream

    processors: List[Processor] = [
        NormalizationProcessor(),
        PriorityEscalator(),
        StatusValidator(),
    ]
    sinks: List[Sink] = [LoggingSink()]
    return AnalysisPipeline(processors, sinks, concurrency=8)


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    collection = TaskCollection("demo")
    pipeline = build_pipeline(collection)
    snapshot = await pipeline.run_batch(collection.all())
    print(snapshot.as_dict())


if __name__ == "__main__":
    asyncio.run(main())
