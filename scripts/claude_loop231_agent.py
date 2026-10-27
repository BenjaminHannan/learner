#!/usr/bin/env python3
"""Experiment 231 -- POSSESSIVE CHAINS INSIDE TABLE QUESTIONS, on loop221.

loop231 = loop221 (scripts/fable_loop221_agent.py) + ONE change:
Chain231Mixin sits OUTERMOST on the 221 ears (outside TableAsk221Mixin).

It acts only on turns ending in "?", and only when the full 221 stack
did not understand the turn (fable_fix221_tableask.base_missed221), or
when the 221 stack produced a single one-key ask on a relation key that no
notebook fact has ever used (e.g. "Who is Kim's boss married to?" ->
key "boss_married_to"). Every other turn -- every single-hop question and
every chain the base already answers -- keeps the 221 actions untouched.

What it does:
 1. Reads the turn through the SAME relation-table templates as 221 (ask +
    yes/no rows; relation_table_v1.json, read-only), but lets the subject
    slot {X} hold a possessive chain:
      "Kim's boss", "Kim's boss's sister", "the boss of Kim",
      "the sister of Kim's boss", "my boss", "my boss's sister".
    Exactly one distinct reading (over all templates, chains and plain
    subjects together) is required, and it must have >= 1 hop; otherwise
    the 221 reply stays byte-identical.
 2. Resolves the chain hop by hop through the notebook (READ-ONLY):
    taught, active rows only (source == "taught"; retracted / superseded /
    inferred / sleep rows never used). Each hop must have exactly one
    distinct current value (a key with no rows may fall back to its table
    group keys, only if they all agree -- the 221 rule), and that value must
    resolve to exactly one known entity. Otherwise: an honest abstain that
    says how far the chain got.
 3. Reads the template's relation for the resolved entity (canonical key,
    then the table group; single-valued relations need exactly one value).
 4. Replies in plain words, e.g.
      "Kim's boss is Lee, and Lee lives in Oslo."
      "Yes. Kim's boss is Lee, and Lee lives in Oslo."
    The reply is a clarify action (text only). No teach / correct / forget
    action is ever emitted, so no write path is reachable.

Chain-only input tidy (declared deviation): a leading filler word
("so", "and", "ok", "okay", "hey", "um", "well", "oh") and a trailing
" again" / " now" / ", then" are stripped before the chain reading only.
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

import fable_agent_loop as A  # noqa: E402 (read-only)
import fable_daemon108_run as D108  # noqa: E402 (read-only)
import fable_daemon141_settle as D141  # noqa: E402 (read-only)
import fable_fix221_tableask as T221  # noqa: E402 (read-only)
import fable_loop221_agent as L221  # noqa: E402 (wrapped base, read-only)

STAGE231 = "loop231-chain"
MAX_HOPS231 = 4

_FILLER_LEAD = re.compile(r"^(?:so|and|ok|okay|hey|um|well|oh)\b,?\s+", re.I)
_FILLER_TAIL = re.compile(r"(?:\s+again|\s+now|,\s*then)\s*\?$", re.I)
_HOP_BAD = (T221._BAD_START | T221._BAD_INNER | T221._BAD_END
            | T221._SELF_WORDS | {"and", "or", "not", "no"})
_HOP_WORD = re.compile(r"^[a-z][a-z-]*$")


def _tidy231(turn: str) -> str:
    t = " ".join(str(turn).replace("’", "'").split())
    t = _FILLER_LEAD.sub("", t, count=1)
    t = _FILLER_TAIL.sub("?", t)
    if t and t[0].islower():
        t = t[0].upper() + t[1:]
    return t


# ------------------------------------------------------------ chain parse
def _hop_ok(h: str) -> bool:
    """A hop word: 1-3 plain lowercase words, or a table relation surface
    (which may contain "of", e.g. "country of citizenship")."""
    ws = h.split()
    if 1 <= len(ws) <= 3 and all(_HOP_WORD.match(w) and w not in _HOP_BAD
                                 for w in ws):
        return True
    return (1 <= len(ws) <= 5 and all(_HOP_WORD.match(w) for w in ws)
            and T221.key221(h) in T221.get_table221().key2rel)


_ROOT_TAIL_BAD = frozenset({"as", "in", "at", "on", "for", "by", "from",
                            "since", "before", "after", "during", "now",
                            "today", "currently", "then"})


def _root_ok(r: str, of_rest: bool = False) -> bool:
    """A chain root: 221's slot gate, no relation phrase ("citizenship of
    Bram Kite"), no trailing qualifier ("Cora Lind as of 2020"); an of-form
    root ("the boss of Kim") must start with a capital letter."""
    if not T221._slot_ok(r):
        return False
    ws = r.split()
    if " of " in f" {r} " and ws[0].islower():
        return False
    if any(w.lower() in _ROOT_TAIL_BAD for w in ws[1:]):
        return False
    return not (of_rest and not ws[0][:1].isupper())


def parse_chain231(x: str):
    """Subject-slot text -> (root, [hop keys]) or None.

    root is a plain name that passes 221's slot gate, or T221.USER_KEY221
    for "my". Hop keys use the FakeEars key rule (T221.key221).
    of-form: every " of " split is tried; a split whose relation is a table
    key wins (longest first); otherwise exactly one split must parse.
    """
    x = " ".join(str(x).replace("\u2019", "'").split()).strip()
    if not x:
        return None
    low = x.lower()
    # of-form: "the R of REST" (lowercase "the" only; titles like
    # "The Lord of Rings" are never read as chains)
    if x.startswith("the ") and " of " in x:
        cands = []
        for m in re.finditer(r" of ", x):
            rel = x[4:m.start()].strip().lower()
            rest = x[m.end():].strip()
            if not rel or not _hop_ok(rel):
                continue
            sub = parse_chain231(rest)
            if sub is None:
                if not _root_ok(rest, of_rest=True):
                    continue
                sub = (rest, [])
            cands.append((rel, (sub[0], sub[1] + [T221.key221(rel)])))
        known = [c for c in cands
                 if T221.key221(c[0]) in T221.get_table221().key2rel]
        if known:
            return max(known, key=lambda c: len(c[0]))[1]
        return cands[0][1] if len(cands) == 1 else None
    if low.startswith("my "):
        root = T221.USER_KEY221
        hops = x[3:].split("'s ")
    else:
        parts = x.split("'s ")
        if len(parts) < 2:
            return None
        root = parts[0]
        if not _root_ok(root):
            return None
        hops = parts[1:]
    hops = [h.strip().lower() for h in hops]
    if not hops or not all(_hop_ok(h) for h in hops):
        return None
    return (root, [T221.key221(h) for h in hops])


def chain_readings231(turn: str, table=None) -> list[dict]:
    """Every distinct question reading of the (tidied) turn over the 221
    ask + yes/no templates, allowing a chain in {X}. Pure text function."""
    table = table or T221.get_table221()
    t = _tidy231(turn)
    if not t.endswith("?"):
        return []
    if set(re.findall(r"[a-z]+", t.lower())) & T221._SELF_WORDS:
        return []
    body = t.rstrip(" .?!")
    out, seen = [], set()
    for rel, kind, rx, tmpl in _patterns231(table):
        m = rx.fullmatch(body)
        if not m:
            continue
        g = {k: v.strip() for k, v in m.groupdict().items() if v}
        if "X" not in g:
            continue  # "my R" templates: plain one-hop, 221's domain
        if kind == "yesno":
            if "Y" not in g or not T221._slot_ok(g["Y"]):
                continue
        ch = parse_chain231(g["X"])
        if ch is None:
            if _root_ok(g["X"]):
                ch = (g["X"], [])  # a plain subject reading still counts
            else:
                continue
        root, hops = ch
        if len(hops) > MAX_HOPS231:
            continue
        sig = (rel, kind, T221._norm(root), tuple(hops),
               T221._norm(g.get("Y", "")))
        if sig in seen:
            continue
        seen.add(sig)
        out.append({"rel": rel, "kind": kind, "root": root, "hops": hops,
                    "Y": g.get("Y"), "template": tmpl})
    return out


_PAT_CACHE: dict[int, list] = {}


def _patterns231(table) -> list:
    """221's compiled ask patterns + the table's yes/no rows, compiled the
    same way (221 skipped yes/no)."""
    key = id(table)
    if key in _PAT_CACHE:
        return _PAT_CACHE[key]
    pats = [(r, k, rx, t) for (r, k, rx, t) in table.patterns if k == "ask"]
    data = json.loads(table.path.read_text(encoding="utf-8"))
    gen = data["generic_patterns"]
    seen = set()
    for r in data["relations"]:
        rows = []
        for fam in r["generic"]:
            rows += list(gen[fam].get("yesno", []))
        rows += list(r.get("yesno", []))
        surfaces = [r["name"].replace("_", " ")] + list(r["aliases"])
        for p in rows:
            t = p["t"]
            for s in (surfaces if "{R}" in t else [None]):
                c = t if s is None else t.replace("{R}", s)
                if "{X}" not in c or "{Y}" not in c:
                    continue
                if (r["name"], c) in seen:
                    continue
                seen.add((r["name"], c))
                pats.append((r["name"], "yesno",
                             T221.compile_template221(c), c))
    _PAT_CACHE[key] = pats
    return pats


def unique_chain231(turn: str, table=None):
    rd = chain_readings231(turn, table)
    if len(rd) != 1 or not rd[0]["hops"]:
        return None
    return rd[0]


# ------------------------------------------------------- notebook reads
def _taught_rows(nb, eid: str, key: str) -> list[dict]:
    try:
        rows = nb.current(eid, key)
    except Exception:  # noqa: BLE001
        return []
    return [r for r in rows if r.get("source") == "taught"]


def _vals(nb, rows) -> list[tuple[str, object]]:
    out = []
    for r in rows:
        v = r.get("value") or {}
        out.append((nb._show(v), v.get("entity")))
    return out


def _read_key231(nb, eid: str, key: str, table):
    """(used_key, [(display, entity_id|None)], status). status: "ok",
    "none", "conflict". Taught rows only; group fallback like 221."""
    k = T221.key221(key)
    rows = _taught_rows(nb, eid, k)
    if rows:
        return k, _vals(nb, rows), "ok"
    rel = table.key2rel.get(k)
    if rel is None:
        return k, [], "none"
    hits = []
    for cand in table.forward_keys(rel):
        if cand == k:
            continue
        rows = _taught_rows(nb, eid, cand)
        if rows:
            hits.append((cand, _vals(nb, rows)))
    if not hits:
        return k, [], "none"
    sets = {tuple(sorted(T221._norm(d) for d, _e in vs)) for _c, vs in hits}
    if len(sets) != 1:
        return k, [], "conflict"
    return hits[0][0], hits[0][1], "ok"


def _name(nb, eid: str) -> str:
    return nb.entities.get(eid, eid)


def _poss(nb, eid: str, cap: bool = True) -> str:
    n = _name(nb, eid)
    if n == T221.USER_KEY221:
        return "Your" if cap else "your"
    return f"{n}'s"


def _plain231(table, rel: str, subj: str, key: str, vals: list[str],
              user: bool) -> str:
    """Final sentence in plain words (the relation's first live teach
    template of the form "{X} <words> {Y}.", else "X's key is V")."""
    v = ", ".join(vals)
    r = table.rels.get(rel, {})
    if (not user and key in table.forward_keys(rel, narrower=False)
            and len(vals) == 1):
        for p in r.get("teach", []):
            m = re.fullmatch(r"\{X\} ([a-z][a-z ]*[a-z]) \{Y\}\.", p["t"])
            if p.get("where") == "live" and m:
                return f"{subj} {m.group(1)} {v}"
    who = "your" if user else f"{subj}'s"
    return f"{who} {T221.disp221(key)} is {v}"


def _join(parts: list[str]) -> str:
    parts = [p[0].upper() + p[1:] if i == 0 else p
             for i, p in enumerate(parts)]
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]}, and {parts[1]}"
    return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def answer_chain231(nb, rd: dict, table=None) -> tuple[str, str]:
    """(reply text, outcome) for one chain reading. Read-only.

    outcome: "answer", "yes", "no", or "abstain-<why>"."""
    table = table or T221.get_table221()
    root = rd["root"]
    found = nb.resolve(root)
    status = getattr(found, "status", None)
    if status != "OK":
        if root == T221.USER_KEY221:
            return ("I don't know that: you haven't told me about your "
                    f"{T221.disp221(rd['hops'][0])}.", "abstain-root")
        if status == "AMBIGUOUS":
            return (f"I know more than one {root}, so I don't know which "
                    "one you mean.", "abstain-root")
        return (f"I don't know anyone called {root}.", "abstain-root")
    eid = found.detail["entity_id"]
    said: list[str] = []
    for hop in rd["hops"]:
        subj = _poss(nb, eid)
        used, vals, st = _read_key231(nb, eid, hop, table)
        low = _poss(nb, eid, cap=False)
        if st == "conflict" or len({T221._norm(d) for d, _e in vals}) > 1:
            head = (_join(said) + ", but I") if said else "I"
            return (f"{head} don't know which one you mean: my notes have "
                    f"more than one {T221.disp221(hop)} for "
                    f"{'you' if low == 'your' else _name(nb, eid)}.",
                    "abstain-multi")
        if not vals:
            head = (_join(said) + ", but I") if said else "I"
            return (f"{head} don't know {low} {T221.disp221(hop)}.",
                    "abstain-gap")
        disp, nxt = vals[0]
        said.append(f"{subj} {T221.disp221(used)} is {disp}")
        if nxt is None:
            f2 = nb.resolve(disp)
            if getattr(f2, "status", None) != "OK":
                return (_join(said) + ", but I don't know which "
                        f"{disp} that is.", "abstain-entity")
            nxt = f2.detail["entity_id"]
        eid = nxt
    # final relation read
    rel = rd["rel"]
    subj = _name(nb, eid)
    user = subj == T221.USER_KEY221
    used, vals, st = _read_key231(nb, eid, T221.key221(rel), table)
    disps = [d for d, _e in vals]
    uniq = []
    for d in disps:
        if T221._norm(d) not in {T221._norm(u) for u in uniq}:
            uniq.append(d)
    single = table.rels.get(rel, {}).get("cardinality") != "multi"
    if st == "conflict" or (single and len(uniq) > 1):
        return (_join(said) + ", but my notes disagree about "
                f"{_poss(nb, eid, cap=False)} {T221.disp221(rel)}, so I "
                "don't know which is right.", "abstain-multi")
    if not uniq:
        text = (_join(said) + f", but I don't know "
                f"{_poss(nb, eid, cap=False)} {T221.disp221(rel)}.")
        if rd["kind"] == "yesno":
            return ("I don't know. " + text, "abstain-gap")
        return (text, "abstain-gap")
    final = _plain231(table, rel, subj, used, uniq, user)
    text = _join(said + [final]) + "."
    if rd["kind"] == "yesno":
        want = T221._norm(rd["Y"] or "")
        if want in {T221._norm(u) for u in uniq}:
            return ("Yes. " + text, "yes")
        if single and table.rels.get(rel, {}).get("yesno_can_say_no", True):
            return ("No. " + text, "no")
        return ("I don't know. " + text, "abstain-open")
    return (text, "answer")


# ------------------------------------------------------------------ mixin
def _bogus_ask231(actions, nb) -> bool:
    """A single one-key ask on a key no notebook fact has ever used."""
    if not isinstance(actions, list) or len(actions) != 1:
        return False
    a = actions[0]
    if not isinstance(a, dict) or a.get("act") != "ask":
        return False
    rels = a.get("relations") or []
    if len(rels) != 1:
        return False
    k = str(rels[0])
    try:
        return not any(f.get("relation") == k for f in nb.facts.values())
    except Exception:  # noqa: BLE001
        return False


class Chain231Mixin:
    """Outermost ears stage: possessive chains in table-question subjects."""

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        t = " ".join(str(turn).split())
        if not t.endswith("?") or not isinstance(actions, list):
            return actions
        nb = getattr(self, "nb", None)
        if nb is None:
            return actions
        if not (T221.base_missed221(actions) or _bogus_ask231(actions, nb)):
            return actions
        table = self._table221()  # type: ignore[attr-defined]
        rd = unique_chain231(t, table)
        if rd is None:
            return actions
        text, outcome = answer_chain231(nb, rd, table)
        try:
            self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                f"{STAGE231}-{outcome}", 1.0)
        except AttributeError:
            pass
        return [{"act": "clarify", "text": text, "chain231": outcome,
                 "stage": STAGE231}]


class Loop231Ears(Chain231Mixin, L221.Loop221Ears):
    name = "loop231-chain"


class Loop231AgentLoop(L221.Loop221AgentLoop):
    """Unchanged (renamed for logs)."""


DEFAULT_CONFIG231: dict = copy.deepcopy(L221.DEFAULT_CONFIG221)
DEFAULT_CONFIG231["ears"]["stand_in"] = (
    L221.DEFAULT_CONFIG221["ears"]["stand_in"]
    + "; 231 possessive chains in table-question subjects outermost "
      "(read-only, taught facts only)")
DEFAULT_CONFIG231["daemon"]["module"] = "Loop231Daemon (this file)"


def build_agent231(cfg: dict | None = None) -> Loop231AgentLoop:
    """build_agent221 with the ears class swapped for Loop231Ears."""
    orig_ears, orig_loop = L221.Loop221Ears, L221.Loop221AgentLoop
    L221.Loop221Ears, L221.Loop221AgentLoop = Loop231Ears, Loop231AgentLoop
    try:
        loop = L221.build_agent221(dict(DEFAULT_CONFIG231, **(cfg or {})))
    finally:
        L221.Loop221Ears, L221.Loop221AgentLoop = orig_ears, orig_loop
    loop.notes.append("loop231: loop221 + Chain231Mixin outermost "
                      "(chains in table-question subjects; read-only)")
    return loop


class Loop231Daemon(L221.Loop221Daemon):
    """Loop221Daemon shape with the 231 agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = D141.SETTLE_GRACE_S) -> None:
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
        self.loop = build_agent231(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon231(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    return Loop231Daemon(root, cfg=cfg, idle_seconds=idle_seconds).run()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 231 chains on loop221")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        import fable_loop90_agent as L90  # noqa: E402
        out = copy.deepcopy(DEFAULT_CONFIG231)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print("Wrote %s" % args.write_config)
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG231)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return run_daemon231(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent231(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
