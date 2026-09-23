#!/usr/bin/env python3
"""Exp 252b: ONE change on top of 252, inside the value screen only: the
stopword check tokenises on non-letter characters, so "that's" is caught
like "that", and it also rejects the apostrophe-less spellings of the
contractions it covers ("thats", "isnt", ...; list below).

Bug (252 panel c252-022): value_ok252 split values on spaces only, so the
token "that's" never matched the stopword "that" and "Quenby's manager is
not Tobin anymore, that's outdated." stored the value "that's outdated".

value_ok252 is the only screen in claude_fix252_correct.py that checks words
against the stopword list (every caller -- _fix252, the bare-value path, the
explicit named path and _two252 -- goes through it). The 252 methods look the
function up as a module global at call time, so install_screen252b() rebinds
that global in the loaded module object (no file is edited). All other checks
(1-4 space tokens, token shape, the 139b base screen) are unchanged.

Process note: after install, every 252 agent in the SAME Python process uses
the new screen; the drivers load one agent per process.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_fix252_correct as F252  # noqa: E402 (read-only)

_ORIG_VALUE_OK252 = F252.value_ok252

# Apostrophe-less spellings of the contractions the screen covers (those
# whose first piece is a 252 stopword, e.g. that's -> "that", or that are
# listed whole, e.g. don't). Coordinator ruling 252b option B: safety
# screening, not wording coverage. Spellings that are also ordinary English
# words or plausible names/places are EXCLUDED (never added):
#   its hell shell well ill wed id shed were lets whys hows ive im cant wont
APOSLESS252B = frozenset("""
thats hes shes theres heres whats whos wheres whens
isnt wasnt arent werent doesnt didnt dont
theyre youre
theyll youll itll thatll therell wholl
hed theyd youd itd thatd whod
theyve youve weve whove
""".split())
EXCLUDED252B = ("its hell shell well ill wed id shed were lets whys hows ive "
                "im cant wont").split()


def value_ok252b(z: str) -> bool:
    """252's screen + stopword check on letter-only pieces of each token."""
    if not _ORIG_VALUE_OK252(z):
        return False
    for piece in re.split(r"[^A-Za-z]+", F252._norm(z)):
        if piece and (piece.lower() in F252._STOP
                      or piece.lower() in APOSLESS252B):
            return False
    return True


def install_screen252b() -> None:
    F252.value_ok252 = value_ok252b


install_screen252b()
