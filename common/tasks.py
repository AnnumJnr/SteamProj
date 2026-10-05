"""
Non-blocking Celery task dispatch.

Standard entry point for dispatching Celery tasks from request-handling code
(signals, services, views). Use ``dispatch_task(task, ...)`` instead of
calling ``task.delay(...)`` directly.

Why it exists:
A ``.delay()`` call publishes to the Redis broker synchronously. When the
broker is slow or unreachable (as observed on Render), the request blocks
until the broker connection times out — register/login appeared broken with
~20s+ hangs even though the database work itself was fast. And with no
Celery worker deployed, tasks that did reach Redis were never consumed.

With ``INLINE_TASK_DISPATCH = True`` (core/settings/production.py), dispatch
runs the task body in a short-lived daemon thread instead: no broker in the
request path, and side effects (PostHog delivery, welcome email) actually
execute. Task failure semantics are unchanged — durable records such as
EventLog remain the replay source of truth.
"""

import logging
import threading

from django.conf import settings

logger = logging.getLogger(__name__)


def dispatch_task(task, *args, **kwargs) -> None:
    """
    Dispatch a Celery task without ever blocking the caller.

    Default (INLINE_TASK_DISPATCH falsey): ``task.delay(*args, **kwargs)`` —
    unchanged broker behaviour (development runs with eager mode).

    With INLINE_TASK_DISPATCH true: execute the task body in a daemon thread.
    The calling request returns immediately and no broker is contacted.
    """
    if not getattr(settings, "INLINE_TASK_DISPATCH", False):
        task.delay(*args, **kwargs)
        return

    threading.Thread(
        target=_run_inline,
        args=(task, args, kwargs),
        name=f"inline-task:{getattr(task, 'name', task)}",
        daemon=True,
    ).start()


def _run_inline(task, args, kwargs) -> None:
    try:
        # .apply() executes the task body in this thread with the same
        # bindings (retries, logging) as a real worker execution.
        task.apply(args=args, kwargs=kwargs)
    except Exception:
        # Includes celery.exceptions.Retry raised by in-task retry calls —
        # retry scheduling is a worker concept; inline execution stops after
        # this attempt and the durable record (e.g. EventLog) stays replayable.
        # Never let a side-effect task take down the request that spawned it.
        logger.warning(
            "dispatch_task: inline execution of task '%s' failed.",
            getattr(task, "name", task),
            exc_info=True,
        )
    finally:
        # Threads are not Django request threads — close the thread-local
        # DB connection explicitly so it is not leaked.
        from django.db import connection

        connection.close()
