"""How much padding do sleepb's sorted micro-batches carry? CPU only, tokenizer only (no model). Rebuilds night-shaped batches from a week file with the real chat
template: dream_ex's mix (para + qa 1:1; a Q&A is open-book p=0.5 = diary-test prompt with 8 BM25 notes, else closed-book), bsz 16 (REM steps: 70% Q&A), replay = generic
prompt + a 48-token-max reply. Paraphrase text is a stand-in (the item sentence + one clause): real ones come from the model, so the short-example lengths are assumed.
  python padding_stats.py --tokenizer Qwen/Qwen3.6-35B-A3B --week ../../backbone/sleep/brain/data/week1.json --out padding_stats.json"""
import argparse
import json
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parents[1] / "backbone" / "sleep" / "brain"
sys.path[:0] = [str(BRAIN), str(BRAIN.parent), str(BRAIN.parent.parent)]


def pack(lens, budget):  # first-fit decreasing into bins of <= budget real tokens (what a padding-free path would run)
    bins = []
    for n in sorted(lens, reverse=True):
        for b in bins:
            if b[0] + n <= budget:
                b[0] += n
                break
        else:
            bins.append([n])
    return len(bins), sum(b[0] for b in bins)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizer", default="Qwen/Qwen3.6-35B-A3B")
    ap.add_argument("--week", default=str(BRAIN / "data" / "week1.json"))
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--replay-bsz", type=int, default=8)
    ap.add_argument("--day", type=int, default=5)
    ap.add_argument("--budgets", default="2048,4096")
    ap.add_argument("--out")
    a = ap.parse_args()
    from realistic import pools
    import sleepb as sb
    draw0, rep, mix, _ = pools(a.tokenizer, a.week, a.day)
    rng = random.Random(0)
    draw = lambda rem: draw0(rng, a.bsz, rem)  # noqa: E731

    res = {"mix_tokens": mix, "bsz": a.bsz, "steps": a.steps, "budgets": {}}
    for budget in map(int, a.budgets.split(",")):
        acc = {"real": 0, "padded": 0, "mb": 0, "packed_bins": 0, "packed_real": 0, "rep_real": 0, "rep_padded": 0, "rep_mb": 0, "rep_bins": 0, "oneshot_padded": 0}
        for i in range(a.steps):
            b = draw(i % 4 == 3)
            r = rng.sample(rep, a.replay_bsz)
            for ex, key in ((b, ""), (r, "rep_")):
                gs = sb.groups(ex, budget) if len(sb.groups(ex, budget)) <= 1 else sb.groups(sorted(ex, key=lambda x: -len(x[0])), budget)  # Trainer.step's FAST rule
                pad = sum(len(g) * max(len(x[0]) for x in g) for g in gs)
                nb, nreal = pack([len(x[0]) for x in ex], budget)
                acc[key + "real"] += sum(len(x[0]) for x in ex)
                acc[key + "padded"] += pad
                acc[key + "mb"] += len(gs)
                acc["packed_bins" if not key else "rep_bins"] += nb
        n = a.steps
        real, pad, rr, rp = acc["real"], acc["padded"], acc["rep_real"], acc["rep_padded"]
        res["budgets"][budget] = {"batch": {"real_tok": round(real / n), "padded_tok": round(pad / n), "pad_frac": round(1 - real / pad, 3), "micro_batches": round(acc["mb"] / n, 2), "packed_bins": round(acc["packed_bins"] / n, 2)},
                                  "replay": {"real_tok": round(rr / n), "padded_tok": round(rp / n), "pad_frac": round(1 - rr / rp, 3), "micro_batches": round(acc["rep_mb"] / n, 2), "packed_bins": round(acc["rep_bins"] / n, 2)},
                                  "total_pad_frac": round(1 - (real + rr) / (pad + rp), 3)}
    print(json.dumps(res, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
