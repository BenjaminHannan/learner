"""Milestone 1 evidence on real data (design/06 §11): legacy vs label-free inputs, and C's candidate gap.

Read-only on the data build: the name detector and BM25 table are fitted in memory and written only to the
output directory. CPU only, no training. Example:

    python scripts/premonition_m01_probe.py --data data/village/stream/cache/large-seed0-f78a540c1e8a \
        --out artifacts/opus-m01-<run>/probe.json --workers 8
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch  # noqa: E402

from learnlab import step1  # noqa: E402
from learnlab.step1 import QUESTION_TAG  # noqa: E402
from learnlab.tokenizer import Tokenizer  # noqa: E402
from premonition import data as pdata  # noqa: E402
from premonition import exp1, identity, lookup, preprocess, slices  # noqa: E402
from premonition.train import label_free  # noqa: E402


def compare_caches(legacy: pdata.VisitCache, new: pdata.VisitCache, chunk: int = 64) -> dict:
    """Question-level comparison of legacy (whole-line cache + batch masking) vs the label-free v2 cache."""
    out: Counter = Counter()
    examples = []
    for start in range(0, len(new), chunk):
        visits = list(range(start, min(len(new), start + chunk)))
        a, b = pdata.collate(new, visits), label_free(pdata.collate(legacy, visits))
        for row, visit in enumerate(visits):
            same_table = a.names[row] == b.names[row]
            out["visits"] += 1
            out["visits_name_table_differs"] += not same_table
            if not same_table and len(examples) < 3:
                examples.append({"visit": new.visit_ids[visit], "legacy": b.names[row].spellings,
                                 "label_free": a.names[row].spellings})
        for q in range(a.size[2]):
            row, end = int(a.q_visit[q]), int(a.q_span[q, 1])
            out["questions"] += 1
            same_prefix = (int(b.q_span[q, 1]) == end
                           and torch.equal(a.tokens[row, :end], b.tokens[row, :end]))
            out["questions_input_prefix_differs"] += not same_prefix
            out["questions_target_differs"] += not torch.equal(a.answer[q], b.answer[q])
    stats = new.info["stats"]
    return {**out, "label_only_names": stats.get("label_only_names", 0),
            "visits_with_label_only_names": stats.get("visits_with_label_only_names", 0),
            "targets_with_unbound_names": stats.get("target_names_unbound", 0),
            "legacy_answer_names_unseen": legacy.info["stats"].get("answer_names_unseen", 0),
            "tokens": {"legacy_whole_lines": int(legacy.tokens.numel()), "label_free": int(new.tokens.numel())},
            "examples": examples}


def cut_changes(tokenizer: Tokenizer, questions, seen) -> dict:
    """near / far under A's 736-token cut: with-labels lines vs label-free lines; and what A's inputs show."""
    items_labelled, labelled = slices.tag_questions(tokenizer, questions, seen=seen, source="validation",
                                                    regime=preprocess.WITH_LABELS)
    items_free, free = slices.tag_questions(tokenizer, questions, seen=seen, source="validation")
    count = Counter()
    for item in items_labelled:           # the step-1 / old exp1 convention: whole earlier question lines
        shown = [line for n, line in item.question.context[len(item.question.context) - item.kept_lines:]
                 if line.startswith(QUESTION_TAG)]
        count["with_labels_inputs_showing_earlier_answers"] += bool(shown)
        count["with_labels_earlier_answers_shown"] += len(shown)
        count["with_labels_decision_inputs_showing_earlier_answers"] += bool(shown) and labelled[
            item.question.id].decision
    for item in items_free:
        try:
            preprocess.audit_ids(item.prompt, tokenizer, preprocess.LABEL_FREE)
        except preprocess.MalformedInput:
            count["label_free_inputs_failing_audit"] += 1
    count["inputs"] = len(items_free)
    for qid, tag in labelled.items():
        other = free[qid]
        count["far_with_labels"] += tag.far
        count["far_label_free"] += other.far
        count["near_with_labels"] += tag.near
        count["near_label_free"] += other.near
        count["far_to_near"] += tag.far and other.near
        count["near_to_far"] += tag.near and other.far
        count["decision_far_with_labels"] += tag.far and tag.decision
        count["decision_far_label_free"] += other.far and other.decision
    return dict(count)


def c_gap(tokenizer: Tokenizer, bm25: lookup.Bm25, questions) -> dict:
    """C's inputs under the legacy candidate rule and the current one (label-free lines)."""
    lines = lookup.LineIds(tokenizer, regime=preprocess.LABEL_FREE)
    count: Counter = Counter()
    rounds: Counter = Counter()
    example = None
    for q in questions:
        old = lookup.lookup_input(q, lines, bm25, candidates_rule=preprocess.LEGACY_LOOKUP_CANDIDATES)
        new = lookup.lookup_input(q, lines, bm25)
        text = dict(q.context)
        gap = [n for n in old.gap_lines if n in text and not text[n].startswith(QUESTION_TAG)]
        lost = sorted({e for e in q.evidence if e in set(gap)})
        count["questions"] += 1
        count["legacy_questions_with_gap"] += bool(gap)
        count["legacy_gap_lines"] += len(gap)
        count["legacy_questions_with_evidence_in_gap"] += bool(lost)
        count["legacy_evidence_lines_in_gap"] += len(lost)
        count["now_evidence_in_old_gap_recalled"] += len(set(lost) & set(new.recall.lines))
        count["now_evidence_in_old_gap_in_window"] += sum(e >= new.window.start for e in lost)
        count["now_gap_lines"] += len(new.gap_lines)
        count["now_over_budget"] += len(new.ids) > slices.CUT_MAX_LEN
        count["now_recall_overlaps_window"] += any(n >= new.window.start for n in new.recall.lines)
        count["legacy_with_recall"] += bool(old.recall.lines)
        count["now_with_recall"] += bool(new.recall.lines)
        rounds[new.rounds] += 1
        if lost and (example is None or (not set(example["evidence"]) & set(example["now_recalled"])
                                          and set(lost) & set(new.recall.lines))):
            example = {"question": q.id, "question_text": q.question, "evidence": lost,
                       "a_window_start": old.a_start, "legacy_c_window_start": old.window.start,
                       "legacy_recalled": list(old.recall.lines), "now_c_window_start": new.window.start,
                       "now_recalled": list(new.recall.lines), "now_rounds": new.rounds,
                       "evidence_text": [text[e] for e in lost]}
    return {**count, "rounds": dict(sorted(rounds.items())), "example": example}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--split", default="validation")
    parser.add_argument("--out", required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    out = project / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    timing: dict[str, float] = {}
    report: dict = {"data": args.data, "split": args.split}

    started = time.perf_counter()
    report["tokenizer"] = identity.verify_v2_tokenizer(project)
    tokenizer = Tokenizer.load(project / identity.V2_TOKENIZER["path"])
    report["preprocess"] = {regime: preprocess.identity(regime) for regime in preprocess.REGIMES}
    timing["tokenizer"] = time.perf_counter() - started

    started = time.perf_counter()
    detector = pdata.fit_detector(project / args.data / "train", workers=args.workers)
    (out.parent / "premonition-names.json").write_text(detector.to_json(), encoding="utf-8")
    report["detector_sha256"] = detector.digest
    timing["detector_fit"] = time.perf_counter() - started

    started = time.perf_counter()
    split_dir = project / args.data / args.split
    legacy = pdata.build_cache(split_dir, tokenizer, detector, workers=args.workers)
    new = pdata.build_cache(split_dir, tokenizer, detector, workers=args.workers, regime=preprocess.LABEL_FREE)
    report["cache_paths"] = {"legacy_v1": pdata.cache_relative(args.data, args.split, tokenizer, detector),
                             "label_free_v2": pdata.cache_relative(args.data, args.split, tokenizer, detector,
                                                                   preprocess.LABEL_FREE)}
    timing["caches"] = time.perf_counter() - started
    started = time.perf_counter()
    report["d_inputs"] = compare_caches(legacy, new)
    timing["compare"] = time.perf_counter() - started

    started = time.perf_counter()
    data = exp1.open_data(project, args.data, identity.V2_TOKENIZER["path"])
    questions = exp1.split_questions(data, args.split)
    report["cut"] = cut_changes(tokenizer, questions, data.seen)
    timing["cut"] = time.perf_counter() - started

    started = time.perf_counter()
    bm25 = lookup.fit_bm25(lookup.split_lines(project / args.data / "train"))
    (out.parent / f"premonition-bm25-v{lookup.VERSION}.json").write_text(json.dumps(bm25.to_dict()), encoding="utf-8")
    report["bm25_sha256"] = bm25.digest
    timing["bm25_fit"] = time.perf_counter() - started
    started = time.perf_counter()
    report["c_candidates"] = c_gap(tokenizer, bm25, questions)
    timing["c_candidates"] = time.perf_counter() - started

    started = time.perf_counter()
    refusals = {}
    for path in sorted((project / "artifacts").glob("premonition-step1-4M-*.ckpt")):
        try:
            exp1.evaluate_checkpoint(project, path, data_rel=args.data, log=lambda _m: None)
            refusals[path.name] = "SCORED (unexpected)"
        except identity.CheckpointIncompatible as error:
            refusals[path.name] = f"refused: {error}"
        except Exception as error:  # noqa: BLE001 - a missing or unfinished checkpoint is reported as such
            refusals[path.name] = f"not loadable: {type(error).__name__}: {str(error)[:160]}"
    report["legacy_checkpoints_as_primary"] = refusals
    timing["checkpoint_refusals"] = time.perf_counter() - started
    report["seconds"] = timing
    out.write_text(json.dumps(exp1.jsonable(report), indent=1), encoding="utf-8")
    print(json.dumps(exp1.jsonable(report), indent=1)[:6000])


if __name__ == "__main__":
    main()
