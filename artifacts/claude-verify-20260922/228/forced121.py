# Verifier copy of scripts/claude_determinism228_forced.py, retargeted to the bench121 4-hop split (donor = first item, targets = the rest).
"""Exp 228 forced-flip test: make the fix170 id()-reuse collision happen on demand.

Cause under test: scripts/fable_fix170_compose.py keys _SRC by id(triples list)
and never keeps the list alive. When a cached list from an OLDER notebook is
freed (e.g. _TRIPLES.clear() after >8 notebooks) its _SRC entry survives; if a
new, unrelated list (the copy rewrite_question builds) is later allocated at
the same address, _src_of() hands back the OLD notebook and the fast leaves
(compose_n_hop, compound_subject_hit) read the wrong index -> the rewrite
verify fails -> clarify -> glued decline.

Forcing: before each rewrite_question call, allocate a list, register it in
_SRC for a donor notebook from an earlier item (its current version, as the
real stale entry would be), then free it. CPython's list free-list hands that
address to the next list allocated -- the copy inside rewrite_question.

Usage: claude_determinism228_forced.py <agent.py> <workdir> <out.json> [--no-plant]
"""
from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "scripts")
import fable_suitediff as SD  # noqa: E402
import fable_fix172b_benchv3 as V3  # noqa: E402

agent, work, outp = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
plant = "--no-plant" not in sys.argv
mod, dcls, _b, _c = SD.load_agent(agent)
import fable_fix170_compose as F170  # noqa: E402 (same module object the agent installed)
import fable_qrewrite132 as Q132  # noqa: E402

cfg = SD.load_base_cfg("artifacts/fable-agent138i-20260922/loop138i-config.json")
cfg["sleep_threshold"] = 100000
items = {}
for f in ("data/open/bench121/fable_edit121_4hop.jsonl",):
    for line in open(f, encoding="utf-8"):
        if line.strip():
            d = json.loads(line)
            items[d["id"]] = d
DCLS = SD.mailbox_daemon_cls(dcls)

# donor notebook: run one unrelated item and keep its inner notebook alive
V3.run_item_v3(items[sorted(items)[0]], work, copy.deepcopy(cfg), DCLS, "v3")
DONOR = [e[2] for e in F170._TRIPLES.values()][-1]

# observation: did _src_of ever return the donor notebook?
_seen_src = F170._src_of
STALE = Counter()


def _observe(triples):
    got = _seen_src(triples)
    if got is DONOR:
        STALE["donor-hit"] += 1
    return got


F170._src_of = _observe
_orig_rw = Q132.rewrite_question


def _planted(question, triples):
    if plant:
        bait = [0]
        F170._SRC[id(bait)] = [DONOR, len(DONOR.events)]
        del bait  # freed -> top of the list free-list
    return _orig_rw(question, triples)


Q132.rewrite_question = _planted

targets = sorted(items)[1:]
rows = []
cnt = Counter()
for iid in targets:
    STALE.clear()
    r = V3.run_item_v3(items[iid], work, copy.deepcopy(cfg), DCLS, "v3")
    rows.append({"id": iid, "verdict": r["verdict"], "ears_stage": r["ears_stage"],
                 "donor_hits": STALE["donor-hit"], "reply": r["reply"][:160]})
    cnt[r["verdict"]] += 1
summary = {"agent": agent, "plant": plant, "n": len(rows), "verdicts": dict(cnt),
           "items_with_donor_hits": sum(1 for x in rows if x["donor_hits"]),
           "rewrite_stage": sum(1 for x in rows if x["ears_stage"] == "loop138b-rewrite")}
outp.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1), encoding="utf-8")
print(json.dumps(summary))
