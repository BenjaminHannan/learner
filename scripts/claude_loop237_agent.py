#!/usr/bin/env python3
"""Exp 237 -- relation table v1.1 on loop221 (questions only).

loop237 = loop221 + ONE change: the question stage reads
artifacts/claude-table237-20260922/relation_table_v1_1.json (v1 plus
additions: true-synonym aliases, new everyday relation rows, date
relations; built by scripts/claude_table237_build.py) instead of v1.

Small reader changes that the new rows need, all question-side:
  * templates with no {X} that say I / me / am I (e.g. "Where do I work?")
    read as the user's own slot (221 only accepted templates with "my");
  * a row may list "broader" relations (wife -> spouse, husband -> spouse).
    When the asked key and its own group are empty, the broader row's own
    keys are read too. Replies always use the STORED word, so nothing is
    renamed; wife and husband are never linked to each other.
Everything else is 221 verbatim: exact stored word first; different
values under different words are all listed with their own words and
never merged; inverse answers labelled "(worked out backwards)", never
stored; only ask / clarify actions, so questions never write and
teaches / statements take exactly the 221 path.

The 228 guard is installed at import and by the daemon (SrcGuardMixin228
first in the bases). No existing file is edited.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from claude_fix228_srcguard import (  # noqa: E402 (REQUIRED 228 guard)
    SrcGuardMixin228, install_srcguard228)

install_srcguard228()

import fable_agent_loop as A  # noqa: E402 (read-only)
import fable_daemon108_run as D108  # noqa: E402 (read-only)
import fable_daemon141_settle as D141  # noqa: E402 (read-only)
import fable_doubt146b_store as D146B  # noqa: E402 (read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (read-only)
import fable_loop221_agent as L221  # noqa: E402 (base; applies 138i overrides)
import fable_fix221_tableask as T221  # noqa: E402 (read-only)
import fable_fix167e_label as L167E  # noqa: E402 (read-only)
from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only)
from fable_perf142_index import patch_chain142, patch_loop121_teach  # noqa: E402
from fable_wire51_adapters import HardGate46Sleeper  # noqa: E402

ROOT = SCRIPTS.parent
TABLE_PATH237 = (ROOT / "artifacts" / "claude-table237-20260922"
                 / "relation_table_v1_1.json")
_USER_TMPL = re.compile(r"\b(my|i|me)\b", re.IGNORECASE)


def table_readings237(turn: str, table) -> list[dict]:
    """table_readings221 with one change: an X-less ask template that says
    my / I / me reads the user's slot."""
    t = " ".join(str(turn).split())
    if not t.endswith("?"):
        return []
    if set(re.findall(r"[a-z]+", t.lower())) & T221._SELF_WORDS:
        return []
    body = t.rstrip(" .?!")
    out: list[dict] = []
    seen = set()
    for rel, kind, rx, tmpl in table.patterns:
        m = rx.fullmatch(body)
        if not m:
            continue
        g = {k: v.strip() for k, v in m.groupdict().items() if v}
        r = table.rels[rel]
        if kind == "ask":
            if "X" not in g:
                if _USER_TMPL.search(tmpl):
                    g["X"] = T221.USER_KEY221
                else:
                    continue
            elif not T221._slot_ok(g["X"]):
                continue
        else:
            if "Y" not in g or not T221._slot_ok(g["Y"]):
                continue
            if r.get("date_rule"):
                for w in r["date_rule"]["strip_leading"]:
                    if g["Y"].lower().startswith(w + " "):
                        g["Y"] = g["Y"][len(w) + 1:]
            if not T221._guard_ok(r, g["Y"]):
                continue
        sig = (rel, kind, T221._norm(g.get("X", "")),
               T221._norm(g.get("Y", "")))
        if sig in seen:
            continue
        seen.add(sig)
        out.append({"rel": rel, "kind": kind, "X": g.get("X"),
                    "Y": g.get("Y"), "template": tmpl})
    return out


def unique_reading237(turn: str, table):
    rd = table_readings237(turn, table)
    return rd[0] if len(rd) == 1 else None


def group_keys237(table, rel: str) -> list[str]:
    """Own keys + narrower keys (221) + broader rows' OWN keys (237)."""
    out = list(table.forward_keys(rel))
    for b in table.rels[rel].get("broader", []):
        if b in table.rels:
            for k in table.forward_keys(b, narrower=False):
                if k not in out:
                    out.append(k)
    return out


def choose_key237(nb, name: str, key: str, table):
    """choose_key221 with group_keys237 as the candidate list."""
    k = T221.key221(key)
    rel = table.key2rel.get(k)
    via_inverse_key = False
    if rel is None:
        rel = table.invkey2rel.get(k)
        via_inverse_key = rel is not None
    if rel is None or nb is None:
        return None
    eid = T221._resolve(nb, name)
    if eid is None:
        return None
    if not via_inverse_key and T221._values(nb, eid, k):
        return None  # exact stored word first: taught facts win
    hits = []
    for cand in group_keys237(table, rel):
        if cand == k:
            continue
        vals = T221._values(nb, eid, cand)
        if vals:
            hits.append((cand, vals))
    if not hits:
        return None
    sets = {tuple(sorted(T221._norm(v) for v in vals)) for _c, vals in hits}
    if len(sets) == 1:
        return ("swap", hits[0][0])
    who = T221._who(nb, eid)
    lines = [f"{who} {T221.disp221(c)} is {', '.join(vals)}."
             for c, vals in hits]
    if table.rels[rel].get("cardinality") == "multi":
        return ("text", " ".join(lines))
    return ("text", " ".join(lines) + " These disagree, so I will not "
            "pick one. Which is right?")


class TableAsk237Mixin(T221.TableAsk221Mixin):
    """TableAsk221Mixin reading table v1.1 (reader changes above)."""

    def _rekey221(self, act: dict, nb, table) -> dict:
        rels = act.get("relations") or []
        if len(rels) != 1 or not act.get("name") or act.get("entity_id"):
            return act
        choice = choose_key237(nb, str(act["name"]), str(rels[0]), table)
        if choice is None:
            return act
        if choice[0] == "swap":
            new = dict(act)
            new["relations"] = [choice[1]]
            new["table221"] = f"{rels[0]}->{choice[1]}"
            return new
        return {"act": "clarify", "text": choice[1], "table221": "list"}

    def hear(self, turn: str) -> list[dict]:
        # 221's hear body, with unique_reading237 for the base-miss case.
        actions = super(T221.TableAsk221Mixin, self).hear(turn)
        t = " ".join(str(turn).split())
        if not t.endswith("?") or not isinstance(actions, list):
            return actions
        nb = getattr(self, "nb", None)
        if nb is None:
            return actions
        table = self._table221()
        if T221.base_missed221(actions):
            rd = unique_reading237(t, table)
            if rd is None:
                return actions
            if rd["kind"] == "inverse":
                self._mark221("inverse")
                return [{"act": "clarify", "table221": "inverse",
                         "text": T221.inverse_answer221(
                             nb, rd["rel"], rd["Y"], table)}]
            act = {"act": "ask", "name": rd["X"],
                   "relations": [T221.key221(rd["rel"])],
                   "stage": T221.STAGE221}
            if rd["X"] == T221.USER_KEY221:
                act["me166"] = True
            self._mark221("ask")
            return [self._rekey221(act, nb, table)]
        rev = self._reverse153_221(t, actions, nb, table)
        if rev is not None:
            return rev
        out, changed = [], False
        for a in actions:
            if isinstance(a, dict) and a.get("act") == "ask":
                b = self._rekey221(a, nb, table)
                if b is not a:
                    changed = True
                out.append(b)
            else:
                out.append(a)
        if changed:
            self._mark221("rekey")
            return out
        return actions


class Loop237Ears(TableAsk237Mixin, L138I.Loop138iEars):
    name = "loop237-table11"


class Loop237AgentLoop(L221.Loop221AgentLoop):
    """Unchanged (renamed for logs)."""


DEFAULT_CONFIG237: dict = copy.deepcopy(L221.DEFAULT_CONFIG221)
DEFAULT_CONFIG237["ears"]["stand_in"] = (
    L221.DEFAULT_CONFIG221["ears"]["stand_in"].replace(
        "relation table v1, read-only",
        "relation table v1.1 (237), read-only"))
DEFAULT_CONFIG237["daemon"]["module"] = "Loop237Daemon (scripts/claude_loop237_agent.py)"
DEFAULT_CONFIG237["table221_path"] = str(TABLE_PATH237)


def build_agent237(cfg: dict | None = None) -> Loop237AgentLoop:
    """build_agent221 with Loop237Ears (and table v1.1 by default)."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    install_srcguard228()
    cfg = dict(DEFAULT_CONFIG237, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L167E.Label167eMouth(L138b.Loop138bMouth())
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    inner_ears = Loop237Ears(Loop96Ears(chain))
    inner_ears.table221_path = cfg.get("table221_path") or str(TABLE_PATH237)
    loop = Loop237AgentLoop(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
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
    loop._dc166c = {}
    L138I._wrap_relation154e(loop)
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep138i: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop237: loop221 with relation table v1.1 "
                      "(questions only; writes untouched; 228 guard)")
    return loop


class Loop237Daemon(SrcGuardMixin228, L221.Loop221Daemon):
    """Loop221Daemon shape with the 237 agent inside; 228 guard first."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = D141.SETTLE_GRACE_S) -> None:
        install_srcguard228()
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
        self.pid = _os.getpid()
        self.boot_time = time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent237(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 237 table v1.1 on loop221")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG237)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print("Wrote %s" % args.write_config)
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG237)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.dir:
        return Loop237Daemon(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds).run()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
