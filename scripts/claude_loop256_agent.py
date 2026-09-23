#!/usr/bin/env python3
"""Exp 256 -- the learned ear in front of the loop's reading (stage 1).

loop256 = loop138l (scripts/claude_loop138l_agent.py, unchanged, read-only)
          + ONE mixin, Ear256LoopMixin (this file), outermost on the loop.
Helpers: scripts/claude_ear256_ear.py (the 235 model + 235b gate, imported
unchanged), scripts/claude_ear256_route.py (renderings, round-trip rows,
fixed-act test, 251 veto).

Per turn (config key "ear256"):
 1. Fixed acts stay on the legacy path, decided by the base's own code:
    189b repeat requests, 226 source questions, any pending base dialogue
    state (confirm / pick / replace), then -- only when the ear has frames --
    the base's own ears reading of the raw turn (a dry run on a deep copy of
    the ears): any non-teach/ask action (correct, forget, ...), the
    user-name flow (name173 flags) or any clarify that is not the base's
    plain "didn't understand" / "one fact at a time" failure.
 2. The ear reads the raw turn: greedy + 235's brake + 235b's gate
    (question guard + margin; margin only when tau is set).
    a. TEACH frames -> the canonical teach sentence(s) (round-trip rows only)
       handed to the base's turn path, one after the other, replies joined.
    b. ASK frames -> the canonical question for that subject/relation/chain.
    c. A frame whose round-trip row failed -> the whole turn goes to (e).
    d. ASK frames on a turn the 251 direction check marks backwards -> (e).
    e. NONE / unsure / dropped -> base legacy handling of the raw turn,
       unchanged; if the question guard fired, legacy writes are refused
       with the base's own "Was that a question?" clarify.
    If the ear's frames equal the base's own dry-run reading, the raw turn
    goes to the base unchanged (byte-identical by construction).
Never writes to the notebook itself; no new reply text.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_fix228_srcguard as G228  # noqa: E402 (228 guard, read-only)

G228.install_srcguard228()  # 228 first, at import

import claude_loop138l_agent as L138L  # noqa: E402 (base, read-only)
import claude_ear256_route as R  # noqa: E402
import fable_earsguard91 as EG  # noqa: E402 (read-only: base clarify text)
import fable_loop189b_agent as L189B  # noqa: E402 (read-only)
import fable_loop226_agent as L226  # noqa: E402 (read-only)

REPO = SCRIPTS.parent
WRITE_ACTS256 = {"teach", "correct", "correct_multi154b", "person", "alias"}

_EAR = {}
_RT = {}


def get_ear(ecfg: dict):
    key = (ecfg["ckpt"], ecfg.get("tau"), ecfg.get("k"))
    if key not in _EAR:
        import claude_ear256_ear as EAR  # noqa: E402 (torch import only when used)
        _EAR[key] = EAR.Ear(ecfg["ckpt"], expect_sha=ecfg.get("sha256"), tau=ecfg.get("tau"),
                            k=ecfg.get("k"))
    return _EAR[key]


def get_rt(ecfg: dict):
    p = ecfg["roundtrip"]
    if p not in _RT:
        _RT[p] = R.load_roundtrip(p)
    return _RT[p]


def _pending256(loop) -> str | None:
    for owner_name, owner in (("loop", loop), ("listening", getattr(loop, "listening", None)),
                              ("ears", getattr(loop, "_inner138j_ears", None))):
        if owner is None:
            continue
        for k, v in list(vars(owner).items()):
            if "pending" in k and v:
                return f"{owner_name}.{k}"
    return None


class Ear256LoopMixin:
    """THE ONE CHANGE (outermost on the 138l loop)."""

    ear256_cfg: dict | None = None

    def turn(self, text: str) -> list[str]:  # type: ignore[override]
        cfg = self.ear256_cfg
        if not cfg or not cfg.get("enabled", True):
            return super().turn(text)  # type: ignore[misc]
        tr = {"turn": text}
        log = self.__dict__.setdefault("ear256_log", [])
        log.append(tr)
        try:
            plan = self._plan256(text, tr, cfg)
        except Exception as exc:  # noqa: BLE001 -- the base path always remains
            tr["route"], tr["error"], plan = "legacy_error", repr(exc), None
        if plan is None:
            if tr.get("block_writes"):
                self._ear256_block = tr
                try:
                    return super().turn(text)  # type: ignore[misc]
                finally:
                    self._ear256_block = None
            return super().turn(text)  # type: ignore[misc]
        tr["route"] = "ear"
        tr["canonical"] = list(plan)
        said: list[str] = []
        for c in plan:
            said.extend(super().turn(c))  # type: ignore[misc]
        return said

    def _act(self, action: dict) -> dict:  # type: ignore[override]
        blk = getattr(self, "_ear256_block", None)
        if blk and isinstance(action, dict) and action.get("act") in WRITE_ACTS256:
            blk["blocked_write"] = dict(action)
            return super()._act({"act": "clarify", "text": EG.QUESTION_MSG})  # type: ignore[misc]
        return super()._act(action)  # type: ignore[misc]

    # ------------------------------------------------------------ plan
    def _plan256(self, text: str, tr: dict, cfg: dict):
        if L189B.is_repeat189b(text):
            tr["route"] = "legacy_fixed:repeat189b"
            return None
        if L226.is_source_question226(text):
            tr["route"] = "legacy_fixed:source226"
            return None
        pend = _pending256(self)
        if pend:
            tr["route"] = "legacy_fixed:pending:" + pend
            return None
        ear = get_ear(cfg)
        import torch  # noqa: E402
        prev = torch.get_num_threads()
        torch.set_num_threads(int(cfg.get("threads", 1)))
        try:
            r = ear.read(text)
        finally:
            torch.set_num_threads(prev)
        tr["raw"], tr["ms_ear"] = r["raw"], round(r["ms"], 1)
        kept = r["kept"]
        g = r["gate"]
        if g is not None:
            saved, unsure, guard = g["saved"], g["unsure"], g["guard"]
        else:  # question guard only (no margin gate)
            import claude_smolear235b_beam as B  # noqa: E402
            qm = B.ends_q(text)
            guard = [f for f in kept if f["act"] == "TEACH" and qm]
            saved = [f for f in kept if not (f["act"] == "TEACH" and qm)]
            unsure = []
        tr["frames"] = [_fr(f) for f in saved]
        if guard or any(u.get("why") == "UNSURE_ASK" for u in unsure):
            tr["block_writes"] = True
        if guard:
            tr["route"] = "legacy:guard_q"
            return None
        if unsure:
            tr["route"] = "legacy:unsure"
            return None
        if not saved:
            tr["route"] = "legacy:none" if not r["dropped"] else "legacy:dropped"
            return None
        if any(R.is_second(f["subject"]) for f in saved):
            tr["route"] = "legacy:second_person"
            return None
        if any(f["act"] == "ASK" for f in saved) and R.backwards251(text):
            tr["route"] = "legacy:direction251"
            return None
        acts = copy.deepcopy(self.ears).hear(text)  # the base's own reading (dry run)
        tr["base_acts"] = [{k: v for k, v in a.items() if k in ("act", "name", "relation", "relations",
                                                                "value", "text", "stage")}
                           for a in acts if isinstance(a, dict)]
        why = R.fixed_reason(acts)
        if why:
            tr["route"] = "legacy_fixed:" + why
            return None
        if R.plain_frames_of(acts) == R.ear_keys(saved):
            tr["route"] = "legacy:same_as_base"
            return None
        rt = get_rt(cfg)
        plan = []
        for f in saved:
            c = R.render_teach(rt, f) if f["act"] == "TEACH" else R.render_ask(rt, f)
            if c is None:
                tr["route"] = "legacy:roundtrip_row_failed"
                tr["failed_frame"] = _fr(f)
                return None
            plan.append(c)
        return plan


def _fr(f):
    if f["act"] == "TEACH":
        return f"TEACH | {f['subject']} | {f['relation']} | {f['value']}"
    return f"ASK | {f['subject']} | {' > '.join(f['relation'])}"


class Loop256AgentLoop(Ear256LoopMixin, L138L.Loop138lAgentLoop):
    """138l loop + the 256 ear mixin."""


def install256(loop, cfg: dict | None) -> None:
    if not isinstance(loop, L138L.Loop138lAgentLoop):
        raise RuntimeError("256: base loop is not Loop138lAgentLoop")
    loop.__class__ = Loop256AgentLoop
    loop.ear256_cfg = copy.deepcopy((cfg or {}).get("ear256"))
    loop.notes.append("loop256: loop138l + 256 ear mixin")


DEFAULT_CONFIG256: dict = copy.deepcopy(L138L.DEFAULT_CONFIG138L)
DEFAULT_CONFIG256["daemon"]["module"] = (
    "Loop256Daemon (scripts/claude_loop256_agent.py) over Loop138lDaemon")


def build_agent256(cfg: dict | None = None):
    cfg = dict(DEFAULT_CONFIG256, **(cfg or {}))
    loop = L138L.build_agent138l(cfg)
    install256(loop, cfg)
    return loop


class Ear256DaemonMixin:
    def __init__(self, root, cfg=None, **kwargs):
        G228.install_srcguard228()  # 228 first (idempotent), as in 138l
        super().__init__(root, cfg=cfg, **kwargs)  # type: ignore[call-arg]
        install256(self.loop, cfg)  # type: ignore[attr-defined]


class Loop256Daemon(Ear256DaemonMixin, L138L.Loop138lDaemon):
    """Loop138lDaemon + the 256 ear mixin on its loop.

    SrcGuardMixin228 cannot be listed first here: it is already inside
    Loop138lDaemon's MRO (via Loop138kDaemon), after Loop138lDaemon, so C3
    refuses it as a leading base. The guard is installed at import, first
    thing in Ear256DaemonMixin.__init__, and again by 138l's own mixins;
    it stays the first class of the 138k part of the MRO (asserted below)."""


_D = [c.__name__ for c in Loop256Daemon.__mro__]
assert _D[:4] == ["Loop256Daemon", "Ear256DaemonMixin", "Loop138lDaemon", "Classes138lMixin"], _D
assert _D[4:6] == ["Loop138kDaemon", "SrcGuardMixin228"], _D


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 256 (138l + learned ear)")
    parser.add_argument("--config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    args = parser.parse_args(argv)
    cfg = copy.deepcopy(DEFAULT_CONFIG256)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or args.dir:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return Loop256Daemon(args.dir, cfg=cfg, idle_seconds=args.idle_seconds).run()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
