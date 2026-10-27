"""Screen 4 data: the SAME toy ladder with SIX relations (Claude, 2026-09-19) -- additive.

The frozen `premonition/toy_ladder.py` LadderSpec defaults to 3 relations with relation 2 held out of two-hop
TRAINING questions, so two-hop training covers only 2 relations. This module builds the identical data with
`LadderSpec(relations=6, heldout_relation=5)` -- 5 relations practised at hop 2, 1 held out -- and everything
else at its default, into its own directory:

    artifacts/claude-ladder6-20260919/data/{validation.pt, train-digests.json, manifest.json}

Nothing existing is edited. Opus's `premonition_ovn_ladder` (L) is reused by pointing two of its module
globals at this spec and this directory (`activate()`); `L.held_out`, `L.train_stream`, `L.batch_digest`,
`L.prints`, `L.shortcut_ceilings`, `L.load_split` and `L.checked_train` then all work on the new data, and
`premonition_ovn_retrieval.config_for` picks up the new `vocab_size` through `L.spec()`.

Only the VALIDATION split is built; no test split exists for this data, so it cannot be scored.

    PY -B scripts/premonition_ladder6.py data      # build (a few minutes: 4000 train digests)
    PY -B scripts/premonition_ladder6.py check     # gold-card order / target sanity on validation
    PY -B scripts/premonition_ladder6.py info      # manifest summary
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_ovn_ladder as L  # noqa: E402

OUT = L.ROOT / "artifacts" / "claude-ladder6-20260919"
RELATIONS = 6
HELDOUT_RELATION = 5
_SPEC = None


def spec6():
    """LadderSpec(relations=6, heldout_relation=5); every other field is the frozen default."""
    global _SPEC
    if _SPEC is None:
        from premonition.toy_ladder import LadderSpec
        _SPEC = LadderSpec(relations=RELATIONS, heldout_relation=HELDOUT_RELATION)
    return _SPEC


def activate() -> None:
    """Point L's `spec()` and `OUT` at the 6-relation spec and this data directory (no file is edited)."""
    L.spec = spec6
    L.OUT = OUT


def lines_per_visit(items) -> dict:
    """Min / max / mean of the number of lines in a visit, and of the visit length in tokens."""
    lines, toks = [], []
    for batch, _supplied, _hops in items:
        for v in range(batch.tokens.shape[0]):
            lines.append(int((batch.line_start[v] >= 0).sum()))
            toks.append(int(batch.lengths[v]))
    return {"lines_min": min(lines), "lines_max": max(lines), "lines_mean": round(sum(lines) / len(lines), 2),
            "tokens_min": min(toks), "tokens_max": max(toks), "tokens_mean": round(sum(toks) / len(toks), 2)}


def cmd_data(args) -> None:
    """L.cmd_data, restricted to the validation split (mirrors it line for line otherwise)."""
    import torch
    s = spec6()
    out = OUT / "data"
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"spec": asdict(s), "vocab_size": s.vocab_size, "chance": s.chance, "seeds": L.SEEDS,
                "visits_per_batch": L.VISITS, "label_free": "premonition.train.label_free (legacy toy rule)",
                "vocabulary": "toy synthetic ids (diagnostic exception to the v2 tokenizer rule)",
                "privilege": "gold-evidence diagnostic: the supplied cards per question come from the generator",
                "screen": "4 (six relations: 5 practised at hop 2, heldout_relation=5)",
                "splits": {}}
    seen = {}
    items = L.held_out("validation")
    path = out / "validation.pt"
    torch.save(items, path)
    seen["validation"] = {p for item in items for p in L.prints(item)}
    hops = torch.cat([item[2] for item in items])
    held = torch.cat([item[0].slices["heldout"] for item in items])
    manifest["splits"]["validation"] = {
        "seed": L.SEEDS["validation"], "batches": len(items), "visits": len(items) * L.VISITS,
        "questions": int(hops.numel()), "one_hop": int((hops == 1).sum()), "two_hop": int((hops == 2).sum()),
        "two_hop_heldout": int(held.sum()), "two_hop_practised": int(((hops == 2) & ~held).sum()),
        "file": str(path.relative_to(L.ROOT)).replace("\\", "/"), "sha256": L.sha256(path)}
    manifest["lines_per_visit_validation"] = lines_per_visit(items)
    digests, train_prints, held_train = [], set(), 0
    stream = L.train_stream()
    for _ in range(L.TRAIN_BATCHES):
        item = next(stream)
        digests.append(L.batch_digest(item))
        train_prints.update(L.prints(item))
        held_train += int(item[0].slices["heldout"].sum())
    seen["train"] = train_prints
    (out / "train-digests.json").write_text(json.dumps(digests))
    manifest["splits"]["train"] = {"seed": L.SEEDS["train"], "batches_digested": L.TRAIN_BATCHES,
                                   "heldout_two_hop_in_train": held_train,
                                   "digest_of_digests": hashlib.sha256("".join(digests).encode()).hexdigest()}
    manifest["overlap_visits"] = {"train&validation": len(seen["train"] & seen["validation"])}
    manifest["shortcut_ceilings_validation"] = L.shortcut_ceilings(
        torch.load(out / "validation.pt", weights_only=False))
    manifest["test_split"] = "not built (validation only)"
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps({k: v for k, v in manifest.items() if k != "shortcut_ceilings_validation"}, indent=1))


def cmd_check(args) -> None:
    """Every two-hop validation question: gold_lines[0] = link card of the asker, gold_lines[1] = answer card."""
    from collections import Counter
    import premonition_first_card_probe as P
    s = spec6()
    items = L.load_split("validation")
    order = Counter()
    bad_target = 0
    n2 = n1 = 0
    for batch, _supplied, hops in items:
        for q in range(len(hops)):
            v = int(batch.q_visit[q])
            ask = batch.tokens[v, int(batch.q_span[q, 0]):int(batch.q_span[q, 1])].tolist()
            lines = batch.gold_lines[q][batch.gold_lines[q] >= 0].tolist()
            facts = [batch.tokens[v, int(batch.line_start[v, l]):int(batch.line_start[v, l]) + 4].tolist()
                     for l in lines]
            if int(hops[q]) == 1:
                n1 += 1
                bad_target += not (facts[0][1:3] == ask[1:3] and facts[0][3] == int(batch.answer[q, 0]))
                continue
            n2 += 1
            link, attr = facts
            bad_target += not (link[1] == ask[1] and link[2] == s.link and attr[1] == link[3]
                               and attr[2] == ask[3] and attr[3] == int(batch.answer[q, 0]))
            a = ask[1] - s.vocab_size
            b = int(link[3]) - s.vocab_size
            r = ask[3]
            order[(P.classify(link, a, b, r, s.link, s.vocab_size),
                   P.classify(attr, a, b, r, s.link, s.vocab_size))] += 1
    report = {"one_hop_questions": n1, "two_hop_questions": n2, "target_errors": bad_target,
              "gold_line_order_check": {f"{k[0]}|{k[1]}": v for k, v in order.items()},
              "lines_per_visit": lines_per_visit(items)}
    print(json.dumps(report, indent=1))
    if bad_target or set(report["gold_line_order_check"]) != {"link|answer"}:
        raise SystemExit("FAILED: gold order / targets are not as expected")
    print("OK: link|answer holds for every two-hop validation question")


def cmd_info(args) -> None:
    manifest = json.loads((OUT / "data" / "manifest.json").read_text())
    print(json.dumps({k: v for k, v in manifest.items() if k != "shortcut_ceilings_validation"}, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("data")
    sub.add_parser("check")
    sub.add_parser("info")
    args = parser.parse_args()
    L.bootstrap()
    activate()
    import torch
    torch.set_num_threads(8)
    {"data": cmd_data, "check": cmd_check, "info": cmd_info}[args.cmd](args)


if __name__ == "__main__":
    main()
