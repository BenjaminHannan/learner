#!/usr/bin/env python3
"""Exp 138f STEP 1 -- attribution: run each of the 7 M4 cases on loop138d
with each of the 11 pieces switched off one at a time.

No existing file is edited. Every variant is a mixin subclass defined HERE
(omit-one-mixin from the 138d ears/loop MRO, reasoner without the 159
fallback, loop with the 138b turn for 138c-off, base-notebook init + no
142 patches for 142-off). Judges are imported read-only:
  redteam136 C124/C127/C129/C142 via fable_fix139b_redteam136.run_case139b
  cases139b C10/C21 via fable_fix139b_probe.run_case
  redteam143 M3 via fable_redteam143_run.run_case
Each variant result is compared field-by-field (verdict + reply + stored)
against the SEALED loop138b frozen rows. Output: attribution-138f.json
(diagnosis only, NOT part of any seal).

Run (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_fix138f_ablate.py
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (Protocols, read-only)
import fable_daemon108_run as D108  # noqa: E402 (reconcile, read-only)
import fable_daemon141_settle as D141  # noqa: E402 (settle, read-only)
import fable_doubt146b_store as D146B  # noqa: E402 (doubt mixin, read-only)
import fable_fix139b_probe as P139b  # noqa: E402 (judge, read-only)
import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
import fable_fix150b_subject150b as S150B  # noqa: E402 (guard, read-only)
import fable_fix153_reverse as R153  # noqa: E402 (reverse, read-only)
import fable_fix154_yesno as Y154  # noqa: E402 (yes/no, read-only)
import fable_fix155_inverted as I155  # noqa: E402 (inverted, read-only)
import fable_fix156b_smalltalk as S156B  # noqa: E402 (smalltalk, read-only)
import fable_fix157_filler as F157  # noqa: E402 (filler, read-only)
import fable_fix158_qform as Q158  # noqa: E402 (qform, read-only)
import fable_fix159_hop as H159  # noqa: E402 (hop, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain, read-only)
import fable_loop134_agent as L134  # noqa: E402 (138d turn path, read-only)
import fable_loop138_agent as L138  # noqa: E402 (138b turn path, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (base, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (full stack, read-only)
import fable_loop148b_agent as L148b  # noqa: E402 (screen, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_redteam143_run as R143  # noqa: E402 (judge, read-only)
import fable_sleep145_agent as S145  # noqa: E402 (sleep retrofit, read-only)
from fable_perf128_index import IndexedLoopNotebook  # noqa: E402 (read-only)
from fable_perf142_index import (  # noqa: E402 (142 pieces, read-only)
    FastReasoner142,
    _patch_relation,
    patch_chain142,
    patch_loop121_teach,
)
from fable_wire51_adapters import HardGate46Sleeper  # noqa: E402 (read-only)

ROOT = SCRIPTS.parent
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"
OUTDIR = ROOT / "artifacts" / "fable-agent138f-20260922"

# ------------------------------------------------------------ ears variants
E_BASE = L138b.Loop138bEars


class EarsNo158(F157.Filler157Mixin, S156B.Smalltalk156bMixin,
                D146B.Doubt146bMixin, S150B.Subject150BMixin,
                I155.InvertedFrame155Mixin, R153.Reverse153Mixin, E_BASE):
    name = "ablate-no158"


class EarsNo157(Q158.Qform158Mixin, S156B.Smalltalk156bMixin,
                D146B.Doubt146bMixin, S150B.Subject150BMixin,
                I155.InvertedFrame155Mixin, R153.Reverse153Mixin, E_BASE):
    name = "ablate-no157"


class EarsNo156b(Q158.Qform158Mixin, F157.Filler157Mixin,
                 D146B.Doubt146bMixin, S150B.Subject150BMixin,
                 I155.InvertedFrame155Mixin, R153.Reverse153Mixin, E_BASE):
    name = "ablate-no156b"


class EarsNo146d(Q158.Qform158Mixin, F157.Filler157Mixin,
                 S156B.Smalltalk156bMixin, S150B.Subject150BMixin,
                 I155.InvertedFrame155Mixin, R153.Reverse153Mixin, E_BASE):
    name = "ablate-no146d"


class EarsNo150b(Q158.Qform158Mixin, F157.Filler157Mixin,
                 S156B.Smalltalk156bMixin, D146B.Doubt146bMixin,
                 I155.InvertedFrame155Mixin, R153.Reverse153Mixin, E_BASE):
    name = "ablate-no150b"


class EarsNo155(Q158.Qform158Mixin, F157.Filler157Mixin,
                S156B.Smalltalk156bMixin, D146B.Doubt146bMixin,
                S150B.Subject150BMixin, R153.Reverse153Mixin, E_BASE):
    name = "ablate-no155"


class EarsNo153(Q158.Qform158Mixin, F157.Filler157Mixin,
                S156B.Smalltalk156bMixin, D146B.Doubt146bMixin,
                S150B.Subject150BMixin, I155.InvertedFrame155Mixin, E_BASE):
    name = "ablate-no153"


# ------------------------------------------------------------ loop variants
L_BASE = L138b.Loop138bAgentLoop


def _init138d(self, state_dir, *, ears=None, mouth=None, reasoner=None,
              sleeper=None, thinker=None,
              sleep_threshold: int = A.SLEEP_THRESHOLD) -> None:
    L138d.Loop138dAgentLoop.__init__(
        self, state_dir, ears=ears, mouth=mouth, reasoner=reasoner,
        sleeper=sleeper, thinker=thinker, sleep_threshold=sleep_threshold)


class LoopNo154(D146B.Doubt146bMixin, S150B.Subject150BMixin, L_BASE):
    __init__ = _init138d
    _save = L138d.Loop138dAgentLoop._save
    turn = L138d.Loop138dAgentLoop.turn


class LoopNo146d(Y154.YesNo154Mixin, S150B.Subject150BMixin, L_BASE):
    __init__ = _init138d
    _save = L138d.Loop138dAgentLoop._save
    turn = L138d.Loop138dAgentLoop.turn


class LoopNo150b(Y154.YesNo154Mixin, D146B.Doubt146bMixin, L_BASE):
    __init__ = _init138d
    _save = L138d.Loop138dAgentLoop._save
    turn = L138d.Loop138dAgentLoop.turn


class LoopNo138c(Y154.YesNo154Mixin, D146B.Doubt146bMixin,
                 S150B.Subject150BMixin, L_BASE):
    __init__ = _init138d
    _save = L138d.Loop138dAgentLoop._save
    turn = L138.Loop138AgentLoop.turn  # 138b verbatim turn (138c off)


class LoopNo154_138c(D146B.Doubt146bMixin, S150B.Subject150BMixin, L_BASE):
    __init__ = _init138d
    _save = L138d.Loop138dAgentLoop._save
    turn = L138.Loop138AgentLoop.turn  # 154 off + 138c off


class LoopNo142(Y154.YesNo154Mixin, D146B.Doubt146bMixin,
                S150B.Subject150BMixin, L_BASE):
    """142 off: base-notebook init inherited (no IndexedLoopNotebook)."""


# ------------------------------------------------------------ reasoner variants
class ReasonerNo159(L148b.ScreenStatusReasoner148b, FastReasoner142):
    """138d reasoner minus the 159 fallback (159 off)."""
    name = "ablate-reasoner-no159"


class ReasonerNo142(L148b.ScreenStatusReasoner148b):
    """Screen logic over the base path + 159 fallback (142 fast path off)."""
    name = "ablate-reasoner-no142"

    def answer(self, question: dict, notebook) -> dict:
        rec = super().answer(question, notebook)
        if not isinstance(question, dict):
            return rec
        if question.get("screen148b") in ("neg", "time"):
            return rec
        try:
            if (isinstance(rec, dict) and rec.get("kind") == "answer"
                    and rec.get("status") != C.OK):
                helper = H159.Hop159Reasoner77()
                rec2 = helper.answer(dict(question), notebook)
                if (isinstance(rec2, dict) and rec2.get("kind") == "answer"
                        and rec2.get("status") == C.OK):
                    return rec2
        except Exception:
            pass
        return rec


# piece -> (ears_cls or None for full, loop_cls or None, reasoner factory, skip142)
FULL_EARS = L138d.Loop138dEars
FULL_LOOP = L138d.Loop138dAgentLoop


def _full_reasoner():
    return L138d.Reasoner138d()


VARIANTS: dict[str, dict] = {
    "full138d": {},
    "off142": {"loop_cls": LoopNo142, "reasoner": ReasonerNo142,
               "skip142": True},
    "off138c": {"loop_cls": LoopNo138c},
    "off146d": {"ears_cls": EarsNo146d, "loop_cls": LoopNo146d},
    "off153": {"ears_cls": EarsNo153},
    "off154": {"loop_cls": LoopNo154},
    "off155": {"ears_cls": EarsNo155},
    "off156b": {"ears_cls": EarsNo156b},
    "off157": {"ears_cls": EarsNo157},
    "off158": {"ears_cls": EarsNo158},
    "off159": {"reasoner": ReasonerNo159},
    "off150b": {"ears_cls": EarsNo150b, "loop_cls": LoopNo150b},
    "off155+138c": {"ears_cls": EarsNo155, "loop_cls": LoopNo138c},
    "off154+138c": {"loop_cls": LoopNo154_138c},
    "off155+154": {"ears_cls": EarsNo155, "loop_cls": LoopNo154},
    "off155+154+138c": {"ears_cls": EarsNo155, "loop_cls": LoopNo154_138c},
}


def build_variant(tag: str, extra: dict):
    spec = VARIANTS[tag]
    cfg = copy.deepcopy(L138d.DEFAULT_CONFIG138D)
    cfg.update(extra)
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    rcls = spec.get("reasoner")
    reasoner = rcls() if rcls is not None else L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    ears_cls = spec.get("ears_cls") or FULL_EARS
    inner_ears = ears_cls(Loop96Ears(chain))
    loop_cls = spec.get("loop_cls") or FULL_LOOP
    loop = loop_cls(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    if not spec.get("skip142"):
        patch_chain142(chain)
        patch_loop121_teach(inner_ears)
    thinker, thinker_module = L90.build_thinker(loop.nb)
    loop.thinker = thinker
    loop.parts90 = {"ears": loop.ears, "mouth": mouth, "reasoner": reasoner,
                    "sleeper": sleeper, "thinker": thinker,
                    "thinker_module": thinker_module,
                    "tau_hat": dict(chain.tau), "tau_family": chain.family,
                    "tau_hat_used": chain.tau_hat,
                    "ears_chain_stages": list(chain.stage_names),
                    "config": cfg}
    loop._screen148b_tag = None
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    store = D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    inner_ears.doubt_store146 = store
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    return loop


def build_fn_for(tag: str):
    def _build(extra: dict):
        return build_variant(tag, extra)
    return _build


def daemon_cls_for(tag: str):
    build = build_fn_for(tag)

    class VariantDaemon(L138d.Loop138dDaemon):
        def __init__(self, root, cfg=None, idle_seconds=30.0,
                     sleep_threshold=None, grace_s=D141.SETTLE_GRACE_S):
            self.cfg = dict(cfg or {})
            if sleep_threshold is not None:
                self.cfg["sleep_threshold"] = sleep_threshold
            self.root = Path(root)
            self.inbox = self.root / "inbox"
            self.outbox = self.root / "outbox"
            self.done = self.root / "done"
            for sub in (self.inbox, self.outbox, self.done):
                sub.mkdir(parents=True, exist_ok=True)
            self.stop_file = self.root / "STOP"
            self.idle_seconds = float(idle_seconds)
            self.heartbeat_path = self.root / "heartbeat.json"
            self.status_path = self.root / "daemon_status.json"
            self.log_path = self.root / "daemon.log.jsonl"
            import os as _os
            import time as _time
            self.pid = _os.getpid()
            self.boot_time = _time.time()
            agent_cfg = dict(self.cfg)
            agent_cfg["state_dir"] = str(self.root)
            self.loop = build(agent_cfg)
            self.torn_found = any("torn notebook tail" in note
                                  for note in self.loop.notes)
            self.reconcile_report = D108.boot_reconcile(self)
            self.settle = D141.SettleGate141(grace_s=grace_s)

    VariantDaemon.__name__ = f"LoopAblate_{tag}_Daemon"
    return VariantDaemon


def load_frozen() -> dict:
    frozen: dict = {}
    rows = [json.loads(l) for l in
            (ART138B / "redteam136-loop138b.json").read_text(
                encoding="utf-8").splitlines() if l.strip()]
    for r in rows:
        frozen[("rt136", r["id"])] = r
    rows = [json.loads(l) for l in
            (ART138B / "probe139b-loop138b.json").read_text(
                encoding="utf-8").splitlines() if l.strip()]
    for r in rows:
        frozen[("c139b", r["id"])] = r
    suite = json.loads((ART138B / "redteam143-loop138b.json").read_text(
        encoding="utf-8"))
    for r in suite["rows"]:
        frozen[("rt143", r["id"])] = r
    return frozen


def load_cases() -> dict:
    cases136 = json.loads(
        (ROOT / "artifacts" / "fable-redteam136-20260922" / "cases136.json")
        .read_text(encoding="utf-8"))
    if isinstance(cases136, dict):
        cases136 = cases136.get("cases", cases136)
    c_by_id = {c["id"]: c for c in cases136}
    c139 = json.loads(
        (ROOT / "artifacts" / "fable-fix139-20260922" / "cases139.json")
        .read_text(encoding="utf-8"))
    if isinstance(c139, dict):
        c139 = c139.get("cases", c139)
    c139b = json.loads(
        (ROOT / "artifacts" / "fable-fix139b-20260922" / "cases139b.json")
        .read_text(encoding="utf-8"))
    p_by_id = {c["id"]: c for c in (list(c139) + list(c139b))}
    suite143 = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    t_by_id = {c["id"]: c for c in suite143["cases"]}
    markers = suite143["abstain_markers"]
    return {"rt136": c_by_id, "c139b": p_by_id, "rt143": t_by_id,
            "markers": markers}


SEVEN = [("rt136", "C124"), ("rt136", "C127"), ("rt136", "C129"),
         ("rt136", "C142"), ("c139b", "C10"), ("c139b", "C21"),
         ("rt143", "M3")]


def run_one(fam: str, cid: str, tag: str, cases: dict, workroot: Path) -> dict:
    if fam == "rt136":
        dest = workroot / tag / cid
        dest.mkdir(parents=True, exist_ok=True)
        R136.new_daemon139b = (  # type: ignore[method-assign]
            lambda root, _tag=tag: daemon_cls_for(_tag)(
                root, cfg={**copy.deepcopy(L138d.DEFAULT_CONFIG138D),
                           "state_dir": str(root),
                           "sleep_threshold": 100000},
                idle_seconds=3600.0))
        return R136.run_case139b(cases["rt136"][cid], workroot / tag / cid)
    if fam == "c139b":
        with tempfile.TemporaryDirectory(prefix=f"ab-{tag}-{cid}-") as tmp:
            cfg = {"state_dir": tmp, "sleep_threshold": 100000}
            row = dict(cases["c139b"][cid])
            return P139b.run_case(row, lambda extra, _t=tag, _c=cfg:  # noqa: E731
                                  build_variant(_t, {**_c, **extra}))
    R143.Loop132Daemon = daemon_cls_for(tag)  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L138d.DEFAULT_CONFIG138D)
    return R143.run_case(cases["rt143"][cid],
                         workroot / "rt143" / tag / cid, cases["markers"])


def main() -> int:
    import os as _os
    only = _os.environ.get("ABLATE_ONLY", "")
    only_tags = set(only.split(",")) if only else set()
    only_cases = set(_os.environ.get("ABLATE_CASES", "").split(",")) \
        if _os.environ.get("ABLATE_CASES") else set()
    tags = [t for t in VARIANTS if not only_tags or t in only_tags]
    sevens = [s for s in SEVEN
              if not only_cases or f"{s[0]}/{s[1]}" in only_cases]
    OUTDIR.mkdir(parents=True, exist_ok=True)
    workroot = OUTDIR / "work-ablate138f"
    workroot.mkdir(parents=True, exist_ok=True)
    frozen = load_frozen()
    cases = load_cases()
    report: dict = {"cases": {}}
    for fam, cid in sevens:
        frow = frozen[(fam, cid)]
        entry: dict = {"frozen138b": {
            "verdict": frow["verdict"],
            "reply": str(frow.get("reply", ""))[:200],
            "stored": frow.get("stored", "n/a")}, "variants": {}}
        print(f"--- {fam}/{cid} (138b: {frow['verdict']})", flush=True)
        for tag in tags:
            try:
                rec = run_one(fam, cid, tag, cases, workroot)
            except Exception as exc:  # noqa: BLE001
                entry["variants"][tag] = {"error": repr(exc)[:160]}
                print(f"  {tag}: ERROR {exc!r}"[:160], flush=True)
                continue
            same_v = (rec.get("verdict") == frow.get("verdict"))
            same_r = (str(rec.get("reply", "")).strip()
                      == str(frow.get("reply", "")).strip())
            same_s = ("stored" not in rec and "stored" not in frow) or (
                rec.get("stored") == frow.get("stored"))
            entry["variants"][tag] = {
                "verdict": rec.get("verdict"),
                "reply": str(rec.get("reply", ""))[:200],
                "stored": rec.get("stored", "n/a"),
                "match138b": bool(same_v and same_r and same_s)}
            print(f"  {tag}: {rec.get('verdict')} "
                  f"match138b={same_v and same_r and same_s} "
                  f"reply={str(rec.get('reply', ''))[:100]!r}", flush=True)
        report["cases"][f"{fam}/{cid}"] = entry
    table = {}
    for key, entry in report["cases"].items():
        table[key] = sorted(
            t for t, v in entry["variants"].items() if v.get("match138b"))
    report["attribution"] = table
    (OUTDIR / "attribution-138f.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print("ATTRIBUTION (variants identical to loop138b):", flush=True)
    for key, tags in table.items():
        print(f"  {key} -> {tags}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
