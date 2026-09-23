"""Parity + behaviour test for the ordered-evidence variant (Claude, 2026-09-19).

Run it directly (it needs the frozen snapshot on sys.path, which L.bootstrap() provides):

    PY -B tests/test_premonition_ordered_evidence.py

Checks, all on CPU:
  1  state_dict parity: `premonition_ordered_evidence.build(arm, seed, ordered=False/True)` produces exactly the
     same parameters as `premonition_ovn_retrieval.build(arm, seed)` for the same seed.
  2  loss parity: with ordering DISABLED the copied forward gives bit-identical lm/ask/ans/halt/loss to the frozen
     `PremonitionMini.forward` (as reached through CardBypassMini), in BOTH "teacher" and "own" mode.
  3  data fact: on validation, gold_lines[:, 0] is the link card and gold_lines[:, 1] the answer card for every
     two-hop question.
  4  ordering behaviour: with ordering ENABLED, at step 0 the SET target of every two-hop question is exactly
     {link card} and the teacher's first inserted card is the link card; for one-hop questions the target set is
     unchanged (equal to the full "need" set) at every loop.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import premonition_ovn_ladder as L  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402

ARM, SEED = "bypass-k1", 0


def _losses(model, batch, mode, p_own, seed):
    import torch
    gen = torch.Generator().manual_seed(seed)
    model.eval()
    with torch.no_grad():
        out = model(batch, mode=mode, p_own=p_own, generator=gen)
    return {k: float(out[k]) for k in ("lm", "ask", "ans", "halt", "loss")}


def main() -> int:
    L.bootstrap()
    import torch
    import premonition_ordered_evidence as O
    import premonition_first_card_probe as P
    torch.set_num_threads(4)
    failures = []

    def check(name, ok, detail=""):
        print(("PASS " if ok else "FAIL ") + name + ((" :: " + detail) if detail else ""), flush=True)
        if not ok:
            failures.append(name)

    # ---- 1. state_dict parity ------------------------------------------------
    base = R.build(ARM, SEED)
    off = O.build(ARM, SEED, ordered=False)
    on = O.build(ARM, SEED, ordered=True)
    same_keys = sorted(base.state_dict()) == sorted(off.state_dict()) == sorted(on.state_dict())
    same_values = all(torch.equal(base.state_dict()[k], off.state_dict()[k])
                      and torch.equal(base.state_dict()[k], on.state_dict()[k]) for k in base.state_dict())
    check("state_dict keys identical to the baseline", same_keys)
    check("state_dict values identical to the baseline", same_values,
          f"{len(base.state_dict())} tensors")
    check("no extra parameters", sum(p.numel() for p in base.parameters())
          == sum(p.numel() for p in on.parameters()))

    # ---- 2. loss parity with ordering disabled ------------------------------
    stream = L.checked_train()
    items = [next(stream) for _ in range(2)]
    for mode, p_own in (("teacher", 0.0), ("own", 0.5)):
        for i, item in enumerate(items):
            a = _losses(base, item[0], mode, p_own, 1234 + i)
            b = _losses(off, item[0], mode, p_own, 1234 + i)
            check(f"loss parity mode={mode} batch={i}", a == b, f"{a} vs {b}")

    # ---- 3. gold_lines order on validation ----------------------------------
    spec = L.spec()
    val = L.load_split("validation")
    bad_link = bad_answer = two_hop = 0
    for batch, _supplied, hops in val:
        for q in range(len(hops)):
            if int(hops[q]) != 2:
                continue
            two_hop += 1
            v = int(batch.q_visit[q])
            ask_tokens = batch.tokens[v, int(batch.q_span[q, 0]):int(batch.q_span[q, 1])].tolist()
            a_id, rel = ask_tokens[1] - spec.vocab_size, ask_tokens[3]
            link_line = int(batch.gold_lines[q, 0])
            b_id = int(batch.tokens[v, int(batch.line_start[v, link_line]) + 3]) - spec.vocab_size

            def kind(line):
                start = int(batch.line_start[v, line])
                return P.classify(batch.tokens[v, start:start + 4].tolist(), a_id, b_id, rel,
                                  spec.link, spec.vocab_size)
            bad_link += kind(link_line) != "link"
            bad_answer += kind(int(batch.gold_lines[q, 1])) != "answer"
    check("validation: gold_lines[:,0] is always the link card", bad_link == 0,
          f"{two_hop} two-hop questions, {bad_link} exceptions")
    check("validation: gold_lines[:,1] is always the answer card", bad_answer == 0,
          f"{bad_answer} exceptions")

    # ---- 4. ordering behaviour ----------------------------------------------
    batch, _supplied, hops = items[0]
    records = []
    real_next = O._next_needed

    def spy_next(cols, fetched, need):
        out = real_next(cols, fetched, need)
        records.append({"need": need.clone(), "out": out.clone()})
        return out

    teacher_calls = []
    real_teacher = on._teacher_cards

    def spy_teacher(store, episode, index, need, gold, generator):
        cards = real_teacher(store, episode, index, need, gold, generator)
        teacher_calls.append(cards.clone())
        return cards

    O._next_needed = spy_next
    on._teacher_cards = spy_teacher
    try:
        _losses(on, batch, "teacher", 0.0, 7)
    finally:
        O._next_needed = real_next
        del on._teacher_cards

    two = torch.tensor([int(h) == 2 for h in hops])
    one = torch.tensor([int(h) == 1 for h in hops])
    link_col = batch.gold_lines[:, 0]
    step0 = records[0]["out"]
    only_link = True
    for q in torch.nonzero(two).squeeze(1).tolist():
        cols = torch.nonzero(step0[q]).squeeze(1).tolist()
        only_link = only_link and cols == [int(link_col[q])]
    check("step-0 SET target of a two-hop question is exactly {link card}", only_link,
          f"{int(two.sum())} two-hop questions in the batch")
    first_cards = teacher_calls[0][:, 0]
    teacher_ok = bool((first_cards[two] == link_col[two]).all())
    check("teacher's first inserted card is always the link card", teacher_ok,
          f"{int((first_cards[two] == link_col[two]).sum())}/{int(two.sum())}")
    unchanged = all(bool(torch.equal(r["out"][one], r["need"][one])) for r in records)
    check("one-hop questions: SET target unchanged at every loop", unchanged,
          f"{int(one.sum())} one-hop questions, {len(records)} loops")

    print(("\nALL CHECKS PASSED" if not failures else "\nFAILURES: " + ", ".join(failures)), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
