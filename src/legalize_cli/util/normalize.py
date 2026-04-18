"""Unicode normalization helpers applied at parser boundaries.

Korean law text lands in the repo with two sources of canonicalization drift:

1. NFC vs NFD — the pipeline writes NFC but older API responses sometimes
   carry precomposed vs decomposed jamo; we re-normalize on read.
2. Middle-dot variants — ``·`` (U+00B7 MIDDLE DOT) and ``ㆍ`` (U+318D
   HANGUL LETTER ARAEA) are visually identical for legal names like
   ``대ㆍ중ㆍ소기업 상생협력 촉진에 관한 법률``. The pipeline's canonical
   form uses ``ㆍ``; we fold ``·`` to it for law-name comparisons.
"""

from __future__ import annotations

import unicodedata

#: U+00B7 MIDDLE DOT (Latin/Korean keyboards often produce this).
MIDDLE_DOT = "\u00B7"
#: U+318D HANGUL LETTER ARAEA (the canonical form in the pipeline).
HANGUL_ARAEA = "\u318D"
#: UTF-8 BOM as a string (Python decodes it as ``\ufeff``).
BOM = "\ufeff"


def normalize_text(s: str) -> str:
    """NFC-normalize and strip a leading BOM."""
    if not s:
        return s
    if s.startswith(BOM):
        s = s[1:]
    return unicodedata.normalize("NFC", s)


def normalize_lawname(s: str) -> str:
    """Canonicalize a 법령명: NFC + ``·`` → ``ㆍ``."""
    return normalize_text(s).replace(MIDDLE_DOT, HANGUL_ARAEA)


__all__ = ["normalize_text", "normalize_lawname", "MIDDLE_DOT", "HANGUL_ARAEA", "BOM"]
