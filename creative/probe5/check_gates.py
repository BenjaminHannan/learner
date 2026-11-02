"""Probe-5 validity gates (PREREG.md), checked BEFORE any picker result is read. If one fails the run is INVALID (not a result): fix the fault, repeat once.
  replay   replaying each try's tool calls reproduces its recorded success on >= 99% of tries
  parse    >= 90% of tries contain at least one parsed tool call or a non-empty final reply (no format collapse)
  val      LoRA val loss after training is below val loss before
  empty    TEST-T empty-sample share <= 10%: share of the writer's samples that give no valid check (unparsable reply, empty list, or only invalid checks)
Also reported, no gate: how often the tool calls came from the server (native) vs from the raw text fallback, raw-empty replies, the same empty share for TEST-B.
Usage: check_gates.py --out DIR [--tasks tasks_new.jsonl] [--tries 12] [--advisory]        exit 0 = valid, 8 = INVALID, 9 = inputs incomplete   (--advisory: always exit 0, for the smoke run)"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5common as C
import analyze_e2e as E
import analyze as an

P = C.P
REPLAY_MIN, PARSE_MIN, EMPTY_MAX = 0.99, 0.90, 0.10
EXIT_INVALID, EXIT_INCOMPLETE = 8, 9


def parse_rate(rows):
    """Share of tries with at least one tool call or a non-empty final reply (a try that only produced empty/garbled turns counts against the gate)."""
    ok = 0
    for r in rows:
        calls = any(m.get("tool_calls") for m in r["transcript"] if m["role"] == "assistant")
        ok += bool(calls or (r.get("final_reply") or "").strip())
    return ok / max(1, len(rows))


def empty_share(probe_path, n_expected=None):
    """-> dict(n, empty (no valid check), raw_empty (no text at all), share)."""
    rows = C.read_jsonl(probe_path)
    empty = sum(not [c for c in (r.get("checks") or []) if an.valid(c)] for r in rows)
    raw = sum(not (r.get("raw") or "").strip() for r in rows)
    n = max(len(rows), n_expected or 0)
    return dict(n=len(rows), expected=n_expected, empty=empty, raw_empty=raw, share=empty / n if n else 1.0)


def val_losses(out):
    p = os.path.join(out, "train", "train_summary.json")
    if os.path.exists(p):
        s = json.load(open(p))
        return s["val_loss_before"], s["val_loss_after"]
    vals = [r for r in C.read_jsonl(os.path.join(out, "train", "train_log.jsonl")) if r.get("event") == "val"]
    return (vals[0]["val_loss"], vals[-1]["val_loss"]) if len(vals) >= 2 else (None, None)


def evaluate(out, tasks_path, tries=P.N_TRIES, test_t=None, test_b=None):
    tasks = P.load_tasks(tasks_path)
    tries_path = os.path.join(out, "tries", "results.jsonl")
    alltasks, full, rows = E.load_inputs(tasks_path, tries_path, require=tries)
    res, missing = {}, []
    if len(full) < len(tasks):
        missing.append(f"tries: {len(full)}/{len(tasks)} tasks have all {tries} tries")
    rate, _ = E.gate(alltasks, rows) if rows else (0.0, None)
    res["replay"] = dict(value=rate, need=f">= {REPLAY_MIN}", ok=rate >= REPLAY_MIN, n_tries=len(rows))
    pr = parse_rate(list(rows.values()))
    src = [s for r in rows.values() for s in r.get("tool_call_sources", [])]
    res["parse"] = dict(value=pr, need=f">= {PARSE_MIN}", ok=pr >= PARSE_MIN, tool_call_sources={k: src.count(k) for k in ("native", "text", "none")})
    b, a_ = val_losses(out)
    res["val"] = dict(before=b, after=a_, need="after < before", ok=b is not None and a_ < b)
    tp = test_t or os.path.join(out, "tests_t", "probes_lfm3.jsonl")
    want = len(tasks) * C.N_SAMPLES
    if not os.path.exists(tp):
        missing.append("TEST-T probe file missing")
        res["empty"] = dict(value=None, need=f"<= {EMPTY_MAX}", ok=False)
    else:
        e = empty_share(tp, want)
        if e["n"] < want:
            missing.append(f"TEST-T: {e['n']}/{want} samples")
        res["empty"] = dict(**e, value=e["share"], need=f"<= {EMPTY_MAX}", ok=e["share"] <= EMPTY_MAX)
    bp = test_b or os.path.join(out, "tests_b", "probes_lfm3base.jsonl")
    if os.path.exists(bp):
        res["empty_test_b_info"] = empty_share(bp, want)
    return res, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--tasks", default=C.TASKS)
    ap.add_argument("--tries", type=int, default=P.N_TRIES)
    ap.add_argument("--advisory", action="store_true")
    a = ap.parse_args()
    res, missing = evaluate(a.out, a.tasks, a.tries)
    valid = all(v["ok"] for k, v in res.items() if "ok" in v) and not missing
    res["valid"], res["missing"] = valid, missing
    C.atomic_write(os.path.join(a.out, "gates.json"), json.dumps(res, indent=1))
    for k, v in res.items():
        if isinstance(v, dict) and "ok" in v:
            print(f"gate {k}: {'ok' if v['ok'] else 'FAIL'}  " + ", ".join(f"{x}={y if not isinstance(y, float) else round(y, 4)}" for x, y in v.items() if x not in ("ok",)))
    for m in missing:
        print("incomplete:", m)
    print("GATES:", "VALID" if valid else "INVALID" + (" (advisory only)" if a.advisory else ""))
    if a.advisory:
        return 0
    return EXIT_INCOMPLETE if missing else 0 if valid else EXIT_INVALID


if __name__ == "__main__":
    sys.exit(main())
