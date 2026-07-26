"""In-memory async batch jobs with per-company progress events (for SSE).

One background thread per job; per-company isolation is inherited from the
pipeline's contract (an exception is an event, never an abort). Events are
appended to a list consumed by index-cursor -- multiple SSE subscribers can
replay from the start.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import structlog

LOG = structlog.get_logger("creditrating_api.jobs")


@dataclass
class Job:
    job_id: str
    tickers: list[str]
    status: str = "queued"  # queued | running | done | failed
    completed: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
    results: list[Any] = field(default_factory=list)  # RatingEnvelope
    lock: threading.Lock = field(default_factory=threading.Lock)

    def emit(self, event: dict[str, Any]) -> None:
        event["ts"] = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
        with self.lock:
            self.events.append(event)


_REGISTRY: dict[str, Job] = {}
_REG_LOCK = threading.Lock()


def get(job_id: str) -> Optional[Job]:
    with _REG_LOCK:
        return _REGISTRY.get(job_id)


def start(tickers: list[str], envelope_fn, live: bool) -> Job:
    """Create a job and run it on a daemon thread.

    ``envelope_fn(ticker, live)`` -> (RatingEnvelope | None, error_code | None);
    it owns offline policy and isolation.
    """
    job = Job(job_id=uuid.uuid4().hex[:12], tickers=[t.upper() for t in tickers])
    with _REG_LOCK:
        _REGISTRY[job.job_id] = job

    def _run() -> None:
        structlog.contextvars.bind_contextvars(run_id=job.job_id)
        job.status = "running"
        job.emit({"event": "start", "total": len(job.tickers)})
        for t in job.tickers:
            envelope, err = envelope_fn(t, live)
            job.completed += 1
            if envelope is not None:
                job.results.append(envelope)
                job.emit(
                    {
                        "event": "company",
                        "ticker": t,
                        "status": "ok",
                        # EM convergence, streamed as it lands per company.
                        "em_iterations": (
                            envelope.estimates.em_iterations if envelope.estimates else None
                        ),
                        "em_converged": (
                            envelope.estimates.em_converged if envelope.estimates else None
                        ),
                        "sigma_a": (
                            envelope.estimates.sigma_a if envelope.estimates else None
                        ),
                        "risk_score": (
                            envelope.measures.risk_score if envelope.measures else None
                        ),
                        "letter": envelope.rating.letter,
                        "determination": envelope.rating.determination,
                        "completed": job.completed,
                        "total": len(job.tickers),
                    }
                )
            else:
                job.emit(
                    {
                        "event": "company",
                        "ticker": t,
                        "status": "error",
                        "code": err or "INTERNAL",
                        "completed": job.completed,
                        "total": len(job.tickers),
                    }
                )
        job.status = "done"
        job.emit({"event": "done", "completed": job.completed})
        LOG.info("batch.done", job_id=job.job_id, completed=job.completed)

    threading.Thread(target=_run, daemon=True, name=f"batch-{job.job_id}").start()
    return job
