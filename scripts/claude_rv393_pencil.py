#!/usr/bin/env python3
"""rv-393 (thought-memory thread, 2026-09-26): pencil marks. Can the loop net learn to doubt its own guesses?

Why: the going-back work (artifacts/claude-rv391-20260926/) found no signal that marks a wrong written guess: not the
net's own values (rv-391 dev, best AUC 0.53) and not a learned critic reading its state (PROVED WRONG on 358i's and on
rsn-358i2's nets: RESULTS-critic.md, RESULTS-critic-358i2.md). The rv-390 worker writes each guess as a GIVEN (slot 0),
and every given the net ever trained on was true, so it trusts whatever is written. Plan and marks:
artifacts/claude-rv393-20260926/PLAN.md.

The one change: a guess is a PENCIL MARK (the symbol goes into the answer cell, whose slot stays 1, so the net can tell
it from a given; no new weights), and the net is fine-tuned on pages from its own GUESS runs with the pencil marks in,
the true solution as the target (Stream of Search, arXiv 2404.03683: train on your own search, dead ends included).
Arms, per rsn-358i2 net (identical steps, puzzles, rounds and random draws; only the replayed pages differ):
  pencil  replayed trace pages carry the marks as pencil marks
  clean   the same replayed puzzles and rounds with no marks (controls for the extra 7x7 practice itself)
  orig    the untouched net, measured the same way
Traces: rv-390's GUESS as it is (guesses written as givens; 96 rounds; run as rv391_critic.states runs it) on fresh
code-made TRAINING 7x7 puzzles that the 48-round day pass leaves unfinished. Replay keeps h across page changes, as the
worker does: segment m (rounds 8m-7..8m) shows the marks written at checks before m, and the last k rounds (1..6) of
segment j are graded. Loss = 358's (cross-entropy at every answer cell against the true solution, plus 0.5 x the stop
head's BCE). Half the steps are 358's usual practice stream instead (fresh draws, the same in both arms).
Measure: pencil GUESS (the worker's rule; marks stay pencil marks; h carried; never goes back), 96 rounds, on fresh
PRACTICE 7x7 puzzles that the day pass leaves unfinished. Each mark is judged at the first check round after it is
written: "overruled" = the net's top symbol among the puzzle's names differs from the mark. Page score = 1 - the lowest
probability the net gives any mark on the page (dead-page AUC against count-only, as in rv-391 dev 2).
Disclosed code parts: the checker, the worker's when/where rule and its row/column candidate skip (rv-387).

  python -B scripts/claude_rv393_pencil.py make-data --out artifacts/claude-rv393-20260926/data
  python -B scripts/claude_rv393_pencil.py selftest
  python -B scripts/claude_rv393_pencil.py all --ckpt F --seed S --wdir WEIGHTS_DIR --out RESULTS_DIR
  python -B scripts/claude_rv393_pencil.py smoke --ckpt UNTRAINED_NET --out SCRATCH   (CPU wiring check; no test puzzle)
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import claude_rv390 as W  # noqa: E402  (rv-390's worker: rv-387's GUESS, the day pass)
import claude_rv391_critic as C  # noqa: E402  (auc(), the reserved puzzle folders)

_, R, E = W.mods()                        # 358i's net code: legend grids, half-narrow heads, v2 stop rule
import claude_rsn358i2_run as I2  # noqa: E402  (autocast weight cache OFF: the 358i2 repair; patches torch.autocast)

V = W.V
TRACE_SET = ("tr-grids7", 7, 39331, 4000)       # (name, size, seed, n) training puzzles for the traces
PRACTICE_SET = ("pp-grids7", 7, 39334, 1000)    # practice puzzles for the marks
REPORT_SET = "p-grids7"                          # rv-390's practice 7x7 (report only; the critic's set)
DATA_DIR = ROOT / "artifacts/claude-rv393-20260926/data"
RESERVED = C.RESERVED + [C.TRAIN_DIR]            # 358i tests, rv-390 and rv-392 day + practice, rv-391 critic train
ROUNDS = 96
SEG = V.CHECK_EVERY                              # 8: the worker checks every 8th round, so pages change only then
STEPS, BATCH, LR, WARMUP, MIX, GRAD_ROUNDS = 3000, 128, 1e-4, 100, 0.5, 6
STREAM_OFFSET = 50                               # usual practice stream seed = net seed + 50 (fresh draws)
NO_HARM = ["grids6", "grids7", "sums6"]
ARMS = ["pencil", "clean"]


# ---------------- puzzles ----------------
def reserved_keys(dirs):
    keys = set()
    for d in dirs:
        for f in sorted(Path(d).glob("*.jsonl")):
            for line in f.read_text().splitlines():
                keys.add(json.dumps(json.loads(line)["tokens"]))
    return keys


def make_data(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    seen = reserved_keys(RESERVED)
    report = {"reserved_items": len(seen)}
    for name, size, seed, n in (TRACE_SET, PRACTICE_SET):
        kept, clash = [], 0
        for it in W.make_items(E, "grids", size, seed, n):
            k = json.dumps(it.tokens)
            if k in seen:
                clash += 1
                continue
            seen.add(k)                          # no repeats inside a set, and practice never repeats a trace puzzle
            kept.append(it)
        (out / f"{name}.jsonl").write_text("".join(json.dumps(R.item_to_json(i)) + "\n" for i in kept))
        report[name] = {"seed": seed, "made": n, "kept": len(kept), "dropped_as_reserved_or_repeat": clash}
        print(name, report[name], flush=True)
    (out / "make-data.json").write_text(json.dumps(report, indent=1) + "\n")


# ---------------- traces (the untouched net's own GUESS runs) ----------------
@torch.no_grad()
def trace(w, it, rounds=ROUNDS):
    """rv-390's GUESS on one puzzle, run exactly as rv391_critic.states runs it (guesses written as givens).
    Returns the guesses [(check, r, c, tok)] and the checks at which the page held at least one guess."""
    net = w.net
    names = [E.SYM + n for n in it.meta["names"]]
    page = W.AnyPage(it, E)
    e, (dr, dc) = w.embed(page)
    h = torch.zeros_like(e)
    guesses, checks, since, check = [], [], 0, 0
    for _ in range(rounds):
        h = net.step(h, e, dr, dc)
        lg, qq = net.read(h)
        q = float(torch.sigmoid(qq.float())[0])
        if E.check(it, w.final(page, lg[0].argmax(-1).tolist())):
            break
        since += 1
        if since < SEG:
            continue
        since = 0
        check += 1
        if page.written:
            checks.append(check)
        if q >= V.CUT:
            continue
        cell, cands = w.pick(page, lg[0], names)
        if cell is None:
            continue
        page.write(*cell, cands[0])
        guesses.append([check, cell[0], cell[1], cands[0]])
        e, (dr, dc) = w.embed(page)
    return guesses, checks


def make_traces(net, items, dev):
    w = W.Worker(net, E, dev)
    day = W.day_pass(net, R, E, items, dev)
    out = []
    for i, (it, d) in enumerate(zip(items, day)):
        if d["right"]:
            continue
        g, ch = trace(w, it)
        if ch:
            out.append({"item": i, "guesses": g, "checks": ch,
                        "dead_at": [int(any(tok != it.target[r][c] for gg, r, c, tok in g if gg < j)) for j in ch]})
    return out, sum(not d["right"] for d in day)


# ---------------- fine-tune ----------------
class Replay:
    """Draws for replay batches: a check j (from the pool of trace states) and B traces that have a state at j."""

    def __init__(self, traces, seed):
        self.rng = random.Random(9400 + seed)
        self.pool = [(n, j) for n, tr in enumerate(traces) for j in tr["checks"]]
        self.by_j = {}
        for n, j in self.pool:
            self.by_j.setdefault(j, []).append(n)

    def draw(self, B):
        _, j = self.rng.choice(self.pool)
        return [self.rng.choice(self.by_j[j]) for _ in range(B)], j


def pages(items, traces, rows, j, arm):
    """token tensors for segments 1..j. pencil: a mark written at check g shows from segment g+1 on (slot stays 1).
    clean: the bare puzzle in every segment."""
    base = torch.tensor([items[traces[n]["item"]].tokens for n in rows])
    segs = []
    for m in range(1, j + 1):
        t = base.clone()
        if arm == "pencil":
            for b, n in enumerate(rows):
                for g, r, c, tok in traces[n]["guesses"]:
                    if g < m:
                        t[b, r, c] = tok
        segs.append(t)
    return segs


def replay_outs(net, segs, s, env, k):
    """h carried across the page changes, as the worker does; only the last k rounds are graded."""
    free, n, h, outs = SEG * len(segs) - k, 0, None, []
    for t in segs:
        e, (dr, dc) = net.embed(t, s, env)
        if h is None:
            h = torch.zeros_like(e)
        for _ in range(SEG):
            n += 1
            if n <= free:
                with torch.no_grad():
                    h = net.step(h, e.detach(), dr, dc)
            else:
                h = net.step(h, e, dr, dc)
                outs.append(net.read(h))
    return outs


def loss_of(outs, s, y):
    ces, hls = [], []
    for lg, q in outs:
        c_, ex = R.ce_and_exact(lg, s, y)
        ces.append(c_)
        hls.append(F.binary_cross_entropy_with_logits(q.float(), ex))
    return torch.stack(ces).mean() + 0.5 * torch.stack(hls).mean(), torch.stack(ces).mean(), ex


def block_mats(net):
    return [p for n, p in net.named_parameters() if n.startswith("blocks.") and p.dim() == 2
            and not n.endswith((".br", ".bc"))]


def finetune(a, arm, items, traces, dev, wout, log_path):
    torch.manual_seed(a.seed)
    net = R.load(a.ckpt, dev)
    net.train()
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / a.warmup) * 0.5 *
                                              (1 + math.cos(math.pi * min(i, a.steps) / a.steps)))
    t0 = time.time()
    src = R.Source(a.seed + STREAM_OFFSET, latin_pool=a.latin_pool)
    rep = Replay(traces, a.seed)
    mix_rng, round_rng = random.Random(9300 + a.seed), random.Random(9500 + a.seed)
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if dev == "cuda" else torch.autocast("cpu", enabled=False)
    mats, nograd = block_mats(net), 0
    run = {"replay": [0.0, 0.0, 0], "usual": [0.0, 0.0, 0]}
    log = open(log_path, "w", encoding="utf-8")
    for step in range(1, a.steps + 1):
        if mix_rng.random() < MIX:
            kind = "replay"
            rows, j = rep.draw(a.batch)
            t, s, y, env = R.tensors([items[traces[n]["item"]] for n in rows], dev)
            segs = [x.to(dev) for x in pages(items, traces, rows, j, arm)]
            k = round_rng.randint(1, GRAD_ROUNDS)
            with amp:
                loss, ce, ex = loss_of(replay_outs(net, segs, s, env, k), s, y)
        else:
            kind = "usual"
            t, s, y, env = R.tensors(src.batch(a.batch), dev)
            total = round_rng.randint(1, R.TRAIN_ROUNDS)
            k = round_rng.randint(1, min(total, R.GRAD_ROUNDS))
            with amp:
                loss, ce, ex = loss_of(net.loop_train(t, s, env, total - k, k), s, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        nograd += any(p.grad is None or not bool(p.grad.detach().abs().sum()) for p in mats)
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
        sched.step()
        rk = run[kind]
        rk[0] += ce.item(); rk[1] += ex.mean().item(); rk[2] += 1
        if step % a.log_every == 0 or step == a.steps:
            rec = {"step": step, "min": round((time.time() - t0) / 60, 2), "lr": sched.get_last_lr()[0],
                   "steps_block_nograd": nograd,
                   **{f"{kk}_ce": round(v[0] / v[2], 4) for kk, v in run.items() if v[2]},
                   **{f"{kk}_exact": round(v[1] / v[2], 4) for kk, v in run.items() if v[2]}}
            log.write(json.dumps(rec) + "\n"); log.flush()
            print(arm, json.dumps(rec), flush=True)
            run = {"replay": [0.0, 0.0, 0], "usual": [0.0, 0.0, 0]}
    log.close()
    wout.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"arm": "loop", "seed": a.seed, "rv393": arm, "state": net.state_dict()}, wout)
    return {"arm": arm, "steps": a.steps, "batch": a.batch, "lr": a.lr, "warmup": a.warmup, "mix": MIX,
            "steps_block_nograd": nograd, "minutes": round((time.time() - t0) / 60, 1), "torch": torch.__version__,
            "autocast_cache_off": torch.autocast is I2.NoCacheAutocast, "device": dev,
            "trace_states": len(rep.pool), "weights_sha256": weights_sha(net)}


def weights_sha(net):
    import hashlib
    hs = hashlib.sha256()
    for k, v in sorted(net.state_dict().items()):
        hs.update(k.encode()); hs.update(v.detach().float().cpu().numpy().tobytes())
    return hs.hexdigest()


# ---------------- measure (pencil GUESS, never goes back) ----------------
class PencilPage(W.AnyPage):
    """a guess stays an answer cell (slot 1) that holds the guessed symbol: a pencil mark, not a given."""

    def copy(self):
        p = PencilPage.__new__(PencilPage)
        p.it, p.E = self.it, self.E
        p.tokens, p.slot, p.written = [r[:] for r in self.tokens], [r[:] for r in self.slot], dict(self.written)
        return p

    def write(self, r, c, tok):
        assert self.it.slot[r][c] == 1 and (r, c) not in self.written
        self.tokens[r][c] = tok
        self.written[(r, c)] = tok


@torch.no_grad()
def pencil_run(w, it, rounds=ROUNDS):
    net = w.net
    names = [E.SYM + n for n in it.meta["names"]]
    Wd = len(it.tokens[0])
    page = PencilPage(it, E)
    e, (dr, dc) = w.embed(page)
    h = torch.zeros_like(e)
    states, judged, fresh, since, check, solved = [], [], [], 0, 0, False
    for _ in range(rounds):
        h = net.step(h, e, dr, dc)
        lg, qq = net.read(h)
        q = float(torch.sigmoid(qq.float())[0])
        if E.check(it, w.final(page, lg[0].argmax(-1).tolist())):
            solved = True
            break
        since += 1
        if since < SEG:
            continue
        since = 0
        check += 1
        if page.written:
            cells = list(page.written.items())
            idx = torch.tensor([r * Wd + c for (r, c), _ in cells], device=lg.device)
            p = torch.softmax(lg[0, idx][:, names].float(), -1)
            pos = torch.tensor([names.index(tok) for _, tok in cells], device=lg.device)
            pm = p[torch.arange(len(cells), device=lg.device), pos].tolist()
            top = [names[j] for j in p.argmax(-1).tolist()]
            right = [int(tok == it.target[r][c]) for (r, c), tok in cells]
            over = [int(top[n] != tok) for n, (_, tok) in enumerate(cells)]
            states.append({"check": check, "k": len(cells), "dead": int(not all(right)), "score": round(1 - min(pm), 6),
                           "wrong": right.count(0), "wrong_over": sum(o for o, rr in zip(over, right) if not rr),
                           "right": sum(right), "right_over": sum(o for o, rr in zip(over, right) if rr)})
            for n, ((r, c), tok) in enumerate(cells):
                if (r, c) in fresh:
                    judged.append({"check": check, "right": right[n], "over": over[n], "p": round(pm[n], 6)})
            fresh = []
        if q >= V.CUT:
            continue
        cell, cands = w.pick(page, lg[0], names)
        if cell is None:
            continue
        page.write(*cell, cands[0])
        fresh.append(cell)
        e, (dr, dc) = w.embed(page)
    return {"solved": solved, "states": states, "judged": judged, "unjudged": len(fresh), "marks": len(page.written)}


def rate(x, n):
    return None if not n else round(x / n, 4)


def measure(net, items, dev, name):
    w = W.Worker(net, E, dev)
    day = W.day_pass(net, R, E, items, dev)
    rows_s, rows_j, solved, unjudged, unf = [], [], 0, 0, 0
    for i, (it, d) in enumerate(zip(items, day)):
        if d["right"]:
            continue
        unf += 1
        r = pencil_run(w, it)
        solved += r["solved"]
        unjudged += r["unjudged"]
        rows_s += [dict(s, set=name, item=i) for s in r["states"]]
        rows_j += [dict(j, set=name, item=i) for j in r["judged"]]
    wj = [j for j in rows_j if not j["right"]]
    rj = [j for j in rows_j if j["right"]]
    pos, neg = C.split([s["score"] for s in rows_s], [s["dead"] for s in rows_s])
    kp, kn = C.split([float(s["k"]) for s in rows_s], [s["dead"] for s in rows_s])
    rec = {"n": len(items), "day_right": len(items) - unf, "unfinished": unf, "pencil_solved": solved,
           "states": len(rows_s), "dead": len(pos), "auc": C.auc(pos, neg), "auc_count_only": C.auc(kp, kn),
           "wrong_judged": len(wj), "wrong_over": sum(j["over"] for j in wj), "wrong_over_rate": rate(sum(j["over"] for j in wj), len(wj)),
           "right_judged": len(rj), "right_over": sum(j["over"] for j in rj), "right_over_rate": rate(sum(j["over"] for j in rj), len(rj)),
           "unjudged": unjudged}
    return rec, rows_s, rows_j


def no_harm(net, tests, dev):
    return {n: R.evaluate(net, tests[n], dev)["right"] for n in tests}


# ---------------- the job, per net ----------------
def load_items(d, name, limit=None):
    return [R.item_from_json(json.loads(l)) for l in (Path(d) / f"{name}.jsonl").read_text().splitlines()[:limit]]


def all_(a):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    out, wdir = Path(a.out), Path(a.wdir)
    out.mkdir(parents=True, exist_ok=True)
    t00 = time.time()
    tag = f"s{a.seed}"
    tr_items = load_items(a.data, TRACE_SET[0], a.n_trace)
    pr_items = {PRACTICE_SET[0]: load_items(a.data, PRACTICE_SET[0], a.n_practice),
                REPORT_SET: load_items(a.report_dir, REPORT_SET, a.n_practice)}
    tests = {n: load_items(a.tests, n, a.limit_tests) for n in NO_HARM}
    info = {"ckpt": str(a.ckpt), "sha256": V.sha256(a.ckpt), "seed": a.seed, "device": dev, "torch": torch.__version__,
            "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0) if dev == "cuda" else None,
            "tests": str(a.tests), "trace_puzzles": len(tr_items)}
    orig = R.load(a.ckpt, dev).eval()
    info["orig_weights_sha256"] = weights_sha(orig)
    # 1. traces from the untouched net
    f = out / f"trace-{tag}.jsonl"
    if f.exists():
        traces = [json.loads(l) for l in f.read_text().splitlines()]
    else:
        t0 = time.time()
        traces, unf = make_traces(orig, tr_items, dev)
        f.write_text("".join(json.dumps(x) + "\n" for x in traces))
        info["trace"] = {"unfinished": unf, "traced": len(traces), "states": sum(len(x["checks"]) for x in traces),
                         "dead_states": sum(sum(x["dead_at"]) for x in traces), "min": round((time.time() - t0) / 60, 1)}
        print("trace", json.dumps(info["trace"]), flush=True)
    (out / f"info-{tag}.json").write_text(json.dumps(info, indent=1) + "\n")
    # 2. measure the untouched net; 3. fine-tune and measure each arm; 4. no-harm tests for all three
    nets = {"orig": orig}
    for arm in ["orig"] + ARMS:
        mf = out / f"measure-{arm}-{tag}.json"
        if arm != "orig":
            wf = wdir / f"rv393-{arm}-{tag}" / "final.pt"
            if not wf.exists():
                summ = finetune(a, arm, tr_items, traces, dev, wf, out / f"trainlog-{arm}-{tag}.jsonl")
                (out / f"train-{arm}-{tag}.json").write_text(json.dumps(summ, indent=1) + "\n")
            nets[arm] = R.load(wf, dev).eval()
        if mf.exists():
            continue
        t0 = time.time()
        res, rows = {"arm": arm, "sets": {}}, []
        for name, its in pr_items.items():
            rec, rs, rj = measure(nets[arm], its, dev, name)
            res["sets"][name] = rec
            rows += [dict(x, row="state") for x in rs] + [dict(x, row="mark") for x in rj]
            print(arm, name, json.dumps(rec), flush=True)
        res["min"] = round((time.time() - t0) / 60, 1)
        mf.write_text(json.dumps(res, indent=1) + "\n")
        mf.with_suffix(".rows.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
    nf = out / f"noharm-{tag}.json"
    if not nf.exists():
        res = {arm: no_harm(net, tests, dev) for arm, net in nets.items()}
        nf.write_text(json.dumps(res, indent=1) + "\n")
        print("noharm", json.dumps(res), flush=True)
    print(f"all done {tag}: {round((time.time() - t00) / 60, 1)} min", flush=True)


# ---------------- checks ----------------
def selftest():
    assert torch.autocast is I2.NoCacheAutocast
    rng = random.Random(0)
    it = E.latin_item(rng, *E.make_latin_base(rng, 5))
    open_ = [(r, c) for r in range(5) for c in range(5) if it.slot[r][c] == 1]
    (r1, c1), (r2, c2) = open_[:2]
    wrong = next(E.SYM + n for n in it.meta["names"] if E.SYM + n != it.target[r1][c1])
    pp, gp = PencilPage(it, E), W.AnyPage(it, E)
    pp.write(r1, c1, wrong)
    gp.write(r1, c1, wrong)
    assert pp.slot[r1][c1] == 1 and pp.tokens[r1][c1] == wrong and (r1, c1) not in pp.open_cells()
    assert gp.slot[r1][c1] == 0 and gp.tokens[r1][c1] == wrong
    assert it.tokens[r1][c1] == E.MASK and it.slot[r1][c1] == 1        # the item itself is untouched
    # replay pages: a mark written at check g shows from segment g+1; clean never shows it
    tr = [{"item": 0, "guesses": [[1, r1, c1, wrong], [3, r2, c2, it.target[r2][c2]]], "checks": [2, 3, 4]}]
    P, Cl = pages([it], tr, [0], 4, "pencil"), pages([it], tr, [0], 4, "clean")
    base = torch.tensor([it.tokens])
    assert torch.equal(P[0], base) and all(torch.equal(x, base) for x in Cl)
    assert P[1][0, r1, c1] == wrong and P[2][0, r2, c2] == E.MASK and P[3][0, r2, c2] == it.target[r2][c2]
    assert int((P[3] != Cl[3]).sum()) == 2 and int((P[1] != Cl[1]).sum()) == 1
    # graded rounds after free rounds under bf16 autocast (cache off): every block weight gets a gradient
    torch.manual_seed(0)
    net = R.Net("loop")
    t, s, y, env = R.tensors([it, it], "cpu")
    segs = pages([it, it], tr * 2, [0, 1], 4, "pencil")
    with torch.autocast("cpu", dtype=torch.bfloat16):
        outs = replay_outs(net, segs, s, env, 3)
        loss = loss_of(outs, s, y)[0]
    loss.backward()
    assert len(outs) == 3
    none = sum(p.grad is None or not bool(p.grad.abs().sum()) for p in block_mats(net))
    assert len(block_mats(net)) == 8 and none == 0, none
    # the trace pool draws only states that exist
    rep = Replay(tr, 0)
    assert sorted(rep.pool) == [(0, 2), (0, 3), (0, 4)] and rep.draw(5)[0] == [0] * 5
    print(f"selftest ok: torch {torch.__version__}, cache off, pencil marks keep slot 1, replay pages right, "
          f"0/8 block weights without gradient after 29 free + 3 graded rounds")


def smoke(a):
    """wiring check on an untrained net, CPU, tiny sizes. The no-harm step reads fresh dev puzzles, never a test."""
    out = Path(a.out)
    dev_tests = out / "devtests"
    dev_tests.mkdir(parents=True, exist_ok=True)
    for name, env, size, seed, _ in R.TESTS:
        if name in NO_HARM:                      # fresh seeds (test seed + 50000), never the test files
            its = R.make_test(name, env, size, seed + 50000, n=6)
            (dev_tests / f"{name}.jsonl").write_text("".join(json.dumps(R.item_to_json(i)) + "\n" for i in its))
    ns = argparse.Namespace(ckpt=a.ckpt, seed=1, out=out / "res", wdir=out / "w", data=a.data, report_dir=a.report_dir,
                            tests=dev_tests, limit_tests=6, n_trace=12, n_practice=10, steps=4, batch=4,
                            lr=LR, warmup=2, latin_pool=20, log_every=2)
    all_(ns)
    print("smoke ok", out)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("make-data"); p.add_argument("--out", default=str(DATA_DIR))
    sub.add_parser("selftest")
    for name in ("all", "smoke"):
        p = sub.add_parser(name)
        p.add_argument("--ckpt", required=True); p.add_argument("--out", required=True)
        p.add_argument("--data", default=str(DATA_DIR)); p.add_argument("--report-dir", default=str(C.RV390_DAY))
        if name == "all":
            p.add_argument("--seed", type=int, required=True); p.add_argument("--wdir", required=True)
            p.add_argument("--tests", default=str(W.RESERVED_TEST_DIR)); p.add_argument("--limit-tests", type=int, default=None)
            p.add_argument("--n-trace", type=int, default=None); p.add_argument("--n-practice", type=int, default=None)
            p.add_argument("--steps", type=int, default=STEPS); p.add_argument("--batch", type=int, default=BATCH)
            p.add_argument("--lr", type=float, default=LR); p.add_argument("--warmup", type=int, default=WARMUP)
            p.add_argument("--latin-pool", type=int, default=20000); p.add_argument("--log-every", type=int, default=100)
    a = ap.parse_args()
    if a.cmd == "make-data":
        make_data(a)
    elif a.cmd == "selftest":
        selftest()
    elif a.cmd == "all":
        all_(a)
    else:
        smoke(a)


if __name__ == "__main__":
    main()
