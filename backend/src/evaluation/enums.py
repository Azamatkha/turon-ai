from enum import StrEnum


class EvalStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


ACTIVE_STATUSES = (EvalStatus.QUEUED.value, EvalStatus.RUNNING.value)
