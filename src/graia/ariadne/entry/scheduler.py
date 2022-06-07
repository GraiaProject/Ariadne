import contextlib

__all__ = []

with contextlib.suppress(ImportError):
    from graia.scheduler import GraiaScheduler as GraiaScheduler
    from graia.scheduler import SchedulerTask as SchedulerTask
    from graia.scheduler.exception import AlreadyStarted as AlreadyStarted
    from graia.scheduler.saya.behaviour import (
        GraiaSchedulerBehaviour as GraiaSchedulerBehaviour,
    )
    from graia.scheduler.saya.behaviour import SchedulerSchema as SchedulerSchema
    from graia.scheduler.timers import crontabify as crontabify
    from graia.scheduler.timers import every as every
    from graia.scheduler.timers import every_custom_hours as every_custom_hours
    from graia.scheduler.timers import every_custom_minutes as every_custom_minutes
    from graia.scheduler.timers import every_custom_seconds as every_custom_seconds
    from graia.scheduler.timers import every_hours as every_hours
    from graia.scheduler.timers import every_minute as every_minute
    from graia.scheduler.timers import every_second as every_second

    __all__ = [
        "GraiaScheduler",
        "SchedulerTask",
        "AlreadyStarted",
        "GraiaSchedulerBehaviour",
        "SchedulerSchema",
        "crontabify",
        "every",
        "every_custom_hours",
        "every_custom_minutes",
        "every_custom_seconds",
        "every_hours",
        "every_minute",
        "every_second",
    ]
