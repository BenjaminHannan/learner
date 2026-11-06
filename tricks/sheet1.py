"""Sheet-1 GPU run (see PREREG-sheet1.md): baseline + 6 Claude-written instruction sheets on 100 train / 200 test GSM-Hard rows,
python tool, 4 rounds. Best candidate is picked on TRAIN only; primary = best minus baseline on TEST (paired bootstrap).
--extra adds the 6 "quirk" sheets (exploratory): picked among themselves the same way, never eligible for the primary."""
import argparse, json, random, time
from pathlib import Path
import tricks1 as t

HERE = Path(__file__).parent
MAX_PROMPT = 12288 - 32  # make_engine's max_model_len, less a margin; vLLM rejects the whole batch if one prompt is longer

def guard(eng, tok, limit=MAX_PROMPT, counter=None):
    """Answer over-long prompts with a stub (no tool call, no number: that conversation ends and scores wrong) instead of crashing."""
    def g(prompts, **kw):
        lens = [len(x) for x in tok(prompts, add_special_tokens=False)["input_ids"]]
        keep = [i for i, n in enumerate(lens) if n < limit]
        if len(keep) < len(prompts):
            print(f"[warn] {len(prompts) - len(keep)} prompts over {limit} tokens, stubbed", flush=True)
            if counter is not None:
                counter[0] += len(prompts) - len(keep)
        outs = iter(eng([prompts[i] for i in keep], **kw) if keep else [])
        keep = set(keep)
        return [next(outs) if i in keep else [("(context limit)", 0)] for i in range(len(prompts))]
    return g

def normal_gold(g):
    """GSM-Hard golds that read like a real answer (non-negative whole number); the rest are the 'odd' rows."""
    return g >= 0 and float(g).is_integer()

def build_convs(sheets, rows):
    """One conversation per (sheet, row), sheet-major: index = sheet_idx * len(rows) + row_idx. Same messages as run_arm_set 'py'."""
    return [[{"role": "system", "content": s}, {"role": "user", "content": r["q"] + "\n\nEnd with 'Final answer: <number>'."}] for _, s in sheets for r in rows]

def score(r, o):
    pred = t.parse_answer(t.strip_think(o["text"]))
    return {"id": r["id"], "gold": r["gold"], "tokens": o["tokens"], "tool_calls": o["calls"], "pred": pred,
            "correct": t.num_match(pred, r["gold"]), "text": o["text"][-1500:]}

def run_split(sheets, rows, eng, tok):
    """All sheets x all rows in ONE batched tool loop; returns one list of scored rows per sheet."""
    res = t.run_tool_loop(eng, tok, build_convs(sheets, rows), [t.PY_TOOL], 4, 2048)
    n = len(rows)
    return [[score(r, res[si * n + ri]) for ri, r in enumerate(rows)] for si in range(len(sheets))]

def pick_best(stats, lo=1, hi=None):
    """Index in [lo, hi) (0 is the baseline) with the highest accuracy; ties -> lower mean tokens; then lower index."""
    return min(range(lo, len(stats) if hi is None else hi), key=lambda i: (-stats[i]["accuracy"], stats[i]["mean_tokens"], i))

def compare(te, i, j=0, keep=None):
    """Test-set difference of sheet i minus sheet j, in points, with the paired CI (in points); keep(row) limits the rows."""
    ok = [k for k, r in enumerate(te[j]) if keep is None or keep(r)]
    if not ok:
        return 0.0, 0.0, 0.0
    af, bf = [int(te[i][k]["correct"]) for k in ok], [int(te[j][k]["correct"]) for k in ok]
    lo, hi = paired_ci(af, bf)
    return 100.0 * (sum(af) - sum(bf)) / len(af), 100 * lo, 100 * hi

def paired_ci(a_flags, b_flags, B=2000, seed=0):
    """95% bootstrap CI [lo, hi] of mean(a - b) over resampled question indices."""
    rng = random.Random(seed); n = len(a_flags)
    d = [int(x) - int(y) for x, y in zip(a_flags, b_flags)]
    ds = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return [ds[int(0.025 * B)], ds[int(0.975 * B) - 1]]

def verdict(diff_pts, lo):
    return "PASS" if diff_pts >= 5.0 and lo > 0 else "OUT" if diff_pts < 2.0 else "INCONCLUSIVE"

def write_rows(out, si, split, recs):
    (out / f"rows_{si}_{split}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B"); ap.add_argument("--data", default=str(HERE / "sheet1_data.json"))
    ap.add_argument("--sheets", default=str(HERE / "sheets1.json")); ap.add_argument("--out", default="out/sheet1")
    ap.add_argument("--extra", default=str(HERE / "sheets1_quirk.json"), help="exploratory sheets; '' for none")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rf = out / "result_sheet1.json"
    d = json.loads(Path(a.data).read_text())
    train, test = (d[k][:a.limit] if a.limit else d[k] for k in ("train", "test"))
    load = lambda f: [(s["name"], s["sheet"]) for s in json.loads(Path(f).read_text())["sheets"]]
    sheets = [("baseline", t.PY_SYS)] + load(a.sheets)
    n_main = len(sheets)  # baseline + primary candidates; anything after is exploratory
    sheets += load(a.extra) if a.extra else []
    group = lambda i: "baseline" if i == 0 else "general" if i < n_main else "quirk"
    if rf.exists():  # resume only if it is this exact run (a --limit smoke test or other sheets must not pass as the result)
        old = json.loads(rf.read_text())
        if (old["n_train"], old["n_test"], [(x["name"], x["sheet"]) for x in old["sheets"]]) != (len(train), len(test), sheets):
            raise SystemExit(f"{rf} is from a different run (limit or sheets differ); use another --out")
        print(rf.read_text()); return
    eng, tok = t.make_engine(a.model)
    over = [0]
    eng = guard(eng, tok, counter=over)
    t0 = time.time()
    tr = run_split(sheets, train, eng, tok)
    for si, recs in enumerate(tr):
        write_rows(out, si, "train", recs)
    trs = [t.stats(r) for r in tr]
    best = pick_best(trs, 1, n_main)
    for i, (n, _) in enumerate(sheets):
        print(f"[train] {i} {group(i)[0]} {n[:40]}: acc={trs[i]['accuracy']:.3f} tok={trs[i]['mean_tokens']:.0f}", flush=True)
    print(f"[result] train done in {time.time()-t0:.0f}s; best on train = {best} ({sheets[best][0]}) acc={trs[best]['accuracy']:.3f}", flush=True)
    te = run_split(sheets, test, eng, tok)
    for si, recs in enumerate(te):
        write_rows(out, si, "test", recs)
    tes = [t.stats(r) for r in te]
    diff, lo, hi = compare(te, best)
    v = verdict(diff, lo / 100)
    nd, nlo, nhi = compare(te, best, keep=lambda r: normal_gold(r["gold"]))
    flips = lambda i, j: [r["id"] for r, b in zip(te[i], te[j]) if r["correct"] and not b["correct"]]
    res = {"model": a.model, "n_train": len(train), "n_test": len(test),
           "sheets": [{"idx": i, "group": group(i), "name": n, "sheet": s, "train": trs[i], "test": tes[i]} for i, (n, s) in enumerate(sheets)],
           "best": {"index": best, "name": sheets[best][0]},
           "primary": {"diff_points": diff, "ci95_points": [lo, hi], "best_test_acc": tes[best]["accuracy"],
                       "baseline_test_acc": tes[0]["accuracy"], "boot": "paired, B=2000, seed=0"},
           "verdict": v,
           # fixed before the run (PREREG amendment): a PASS that gains < +2.0 points on the normal-gold rows is reported as quirk-driven
           "normal_gold_rows": {"n": sum(normal_gold(r["gold"]) for r in test), "diff_points": nd, "ci95_points": [nlo, nhi],
                                "quirk_driven": v == "PASS" and nd < 2.0},
           "flips": {"wrong_to_right": flips(best, 0), "right_to_wrong": flips(0, best)},
           "over_limit_prompts": over[0]}
    if len(sheets) > n_main:
        q = pick_best(trs, n_main)
        qd, qlo, qhi = compare(te, q)
        res["exploratory_quirk"] = {"index": q, "name": sheets[q][0], "diff_points": qd, "ci95_points": [qlo, qhi],
                                    "minus_best_general_points": compare(te, q, best)[0]}
    lines = [f"[sum] {i} {group(i)[0]} {n[:40]}: train={trs[i]['accuracy']:.3f} test={tes[i]['accuracy']:.3f} tok={tes[i]['mean_tokens']:.0f}" for i, (n, _) in enumerate(sheets)]
    lines.append(f"[sum] n={len(train)}/{len(test)} best={best} {sheets[best][0][:40]} diff={diff:+.1f} pts CI=[{lo:+.1f}, {hi:+.1f}] verdict={v}"
                 f" | normal-gold rows ({res['normal_gold_rows']['n']}): {nd:+.1f} CI=[{nlo:+.1f}, {nhi:+.1f}]"
                 f"{' QUIRK-DRIVEN' if res['normal_gold_rows']['quirk_driven'] else ''} | flips +{len(res['flips']['wrong_to_right'])}/-{len(res['flips']['right_to_wrong'])}"
                 f" | over-limit {over[0]}")
    if "exploratory_quirk" in res:
        x = res["exploratory_quirk"]
        lines.append(f"[sum] quirk best={x['index']} {x['name'][:40]} diff={x['diff_points']:+.1f} CI=[{x['ci95_points'][0]:+.1f}, {x['ci95_points'][1]:+.1f}] vs general best {x['minus_best_general_points']:+.1f}")
    (out / "summary.txt").write_text("\n".join(lines) + "\n")
    rf.write_text(json.dumps(res, indent=1))
    for l in lines:
        print(l, flush=True)

if __name__ == "__main__":
    main()
