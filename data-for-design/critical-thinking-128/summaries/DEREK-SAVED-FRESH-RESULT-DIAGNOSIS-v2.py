#!/usr/bin/env python3
"""Post-score stdlib diagnosis of saved records; no scorer/model/decoder calls."""
import collections
import hashlib
import json
import pathlib
import statistics

W = pathlib.Path(__file__).resolve().parents[4]
F = pathlib.Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned(path, expected=None):
    path = pathlib.Path(path)
    sha = digest(path)
    if expected is not None:
        assert sha == expected, (str(path), sha, expected)
    return {"path": path.relative_to(W).as_posix(), "sha256": sha}


def write_once(name, data):
    with (F / name).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(data)


def main():
    source = pinned(__file__)
    score_path = F / "POSTTERMINAL-CPU-SCORING-v1/SCORE-v1.json"
    raw_path = F / "ACTUAL-NATIVE-CLOSEOUT-MIRROR-v1/EVAL-OBSERVATIONS.jsonl"
    gold_path = F / "POSTTERMINAL-CPU-SCORING-v1/GOLD-PRIVATE-v1.json"
    map_path = F / "GENERIC-NUMERIC-TOKEN-PROOF-v1.json"
    pins = {
        "source": source,
        "score": pinned(score_path, "e6298b7f9ed033a9e079e7720bb8b447290155ea5d7da88166293f84e6ba1ebc"),
        "raw": pinned(raw_path, "9c26b925e133307d81345e14b71bd518c5ca05750c47529a4c24633df41ba852"),
        "gold_already_consumed_by_completed_score": pinned(gold_path, "66c0b23e63730c389ad06ee1b53a14512651c8d589902721f190e406e367bc74"),
        "qualified_generic_integer_map": pinned(map_path, "bc070262bd35d32c252aabcc32205a799e5620a7aa5be570752f3d48fbe0344c"),
    }
    score = json.loads(score_path.read_text())
    raw = [json.loads(line) for line in raw_path.read_text().splitlines()]
    gold = json.loads(gold_path.read_text())["rows"]
    number_tokens = json.loads(map_path.read_text())["numeric_tokens"]
    inverse = {int(token): int(number) for number, token in number_tokens.items()}
    assert len(inverse) == 90 and not {0, 1, 7}.intersection(inverse)
    assert len(raw) == 128 and len(gold) == 16 and len(score["results"]) == 8
    assert score["all128_raw_verified_before_first_gold_open"] is True
    assert score["raw_unchanged_after_scoring"] is True
    gold_by_id = {frame["id"]: frame for frame in gold}
    assert len(gold_by_id) == 16
    for frame in gold:
        a, b = frame["operands"]
        expected = a + b if frame["operation"] == "add" else a - b
        assert int(frame["canonical_numeric_target"]) == expected
        assert frame["labels"] == [[number_tokens[str(expected)], 7]]
    by_endpoint = collections.defaultdict(list)
    for row in raw:
        by_endpoint[(row["seed"], row["arm"], row["condition"])].append(row)
    table = []
    row_table = []
    totals = collections.Counter()
    primary_rows = []
    failure_distances = []
    emitted_distribution = collections.Counter()
    for endpoint in score["results"]:
        key = (endpoint["seed"], endpoint["arm"], endpoint["condition"])
        actual = by_endpoint[key]
        assert len(actual) == 16
        assert [row["id"] for row in actual] == [frame["id"] for frame in gold]
        answers = {answer["id"]: answer for answer in endpoint["answers"]}
        counts = collections.Counter()
        grouped = collections.defaultdict(collections.Counter)
        details = []
        for row in actual:
            frame = gold_by_id[row["id"]]
            answer = answers[row["id"]]
            ids = row["MODEL_generated_ids_with_observed_EOS"]
            assert len(ids) == 2 and ids[1] == 7 and ids.count(7) == 1
            assert ids == answer["full_token_sequence"]
            assert row["native_generate_call_count"] == 1
            assert row["total_advances"] == 4 and len(row["predicted_trace"]) == 4
            call, *remaining = row["predicted_trace"]
            assert all(x["action"] == "NONE" for x in remaining)
            assert call["action"] in ("ADD", "SUB", "NONE")
            operands = call.get("operand_values")
            if operands is None and call["action"] != "NONE":
                registry = {entry["id"]: entry["value"] for entry in frame["numeric_registry"]}
                operands = [registry[ref] for ref in call["refs"]]
            operands = operands or []
            independent_attempt_result = None if not operands else (operands[0] + operands[1] if call["action"] == "ADD" else operands[0] - operands[1])
            independent_call_result = independent_attempt_result if call["status"] == "OK" else None
            if call["status"] == "OK":
                assert call["result"]["value"] == independent_call_result
            else:
                assert call["result"] is None and call["numeric_token_id"] is None
            operation_correct = call["action"].lower() == frame["operation"]
            operands_correct = (sorted(operands) == sorted(frame["operands"])) if frame["operation"] == "add" else (operands == frame["operands"])
            call_correct = call["status"] == "OK" and operation_correct and operands_correct and independent_call_result == int(frame["canonical_numeric_target"])
            final_correct = ids == frame["labels"][0]
            assert call_correct == answer["equivalent_task_call_correct"]
            assert final_correct == answer["strict_final_correct"]
            assert answer["mechanically_valid"] is True and answer["mechanical_errors"] == []
            emitted = inverse.get(ids[0])
            distance = None if emitted is None else emitted - int(frame["canonical_numeric_target"])
            category = "correct" if final_correct else ("correct_call_wrong_final" if call_correct else "wrong_call_wrong_final")
            counts["final"] += final_correct
            counts["call"] += call_correct
            counts[category] += 1
            counts["wrong_operation"] += not operation_correct
            counts["wrong_operands"] += not operands_correct
            counts["first_action_" + call["action"]] += 1
            counts["call_status_" + call["status"]] += 1
            if not call_correct:
                cause = "no_call" if call["action"] == "NONE" else ("tool_error_" + call["error_code"] if call["status"] == "ERROR" else ("wrong_operation" if not operation_correct else "wrong_operand_selection"))
                counts["wrong_task_call_" + cause] += 1
            family = frame["id"].split("-")[0]
            grouped[family]["rows"] += 1
            grouped[family]["final"] += final_correct
            grouped[family]["call"] += call_correct
            grouped[frame["operation"]]["rows"] += 1
            grouped[frame["operation"]]["final"] += final_correct
            grouped[frame["operation"]]["call"] += call_correct
            detail = {"id": row["id"], "expected": int(frame["canonical_numeric_target"]), "emitted_saved_map_value": emitted,
                      "emitted_token_ids": ids, "expected_token_ids": frame["labels"][0], "category": category,
                      "executed_operation": call["action"], "executed_operands": operands,
                      "independently_checked_calculator_result": independent_call_result,
                      "independent_arithmetic_of_attempted_operands": independent_attempt_result,
                      "calculator_status": call["status"], "calculator_error": call.get("error_code"),
                      "calculator_numeric_token_id": call["numeric_token_id"], "operation_correct": operation_correct,
                      "operands_correct": operands_correct, "task_call_correct": call_correct,
                      "strict_final_correct": final_correct, "signed_numeric_distance": distance}
            details.append(detail)
            row_table.append([*key, row["id"], detail["expected"], emitted, ids[0], call["action"], ",".join(map(str, operands)), independent_call_result, call["numeric_token_id"], category])
            if key == (1, "contextual", "low_lr"):
                detail = dict(detail, original_question=frame["question"])
                primary_rows.append(detail)
            if not final_correct and distance is not None:
                failure_distances.append(distance)
            emitted_distribution[str(emitted) if emitted is not None else "unmapped_token:" + str(ids[0])] += 1
        assert counts["final"] == endpoint["strict_final_correct"]
        assert counts["call"] == endpoint["equivalent_task_call_correct"]
        conditioned = endpoint["correct_call_conditioned_readout"]
        assert conditioned["correct_call_wrong_final"] == counts["correct_call_wrong_final"]
        assert conditioned["strict_final_correct_given_equivalent_task_call"] == counts["correct"]
        pair_count = sum(all(answers[f["id"]]["strict_final_correct"] for f in gold if f["pair_id"] == pair) for pair in {f["pair_id"] for f in gold})
        assert pair_count == endpoint["pair_correct"]
        totals.update(counts)
        table.append({"seed": key[0], "arm": key[1], "condition": key[2], "learning_rate": endpoint["learning_rate"],
                      "strict_final_correct": counts["final"], "rows": 16, "strict_pair_correct": pair_count, "pairs": 8,
                      "correct_task_calls": counts["call"], "strict_final_given_correct_call_numerator": counts["correct"],
                      "strict_final_given_correct_call_denominator": counts["call"],
                      "correct_call_wrong_final": counts["correct_call_wrong_final"], "wrong_call_wrong_final": counts["wrong_call_wrong_final"],
                      "wrong_operation": counts["wrong_operation"], "wrong_operands": counts["wrong_operands"],
                      "groups": dict(grouped), "checkpoint": endpoint["checkpoint"]})
    consultation = json.loads((W / "docs/premonition-recovery/CURRENT.json").read_text())
    assert digest(W / consultation["path"]) == consultation["sha256"]
    report = {"schema": "cap256.saved-fresh-result-diagnosis.v1", "status": "SAVED_SCORE_AND_TRACE_DIAGNOSIS_COMPLETED",
              "source_pins": pins, "score_reexecuted": False, "model_calls": 0, "Torch_imports": 0,
              "GPU_calls": 0, "PC_calls": 0, "tokenizer_or_decoder_calls": 0,
              "emitted_number_method": "Lookup saved token IDs in the already qualified generic90 map; no decoding or model call.",
              "gold_access_stage": "Completed score already consumed gold after root and independent raw128/closure gates; this diagnosis reads saved Gold only.",
              "endpoint_table": table, "totals": dict(totals), "total_rows": 128, "total_pairs": 64,
              "strict_complete_pairs": sum(t["strict_pair_correct"] for t in table), "primary_seed1_contextual_low_lr_rows": primary_rows,
              "numeric_error_description": {"mapped_wrong_finals": len(failure_distances), "emitted_minus_expected_mean": statistics.mean(failure_distances),
                                            "mean_absolute_distance": statistics.mean(map(abs, failure_distances)),
                                            "negative": sum(x < 0 for x in failure_distances), "positive": sum(x > 0 for x in failure_distances),
                                            "emitted_distribution_all128": dict(emitted_distribution)},
              "matched_contrasts": score["matched_contrasts"], "comparative_decisions": score["comparative_decisions"],
              "measured_findings": ["All128 strict native/EOS/four-loop contracts pass saved checks.",
                                    "Wrong task calls include operation selection, operand selection, one omitted call and three saved tool errors; exact counts recorded.",
                                    "Correct numeric calculator signals frequently coexist with wrong emitted numeric tokens.",
                                    "Every fixed matched-pair comparison ties zero complete pairs; no two-seed pair improvement."],
              "claim_scope": score["claim_scope"], "novelty_claim_limits": score["novelty_claim_limits"],
              "hypotheses_not_proved": ["A cause of wrong operation selection or numeric readout", "Broad English reasoning transfer", "Own-core independence"],
              "prior_fitting_STOP_unchanged": score["prior_fitting_STOP_unchanged"], "new_experiment_or_architecture_change_authorized_by_diagnosis": False,
              "separate_peer_full_recount": "Parent designated independent reviewer; this artifact does not rerun the scorer.",
              "runbook": {"version": consultation["version"], "sha256": consultation["sha256"],
                          "rules": ["execution.preflight", "limits.authority", "failure.preserve"],
                          "action": "Derive CPU-only summaries from immutable completed score/trace evidence; preserve failed admission and all receipts; no new experiment."}}
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    assert len(encoded.encode()) < 128 * 1024
    write_once("DEREK-SAVED-FRESH-RESULT-DIAGNOSIS-v1.json", encoded)
    columns = ["seed", "arm", "condition", "LR", "strict_final/16", "complete_pairs/8", "correct_calls/16", "final_given_correct_call", "correct_call_wrong_final", "wrong_call_wrong_final"]
    lines = ["\t".join(columns)]
    for t in table:
        lines.append("\t".join(map(str, [t["seed"], t["arm"], t["condition"], t["learning_rate"], t["strict_final_correct"], t["strict_pair_correct"], t["correct_task_calls"], str(t["strict_final_given_correct_call_numerator"]) + "/" + str(t["strict_final_given_correct_call_denominator"]), t["correct_call_wrong_final"], t["wrong_call_wrong_final"]])))
    write_once("DEREK-RESULT-TABLE-v1.tsv", "\n".join(lines) + "\n")
    headers = ["seed", "arm", "condition", "id", "expected", "emitted_saved_map_value", "emitted_numeric_ID", "executed_operation", "executed_operands", "calculator_value", "calculator_numeric_ID", "outcome"]
    write_once("DEREK-SAVED-128-ROW-NUMERIC-TRACE-v1.tsv", "\n".join(["\t".join(headers)] + ["\t".join(map(str, row)) for row in row_table]) + "\n")
    print(json.dumps({"report": pinned(F / "DEREK-SAVED-FRESH-RESULT-DIAGNOSIS-v1.json"), "table": pinned(F / "DEREK-RESULT-TABLE-v1.tsv"), "rows": pinned(F / "DEREK-SAVED-128-ROW-NUMERIC-TRACE-v1.tsv"), "totals": dict(totals)}, sort_keys=True))


if __name__ == "__main__":
    main()
