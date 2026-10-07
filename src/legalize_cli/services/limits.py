from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from ..util.errors import RequestBudgetExceededError


@dataclass
class RequestBudget:
    max_requests: int = 100
    deadline_seconds: float = 60.0
    clock: Callable[[], float] = time.monotonic
    used_requests: int = 0
    _started_at: float = field(init=False)

    def __post_init__(self) -> None:
        self._started_at = self.clock()

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.deadline_seconds - (self.clock() - self._started_at))

    def checkpoint(self) -> None:
        if self.remaining_seconds <= 0:
            raise RequestBudgetExceededError("도구 호출의 60초 협력적 deadline을 초과했습니다.")

    def consume_request(self) -> None:
        self.checkpoint()
        if self.used_requests >= self.max_requests:
            raise RequestBudgetExceededError("도구 호출의 HTTP 요청 100회 한도를 초과했습니다.")
        self.used_requests += 1


__all__ = ["RequestBudget"]
