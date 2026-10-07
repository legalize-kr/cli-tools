from __future__ import annotations

import pytest

from legalize_cli.services.limits import RequestBudget
from legalize_cli.util.errors import RequestBudgetExceededError


def test_request_count_and_deadline_stop_future_calls() -> None:
    now = [10.0]
    budget = RequestBudget(max_requests=1, deadline_seconds=5, clock=lambda: now[0])
    budget.consume_request()
    with pytest.raises(RequestBudgetExceededError):
        budget.consume_request()
    now[0] = 16.0
    with pytest.raises(RequestBudgetExceededError):
        budget.checkpoint()
