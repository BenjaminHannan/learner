"""P0 checkpoint diagnostics (codi-plan section 3.5 rows 1-3, 5, 6; section 6 P0) on a trained tj / tf checkpoint. No training, CPU or GPU.

    python backbone/think/p0_ckpt.py --ckpt out/think/tj_s0 --data out/data --device cpu --limit 200 --out p0_tj_s0.json

--ckpt is the arm's output dir: adapter/ (LoRA) and think_block.pt, exactly as think1.py saves them (--adapter / --block override the two paths).
Readings, all on the first --limit validation rows (N), written to one JSON:
  wiring    answer logits (teacher-forced, true answer tokens) with every gate forced to 0.5 vs every gate 0, max |dlogit|; rule: <= 1e-3 is a wiring bug (row 1)
  gates     mean |tanh a| over the 6 x heads gates (row 2)
  drift     ||theta_end - theta_start|| / ||theta_start|| per board parameter group; theta_start is the block re-created with torch.manual_seed(seed) and
            ThinkBoard.from_model(..., alpha_init), the call think1.run_arm makes. If two such builds differ, drift is skipped and the JSON says so (row 3)
  notes     variance of the final notes across rows / across stories, over the mean squared note value (row 5); per-lap change ||n(k)-n(k-1)|| / ||n(k-1)||, k = 1..lmax (row 6)
  blind     arm tf only (or --blind on): blind-pass greedy accuracy with the true notes, with zeroed notes, with swapped notes (row of another story, same depth)
  bridge    TODO (row 7, needs the gold-line entity labels and a 3,000-row fit/test split); not run here.
The numbers carry a "rules" block that restates each fixed rule of section 3.5 as true / false; the routing itself stays Ben's.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import train as T  # noqa: E402
import board as B  # noqa: E402
import think1 as K  # noqa: E402

WIRING_GATE = 0.5  # the forced value of tanh(a) in the wiring reading
BOARD_PARTS = ("alpha", "e0_hat", "eta", "w_in", "blocks", "norm", "w_out")  # top-level board parameters / modules, for the drift table


def load_ckpt(args, device, dtype):
    """Model + frozen LoRA adapter + trained board, rebuilt the way think1.run_arm builds them. Returns (runner, board, tok, meta)."""
    from peft import PeftModel
    ckpt = Path(args.ckpt)
    blk = torch.load(Path(args.block) if args.block else ckpt / "think_block.pt", map_location="cpu")
    res = next(iter(ckpt.glob("result_*.json")), None)
    res = json.loads(res.read_text()) if res else {}
    meta = dict(arm=blk.get("arm"), seed=blk["seed"] if args.seed is None else args.seed, K=blk["K"],
                alpha_init=args.alpha_init if args.alpha_init is not None else blk.get("alpha_init", res.get("alpha_init", 0.0)),
                lmax=args.lmax or res.get("lmax") or 4, result_json=bool(res))
    lm, tok = T.load_model(argparse.Namespace(smoke=args.smoke, seed=meta["seed"], model=args.model), device, dtype)
    pm = PeftModel.from_pretrained(lm, str(Path(args.adapter) if args.adapter else ckpt / "adapter"))  # frozen, as think1's t arm loads a
    for q in pm.parameters():
        q.requires_grad_(False)
    pm.eval()
    runner = T.Runner(pm.base_model.model, loops=1)
    torch.manual_seed(meta["seed"])
    board = B.ThinkBoard.from_model(runner.lm, tok, K=meta["K"], alpha_init=meta["alpha_init"]).to(device)
    start = {k: v.detach().clone() for k, v in board.state_dict().items()}
    board.load_state_dict(blk["state_dict"])
    board.eval()
    return runner, board, tok, meta, start


# ---------------------------------------------------------------- readings that need no data

def gate_reading(board):
    g = board.gate().detach().abs()
    return dict(mean_abs_tanh=float(g.mean()), per_layer=[round(float(x), 5) for x in g.mean(1)], max=float(g.max()), min=float(g.min()))


def fresh_start(args, lm_runner, tok, meta, device):
    """A second, independent build of theta_start; True if it equals the first bitwise (the init is deterministic given the seed)."""
    torch.manual_seed(meta["seed"])
    return B.ThinkBoard.from_model(lm_runner.lm, tok, K=meta["K"], alpha_init=meta["alpha_init"]).to(device)


def drift_reading(board, start, again):
    """Relative drift per parameter / module, and per think1 optimizer group (alpha, e0eta, refiner). start / again: two state dicts of independent builds."""
    if not all(torch.equal(start[k], again.state_dict()[k]) for k in start):
        return dict(skipped="theta_start is not deterministic given the seed: two builds with the same seed differ")
    end = board.state_dict()
    if not torch.equal(start["rho"], end["rho"]):
        return dict(skipped=f"rho differs between the re-created start ({float(start['rho'])}) and the checkpoint ({float(end['rho'])}): different base weights or code path")

    def rel(keys):
        a = torch.cat([start[k].flatten().float() for k in keys])
        b = torch.cat([end[k].flatten().float() for k in keys])
        n0 = float(a.norm())
        return dict(start_norm=n0, delta_norm=float((b - a).norm()), rel=float((b - a).norm()) / n0 if n0 > 0 else None)

    parts = {p: rel([k for k in start if k == p or k.startswith(p + ".")]) for p in BOARD_PARTS}
    groups = {g["name"]: rel([n for n, q in board.named_parameters() if any(q is x for x in g["params"])]) for g in K.board_groups(board)}
    return dict(parts=parts, groups=groups, refiner_rel=groups["refiner"]["rel"])


# ---------------------------------------------------------------- readings that run the model

def batches_of(prompts, args):
    """Index chunks in descending prompt length (as eval_board does), each within --eval-bsz rows and --eval-tokens tokens."""
    order = sorted(range(len(prompts)), key=lambda i: -len(prompts[i]))
    k = 0
    while k < len(order):
        n = max(1, min(args.eval_bsz, args.eval_tokens // len(prompts[order[k]])))
        yield order[k:k + n]
        k += n


@torch.no_grad()
def model_readings(runner, board, enc, rows, meta, args, device):
    """One prefill + think() per batch: the wiring reading, every lap's notes (kept on the CPU), and (if wanted) the true slot K/V of the last lap."""
    L, n = meta["lmax"], len(rows)
    prompts = [enc.prompt(r)[0] for r in rows]
    answers = [enc.ids(" " + r["answer"]) + [enc.eos] for r in rows]
    on, off = torch.full_like(board.alpha, WIRING_GATE), torch.zeros_like(board.alpha)
    notes, kv_rows, dmax, dsum, dcnt = [None] * (L + 1), [None] * n, 0.0, 0.0, 0
    t0 = time.time()
    for ids in batches_of(prompts, args):
        ps = [prompts[i] for i in ids]
        C, mask, p = B.prefill(runner, ps)
        lt = B.last_ids(ps, device)
        kv, st = B.think(board, runner, C, mask, p, L, keep={L}, stats=False)
        ans = [answers[i] for i in ids]
        lo = B.answer_logits(runner, on, C, mask, p, lt, ans, kv[L])[0]
        lz = B.answer_logits(runner, off, C, mask, p, lt, ans, kv[L])[0]
        d = (lo - lz).abs()
        dmax, dsum, dcnt = max(dmax, float(d.max())), dsum + float(d.sum()), dcnt + d.numel()
        for t, e in enumerate(st["e"]):
            if notes[t] is None:
                notes[t] = torch.zeros(n, *e.shape[1:])
            notes[t][ids] = B.f32(e).cpu()
        if args.blind_on:
            for j, i in enumerate(ids):
                kv_rows[i] = [(k[j].cpu(), v[j].cpu()) for k, v in kv[L]]
        print(f"[p0] batch of {len(ids)} rows done {time.time() - t0:.0f}s", flush=True)
    wiring = dict(gate=WIRING_GATE, rows=n, max_abs_dlogit=dmax, mean_abs_dlogit=dsum / max(dcnt, 1), bug=dmax <= 1e-3)
    return wiring, notes, kv_rows, prompts


def notes_reading(notes, rows):
    """notes[t]: [N, K, d] board after lap t. Story-dependence of the final board and the per-lap change."""
    fin = notes[-1]
    msq = float(fin.pow(2).mean())
    across_rows = float((fin - fin.mean(0)).pow(2).mean())
    story = [r.get("visit_id", i) for i, r in enumerate(rows)]  # a row with no visit_id is its own story
    ids = sorted(set(story), key=story.index)
    out = dict(rows=len(rows), stories=len(ids), mean_sq_note=msq, var_across_rows=across_rows, ratio_across_rows=across_rows / msq if msq else None)
    if len(ids) > 1:  # between stories: the variance of the per-story mean board (rows of one story differ only by their question)
        means = torch.stack([fin[[i for i, s in enumerate(story) if s == v]].mean(0) for v in ids])
        out["var_across_stories"] = float((means - means.mean(0)).pow(2).mean())
        out["ratio_across_stories"] = out["var_across_stories"] / msq if msq else None
    else:
        out["ratio_across_stories"] = None
    flat = lambda x: x.flatten(1)
    ch = [(flat(notes[k] - notes[k - 1]).norm(dim=1) / flat(notes[k - 1]).norm(dim=1).clamp(min=1e-12)).mean().item() for k in range(1, len(notes))]
    out["lap_change"] = dict(first_lap=1, values=ch)  # values[i] = change into lap i + 1
    return out


def swap_partners(rows):
    """For each row the nearest following row (cyclic) with the same depth and another story; if none, the nearest of the same depth; None if it is alone at its depth.
    Returns (partner list, number of rows whose partner is from the same story)."""
    n, out, same = len(rows), [], 0
    for i, r in enumerate(rows):
        cand = [(i + s) % n for s in range(1, n)]
        same_d = [j for j in cand if rows[j].get("depth") == r.get("depth")]
        j = next((j for j in same_d if rows[j].get("visit_id") != r.get("visit_id") or r.get("visit_id") is None), None)
        if j is None and same_d:
            j, same = same_d[0], same + 1
        out.append(j)
    return out, same


@torch.no_grad()
def blind_reading(runner, board, enc, rows, prompts, kv_rows, args, device):
    """Greedy blind-pass accuracy (the answer sees no prompt: B.decode(blind=True)) under three kinds of notes, on the same rows:
      true      the row's own last-lap slot K/V
      zeroed    slot K/V of all-zero notes on an empty cache (B.zero_notes_kv): the literal 'notes = 0' with the gates on. On the prompt's own cache the zero
                slots would still pick the story up through attention, so the story is removed. Expect it to equal gates_off (zero in, zero out through
                every layer), which is also run, with the true K/V and the gates forced to 0, as a check.
      swapped   the last-lap slot K/V of another row of the same depth (another story if there is one); rows with no partner are left out of 'swapped_n'."""
    n = len(rows)
    partner, same_story = swap_partners(rows)
    kinds = dict(true=list(range(n)), swapped=[j if j is not None else i for i, j in enumerate(partner)], zeroed=None, gates_off=None)  # no partner: own notes, scored out
    hits = {k: ["0"] * n for k in kinds}
    gold = [T.normalise(r["answer"]) for r in rows]
    nl = len(kv_rows[0])
    for ids in batches_of(prompts, args):
        ps = [prompts[i] for i in ids]
        p = torch.tensor([len(x) - 1 for x in ps], device=device)
        lt, dummy = B.last_ids(ps, device), torch.ones(len(ps), 1, dtype=torch.long, device=device)
        stack = lambda src: [(torch.stack([kv_rows[src[i]][l][0] for i in ids]).to(device), torch.stack([kv_rows[src[i]][l][1] for i in ids]).to(device)) for l in range(nl)]
        for kind, src in kinds.items():
            if kind == "zeroed":
                skv, gates = B.zero_notes_kv(runner, board, p), None
            elif kind == "gates_off":
                skv, gates = stack(kinds["true"]), torch.zeros_like(board.alpha)
            else:
                skv, gates = stack(src), None
            gen = B.decode(runner, board, None, dummy, p, lt, skv, eos=enc.eos, gates=gates, blind=True)
            for i, g in zip(ids, gen):
                hits[kind][i] = "1" if T.normalise(enc.tok.decode(g, skip_special_tokens=True)) == gold[i] else "0"
    acc = lambda h, idx: sum(h[i] == "1" for i in idx) / max(len(idx), 1)
    sw = [i for i in range(n) if partner[i] is not None]
    out = dict(rows=n, true=acc(hits["true"], range(n)), zeroed=acc(hits["zeroed"], range(n)), gates_off=acc(hits["gates_off"], range(n)),
               swapped=acc(hits["swapped"], sw), true_on_swapped_rows=acc(hits["true"], sw), swapped_n=len(sw), swapped_same_story_rows=same_story)
    out["swap_cost"] = out["true_on_swapped_rows"] - out["swapped"]
    out["zero_cost"] = out["true"] - out["zeroed"]
    return out


# ---------------------------------------------------------------- run

def run(args):
    device = torch.device(("cuda" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device)
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    t0 = time.time()
    runner, board, tok, meta, start = load_ckpt(args, device, dtype)
    enc = T.Encoder(tok, args.max_len)
    rows = T.read_jsonl(Path(args.data) / "validation.jsonl", limit=args.limit)
    args.blind_on = {"on": True, "off": False}.get(args.blind, meta["arm"] == "tf")
    print(f"[p0] arm {meta['arm']} seed {meta['seed']} K {meta['K']} lmax {meta['lmax']} alpha_init {meta['alpha_init']} rows {len(rows)} device {device}", flush=True)
    out = dict(ckpt=str(args.ckpt), arm=meta["arm"], seed=meta["seed"], k_slots=meta["K"], lmax=meta["lmax"], alpha_init=meta["alpha_init"], rows=len(rows),
               device=str(device), dtype=str(dtype).replace("torch.", ""), smoke=args.smoke, env=K.env_info(device, dtype))
    out["gates"] = gate_reading(board)
    out["drift"] = drift_reading(board, start, fresh_start(args, runner, tok, meta, device))
    out["wiring"], notes, kv_rows, prompts = model_readings(runner, board, enc, rows, meta, args, device)
    out["notes"] = notes_reading(notes, rows)
    if args.blind_on:
        out["blind"] = blind_reading(runner, board, enc, rows, prompts, kv_rows, args, device)
    else:
        out["blind"] = dict(skipped=f"arm {meta['arm']} is not tf-style blind-capable (use --blind on to force)")
    out["bridge"] = dict(skipped="TODO: row 7 (bridge probe) is not implemented")
    d, nt = out["drift"], out["notes"]
    out["rules"] = dict(  # section 3.5, restated; None where the reading was skipped
        row1_wiring_bug=out["wiring"]["bug"],
        row2_gate_closed=out["gates"]["mean_abs_tanh"] < 0.1,
        row3_block_barely_trained=None if "skipped" in d else (d["refiner_rel"] < 0.01),
        row5_notes_story_independent=None if nt["ratio_across_stories"] is None else nt["ratio_across_stories"] < 0.01,
        row6_refiner_stuck=nt["lap_change"]["values"][-1] < 0.01 if nt["lap_change"]["values"] else None,
        note="row 5 uses the between-story ratio (ratio_across_rows if there is one story); row 6 uses the change into the last lap")
    if nt["ratio_across_stories"] is None:
        out["rules"]["row5_notes_story_independent"] = nt["ratio_across_rows"] < 0.01 if nt["ratio_across_rows"] is not None else None
    out["seconds"] = time.time() - t0
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(f"[p0] wrote {args.out}: wiring max|dlogit| {out['wiring']['max_abs_dlogit']:.3g} mean|tanh a| {out['gates']['mean_abs_tanh']:.4f} "
          f"refiner drift {d.get('refiner_rel', d.get('skipped'))} rules {out['rules']}", flush=True)
    return out


def parse(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ckpt", required=True, help="arm output dir with adapter/ and think_block.pt (result_*.json there, if present, supplies lmax / alpha_init)")
    ap.add_argument("--adapter", default=None, help="LoRA adapter dir (default: <ckpt>/adapter)")
    ap.add_argument("--block", default=None, help="think_block.pt (default: <ckpt>/think_block.pt)")
    ap.add_argument("--data", default="out/data", help="dir with validation.jsonl")
    ap.add_argument("--out", default=None, help="result JSON (default: <ckpt>/p0_readout.json)")
    ap.add_argument("--model", default="Qwen/Qwen3.5-0.8B")
    ap.add_argument("--device", default="auto", help="auto / cpu / cuda")
    ap.add_argument("--limit", type=int, default=200, help="N: first N validation rows for every reading")
    ap.add_argument("--max-len", type=int, default=2048)
    ap.add_argument("--eval-bsz", type=int, default=16)
    ap.add_argument("--eval-tokens", type=int, default=16384)
    ap.add_argument("--lmax", type=int, default=None, help="laps (default: the result JSON's lmax, else 4)")
    ap.add_argument("--seed", type=int, default=None, help="seed of the run (default: the one in think_block.pt)")
    ap.add_argument("--alpha-init", type=float, default=None, help="gate start of the run (default: think_block.pt, else the result JSON, else 0)")
    ap.add_argument("--blind", choices=("auto", "on", "off"), default="auto", help="blind baselines: auto = arm tf only")
    ap.add_argument("--smoke", action="store_true", help="the tiny random qwen3_5 of think1 --smoke (for tests)")
    args = ap.parse_args(argv)
    args.out = args.out or str(Path(args.ckpt) / "p0_readout.json")
    return args


def main(argv=None):
    run(parse(argv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
