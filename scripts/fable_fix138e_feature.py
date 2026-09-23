#!/usr/bin/env python3
"""Exp 138e STEP 1b -- evaluate the sibling-divergence feature on dev data.

Candidate rule: the rewriter's officeholder hop through compound C="P of T"
is used ONLY when no sibling compound C'="P of T'" (same office prefix P,
different target T') in the notebook resolves to a DIFFERENT officeholder.
Otherwise the base 113c answer/abstain stands.

Dev data only (bench splits + redteam143 cases with officeholder chains).
No seal, no registered run.

Run:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_fix138e_feature.py
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench121_run as B  # noqa: E402 (paths, read-only)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (base loop, read-only)
import fable_qrewrite132 as Q132  # noqa: E402 (rewriter, read-only)
import fable_redteam143_run as R143  # noqa: E402 (cases, read-only)

ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"
ART138E = ROOT / "artifacts" / "fable-officechain138e-20260922"
DATA134 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
DATA132 = ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl"


def reachable_from(seeds: set[str], triples) -> set[str]:
    """BFS over the triple graph plus island-containment edges
    (entity -> compound subject containing it -> its object), mirroring
    the rewriter's own walk semantics."""
    nodes = set(seeds)
    changed = True
    guard = 0
    while changed and guard < 12:
        guard += 1
        changed = False
        for s, _r, o in triples:
            s, o = str(s), str(o)
            if s in nodes and o not in nodes:
                nodes.add(o)
                changed = True
        for (s2, _r2, o2) in triples:
            s2, o2 = str(s2), str(o2)
            parts = Q132._split_of(s2)
            if parts is None:
                continue
            tgt = parts[1]
            if tgt in nodes and s2 not in nodes:
                nodes.add(s2)
                changed = True
            if s2 in nodes and o2 not in nodes:
                nodes.add(o2)
                changed = True
    return nodes


def siblings_diverge(triples, chain_rels, question) -> dict:
    """Combined rule: veto iff a sibling officeholder compound (same
    office prefix, different target) is UNREACHABLE from the question's
    seed entities AND resolves to a DIFFERENT holder than the used hop.
    A dangling contradictory branch means the notebook is incomplete
    (a linking teach was refused) -- the rewrite would answer from the
    stale reachable branch."""
    off = {}
    for s, r, o in triples:
        if r == "officeholder":
            off.setdefault(str(s), str(o))
    # resolved holders: officeholder objects of compounds whose target is
    # on the used chain -- approximate: the holder the canonical text names
    info = {"n_officeholder_hops": sum(1 for r in chain_rels
                                       if r == "officeholder"),
            "used": [], "veto": False, "reasons": []}
    seeds = set(Q132._seed_subjects(question, triples))
    reach = reachable_from(seeds, triples)
    by_pre: dict[str, list[tuple[str, str]]] = {}
    for s, holder in off.items():
        parts = Q132._split_of(s)
        if parts is None:
            continue
        by_pre.setdefault(Q132._typonorm(parts[0]), []).append(
            (s, holder, parts[1]))
    for pre, lst in by_pre.items():
        if len({s for s, _, _ in lst}) < 2:
            continue
        # the used compound: target reachable from seed (walkable chain)
        used = [(s, h) for s, h, t in lst if t in reach]
        dangling = [(s, h) for s, h, t in lst if t not in reach]
        if not used or not dangling:
            continue
        used_holders = {h for _, h in used}
        for s, h in dangling:
            if h not in used_holders:
                info["veto"] = True
                info["reasons"].append(
                    f"dangling sibling {s!r} -> {h!r} contradicts "
                    f"used {sorted(used_holders)}; target unreachable "
                    f"from seed {sorted(seeds)}")
        info["used"].append({"prefix": pre,
                             "used": sorted(s for s, _ in used),
                             "dangling": sorted(s for s, _ in dangling)})
    return info


def main() -> int:
    sealed: dict = {}
    for name in ("fable_bench121_loop138b_new_121_4hop_rows.jsonl",
                 "fable_bench121_loop138b_old_s2fresh_4hop_rows.jsonl",
                 "fable_bench121_loop138b_edit200_rows.jsonl",
                 "fable_bench121_loop138b_bench132_4hop_rows.jsonl"):
        p = ART138B / name
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    sealed[r["id"]] = r
    items: list[tuple[str, str, str, list[str]]] = []
    for tag, path in (("new", B.DATA_NEW), ("old", B.DATA_OLD),
                      ("edit200", DATA134), ("bench132", DATA132)):
        for line in Path(str(path)).read_text(
                encoding="utf-8").splitlines():
            if line.strip():
                it = json.loads(line)
                items.append((tag, it["id"], it["question"],
                              [t["sentence_en"] for t in it["taught"]]))
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    rt = {c["id"]: c for c in suite["cases"]}
    for c in suite["cases"]:
        items.append(("rt143", c["id"], c["question"],
                      list(c.get("teaches", []))))

    import shutil
    base_cfg = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
    base_cfg["sleep_threshold"] = 100000
    workroot = ART138E / "scratch-feat"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)

    n_off = 0
    lost_correct, saved_wrong = [], []
    vetoed_correct, vetoed_other = [], []
    kept_wrong = []
    table: list[dict] = []
    for i, (tag, iid, question, teaches) in enumerate(items):
        ddir = workroot / f"c{i:05d}"
        ddir.mkdir(parents=True)
        daemon = L138b.Loop138bDaemon(
            str(ddir), cfg=dict(base_cfg), idle_seconds=30.0)
        n = 0
        for t in teaches:
            n += 1
            name = f"t{n:03d}.txt"
            (ddir / "inbox" / name).write_text(str(t) + "\n",
                                               encoding="utf-8")
            daemon.process_file(ddir / "inbox" / name)
        triples = L90.notebook_triples(daemon.loop.nb)
        try:
            _newq, info = Q132.rewrite_question(question, triples)
        except Exception:
            continue
        if not info.get("fired"):
            continue
        rels = list(info.get("rels", []))
        if "officeholder" not in rels:
            continue
        n_off += 1
        feat = siblings_diverge(triples, rels, question)
        v = (sealed.get(iid, {}) or {}).get("verdict", "rt143")
        row = {"id": iid, "split": tag, "verdict": v,
               "veto": feat["veto"], "reasons": feat["reasons"],
               "used": feat["used"], "canonical": info.get("canonical"),
               "question": question}
        table.append(row)
        if feat["veto"] and v == "correct":
            vetoed_correct.append(iid)
        if feat["veto"] and v == "wrong":
            saved_wrong.append(iid)
        if not feat["veto"] and v == "wrong":
            kept_wrong.append(iid)
        if feat["veto"] and v not in ("wrong",):
            vetoed_other.append((iid, v))
    (ART138E / "feat-sibling-divergence.json").write_text(
        json.dumps(table, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"officeholder chains: {n_off}")
    print(f"VETOED correct (must be 0): {vetoed_correct}")
    print(f"vetoed wrong (want 025/073/149): {saved_wrong}")
    print(f"kept wrong (want []): {kept_wrong}")
    print(f"vetoed non-wrong: {vetoed_other}")
    for r in table:
        if r["veto"] or r["verdict"] == "wrong":
            print(f"- {r['split']}/{r['id']} [{r['verdict']}] "
                  f"veto={r['veto']} {r['reasons']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
