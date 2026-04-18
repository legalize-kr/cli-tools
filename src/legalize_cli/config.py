"""Project-wide configuration constants.

These are intentionally simple module-level constants rather than a class —
the values are process-lifetime-immutable and callers want cheap import-time
access. Any runtime overrides (e.g. cache dir via env var) are resolved here
so downstream modules can treat the resulting values as canonical.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import __version__

#: GitHub org that owns the mirror repos.
OWNER: str = "legalize-kr"

#: Repository holding Korean laws as Markdown (author-dated commits).
LAWS_REPO: str = "legalize-kr"

#: Repository holding Korean court precedents as Markdown + metadata.json.
PRECEDENTS_REPO: str = "precedent-kr"

#: Default branch used by both mirror repos.
DEFAULT_BRANCH: str = "main"

#: User-Agent string sent on every HTTP request.
USER_AGENT: str = f"legalize-cli/{__version__} (+https://github.com/legalize-kr)"


def _resolve_default_cache_dir() -> Path:
    """Resolve the default on-disk cache directory.

    Precedence:
    1. ``$LEGALIZE_CLI_CACHE_DIR`` — explicit override wins.
    2. ``$XDG_CACHE_HOME/legalize-cli`` — XDG spec, used on Linux & respected
       on macOS when the user has set it.
    3. ``~/.cache/legalize-cli`` — portable fallback.
    """
    override = os.environ.get("LEGALIZE_CLI_CACHE_DIR")
    if override:
        return Path(override).expanduser()

    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg).expanduser() if xdg else Path("~/.cache").expanduser()
    return base / "legalize-cli"


#: Default on-disk cache directory. Computed at import time; callers that
#: want to honor runtime env changes should call :func:`_resolve_default_cache_dir`.
DEFAULT_CACHE_DIR: Path = _resolve_default_cache_dir()

#: GitHub REST API root.
GITHUB_API_ROOT: str = "https://api.github.com"

#: Host for raw file downloads (not rate-limit charged).
GITHUB_RAW_HOST: str = "https://raw.githubusercontent.com"
