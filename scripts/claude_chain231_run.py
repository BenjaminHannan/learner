#!/usr/bin/env python3
"""Exp 231 runner + the ONE sealed scorer (dev set and blind chain panel).

Run one arm over an items file (one fresh agent per item: setup turns,
then the question):
  python -B scripts/claude_chain231_run.py run --arm 231 --items F --out DIR
Score arms together (writes scores.json + cases.md):
  python -B scripts/claude_chain231_run.py score --out DIR --items F \\
      --arms 138i,221,231

Arms: 138i = scripts/fable_loop138i_agent.py + its sealed config;
221 = scripts/fable_loop221_agent.py + loop221-config.json;
231 = scripts/claude_loop231_agent.py + loop231-config.json.
sleep_threshold is set to 100000 in every arm (no sleep during items).

SCORING RULES (fixed before any panel is opened):
 * abstain-type reply: matches ABSTAIN_RE (honest "I don't know"-type
   wording, the not-understood clarify, or a "which is right?" ask).
 * stored graph: the arm's own taught triples after setup (before the
   question). Nodes are normalized names; edges subject -> value.
 * question entities: stored subject names found (whole word) in the
   question, plus USER when the question has "my"/"I"/"me".
 * allowed values: gold parts + every node on a stored path from a
   question entity to a gold value + names found in the question.
 * ANSWER item: RIGHT iff every gold part (split on ";") is in the reply
   (whole word, case-insensitive), the reply is not abstain-type, and the
   reply contains no stored value outside the allowed set. WRONG iff the
   reply is not abstain-type and contains a stored value outside the
   allowed set. ABSTAIN iff abstain-type. Else OTHER.
 * YES/NO item (expect yes or no): RIGHT iff the reply starts with the
   expected word ("yes"/"no", case-insensitive, first word). WRONG iff it
   starts with the opposite word. ABSTAIN iff abstain-type. Else OTHER.
 * ABSTAIN item: RIGHT iff abstain-type. WRONG iff not abstain-type and
   the reply contains a stored value not named in the question. Else
   OTHER.
 * write: the notebook fact hash (facts + retracted + superseded)
   differs before vs after the question turn.
 * ANSWERABLE (added after the coordinator's 232 note, before any seal):
   an item is answerable iff, on the 221 arm, every setup turn "landed":
   the fact hash changed on that turn, OR the turn is a bare yes/no reply
   ("Yes."/"No."/"Yes"/"No") following a turn that did not land, and that
   yes/no turn itself changed the hash (confirm-to-change flow). Items
   not answerable are BLOCKED (a base teach did not save) and are reported
   separately; right-answer bars use the answerable subset only.
Only load_items() may be adapted to the panel's field names after the
panel is opened (declared as a deviation); these rules may not.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

CONFIGS = {
    "138i": ("fable_loop138i_agent", "build_agent138i", "DEFAULT_CONFIG138I",
             ROOT / "artifacts/fable-agent138i-20260922/loop138i-config.json"),
    "221": ("fable_loop221_agent", "build_agent221", "DEFAULT_CONFIG221",
            ROOT / "artifacts/claude-tableask221-20260922/loop221-config.json"),
    "231": ("claude_loop231_agent", "build_agent231", "DEFAULT_CONFIG231",
            ROOT / "artifacts/claude-chain231-20260922/loop231-config.json"),
}

ABSTAIN_RE = re.compile(
    r"(\bi don'?t know\b|\bi do not know\b|\bi don't have\b|"
    r"\bi have no record\b|\bno record of\b|\bnot sure\b|\bcan'?t tell\b|"
    r"\bcannot tell\b|\bi didn'?t understand\b|\bwhich is right\b|"
    r"\bwhich one you mean\b|\bi can'?t say\b|\bnot that i know\b)", re.I)


# ------------------------------------------------------------- items
def _as_list(v) -> list:
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v if str(x).strip()]
    return [str(v)] if str(v).strip() else []


def load_items(path: Path) -> list[dict]:
    """Field map (the only part that may be adapted after opening)."""
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        exp = str(d.get("expect", "answer")).strip().lower()
        gold = []
        for g in _as_list(d.get("gold")):
            gold += [p.strip() for p in g.split(";") if p.strip()]
        if exp in ("yes", "no"):
            kind = exp
        elif gold and gold[0].lower() in ("yes", "no") and len(gold) == 1 \
                and exp not in ("abstain",):
            kind = gold[0].lower()
        elif exp.startswith("abstain") or not gold:
            kind = "abstain"
        else:
            kind = "answer"
        out.append({"id": d["id"], "family": d.get("family", ""),
                    "setup": _as_list(d.get("setup")),
                    "question": str(d["question"]),
                    "kind": kind, "gold": gold if kind == "answer" else [],
                    "raw": d})
    return out


# --------------------------------------------------------------- running
def facts_hash(nb) -> str:
    blob = json.dumps({"facts": nb.facts,
                       "retracted": sorted(getattr(nb, "retracted", [])),
                       "superseded": sorted(getattr(nb, "superseded", []))},
                      sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def build(arm: str, tmp: Path):
    import importlib
    mod_name, fn, dflt, cfg_path = CONFIGS[arm]
    mod = importlib.import_module(mod_name)
    cfg = copy.deepcopy(getattr(mod, dflt))
    cfg.update(json.loads(Path(cfg_path).read_text(encoding="utf-8")))
    cfg["state_dir"] = str(tmp)
    cfg["sleep_threshold"] = 100000
    return getattr(mod, fn)(cfg)


def run_arm(arm: str, items: list[dict], out: Path) -> None:
    import fable_loop90_agent as L90
    out.mkdir(parents=True, exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix=f"c231-{arm}-"))
    rows = []
    for n, it in enumerate(items):
        d = base / f"i{n:03d}"
        d.mkdir()
        loop = build(arm, d)
        setup_replies, setup_wrote = [], []
        for t in it["setup"]:
            ha = facts_hash(loop.nb)
            setup_replies.append(" ".join(loop.turn(t)))
            setup_wrote.append(facts_hash(loop.nb) != ha)
        stored = [list(x) for x in L90.notebook_triples(loop.nb)]
        h0 = facts_hash(loop.nb)
        t0 = time.perf_counter()
        reply = " ".join(loop.turn(it["question"]))
        ms = (time.perf_counter() - t0) * 1000.0
        h1 = facts_hash(loop.nb)
        rows.append({"id": it["id"], "question": it["question"],
                     "reply": reply, "ms": round(ms, 2), "wrote": h0 != h1,
                     "stage": str(getattr(loop.ears, "last_stage", "")),
                     "stored": stored, "setup_replies": setup_replies,
                     "setup_wrote": setup_wrote})
        print(f"[{arm}] {it['id']} {reply[:110]!r}", flush=True)
    (out / f"rows-{arm}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8")
    shutil.rmtree(base, ignore_errors=True)


# --------------------------------------------------------------- scoring
def _n(s: str) -> str:
    return " ".join(str(s).lower().replace("’", "'").split()).strip(
        " .!?")


def _has(text: str, val: str) -> bool:
    v = _n(val)
    if not v:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])",
                     _n(text)) is not None


def score_one(it: dict, row: dict) -> str:
    reply = row["reply"]
    abst = ABSTAIN_RE.search(reply) is not None
    q = it["question"]
    stored = row["stored"]
    values = {_n(v) for _s, _r, v in stored}
    if it["kind"] in ("yes", "no"):
        first = re.findall(r"[a-z]+", reply.lower())[:1]
        if first == [it["kind"]]:
            return "RIGHT"
        if first == ["no" if it["kind"] == "yes" else "yes"]:
            return "WRONG"
        return "ABSTAIN" if abst else "OTHER"
    in_q = {v for v in values if _has(q, v)}
    if it["kind"] == "abstain":
        if abst:
            return "RIGHT"
        if any(_has(reply, v) for v in values - in_q):
            return "WRONG"
        return "OTHER"
    # answer item: allowed = gold + path nodes + names in question
    edges: dict[str, set] = {}
    redges: dict[str, set] = {}
    for s, _r, v in stored:
        edges.setdefault(_n(s), set()).add(_n(v))
        redges.setdefault(_n(v), set()).add(_n(s))
    srcs = {_n(s) for s, _r, _v in stored if _has(q, s)}
    if re.search(r"\b(my|i|me)\b", q.lower()):
        srcs.add("user")
    fwd, stack = set(srcs), list(srcs)
    while stack:
        for y in edges.get(stack.pop(), ()):
            if y not in fwd:
                fwd.add(y)
                stack.append(y)
    golds = {_n(g) for g in it["gold"]}
    back, stack = set(golds), list(golds)
    while stack:
        for y in redges.get(stack.pop(), ()):
            if y not in back:
                back.add(y)
                stack.append(y)
    allowed = golds | (fwd & back) | in_q
    bad = [v for v in values - allowed if _has(reply, v)]
    if not abst and bad:
        return "WRONG"
    if abst:
        return "ABSTAIN"
    if all(_has(reply, g) for g in it["gold"]):
        return "RIGHT"
    return "OTHER"


_YN = re.compile(r"^(yes|no)[.!]?$", re.I)


def answerable(it: dict, row221: dict) -> bool:
    turns = it["setup"]
    wrote = row221.get("setup_wrote") or []
    if len(wrote) != len(turns):
        return False
    for i, t in enumerate(turns):
        if wrote[i]:
            continue
        if _YN.match(t.strip()):
            return False  # a confirmation that did not change anything
        nxt = i + 1
        if not (nxt < len(turns) and _YN.match(turns[nxt].strip())
                and wrote[nxt]):
            return False
    return True


def score(items: list[dict], out: Path, arms: list[str]) -> dict:
    rows = {}
    for a in arms:
        rows[a] = {}
        for line in (out / f"rows-{a}.jsonl").read_text(
                encoding="utf-8").splitlines():
            r = json.loads(line)
            rows[a][r["id"]] = r
    res: dict = {"arms": {}, "items": []}
    for a in arms:
        res["arms"][a] = {"RIGHT": 0, "WRONG": 0, "ABSTAIN": 0, "OTHER": 0,
                          "writes": 0, "by_family": {},
                          "answerable": {"n": 0, "RIGHT": 0,
                                         "n_nonabstain": 0,
                                         "RIGHT_nonabstain": 0,
                                         "n_abstain": 0,
                                         "RIGHT_abstain": 0}}
    ref = "221" if "221" in arms else arms[0]
    lines = ["| id | family | kind | question | " + " | ".join(arms)
             + " | 231 reply |", "|" + "---|" * (5 + len(arms))]
    for it in items:
        rec = {"id": it["id"], "family": it["family"], "kind": it["kind"],
               "answerable": answerable(it, rows[ref][it["id"]])}
        for a in arms:
            r = rows[a][it["id"]]
            g = score_one(it, r)
            rec[a] = g
            A = res["arms"][a]
            A[g] += 1
            A["writes"] += int(bool(r["wrote"]))
            f = A["by_family"].setdefault(it["family"], {"n": 0, "RIGHT": 0})
            f["n"] += 1
            f["RIGHT"] += int(g == "RIGHT")
            if rec["answerable"]:
                S = A["answerable"]
                S["n"] += 1
                S["RIGHT"] += int(g == "RIGHT")
                sub = "abstain" if it["kind"] == "abstain" else "nonabstain"
                S["n_" + sub] += 1
                S["RIGHT_" + sub] += int(g == "RIGHT")
        res["items"].append(rec)
        last = arms[-1]
        lines.append(f"| {it['id']}{'' if rec['answerable'] else ' (BLOCKED)'}"
                     f" | {it['family']} | {it['kind']} | "
                     f"{it['question']} | "
                     + " | ".join(rec[a] for a in arms)
                     + f" | {rows[last][it['id']]['reply']} |")
    res["blocked"] = [x["id"] for x in res["items"] if not x["answerable"]]
    if "221" in arms and "231" in arms:
        res["lost_vs_221"] = [x["id"] for x in res["items"]
                              if x["221"] == "RIGHT" and x["231"] != "RIGHT"]
        d = [rows["231"][i]["ms"] - rows["221"][i]["ms"] for i in rows["231"]]
        res["latency_231_minus_221_ms"] = {
            "median": round(statistics.median(d), 2),
            "p90": round(sorted(d)[int(0.9 * (len(d) - 1))], 2)}
    (out / "scores.json").write_text(json.dumps(res, indent=1),
                                     encoding="utf-8")
    (out / "cases.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "items"},
                     indent=1))
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "score"])
    ap.add_argument("--arm", default=None)
    ap.add_argument("--arms", default="138i,221,231")
    ap.add_argument("--items", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    items = load_items(Path(args.items))
    if args.mode == "run":
        run_arm(args.arm, items, Path(args.out))
    else:
        score(items, Path(args.out), args.arms.split(","))
    return 0


if __name__ == "__main__":
    sys.exit(main())
