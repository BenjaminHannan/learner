#!/usr/bin/env python3
"""Exp 138e STEP 1 diagnosis -- officeholder rewrite chains on dev data only.

Dev data: bench121-new, bench103-old-s2fresh, edit200, bench132-4hop
(sealed 138b rows for verdicts, read-only) + redteam143 cases.
No sealed held-out panel of any other experiment is touched.

For every item: rebuild the notebook in-process with loop138b, run
Q132.rewrite_question on the asked question, record whether the winning
chain touches the officeholder relation, and join the sealed loop138b
verdict. Then tabulate run-time (no-gold) features for each
officeholder-chain ask.

Run (Mac CPU, offline, diagnosis only -- no seal, no registered run):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_fix138e_diagnose.py
"""

from __future__ import annotations

import copy
import json
import re
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


def load_rows(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            r = json.loads(line)
            out[r["id"]] = r
    return out


def notebook_for_factory():
    import shutil
    import time
    base_cfg = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
    base_cfg["sleep_threshold"] = 100000
    workroot = ART138E / "scratch-diag-daemon"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    counter = {"n": 0}

    def run_case(teach_sentences: list[str]):
        # Same per-item fresh-daemon pattern as B.run_item (the sealed
        # driver): faithful teach path, cheap after import warmup.
        counter["n"] += 1
        ddir = workroot / f"c{counter['n']:05d}"
        ddir.mkdir(parents=True)
        daemon = L138b.Loop138bDaemon(
            str(ddir), cfg=dict(base_cfg), idle_seconds=30.0)
        n = 0
        for t in teach_sentences:
            n += 1
            name = f"t{n:03d}.txt"
            (ddir / "inbox" / name).write_text(str(t) + "\n",
                                               encoding="utf-8")
            daemon.process_file(ddir / "inbox" / name)
        return daemon.loop

    return run_case


def office_features(question: str, triples, rels: list[str]) -> dict:
    ql = str(question).lower()
    q_tok = set(Q132._tok(question))
    subjects = [str(s) for s, _, _ in triples]
    # F1: user-typed office word present in the question?
    office_words = ["head coach", "prime minister", "original broadcaster",
                    "broadcaster", "chairperson", "director", "manager",
                    "coach", "minister", "chair", "head of"]
    typed = [w for w in office_words if w in ql]
    # F2: how many officeholder hops in the winning chain?
    n_off = sum(1 for r in rels if r == "officeholder")
    # F3: does a stored compound "P of T" subject match the question
    # word-for-word (verbatim span) vs only via typo/decomp matching?
    verbatim_hits, decomp_only = [], []
    for s in subjects:
        if Q132._split_of(s) is None:
            continue
        if s.lower() in ql:
            verbatim_hits.append(s)
        elif Q132._decomp_span(ql, s) is not None:
            decomp_only.append(s)
    # F4: qualifier/date tokens in the question?
    qual = bool(re.search(
        r"\b(19|20)\d{2}\b|as of|in \d{4}|not\b|never\b|former\b|ex-\b",
        ql))
    # F5: competing officeholder facts -- distinct compound subjects
    # sharing the same target entity.
    targets: dict[str, list[str]] = {}
    for s in subjects:
        parts = Q132._split_of(s)
        if parts is None:
            continue
        targets.setdefault(parts[1].lower(), []).append(s)
    competing = {t: v for t, v in targets.items() if len(set(v)) > 1}
    # F6: for the officeholder hop target, is there ALSO a plain
    # (non-compound) triple on the same entity whose relation the
    # question's office word evidences (director_manager etc.)?
    plain_rels: dict[str, list[str]] = {}
    for s, r, _o in triples:
        if Q132._split_of(str(s)) is None:
            plain_rels.setdefault(str(s), []).append(str(r))
    return {
        "typed_office_words": typed,
        "n_officeholder_hops": n_off,
        "chain_rels": list(rels),
        "verbatim_compound_hits": verbatim_hits,
        "decomp_only_compounds": decomp_only,
        "qualifier_or_date": qual,
        "competing_compound_targets": competing,
        "plain_rels_sample": {k: v for k, v in list(plain_rels.items())[:0]},
        "n_triples": len(triples),
        "n_compound_subjects": sum(
            1 for s in subjects if Q132._split_of(s) is not None),
    }


def main() -> int:
    ART138E.mkdir(parents=True, exist_ok=True)
    verdicts: dict = {}
    for name in ("fable_bench121_loop138b_new_121_4hop_rows.jsonl",
                 "fable_bench121_loop138b_old_s2fresh_4hop_rows.jsonl",
                 "fable_bench121_loop138b_edit200_rows.jsonl",
                 "fable_bench121_loop138b_bench132_4hop_rows.jsonl"):
        p = ART138B / name
        if p.exists():
            verdicts.update(load_rows(p))
    print(f"loaded {len(verdicts)} sealed loop138b verdict rows")

    items: list[tuple[str, str, list[str]]] = []
    for tag, path in (("new", B.DATA_NEW), ("old", B.DATA_OLD),
                      ("edit200", DATA134), ("bench132", DATA132)):
        for line in Path(str(path)).read_text(
                encoding="utf-8").splitlines():
            if line.strip():
                it = json.loads(line)
                items.append((tag, it["id"], [it["question"]],
                              [t["sentence_en"] for t in it["taught"]]))
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    for c in suite["cases"]:
        items.append(("rt143", c["id"], [c["question"]],
                      list(c.get("teaches", []))))
    print(f"diagnosing {len(items)} dev items")

    office_rows: list[dict] = []
    n_fired = 0
    run_case = notebook_for_factory()
    for tag, iid, (question,), teaches in items:
        loop = run_case(teaches)
        triples = L90.notebook_triples(loop.nb)
        try:
            newq, info = Q132.rewrite_question(question, triples)
        except Exception as exc:  # noqa: BLE001 -- diagnosis must not stop
            office_rows.append({"id": iid, "split": tag,
                                "error": str(exc)[:100]})
            continue
        if not info.get("fired"):
            continue
        n_fired += 1
        rels = list(info.get("rels", []))
        if "officeholder" not in rels:
            continue
        v = verdicts.get(iid, {})
        feat = office_features(question, triples, rels)
        office_rows.append({
            "id": iid, "split": tag, "question": question,
            "canonical": info.get("canonical"),
            "verdict": v.get("verdict", "n/a-rt143-separate"),
            "reply": v.get("reply", "")[:200],
            "gold": v.get("extracted", ""),
            **feat,
        })
    (ART138E / "diag-officeholder-rows.json").write_text(
        json.dumps(office_rows, indent=1, ensure_ascii=False),
        encoding="utf-8")
    print(f"rewriter fired on {n_fired}/{len(items)}; "
          f"{len(office_rows)} officeholder chains")
    for r in office_rows:
        if "error" in r:
            continue
        print(f"- {r['split']}/{r['id']} [{r['verdict']}] "
              f"rels={r['chain_rels']} typed={r['typed_office_words']} "
              f"verbatim={len(r['verbatim_compound_hits'])} "
              f"decomp_only={len(r['decomp_only_compounds'])} "
              f"qual={r['qualifier_or_date']} "
              f"competing_targets={len(r['competing_compound_targets'])}")
        print(f"  Q: {r['question'][:150]}")
        print(f"  C: {str(r['canonical'])[:150]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
