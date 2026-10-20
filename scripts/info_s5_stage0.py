"""S5 Stage 0 (design/info-constraints/S5-STAGE0-CARD.md): D + S2 vs D + S2 + `dec_ent_match`, far-fact toy, tiny.

$0 CPU. Stage 1: the S2 protocol (800 gold-only steps, kappa_d frozen). Stage 2: 1,600 steps, each visit preloads the
gold card + k fact distractors (k uniform in {0, 1, 2} per visit, generator 1000 + seed), answer loss averaged over
the 2 loops; shared lr 1e-3, kappa_d its own group at lr 1e-2. Primary: acc_d2 (gold + 2 fact cards, generator 7002).
Readings reuse the S2 runner. `summarize` applies card §5-§7.

    python3 -B scripts/info_s5_stage0.py run --arm treated --seed 0
    python3 -B scripts/info_s5_stage0.py summarize
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys
import time

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from learnlab.core import IGNORE_INDEX                                      # noqa: E402
from premonition.config import MiniConfig                                   # noqa: E402
from premonition.model import PremonitionMini, _norm, rope                   # noqa: E402
from premonition.toy import ToySpec, toy_set, toy_stream                     # noqa: E402
from premonition.train import label_free                                    # noqa: E402

_spec = importlib.util.spec_from_file_location("info_s2_stage0", ROOT / "scripts" / "info_s2_stage0.py")
S2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S2)

OUT = ROOT / "artifacts/claude-infoconstraints-20261018/s5-stage0"
STAGE1, STAGE2, EVERY, LOOPS, LR, LR_KAPPA, WARMUP = 800, 1600, 400, S2.LOOPS, S2.LR, 1e-2, S2.WARMUP
SEEDS, CHANCE = (0, 1, 2), 1 / 16


def shared_digest(model: PremonitionMini) -> str:
    digest = hashlib.sha256()
    for name, param in sorted(model.named_parameters()):
        if name != "dec_kappa":
            digest.update(name.encode())
            digest.update(param.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def question_entities(batch, vocab: int) -> list[set[int]]:
    out = []
    for q in range(batch.q_visit.shape[0]):
        start, end = (int(x) for x in batch.q_span[q])
        out.append({int(t) - vocab for t in batch.tokens[int(batch.q_visit[q]), start:end] if int(t) >= vocab})
    return out


def preload_k(model: PremonitionMini, store, batch, episode, generator: torch.Generator) -> None:
    """Stage 2: gold + k fact distractors, k uniform in {0, 1, 2} per visit (card §3), shuffled."""
    k_visit = torch.randint(3, (batch.tokens.shape[0],), generator=generator)
    k = k_visit[batch.q_visit]
    gold, _, missing = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
    if int(missing.sum()) or bool((batch.gold_lines[:, 0] < 0).any()) or bool((batch.gold_lines[:, 1:] >= 0).any()):
        raise ValueError("stage 2 needs exactly one gold line with a card per question (far-fact toy)")
    pool = store.eligible(batch.q_visit, batch.q_line) & ~gold
    pool[:, store.null] = False
    pool[:, :store.null] &= store.ents[batch.q_visit, :, 0] >= 0                 # fact lines only
    noise = torch.rand(pool.shape, generator=generator).masked_fill(~pool, -1.0)
    best, extra = noise.topk(2, 1)
    rank = torch.arange(2).unsqueeze(0)
    extra = extra.masked_fill((best < 0) | (rank >= k.unsqueeze(1)), -1)
    cards = torch.cat([batch.gold_lines[:, :1], extra], dim=1)
    cards = cards.gather(1, torch.rand(cards.shape, generator=generator).argsort(1))
    model._insert(episode, store, torch.arange(batch.q_visit.shape[0]), cards)


def stage2_loss(model: PremonitionMini, batch, generator: torch.Generator) -> torch.Tensor:
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    episode = model._start(batch, hidden, store, model._mentions(batch))
    preload_k(model, store, batch, episode, generator)
    answer = batch.answer
    length = int((answer != IGNORE_INDEX).sum(1).max().item())
    targets = answer[:, :max(length, 1)]
    start = batch.tokens[batch.q_visit, batch.q_span[:, 1] - 1]
    inputs = torch.cat([start.unsqueeze(1), targets[:, :-1]], dim=1)
    inputs = inputs.masked_fill(inputs == IGNORE_INDEX, model.config.pad_id)
    keep = targets != IGNORE_INDEX
    everyone = torch.arange(batch.q_visit.shape[0])
    terms = []
    for step in range(LOOPS):
        rows, _, _, _ = model._step(episode, everyone, step, store)
        out = model._decode_logits(rows, episode.valid, inputs, bias=model._match_bias(episode))
        terms.append(F.cross_entropy(F.linear(out[keep], model.embed.weight).float(), targets[keep]))
    return sum(terms) / len(terms)


@torch.no_grad()
def d2_detail(model: PremonitionMini, batches: list) -> dict:
    """The S2 §10b reading (gold + 2 fact cards, generator 7002) per question: correct, a distractor names the
    question's person, and the decoder's position-0 attention share on the gold card's rows among the supplied
    cards' rows (averaged over heads)."""
    was = model.training
    model.eval()
    generator = torch.Generator().manual_seed(7002)
    rows_out = []
    config = model.config
    for batch in batches:
        hidden = model.read(batch)
        store = model.build_store(hidden, batch)
        mentions = model._mentions(batch)
        episode = model._start(batch, hidden, store, mentions)
        cards = S2.preload_distractors(model, store, batch, episode, 2, generator, facts_only=True)
        everyone = torch.arange(batch.q_visit.shape[0])
        for step in range(LOOPS):
            model._step(episode, everyone, step, store)
        tokens, lengths = model._greedy(batch, episode, mentions, None)
        share = attention_share(model, batch, episode, cards)
        names = question_entities(batch, config.vocab_size)
        for q in range(batch.q_visit.shape[0]):
            target = batch.answer[q][batch.answer[q] != IGNORE_INDEX].tolist()
            v, gold_line = int(batch.q_visit[q]), int(batch.gold_lines[q, 0])
            same = any(int(c) >= 0 and int(c) != gold_line
                       and bool({int(e) for e in batch.line_ents[v, int(c)] if int(e) >= 0} & names[q])
                       for c in cards[q])
            rows_out.append({"correct": tokens[q, :int(lengths[q])].tolist() == target, "same_person": same,
                             "said": tuple(tokens[q, :int(lengths[q])].tolist()), "gold_share": float(share[q])})
    model.train(was)
    return summarize_d2(rows_out)


def summarize_d2(rows: list[dict]) -> dict:
    def acc(sub):
        return sum(r["correct"] for r in sub) / len(sub) if sub else None
    same = [r for r in rows if r["same_person"]]
    other = [r for r in rows if not r["same_person"]]
    return {"n": len(rows), "correct": sum(r["correct"] for r in rows), "acc": acc(rows),
            "distinct_256": len({r["said"] for r in rows[:256]}),
            "same_person": {"n": len(same), "acc": acc(same)}, "no_same_person": {"n": len(other), "acc": acc(other)},
            "gold_share_no_same_person": statistics.fmean(r["gold_share"] for r in other) if other else None}


def attention_share(model: PremonitionMini, batch, episode, cards: torch.Tensor) -> torch.Tensor:
    """[Q] share of position-0 cross-attention (mean over heads) on the gold card's two rows among the supplied
    cards' rows. Slots follow insertion order into a fresh ring (slot j = j-th real card)."""
    dec, config = model.decoder, model.config
    base, think = model._card_base, config.rows
    inputs = batch.tokens[batch.q_visit, batch.q_span[:, 1] - 1].unsqueeze(1)
    x = model.embed(inputs)
    n, length, width = x.shape
    h = dec.heads
    q, k, v = dec.qkv(dec.norm1(x)).view(n, length, 3, h, -1).permute(2, 0, 3, 1, 4)
    pos = torch.arange(length)
    q, k = rope(q, pos, dec.base), rope(k, pos, dec.base)
    x = x + dec.proj(F.scaled_dot_product_attention(q, k, v, is_causal=True).transpose(1, 2).reshape(n, length, width))
    q = dec.cross_q(dec.norm2(x)).view(n, length, h, -1).transpose(1, 2)
    kk, _ = dec.cross_kv(_norm(episode.x)).view(n, episode.x.shape[1], 2, h, -1).permute(2, 0, 3, 1, 4)
    logits = q @ kk.transpose(-1, -2) / math.sqrt(q.shape[-1])
    bias = model._match_bias(episode)
    if bias is not None:
        logits = logits + bias[:, None, None, :]
    attn = torch.softmax(logits.masked_fill(~episode.valid[:, None, None, :], -math.inf), -1)[:, :, 0].mean(1)
    share = torch.zeros(n)
    for qi in range(n):
        real = [int(c) for c in cards[qi] if int(c) >= 0]
        slots = {c: j for j, c in enumerate(real)}
        gold = slots.get(int(batch.gold_lines[qi, 0]))
        rows = [r for j in range(len(real)) for r in (base + j, think + j)]
        total = float(attn[qi, rows].sum())
        if gold is not None and total > 0:
            share[qi] = float(attn[qi, [base + gold, think + gold]].sum()) / total
    return share


def train(arm: str, seed: int, threads: int, test: list):
    torch.set_num_threads(threads)
    spec = ToySpec()
    torch.manual_seed(seed)
    config = MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64, decoder_raw_cards=True,
                               dec_ent_match=arm == "treated")
    model = PremonitionMini(config)
    kappa = getattr(model, "dec_kappa", None)
    if kappa is not None:
        kappa.requires_grad_(False)                                 # stage 1: frozen (card §3)
    shared = [p for n, p in model.named_parameters() if n != "dec_kappa"]
    optimizer = torch.optim.AdamW(
        [{"params": [p for p in shared if p.dim() >= 2], "weight_decay": 0.1},
         {"params": [p for p in shared if p.dim() < 2], "weight_decay": 0.0}],
        lr=LR, betas=(0.9, 0.99), eps=1e-8)
    stream = (label_free(b) for b in toy_stream(spec, S2.VISITS, S2.TRAIN_SEED))
    generator = torch.Generator().manual_seed(1000 + seed)
    record = {"history": [], "progress": [], "finite": True, "first_stage2_kappa_grad": None}
    started = time.perf_counter()
    for step in range(STAGE1 + STAGE2):
        if step == STAGE1:
            record["stage1_digest"] = shared_digest(model)
            record["stage1_acc_gold"] = S2.score(model, test, card=True)["acc"]
            if kappa is not None:
                kappa.requires_grad_(True)
                optimizer.add_param_group({"params": [kappa], "lr": LR_KAPPA, "weight_decay": 0.0})
        for group in optimizer.param_groups[:2]:
            group["lr"] = LR * min(1.0, (step + 1) / WARMUP)
        batch = next(stream)
        if step < STAGE1:
            loss = model.forward(batch, mode="gold", loops=LOOPS, weights={"ans": 1.0})["ans"]
        else:
            loss = stage2_loss(model, batch, generator)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        if step == STAGE1 and kappa is not None:
            record["first_stage2_kappa_grad"] = float(kappa.grad)
        record["finite"] &= all(p.grad is None or bool(torch.isfinite(p.grad).all()) for p in model.parameters())
        torch.nn.utils.clip_grad_norm_(list(model.parameters()), 1.0)
        optimizer.step()
        done = step + 1
        if done % 100 == 0 or step == 0:
            record["history"].append({"step": done, "loss": round(float(loss.detach()), 4),
                                      "kappa_d": None if kappa is None else round(float(kappa.detach()), 4),
                                      "seconds": round(time.perf_counter() - started, 1)})
            print(json.dumps(record["history"][-1]), flush=True)
        if done > STAGE1 and (done - STAGE1) % EVERY == 0:
            record["progress"].append({"stage2_step": done - STAGE1,
                                       "acc_gold": S2.score(model, test, card=True)["acc"],
                                       "acc_d2": S2.distract(model, test, 2, True)["acc"]})
    record["steps_run"] = done
    record["seconds"] = time.perf_counter() - started
    return model, record


def cmd_run(args) -> None:
    test = [label_free(b) for b in toy_set(ToySpec(), S2.TEST_BATCHES, S2.VISITS, S2.TEST_SEED)]
    model, record = train(args.arm, args.seed, args.threads, test)
    detail = d2_detail(model, test)
    check = S2.distract(model, test, 2, True)
    if check["correct"] != detail["correct"]:                       # the per-question tally is the S2 reading
        raise RuntimeError(f"d2 tally {detail['correct']} differs from S2.distract {check['correct']}")
    result = {"arm": args.arm, "seed": args.seed, "threads": args.threads, "torch": torch.__version__,
              **record, "gold": S2.score(model, test, card=True), "nocard": S2.score(model, test, card=False),
              "d2": detail, "kappa_d": float(model.dec_kappa.detach()) if args.arm == "treated" else None}
    if args.arm == "treated":                                     # card §7: eval-only, kappa_d forced to 8
        kept = model.dec_kappa.detach().clone()
        with torch.no_grad():
            model.dec_kappa.fill_(8.0)
        result["d2_kappa8"] = S2.distract(model, test, 2, True)
        with torch.no_grad():
            model.dec_kappa.copy_(kept)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{args.arm}-seed{args.seed}.json").write_text(json.dumps(result, indent=1))
    d2 = result["d2"]
    print(f"{args.arm} seed {args.seed}: d2 {d2['acc']:.4f} (same {d2['same_person']['acc']}, other "
          f"{d2['no_same_person']['acc']}) gold {result['gold']['acc']:.4f} nocard {result['nocard']['acc']:.4f} "
          f"kappa_d {result['kappa_d']} share {d2['gold_share_no_same_person']} | {record['seconds']:.0f} s")


def cmd_summarize(args) -> None:
    """Card §5-§7, verbatim."""
    runs, missing = {}, []
    for arm in ("control", "treated"):
        for seed in SEEDS:
            path = OUT / f"{arm}-seed{seed}.json"
            if path.exists():
                runs[(arm, seed)] = json.loads(path.read_text())
            else:
                missing.append(path.name)
    if missing:
        summary = {"verdict": "INCOMPLETE", "missing": missing}
    else:
        rows = []
        for seed in SEEDS:
            c, t = runs[("control", seed)], runs[("treated", seed)]
            void = {"one_distinct": c["d2"]["distinct_256"] == 1,
                    "control_gold_lt_95_after_stage1": c["stage1_acc_gold"] < 0.95,
                    "control_gold_lt_90_after_stage2": c["gold"]["acc"] < 0.90,
                    "stage1_digests_differ": c["stage1_digest"] != t["stage1_digest"],
                    "kappa_grad_zero": not t["first_stage2_kappa_grad"]}
            other, same = t["d2"]["no_same_person"]["acc"], t["d2"]["same_person"]["acc"]
            rows.append({"seed": seed, "void": any(void.values()), "void_reasons": void,
                         "d": t["d2"]["acc"] - c["d2"]["acc"], "control_d2": c["d2"]["acc"], "treated_d2": t["d2"]["acc"],
                         "treated_gold": t["gold"]["acc"], "treated_nocard": t["nocard"]["acc"],
                         "treated_distinct": t["d2"]["distinct_256"], "treated_other": other, "treated_same": same,
                         "kappa_d": t["kappa_d"], "gold_share": t["d2"]["gold_share_no_same_person"],
                         "d2_kappa8": t["d2_kappa8"]["acc"],
                         "complete": all(x["finite"] and x["steps_run"] == STAGE1 + STAGE2 for x in (c, t))})
        valid = [r for r in rows if not r["void"]]
        every_complete = all(r["complete"] for r in rows)
        detail = {"rows": rows, "every_run_complete": every_complete}
        if len(valid) < 2:
            summary = {"verdict": "INCONCLUSIVE", "why": "fewer than 2 valid seeds", **detail}
        else:
            d = [r["d"] for r in valid]
            mean = statistics.fmean(d)
            bound = mean - 2 * statistics.stdev(d) / math.sqrt(len(d))
            marks = {
                "1_d_ge_15_every_seed": all(x >= 0.15 for x in d), "1_mean_minus_2se_gt_0": bound > 0,
                "2_treated_d2_ge_60": all(r["treated_d2"] >= 0.60 for r in valid),
                "3_other_minus_same_ge_20": all(r["treated_other"] is not None and r["treated_same"] is not None
                                                and r["treated_other"] - r["treated_same"] >= 0.20 for r in valid),
                "4_gold_ge_95": all(r["treated_gold"] >= 0.95 for r in valid),
                "4_nocard_le_9.25": all(r["treated_nocard"] <= CHANCE + 0.03 for r in valid),
                "4_distinct_gt_1": all(r["treated_distinct"] > 1 for r in valid),
                "4_finite_complete": every_complete}
            fail = mean <= 0.03 or sum(r["treated_d2"] < 0.45 for r in valid) >= 2
            wrong = sum(abs(x) <= 0.03 for x in d) >= 2
            verdict = "FAIL" if fail or wrong else ("PASS" if all(marks.values()) else "INCONCLUSIVE")
            engaged = all(r["kappa_d"] >= 1.0 and (r["gold_share"] or 0) >= 0.6 for r in valid)
            notes = []
            if all(r["d2_kappa8"] <= 0.45 for r in valid):
                notes.append("kappa_d = 8 leaves acc_d2 <= 45%: the fault is after selection (decoder query or value path)")
            if all(r["control_d2"] >= 0.60 for r in valid):
                notes.append("the protocol alone teaches choosing")
            summary = {"verdict": verdict, "mean_d": mean, "mean_minus_2se": bound, "marks": marks,
                       "fail_rule": fail, "proves_S5_wrong_rule": wrong, "engaged": engaged, "notes": notes, **detail}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--arm", choices=("control", "treated"), required=True)
    run.add_argument("--seed", type=int, required=True)
    run.add_argument("--threads", type=int, default=1)
    sub.add_parser("summarize")
    args = parser.parse_args()
    {"run": cmd_run, "summarize": cmd_summarize}[args.cmd](args)


if __name__ == "__main__":
    main()
