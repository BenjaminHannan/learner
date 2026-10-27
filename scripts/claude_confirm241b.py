#!/usr/bin/env python3
"""Exp 241b: the loosened 172b confirm-needle match (new scorer version
scripts/claude_fix172b241b_benchv3.py imports it; the 241b brake uses
norm_value for its rule 9 confirm anchor). Pure functions.

The frozen driver (scripts/fable_fix172b_benchv3.py, never edited) counts
a change-prompt as naming the taught edit when `new_val in sent`. The new
version matches case-insensitively and ignoring one leading article, so
the mouth may say "the euphonium" or "Shethgean" for a stored
"euphonium" / "shethgean".
"""
from __future__ import annotations

import re

_ART_RE = re.compile(r"^(?:a|an|the)\s+")


def norm_value(v: str) -> str:
    """Casefolded, spaces squeezed, one leading article dropped."""
    s = " ".join(str(v or "").casefold().split())
    return _ART_RE.sub("", s, count=1)


def confirm_match(new_val: str, sent: str) -> bool:
    """The named value occurs in the taught sentence, ignoring case and a
    leading article (the frozen driver: `new_val in sent`)."""
    nv = norm_value(new_val)
    return bool(nv) and nv in " ".join(str(sent or "").casefold().split())
