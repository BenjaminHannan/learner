#!/usr/bin/env python3
"""Exp 266b THE ONE CHANGE: let the chain-subject lift accept two-word names.

266 is a registered FAIL on multi-word chains (design note
design/v3/30-modes/266b-multiword-chain-base.md, cause b): its detector
takes only the last word before "'s" as the name, so for a chain starting
with a two-word name ("Mara Voss's boss") the rewritten probe question is
broken ("Where does Mara Zqbex live?"), the gate clarifies, and the lift
never fires.

266b = 266 + ONE detector change: the chain's first link may be a name of
one to three capitalised words ("Mara Voss's boss", "Del Ray Okoro's
coach"), matched against names the notebook holds, longest first. Nothing
else changes: the same dry probe, the same canonical question, the same
pass-through.

Rules (exactly as specced):
  - one-word base or "my"-form: exactly 266's path (delegated to
    F266.ChainLift266Mixin.hear on the same turn), so one-word behaviour
    is identical by construction;
  - two/three-word base, exact base in the notebook: lift with the full
    span (answers about "Mara Voss's boss", never "Voss's boss");
  - two/three-word base NOT in the notebook: pass through with NO
    fallback to a shorter sub-span (an untaught multi-word name is never
    lifted into a guess, and never answered as its last word).

New file only; 266 (scripts/claude_fix266_chainlift.py) and every base
module are imported read-only. This mixin subclasses 266's lift and owns
no save code, no ask code and no screens. Questions only, never writes.
"""

from __future__ import annotations

import json
import os
import re

import claude_fix266_chainlift as F266  # noqa: E402 (266, read-only)

_LINK266B = r"(?:" + F266._APOS266 + r"s " + F266._REL266 + r")"
_BASE266B = r"(?:" + F266._NAME266 + r"(?: " + F266._NAME266 + r"){0,2})"
CHAIN266B_RE = re.compile(
    r"(?:" + F266._MY266 + r" " + F266._REL266 + _LINK266B + r"{0,2}"
    r"|" + _BASE266B + _LINK266B + r"{1,3})")

STAGE266B = "loop266b-multiword-chainlift"


def find_chain266b(turn: str) -> tuple[str, int, int] | None:
    """Longest multi-word-aware possessive-chain span in a ?-turn, else None.

    Returns (chain, start, end). The base may be one to three capitalised
    words; greedy matching takes the longest base at the leftmost start.
    """
    t = " ".join(str(turn).split())
    if not t.endswith("?"):
        return None
    m = CHAIN266B_RE.search(t)
    if m is None:
        return None
    return (m.group(0), m.start(), m.end())


def split266b(chain: str) -> tuple[str, str | None]:
    """Split a chain span into ("my", None) or ("name", base)."""
    s = str(chain)
    if re.match(r"[Mm][Yy](?: |$)", s):
        return ("my", None)
    m = re.search(F266._APOS266 + r"s ", s)
    base = s[:m.start()] if m is not None else s
    return ("name", base)


def known_names266b(ears) -> set[str]:
    """Names the notebook holds (subjects of stored triples)."""
    try:
        nb = getattr(ears, "nb", None)
        if nb is None:
            return set()
        import fable_loop90_agent as L90  # noqa: E402 (read-only)
        names = set()
        for triple in L90.notebook_triples(nb):
            try:
                names.add(triple[0])
            except Exception:
                continue
        return names
    except Exception:
        return set()


class ChainLift266bMixin(F266.ChainLift266Mixin):
    """266's lift with a multi-word-aware detector (questions only)."""

    last_chainlift266b: dict | None = None

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        self.last_chainlift266b = None
        try:
            t = " ".join(str(turn).split())
            if F266.PLACEHOLDER266 in str(turn) or not t.endswith("?"):
                return super().hear(turn)  # type: ignore[misc]
            found = find_chain266b(t)
            if found is None:
                return super().hear(turn)  # type: ignore[misc]
            chain, start, end = found
            kind, base = split266b(chain)
            if kind == "name" and base is not None \
                    and len(base.split()) > 1:
                if base not in known_names266b(self):
                    # Untaught multi-word base: pass through. No fallback
                    # to a shorter sub-span (that would answer about the
                    # wrong person, e.g. "Voss" for "Mara Voss's boss").
                    return super().hear(turn)  # type: ignore[misc]
                return self._lift266b(turn, t, chain, start, end)
            # One-word base or my-form: exactly 266's path.
            return F266.ChainLift266Mixin.hear(self, turn)
        except Exception:  # noqa: BLE001 -- lift never breaks a turn
            try:
                return super().hear(turn)  # type: ignore[misc]
            except Exception:
                return F266.ChainLift266Mixin.hear(self, turn)

    def _lift266b(self, turn: str, t: str, chain: str,
                  start: int, end: int) -> list[dict]:
        """266's probe/gate/canonical sequence for a known multi-word span."""
        if F266.placeholder_in_notebook266(self):
            return super().hear(turn)  # type: ignore[misc]
        rewritten = t[:start] + F266.PLACEHOLDER266 + t[end:]
        try:
            probe = super().hear(rewritten)  # type: ignore[misc]
        except Exception:
            probe = None
        relation = F266.gate266(probe) if probe is not None else None
        if relation is None:
            return super().hear(turn)  # type: ignore[misc]
        canonical = F266.canonical266(chain, relation)
        try:
            acts = super().hear(canonical)  # type: ignore[misc]
        except Exception:
            return super().hear(turn)  # type: ignore[misc]
        if isinstance(acts, list):
            info = {"turn": turn, "canonical": canonical}
            self.last_chainlift266b = info
            self.last_chainlift266 = info
            log = os.environ.get("CHAINLIFT266B_LOG")
            if log:
                try:
                    with open(log, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(info) + "\n")
                except OSError:
                    pass
            return acts
        return super().hear(turn)  # type: ignore[misc]


def selftest266b() -> int:
    """Pure-function checks: multi-word spans, splits, canonical phrasing."""
    ok = True

    def check(turn, want_chain):
        nonlocal ok
        got = find_chain266b(turn)
        good = (got is None and want_chain is None) or (
            got is not None and want_chain is not None
            and got[0] == want_chain)
        ok = ok and good
        print(f"{'OK' if good else 'MISMATCH'}: {turn!r} -> "
              f"{(got[0] if got else None)!r} (want {want_chain!r})")

    check("Where does Mara Voss's boss live?", "Mara Voss's boss")
    check("Where does Pix's boss's boss live?", "Pix's boss's boss")
    check("Where does Del Ray Okoro's coach's boss live?",
          "Del Ray Okoro's coach's boss")
    check("Where does my teacher live?", "my teacher")
    check("Who does my brother's boss work for?", "my brother's boss")
    check("What is Mara Voss's boss's city?", "Mara Voss's boss's city")
    check("Where does Tovi live?", None)
    check("What town does Tovi live in?", None)
    check("Mara Voss's boss is Taren.", None)
    check("What does Tovi do?", None)
    check("Where does Mara Voss live?", None)

    def check_split(chain, want):
        nonlocal ok
        got = split266b(chain)
        good = got == want
        ok = ok and good
        print(f"{'OK' if good else 'MISMATCH'}: split {chain!r} -> "
              f"{got!r} (want {want!r})")

    check_split("Mara Voss's boss", ("name", "Mara Voss"))
    check_split("Del Ray Okoro's coach's boss", ("name", "Del Ray Okoro"))
    check_split("Vex's boss", ("name", "Vex"))
    check_split("my teacher", ("my", None))
    check_split("my brother's boss", ("my", None))

    def check_canon(chain, rel, want):
        nonlocal ok
        got = F266.canonical266(chain, rel)
        good = got == want
        ok = ok and good
        print(f"{'OK' if good else 'MISMATCH'}: ({chain!r}, {rel!r}) -> "
              f"{got!r} (want {want!r})")

    check_canon("Mara Voss's boss", "city",
                "What is Mara Voss's boss's city?")
    check_canon("Del Ray Okoro's coach", "employer",
                "Who is Del Ray Okoro's coach's employer?")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(selftest266b())
