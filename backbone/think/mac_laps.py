"""PREREG-think2 Addendum H: do extra laps help the assistant's own big model with no training? Mac (MLX), inference only.
  python backbone/think/mac_laps.py build OUT            the deep hops rows (dev + test) and LAPS_REPORT.json (sha256 of each split)
  python backbone/think/mac_laps.py run --model M --data OUT --out RUN [--wait] [--yes]
                                                         --wait: wait until --min-free-gb (20) is free; the run self-checks first
  python backbone/think/mac_laps.py selftest --model M --data OUT    the same self-check alone (one-token places, our pass = mlx_lm's)
  python backbone/think/mac_laps.py summarize RUN        prints the marks, OUTCOME and NEXT (also written to RUN/SUMMARY_laps.txt)

The model is Qwen3.6-35B-A3B 3-bit (the assistant's model), loaded with mlx_lm, weights untouched. A "lap" re-runs a block of whole
layer periods (3 linear-attention layers + 1 full-attention layer each) on the block's own output: lap 1 is the plain model, lap r runs
the block r times in a row, then the layers after it. Every pass is a full-sequence pass (no cache), so each re-run of a linear-attention
layer starts its recurrent state from zero, as the first pass does; this matches a repeated layer list with one cache entry per pass.

Rows come from build_hops.make_row with 64 lines and chains of up to 16 hops (7 chains, distinct end places, floor 1/7). The prompt
gives the facts and the question, and the answer is read as the next token after "The {object} is at the", over the row's 7 places.
Stages (each resumable; results are one JSON line per row):
  calib  dev rows, plain model only -> the deep slice D: depths whose plain dev accuracy lies in [FLOOR + 10, 80]
  sweep  dev rows at depths in D: every block (size 4, 8 or 12 layers, starting on a period edge, ending at least 4 layers before the
         top) at lap 2 -> C*, the block with the best dev accuracy on D (ties: higher mean answer log-prob, then smaller, then earlier).
         If C* beats the plain model on dev D by less than +2 points, the run stops: NO CANDIDATE.
  test   test rows (all depths, other seeds): plain model, C* at laps 2-4, and a control block (same size, the start farthest from C*'s)
         at lap 2. The marks read only this stage.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_hops as H  # noqa: E402
import summarize_hops as SH  # noqa: E402

LINES, MAX_DEPTH = 64, 16
DEV_PER_DEPTH, TEST_PER_DEPTH = 40, 100
SEED = 0
SIZES = (4, 8, 12)
TOP_KEEP = 4  # a block ends at least this many layers before the top
LAPS = (1, 2, 3, 4)
FLOOR = 100 / H.CHAINS
D_LO, D_HI = FLOOR + 10, 80.0
CAND_MIN = 2.0  # C* must beat the plain model on dev D by this much, or the run stops (NO CANDIDATE)
V_SHALLOW = 80.0  # validity: the plain model scores at least this on depth 1 (test)
GAIN, WRONG, HARM, RHO = 5.0, 1.0, 2.0, 0.3
EPS = 1e-9
TOL = 0.05  # self_check: largest allowed |log-prob| gap between our layer-by-layer pass and the model's own forward
PLACE_RE = re.compile(r"The \w+ (?:is at|sits by) the (\w+)\.")


# ---------------------------------------------------------------- data

def build(split):
    seed = SEED if split == "dev" else SEED + 1
    per = DEV_PER_DEPTH if split == "dev" else TEST_PER_DEPTH
    rows = [H.make_row(f"laps{split}", seed, i, d, lines=LINES, max_depth=MAX_DEPTH)
            for i, d in enumerate(d for d in range(1, MAX_DEPTH + 1) for _ in range(per))]
    for r in rows:
        r["places"] = sorted(PLACE_RE.findall(r["context"]))
        assert len(r["places"]) == H.CHAINS and r["answer"] in r["places"], r["id"]
    return rows


def cmd_build(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rep = dict(lines=LINES, chains=H.CHAINS, max_depth=MAX_DEPTH, dev_per_depth=DEV_PER_DEPTH, test_per_depth=TEST_PER_DEPTH, files={})
    for split in ("dev", "test"):
        p = out / f"{split}.jsonl"
        p.write_text("".join(json.dumps(r) + "\n" for r in build(split)))
        rep["files"][split] = dict(n=sum(1 for _ in open(p)), sha256=H.sha(p))
    (out / "LAPS_REPORT.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep, indent=1))
    return 0


def load_rows(data, split):
    return [json.loads(x) for x in open(Path(data) / f"{split}.jsonl")]


# ---------------------------------------------------------------- model

def prompt_ids(tok, row):
    obj = re.match(r"\[question\] Where is the (\w+)\?", row["question"]).group(1)
    facts = "\n".join(x.removeprefix("[world] ") for x in row["context"].split("\n"))
    user = f"Here are some facts.\n{facts}\n\nQuestion: Where is the {obj}? Answer with the place only."
    text = tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    return tok.encode(text + f"The {obj} is at the", add_special_tokens=False)


def cand_ids(tok, places):
    ids = [tok.encode(" " + p, add_special_tokens=False) for p in places]
    bad = [p for p, x in zip(places, ids) if len(x) != 1]
    if bad:
        raise SystemExit(f"these places are not one token after a space: {bad}")
    return [x[0] for x in ids]


class Laps:
    """Runs a Qwen3.5/3.6 (mlx_lm qwen3_5 / qwen3_5_moe) text model layer by layer, keeping the hidden state at every period edge."""

    def __init__(self, model):
        import mlx.core as mx
        self.mx = mx
        lm = getattr(model, "language_model", model)
        self.tm, self.args = lm.model, lm.args
        self.head = self.tm.embed_tokens.as_linear if self.args.tie_word_embeddings else lm.lm_head
        self.layers = list(self.tm.pipeline_layers if hasattr(self.tm, "pipeline_layers") else self.tm.layers)
        self.n, self.period = len(self.layers), self.args.full_attention_interval
        assert self.n % self.period == 0 and all(l.is_linear == ((i + 1) % self.period != 0) for i, l in enumerate(self.layers))
        self.mod = sys.modules[type(self.tm).__module__]  # the mask helpers the model's own forward uses

    def blocks(self):
        return [(s, k) for k in SIZES for s in range(self.period, self.n - TOP_KEEP - k + 1, self.period)]

    def edges(self, ids):
        """Hidden states after layer 0 (the embeddings), period, 2 * period, ..., n."""
        mx = self.mx
        h = self.tm.embed_tokens(mx.array([ids]))
        fa, ssm = self.mod.create_attention_mask(h, None), self.mod.create_ssm_mask(h, None)
        self.masks = (fa, ssm)
        out = {0: h}
        for i, layer in enumerate(self.layers):
            h = layer(h, mask=ssm if layer.is_linear else fa)
            if (i + 1) % self.period == 0:
                mx.eval(h)
                out[i + 1] = h
        return out

    def run(self, h, lo, hi):
        fa, ssm = self.masks
        for layer in self.layers[lo:hi]:
            h = layer(h, mask=ssm if layer.is_linear else fa)
        return h

    def read(self, h, cand):
        """Log-probs (full vocabulary softmax) of the candidate tokens at the last position, and the hidden state's RMS there."""
        mx = self.mx
        last = h[:, -1:, :]
        lg = self.head(self.tm.norm(last))[0, -1].astype(mx.float32)
        lp = lg - mx.logsumexp(lg)
        rms = mx.sqrt(mx.mean(last.astype(mx.float32) ** 2))
        out = lp[mx.array(cand)]
        mx.eval(out, rms)
        return [round(float(x), 4) for x in out.tolist()], round(float(rms), 3)

    def laps(self, E, s, k, rmax, cand):
        """{r: (logps, rms)} for laps 2..rmax of block (s, k), from the period-edge states E of the plain pass."""
        g, out = E[s + k], {}
        for r in range(2, rmax + 1):
            g = self.run(g, s, s + k)
            self.mx.eval(g)
            out[r] = self.read(self.run(g, s + k, self.n), cand)
        return out


def key(s, k):
    return f"s{s}k{k}"


def record(row, cand_places, base, extra):
    rec = dict(id=row["id"], depth=row["depth"], ans=cand_places.index(row["answer"]), base=base[0], base_rms=base[1])
    for name, laps in extra.items():
        rec[name] = {str(r): v[0] for r, v in laps.items()}
        rec[name + "_rms"] = {str(r): v[1] for r, v in laps.items()}
    return rec


def read_jsonl(p):
    """The complete records of a stage file. A torn last line (a crash mid-write) is cut off, and the file always ends in a
    newline, so the next append starts a fresh record."""
    if not p.exists():
        return []
    text = p.read_text()
    recs, keep, pos = [], 0, 0
    for ln in text.split("\n"):
        end = pos + len(ln)
        if ln.strip():
            try:
                recs.append(json.loads(ln))
            except json.JSONDecodeError:
                break
            keep = end
        pos = end + 1
    fixed = text[:keep] + ("\n" if keep else "")
    if fixed != text:
        p.write_text(fixed)
    return recs


def done_ids(p):
    return {r["id"] for r in read_jsonl(p)}


def stage(name, rows, out, lp, tok, extra_fn):
    p = out / f"{name}.jsonl"
    have = done_ids(p)
    rank = {}
    todo = sorted((r for r in rows if r["id"] not in have), key=lambda r: (rank.setdefault(r["depth"], {}).setdefault(r["id"], len(rank[r["depth"]])), r["depth"]))
    print(f"[{name}] {len(have)} done, {len(todo)} to go", flush=True)
    t0 = time.time()
    with open(p, "a") as f:
        for i, r in enumerate(todo):
            cand = cand_ids(tok, r["places"])
            E = lp.edges(prompt_ids(tok, r))
            base = lp.read(E[lp.n], cand)
            f.write(json.dumps(record(r, r["places"], base, extra_fn(lp, E, cand))) + "\n")
            f.flush()
            if i in (4, 49) or (i + 1) % 200 == 0:
                per = (time.time() - t0) / (i + 1)
                print(f"[{name}] {i + 1}/{len(todo)}  {per:.2f} s/row, about {per * (len(todo) - i - 1) / 60:.0f} min left", flush=True)
    return read_jsonl(p)


# ---------------------------------------------------------------- decisions (pure functions; the tests call these)

def hit(lps, ans):
    return int(int(np.argmax(lps)) == ans)


def acc(recs, get):
    return 100 * sum(hit(get(r), r["ans"]) for r in recs) / len(recs) if recs else None


def by_depth(recs, get):
    ds = sorted({r["depth"] for r in recs})
    return {d: acc([r for r in recs if r["depth"] == d], get) for d in ds}


def deep_slice(calib):
    """Depths whose plain dev accuracy lies in [D_LO, D_HI]."""
    return [d for d, v in by_depth(calib, lambda r: r["base"]).items() if D_LO - EPS <= v <= D_HI + EPS]


def choose(sweep, blocks):
    """C* = the block with the best lap-2 dev accuracy on D (sweep rows are D rows). Ties: higher mean log-prob of the answer, smaller, earlier."""
    def score(b):
        name = key(*b)
        return (acc(sweep, lambda r: r[name]["2"]), float(np.mean([r[name]["2"][r["ans"]] for r in sweep])), -b[1], -b[0])
    best = max(blocks, key=score)
    base = acc(sweep, lambda r: r["base"])
    table = {key(*b): acc(sweep, lambda r, n=key(*b): r[n]["2"]) for b in blocks}
    return dict(block=list(best), name=key(*best), dev_acc=table[key(*best)], dev_base=base, dev_gain=table[key(*best)] - base, table=table)


def control_block(best, blocks):
    """Same size as C*, the start farthest from C*'s (ties: the earlier start)."""
    same = [b for b in blocks if b[1] == best[1] and b[0] != best[0]]
    return max(same, key=lambda b: (abs(b[0] - best[0]), -b[0])) if same else None


def halted(r, name, rmax=max(LAPS)):
    """Answer-stable stop over laps 1..rmax at block `name`: the first r >= 2 whose answer equals lap r-1's, else rmax."""
    preds = [int(np.argmax(r["base"]))] + [int(np.argmax(r[name][str(k)])) for k in range(2, rmax + 1)]
    for k in range(2, rmax + 1):
        if preds[k - 1] == preds[k - 2]:
            return k, preds[k - 1]
    return rmax, preds[-1]


def paired(recs, get_a, get_b):
    """Difference of accuracies (a - b) with a paired row-bootstrap 95% interval, as summarize.boot."""
    if not recs:
        return None
    a = np.array([hit(get_a(r), r["ans"]) for r in recs], float)
    b = np.array([hit(get_b(r), r["ans"]) for r in recs], float)
    lo_hi = SH.SU.boot({"a": a, "b": b}, lambda m: m["a"] - m["b"])
    v = 100 * (a.mean() - b.mean())
    return dict(value=v, lo=lo_hi[0] if lo_hi else None, hi=lo_hi[1] if lo_hi else None, n=len(recs))


def analyse(test, sel, D):
    name = sel["name"]
    deep = [r for r in test if r["depth"] in D]
    shallow = [r for r in test if r["depth"] < min(D)] if D else []
    d1 = acc([r for r in test if r["depth"] == 1], lambda r: r["base"])
    out = dict(D=D, block=name, d1_base=d1, valid=d1 is not None and d1 >= V_SHALLOW - EPS,
               base_by_depth=by_depth(test, lambda r: r["base"]),
               laps_by_depth={str(k): by_depth(test, lambda r, k=k: r[name][str(k)]) for k in LAPS[1:]})
    out["H1"] = paired(deep, lambda r: r[name]["2"], lambda r: r["base"])
    out["H2"] = paired(shallow, lambda r: r[name]["2"], lambda r: r["base"])
    stops = {r["id"]: halted(r, name) for r in test}
    out["halt_mean_laps"] = float(np.mean([stops[r["id"]][0] for r in test]))
    out["halt_laps_by_depth"] = {d: float(np.mean([stops[r["id"]][0] for r in test if r["depth"] == d])) for d in sorted({r["depth"] for r in test})}
    onehot = lambda r: [0.0 if i != stops[r["id"]][1] else 1.0 for i in range(H.CHAINS)]  # noqa: E731
    out["H3_acc"] = paired(deep, onehot, lambda r: r["base"])
    dep = np.array([r["depth"] for r in test], float)
    lap = np.array([stops[r["id"]][0] for r in test], float)
    rho, lo, hi = SH.spearman_ci(dep, lap)
    out["H3_rho"] = dict(value=rho, lo=lo, hi=hi)
    ctl = sel.get("control")
    out["control"] = paired(deep, lambda r: r[ctl]["2"], lambda r: r["base"]) if ctl and deep and ctl in deep[0] else None
    rms = {"1": float(np.mean([r["base_rms"] for r in test]))}
    rms.update({str(k): float(np.mean([r[name + "_rms"][str(k)] for r in test])) for k in LAPS[1:]})
    if ctl and ctl + "_rms" in test[0]:
        rms["control 2"] = float(np.mean([r[ctl + "_rms"]["2"] for r in test]))
    out["rms_by_lap"] = rms
    return out


def outcome(res, sel):
    """The first matching outcome, in this order."""
    if not res["D"]:
        return "VOID (no depth has plain dev accuracy in [floor + 10, 80]: the bed does not fit this model)"
    if res["d1_base"] is None:
        return "NOT ENOUGH ROWS YET (no depth-1 test rows)"
    if not res["valid"]:
        return f"VOID (the plain model scores {res['d1_base']:.1f} < {V_SHALLOW:.0f} on depth 1: it cannot read the bed)"
    h1, h2 = res["H1"], res["H2"]
    if h1 is None:
        return "NOT ENOUGH ROWS YET (no test rows in D)"
    if h1["value"] < WRONG - EPS:
        return "PROVED WRONG (extra laps with no training do not add serial depth to this model)"
    if not (h1["value"] >= GAIN - EPS and h1["lo"] is not None and h1["lo"] > 0):
        return "NOT SHOWN"
    if h2 is not None and h2["value"] < -HARM - EPS:
        return "TRADE-OFF (deeper chains gain, shallow chains lose more than 2 points)"
    return "PASS"


NEXT = {
    "VOID": "rebuild the bed so the plain model has headroom (Addendum H revision, before any new run), then rerun",
    "NOT ENOUGH ROWS YET": "wait for the test stage to finish",
    "NO CANDIDATE": "stop this path",
    "PROVED WRONG": "no free extra laps for this model; the trained loop (Addendum G) is the only route",
    "NOT SHOWN": "no follow-up unless Addendum G passes",
    "TRADE-OFF": "check H3 before anything else",
    "PASS": "(1) same test at 4-bit (does the gain survive less quantization noise?), (2) a general-ability guard (MMLU-Pro, 300 items, "
            "no more than -2), (3) only then ask Ben about a think-harder mode in the assistant",
}


def adaptive_line(res):
    a, rho = res["H3_acc"], res["H3_rho"]
    acc_ok = a is not None and a["lo"] is not None and a["value"] >= GAIN - EPS and a["lo"] > 0
    rho_ok = rho["value"] is not None and rho["value"] >= RHO - EPS and rho["lo"] > 0
    return ("ADAPTIVE" if acc_ok and rho_ok else "NOT ADAPTIVE") + f" (halting gain {fmt(a)}; Spearman(depth, laps) {fmt_rho(rho)})"


def fmt(d):
    if d is None:
        return "n/a"
    ci = "" if d.get("lo") is None else f" [{d['lo']:+.2f}, {d['hi']:+.2f}]"
    return f"{d['value']:+.2f}{ci} (n={d['n']})"


def fmt_rho(r):
    return "n/a" if r["value"] is None else f"{r['value']:.3f} [{r['lo']:.3f}, {r['hi']:.3f}]"


def cmd_summarize(a):
    run = Path(a.run)
    lines = []
    sel = json.loads((run / "selection.json").read_text()) if (run / "selection.json").exists() else None
    if sel is None:
        print("no selection.json yet: the sweep has not finished")
        return 1
    lines.append(f"deep slice D (from plain dev accuracy in [{D_LO:.1f}, {D_HI:.0f}]): {sel['D']}")
    if sel["D"]:
        lines.append(f"C* = {sel['name']}: dev D {sel['dev_acc']:.2f} vs plain {sel['dev_base']:.2f} ({sel['dev_gain']:+.2f}); control {sel.get('control')}")
        lines.append("dev lap-2 accuracy on D by block: " + ", ".join(f"{k} {v:.1f}" for k, v in sorted(sel["table"].items(), key=lambda x: -x[1])))
    if not sel["D"]:
        oc = "VOID (no depth has plain dev accuracy in [floor + 10, 80]: the bed does not fit this model)"
        lines.append(f"OUTCOME: {oc}")
    elif sel.get("stopped"):
        oc = "NO CANDIDATE"
        lines.append(f"OUTCOME: {oc} (best dev gain {sel['dev_gain']:+.2f} < +{CAND_MIN:.0f})")
    else:
        test = read_jsonl(run / "test.jsonl")
        full = len(test) >= MAX_DEPTH * TEST_PER_DEPTH
        if not test or (not full and not a.partial):
            print(f"test has {len(test)} of {MAX_DEPTH * TEST_PER_DEPTH} rows (use --partial to look anyway)")
            return 1
        res = analyse(test, sel, sel["D"])
        oc = outcome(res, sel)
        lines.append(f"plain test accuracy by depth: " + ", ".join(f"{d}:{v:.0f}" for d, v in res["base_by_depth"].items()))
        for k, v in res["laps_by_depth"].items():
            lines.append(f"C* lap {k} by depth: " + ", ".join(f"{d}:{x:.0f}" for d, x in v.items()))
        lines.append(f"halting laps by depth: " + ", ".join(f"{d}:{x:.2f}" for d, x in res["halt_laps_by_depth"].items()))
        lines.append(f"H1 C* lap 2 - plain on D: {fmt(res['H1'])} (need >= +{GAIN:.0f}, CI > 0; proved wrong below +{WRONG:.0f})")
        h2 = fmt(res["H2"]) if res["H2"] else "not evaluable (no depth below D; counts as met)"
        lines.append(f"H2 C* lap 2 - plain below D: {h2} (need >= -{HARM:.0f})")
        lines.append(f"control lap 2 - plain on D: {fmt(res['control'])} (reported, no mark)")
        lines.append("hidden-state RMS at the last position, mean by lap (reported, no mark): "
                     + ", ".join(f"{k}: {v:.2f}" for k, v in res["rms_by_lap"].items()))
        judged = oc.startswith(("PASS", "TRADE-OFF"))
        lines.append("H3: " + (adaptive_line(res) if judged else "not judged (only after PASS or TRADE-OFF); " + adaptive_line(res).split(" (", 1)[1].rstrip(")")))
        if not full:
            oc = f"PARTIAL ({len(test)} of {MAX_DEPTH * TEST_PER_DEPTH} rows), not a result: {oc}"
        lines.append(f"OUTCOME: {oc}")
        if full:
            (run / "analysis.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    if oc.startswith("PARTIAL"):
        print("\n".join(lines))
        return 0
    lines.append("NEXT: " + NEXT[next(k for k in NEXT if oc.startswith(k))])
    text = "\n".join(lines)
    (run / "SUMMARY_laps.txt").write_text(text + "\n")
    print(text)
    return 0


# ---------------------------------------------------------------- run

def free_gb():
    import subprocess
    try:
        vm = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return None
    page = int(re.search(r"page size of (\d+)", vm).group(1))
    pages = sum(int(m) for m in re.findall(r"Pages (?:free|inactive|speculative|purgeable):\s+(\d+)", vm))
    return pages * page / 2 ** 30


def check_data(data):
    want = json.loads((Path(__file__).resolve().parent.parent / "results" / "laps" / "LAPS_REPORT.json").read_text())["files"]
    have = {s: H.sha(Path(data) / f"{s}.jsonl") for s in ("dev", "test")}
    if have != {s: want[s]["sha256"] for s in have}:
        raise SystemExit(f"data sha256 differs from backbone/results/laps/LAPS_REPORT.json: {have}")


def cmd_run(a, load=None):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    check_data(a.data)
    if load is None:
        gb, t0 = free_gb(), time.time()
        while gb is not None and gb < a.min_free_gb and getattr(a, "wait", False):
            if int(time.time() - t0) % 1800 < 60:
                print(f"waiting: {gb:.1f} GB free, need {a.min_free_gb:.0f}", flush=True)
            time.sleep(60)
            gb = free_gb()
        if gb is not None and gb < a.min_free_gb and not a.yes:
            raise SystemExit(f"only {gb:.1f} GB of memory is free; the model needs about {a.min_free_gb:.0f} GB (pass --yes to start anyway)")
        print(f"{gb} GB free; loading {a.model}", flush=True)
        from mlx_lm import load as mlx_load
        load = mlx_load
    model, tok = load(a.model)
    lp = Laps(model)
    blocks = lp.blocks()
    meta = dict(model=a.model, n_layers=lp.n, period=lp.period, blocks=[key(*b) for b in blocks], started=time.strftime("%FT%TZ", time.gmtime()))
    if (out / "meta.json").exists():
        old = json.loads((out / "meta.json").read_text())
        if any(old.get(k) != meta[k] for k in ("model", "n_layers", "period", "blocks")):
            raise SystemExit(f"{out} holds a run of another model or block list ({old.get('model')}): use a fresh --out")
    else:
        (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    dev, test = load_rows(a.data, "dev"), load_rows(a.data, "test")
    ok, report = self_check(model, tok, lp, dev + test, TOL)
    print(report, flush=True)
    if not ok:
        raise SystemExit("the layer-by-layer pass does not match this model's own forward: stopping before any row")

    calib = stage("calib", dev, out, lp, tok, lambda lp, E, cand: {})
    D = deep_slice(calib)
    print(f"[calib] plain dev accuracy by depth: {by_depth(calib, lambda r: r['base'])}; D = {D}", flush=True)
    if not D:
        (out / "selection.json").write_text(json.dumps(dict(D=[], name=None, dev_acc=0, dev_base=0, dev_gain=0, table={}, stopped=True)) + "\n")
        return cmd_summarize(argparse.Namespace(run=str(out), partial=False))

    sweep = stage("sweep", [r for r in dev if r["depth"] in D], out, lp, tok,
                  lambda lp, E, cand: {key(s, k): lp.laps(E, s, k, 2, cand) for s, k in blocks})
    sel = choose(sweep, blocks)
    ctl = control_block(tuple(sel["block"]), blocks)
    sel.update(D=D, control=key(*ctl) if ctl else None, stopped=sel["dev_gain"] < CAND_MIN - EPS)
    (out / "selection.json").write_text(json.dumps(sel, indent=1) + "\n")
    print(f"[sweep] C* = {sel['name']} dev gain {sel['dev_gain']:+.2f}; control {sel['control']}", flush=True)
    if sel["stopped"]:
        return cmd_summarize(argparse.Namespace(run=str(out), partial=False))

    s, k = sel["block"]
    rmax = max(LAPS)

    def test_extra(lp, E, cand):
        ex = {sel["name"]: lp.laps(E, s, k, rmax, cand)}
        if ctl:
            ex[sel["control"]] = lp.laps(E, ctl[0], ctl[1], 2, cand)
        return ex

    stage("test", test, out, lp, tok, test_extra)
    return cmd_summarize(argparse.Namespace(run=str(out), partial=False))


def self_check(model, tok, lp, rows, tol):
    """On the model about to be used: every place in the rows is one token; the layer-by-layer pass equals the model's own
    forward; and lap 2 of a middle block equals the model run with that block's layers listed twice. Guards against an mlx_lm
    whose internals differ from the ones the tests ran on. Returns (ok, report)."""
    mx = lp.mx
    for r in rows:
        cand_ids(tok, r["places"])
    tm, row = lp.tm, rows[0]
    ids, cand = prompt_ids(tok, row), cand_ids(tok, row["places"])

    def own(layers):
        orig = list(tm.layers)
        tm.layers = layers
        try:
            lg = model(mx.array([ids]))[0, -1].astype(mx.float32)
        finally:
            tm.layers = orig
        return (lg - mx.logsumexp(lg))[mx.array(cand)].tolist()

    t0 = time.time()
    E = lp.edges(ids)
    mine = lp.read(E[lp.n], cand)[0]
    t1 = time.time() - t0
    blocks = lp.blocks()
    s, k = blocks[len(blocks) // 2]
    lap2 = lp.laps(E, s, k, 2, cand)[2][0]
    orig = list(tm.layers)
    d1 = max(abs(x - y) for x, y in zip(mine, own(orig)))
    d2 = max(abs(x - y) for x, y in zip(lap2, own(orig[:s + k] + orig[s:s + k] + orig[s + k:])))
    ok = d1 < tol and d2 < tol
    return ok, (f"selftest: all {len(rows)} rows have one-token places; {len(ids)} prompt tokens, {lp.n} layers, period {lp.period}, "
                f"{len(blocks)} blocks, plain pass {t1:.2f} s; max |log-prob difference| plain {d1:.4f}, lap 2 of {key(s, k)} {d2:.4f} "
                f"(must be below {tol}): " + ("OK" if ok else "FAILED"))


def cmd_selftest(a, load=None):
    if load is None:
        from mlx_lm import load as mlx_load
        load = mlx_load
    check_data(a.data)
    model, tok = load(a.model)
    ok, report = self_check(model, tok, Laps(model), load_rows(a.data, "dev") + load_rows(a.data, "test"), a.tol)
    print(report, flush=True)
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("out")
    r = sub.add_parser("run")
    r.add_argument("--model", required=True)
    r.add_argument("--data", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--min-free-gb", type=float, default=20.0)
    r.add_argument("--yes", action="store_true")
    r.add_argument("--wait", action="store_true", help="wait (checking each minute) until --min-free-gb is free, then start")
    t = sub.add_parser("selftest")
    t.add_argument("--model", required=True)
    t.add_argument("--data", required=True)
    t.add_argument("--tol", type=float, default=TOL)
    s = sub.add_parser("summarize")
    s.add_argument("run")
    s.add_argument("--partial", action="store_true")
    a = ap.parse_args(argv)
    return {"build": cmd_build, "run": cmd_run, "selftest": cmd_selftest, "summarize": cmd_summarize}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
