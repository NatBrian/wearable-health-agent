"""Scheduler module alias for service.scheduler.

Lazily re-exported: importing this alias must not pull apscheduler in, because the
import sweep in tests/unit/android/ requires every non-PC module to load without the
PC-only packages. The phone never uses this alias; it exists for the CLI and tests.
"""

__all__ = [
    "create_scheduler",
    "run_episode_tick",
    "safe_job_wrapper",
]


def __getattr__(name: str) -> object:
    if name in __all__:
        from wha.service import scheduler as _scheduler

        return getattr(_scheduler, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
