"""Score a saved LoRA adapter without training: cross-card numerics checks, and the fresh-row final claims (PREREG-think2 Addendum F).

  python3 backbone/think/eval_adapter.py --adapter OUT/think/a_s0/adapter --data OUT/data --out X/eval_a.json --board-path \
      --ref OUT/think/a_s0/result_a_s0.json --ref-tag main
  python3 backbone/think/eval_adapter.py --adapter OUT/think/br_s0/adapter --data FRESH --file fresh.jsonl --loops 1,4,8 --out X/fresh_br.json

--loops r1,r2,... scores the model with the default block (layers 8-11) run r times (arms br, hloop, hloops); without it, one plain pass. An
inject.pt beside the adapter directory (arms hloopi, hloopd, hloops, Addendum G) is loaded into the runner, so those arms are scored with their W.
--keep-preds keeps each row's answer and its log-probability (the hops stop rules need them). --board-path decodes
as arms a / aplus / aplong are scored. --ref compares the hits with a stored result's on the same rows: accuracy difference and the share of rows
with the same hit (Addendum F's Radeon check: within 0.3 points, >= 98% the same). --smoke: the tiny CPU model (tests this script).
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
import think1 as K  # noqa: E402
import train as T  # noqa: E402

CHECK_PTS, CHECK_SAME = 0.3, 0.98


def compare(hits, ref):
    """hits vs a reference hit string on the same rows: accuracy difference in points, share of rows with the same hit, and the check."""
    if len(hits) != len(ref):
        raise SystemExit(f"--ref has {len(ref)} rows, this run {len(hits)}: score the same rows (same --limit-eval)")
    d = 100 * (hits.count("1") - ref.count("1")) / len(hits)
    same = sum(a == b for a, b in zip(hits, ref)) / len(hits)
    return dict(acc_diff_pts=d, same_hit=same, ok=abs(d) <= CHECK_PTS + 1e-9 and same >= CHECK_SAME - 1e-12)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--data", required=True, help="dir holding --file")
    ap.add_argument("--file", default="validation.jsonl")
    ap.add_argument("--out", required=True, help="result JSON")
    ap.add_argument("--loops", default=None, help="comma list of loop counts of the default block (arm br); default: one plain pass")
    ap.add_argument("--board-path", action="store_true", help="decode as arms a / aplus / aplong are scored")
    ap.add_argument("--keep-preds", action="store_true", help="store each row's answer and answer log-probability")
    ap.add_argument("--ref", default=None, help="a think1 result JSON scored on the same rows")
    ap.add_argument("--ref-tag", default="main")
    ap.add_argument("--limit-eval", type=int, default=None)
    ap.add_argument("--model", default="Qwen/Qwen3.5-0.8B")
    ap.add_argument("--max-len", type=int, default=2048)
    ap.add_argument("--eval-bsz", type=int, default=64)
    ap.add_argument("--eval-tokens", type=int, default=32768)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args(argv)
    if a.loops and a.board_path:
        ap.error("--board-path cannot loop a block: use one or the other")
    args = K.parse(["--arm", "a", "--out", str(Path(a.out).parent), "--model", a.model, "--max-len", str(a.max_len), "--eval-bsz", str(a.eval_bsz),
                    "--eval-tokens", str(a.eval_tokens), *(["--smoke"] if a.smoke else [])])
    device = torch.device("cuda" if torch.cuda.is_available() and not a.smoke else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    from peft import PeftModel
    lm, tok = T.load_model(args, device, dtype)
    pm = PeftModel.from_pretrained(lm, a.adapter)
    pm.eval()
    runner = T.Runner(pm.base_model.model, loops=1)
    inj = Path(a.adapter).parent / "inject.pt"
    if inj.exists():  # Addendum G arms with input injection: W was saved beside the adapter
        runner.inject = T.Inject(runner.cfg.hidden_size).to(device)
        runner.inject.load_state_dict(torch.load(inj, map_location=device))
    enc = T.Encoder(tok, a.max_len)
    rows = T.read_jsonl(Path(a.data) / a.file, limit=a.limit_eval)
    res = dict(adapter=str(a.adapter), adapter_sha=K.adapter_sha(a.adapter), data=str(Path(a.data) / a.file), n=len(rows), env=K.env_info(device, dtype),
               board_path=a.board_path, eval={},
               inject=dict(path=str(inj), weight_norm=float(runner.inject.proj.weight.detach().norm())) if runner.inject is not None else None)
    t0 = time.time()
    tags = [(f"r{r}", T.block_order(runner.n, runner.start, r, runner.size)) for r in map(int, a.loops.split(","))] if a.loops else [("main", None)]
    for tag, order in tags:
        e = K.eval_greedy(runner, enc, rows, device, args, order=order, name=tag, board_path=a.board_path, keep_preds=a.keep_preds,
                          keep_logp=a.keep_preds)
        by = {}
        for r, h in zip(rows, e["hits"]):
            g = by.setdefault(str(r.get("depth")), [0, 0])
            g[0], g[1] = g[0] + (h == "1"), g[1] + 1
        e["by_depth"] = {d: dict(n=n, acc=k / n) for d, (k, n) in sorted(by.items())}
        res["eval"][tag] = e
        print(f"[eval_adapter] {tag}: {e['acc'] * 100:.2f}% on {e['n']} rows, {time.time() - t0:.0f}s", flush=True)
    if a.ref:
        ref = json.loads(Path(a.ref).read_text())["eval"]["validation"][a.ref_tag]["hits"]
        res["ref"] = dict(path=a.ref, tag=a.ref_tag, **compare(res["eval"][tags[0][0]]["hits"], ref[:len(rows)]))
        print(f"[eval_adapter] vs ref: {res['ref']['acc_diff_pts']:+.2f} points, same hit on {res['ref']['same_hit'] * 100:.2f}% of rows -> "
              f"{'OK' if res['ref']['ok'] else 'MISMATCH'} (needs within {CHECK_PTS} points and >= {CHECK_SAME * 100:.0f}% the same)", flush=True)
    res["seconds"] = time.time() - t0
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res))
    return 0 if not a.ref or res["ref"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
