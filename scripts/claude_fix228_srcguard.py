"""Exp 228 THE ONE CHANGE: identity guard on fix170's _src_of().

Cause (found in exp 228): scripts/fable_fix170_compose.py maps
_SRC[id(triples list)] -> [inner notebook, version] but does not keep the list
alive. Once a cached list is freed (for example _TRIPLES.clear() after more
than 8 notebooks), its _SRC entry can outlive it. CPython reuses the freed
address for the next list allocated -- often the fresh copy that
fable_qrewrite132.rewrite_question builds -- and _src_of() then returns the
OLD notebook (its version still matches, because nothing writes to it any
more). The fast compose_n_hop / compound_subject_hit leaves read the wrong
index, the rewrite verify fails, the clarify stands and the mouth glues the
decline. Whether an address is reused depends on the allocation history of the
whole process, so the flip is rare and looks random.

Fix: _src_of() only answers "this list is ours" when the list IS the list
currently cached for that notebook in _TRIPLES (object identity, which a live
object cannot share). Every other list falls back to the sealed originals,
which 170 already uses for foreign lists (replies identical by construction).
Installed process-locally by rebinding the module global, the same pattern
install_index170() uses. No existing file is edited.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix170_compose as F170  # noqa: E402 (rebound leaf, read-only)

_ORIG_SRC_OF = F170._src_of
_INSTALLED = False


def src_of228(triples):
    """fix170 _src_of, but only for the live cached list object itself."""
    inner = _ORIG_SRC_OF(triples)
    if inner is None:
        return None
    e = F170._TRIPLES.get(id(inner))
    if e is not None and e[2] is inner and e[1] is triples:
        return inner
    return None


class SrcGuardMixin228:
    """Mixin: installs the guard when the daemon is built (idempotent)."""

    def __init__(self, *args, **kwargs):
        install_srcguard228()
        super().__init__(*args, **kwargs)


def install_srcguard228() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    F170._src_of = src_of228
    _INSTALLED = True


def is_installed() -> bool:
    return _INSTALLED
