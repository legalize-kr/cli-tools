"""Slot separator constant for composite precedent filenames.

Format: ``{COURT}{SEP}{DATE}{SEP}{CASENO}.md``

Must be kept in sync with:
- legalize-pipeline/precedents/converter.py  (SEP constant)
- compiler-for-precedent/src/render.rs       (SEP constant)
"""

SEP: str = "--"

__all__ = ["SEP"]
