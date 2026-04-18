"""Gate live tests behind both ``@pytest.mark.live`` marker AND ``LEGALIZE_CLI_LIVE=1``."""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config, items):  # type: ignore[no-untyped-def]
    if os.environ.get("LEGALIZE_CLI_LIVE") != "1":
        skip_live = pytest.mark.skip(reason="live tests require LEGALIZE_CLI_LIVE=1")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)
