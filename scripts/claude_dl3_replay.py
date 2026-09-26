#!/usr/bin/env python3
"""dl-3: does mixing the base's own general answers into each night stop the slow forgetting dl-2 showed?
(Fix-sleep thread, 2026-09-26; marks: artifacts/claude-dl3-20260926/PASSMARKS.md)

Why. dl-2 (registered PASS, artifacts/claude-dl2-20260926/VERIFY.md): a week of copy-practice nights lifted right
guesses on fresh puzzles 64 -> 237/249 with no night worse by more than 11%, but on a 300-item general panel the
nights LOST 26 of the 200 items the base got right by night 7 (5-7 after night 1); net harm looked fine only because
format gains, which the wrong-answer placebo also got, covered it. Ben's bar is that nights almost never make the
model worse. Research (reviews/sleep-nights-research-2026-09-25/REPORT.md Q1-Q3): forgetting tracks drift from the
base (RL's Razor), and replay of old behaviour (InstructGPT's pretraining mix, rehearsal) holds it back; Ben 00:03
UTC 09-26 asked for "replay mixed with old" in sleep.

ONE change from dl-2's S arm: each night also practises REPLAY pairs, as many as the night's puzzle examples. A
replay pair = a general question the BASE 1B wrote itself + the BASE 1B's own greedy answer to it (made once before
night 1, never by Claude, never from the harm panel; questions touching the panel's topics are dropped). Puzzle and
replay pairs are shuffled together into the same 3 epochs, lr 2e-4, batch 8 as dl-2 (claude_dl1_nights.train_copy's
loop). Arms:
  S  dl-2's night unchanged (claude_dl1_nights.train_copy on the day's checked right answers).
  A  S + replay (1 replay pair per puzzle example, new random pairs from the pool each night).
Same day (150 fresh puzzles, greedy + 30 guesses, exact checker), TEST (100 fresh puzzles x 20), HARM (dl-1's 300
items: lost = right at base and wrong now, gained = the reverse), KL. New seeds 4 and 5, new TEST seed 3790.

  python -B scripts/claude_dl3_replay.py --model M --out DIR        (registered run)
  python -B scripts/claude_dl3_replay.py --selftest
  python -B scripts/claude_dl3_replay.py --model M --out DIR --dev  (plumbing rehearsal, tiny counts, other seeds)
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt2 as B2  # noqa: E402
import claude_dl1_nights as D1  # noqa: E402

TEST_SEED = 3790
POOL_SEED = 3791
ASK = "Write one short question that a person might ask a helpful assistant. Reply with the question only."
MAX_Q, MAX_A = 32, 64


def panel_words() -> set:
    """Words that tie a question to the harm panel's topics; such questions never enter the replay pool."""
    w = {"capital", "capitals", "opposite", "opposites", "plural", "plurals", "after", "before", "letter", "letters",
         "alphabet", "bigger", "larger", "smaller", "how many", "number", "numbers", "day", "days", "month", "months",
         "week", "year", "legs", "sides", "wheels", "continents", "cents", "degrees", "players", "minutes", "seconds",
         "hours"}
    w |= {c.lower() for c, _ in D1.CAPITALS} | {g.split("|")[0] for _, g in D1.CAPITALS}
    w |= {a for a, _ in D1.OPPOSITES} | {x for _, g in D1.OPPOSITES for x in g.split("|")}
    w |= {a for a, _ in D1.PLURALS} | {x for _, g in D1.PLURALS for x in g.split("|")}
    w |= {d.lower() for d in D1.DAYS} | {m.lower() for m in D1.MONTHS}
    return w


def clean_question(t: str, bad: set) -> str | None:
    t = t.strip().split("\n")[0].strip().strip('"').strip()
    if not (8 <= len(t) <= 160) or not t.endswith("?") or re.search(r"\d", t):
        return None
    low = " " + re.sub(r"[^a-z' ]", " ", t.lower()) + " "
    if any((" " + b + " ") in low for b in bad):
        return None
    return t


def chat_ids(s, q):
    return s.tok(s.tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False,
                                           add_generation_prompt=True, enable_thinking=False),
                 return_tensors="pt")["input_ids"][0]


def base_answer(s, q):
    """The base's own greedy answer; None if it did not finish within MAX_A tokens (never train a cut answer)."""
    ids = chat_ids(s, q).unsqueeze(0).to(s.dev)
    with s.torch.no_grad():
        out = s.model.generate(input_ids=ids, attention_mask=s.torch.ones_like(ids), max_new_tokens=MAX_A,
                               do_sample=False, pad_token_id=s.tok.eos_token_id)
    new = out[0][ids.shape[1]:]
    if len(new) >= MAX_A and int(new[-1]) != s.tok.eos_token_id:
        return None
    a = s.tok.decode(new, skip_special_tokens=True).strip()
    return a or None


def make_pool(s, n_ask, seed) -> list:
    """(question, base answer) pairs, both written by the base 1B, deduplicated, panel topics dropped."""
    s.torch.manual_seed(seed)
    bad = panel_words()
    ids = chat_ids(s, ASK).unsqueeze(0).to(s.dev)
    qs, seen = [], set()
    left = n_ask
    while left > 0:
        k = min(50, left)
        with s.torch.no_grad():
            out = s.model.generate(input_ids=ids.repeat(k, 1), attention_mask=s.torch.ones_like(ids.repeat(k, 1)),
                                   max_new_tokens=MAX_Q, do_sample=True, temperature=1.0, top_p=0.95,
                                   pad_token_id=s.tok.eos_token_id)
        for o in out:
            q = clean_question(s.tok.decode(o[ids.shape[1]:], skip_special_tokens=True), bad)
            if q and q.lower() not in seen:
                seen.add(q.lower())
                qs.append(q)
        left -= k
    pool = []
    for q in qs:
        a = base_answer(s, q)
        if a:
            pool.append((q, a))
    return pool


def _pair_ids(s, item):
    import torch
    kind, x, y = item
    if kind == "puzzle":
        return D1._ids(s, x, y)
    pr = chat_ids(s, x)
    an = s.tok(y, add_special_tokens=False, return_tensors="pt")["input_ids"][0]
    return pr, torch.cat([pr, an, torch.tensor([s.tok.eos_token_id])])


def train_mixed(s, m, items, seed, epochs=D1.S_RECIPE["epochs"], lr=D1.S_RECIPE["lr"]) -> dict:
    """claude_dl1_nights.train_copy's loop (same optimizer, batch 8, shuffle, answer-only loss) over mixed items:
    ("puzzle", puzzle, expr) or ("replay", question, base answer)."""
    import torch
    torch.manual_seed(seed)
    opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=lr)
    rng, last = random.Random(seed), 0.0
    m.train()
    for ep in range(epochs):
        ex = list(items)
        rng.shuffle(ex)
        for i in range(0, len(ex), 8):
            batch = ex[i:i + 8]
            tot = 0.0
            for it in batch:
                pr, full = _pair_ids(s, it)
                ids = full.unsqueeze(0).to(s.dev)
                lab = ids.clone()
                lab[0, :len(pr)] = -100
                loss = m(input_ids=ids, labels=lab).loss / len(batch)
                loss.backward()
                tot += float(loss.detach())
            opt.step()
            opt.zero_grad()
            last = tot
    m.eval()
    return {"examples": len(items), "replay": sum(1 for it in items if it[0] == "replay"), "last_loss": round(last, 4)}


def run_arm(s, arm, seed, a, test, panel, replies, base_harm, pool) -> dict:
    s.torch.manual_seed(seed)
    m = D1.fresh_model(s)
    nights = []
    for d in range(1, a.nights + 1):
        t0 = time.time()
        day = B2.puzzles(D1.DAY_SEED + a.seed_shift + 100 * seed + d, a.n_day)
        groups = D1.gather(s, m, day, a.n_guess)
        right = D1.copy_examples(groups)
        rec = {"night": d, "day_greedy_right": sum(g["greedy_right"] for g in groups),
               "day_right_guesses": sum(sum(g["rewards"]) for g in groups), "right_examples": len(right)}
        if not right:
            rec["train"] = {"examples": 0}
        elif arm == "S":
            rec["train"] = D1.train_copy(s, m, right, seed * 1000 + d)
        else:
            rp = random.Random(seed * 1000 + d).sample(pool, min(len(pool), len(right)))
            items = [("puzzle", p, e) for p, e in right] + [("replay", q, ans) for q, ans in rp]
            rec["train"] = train_mixed(s, m, items, seed * 1000 + d)
        meas = D1.measure(s, m, test, a.n_guess_test, panel, replies)
        rec["test"] = {k: meas[k] for k in ("lucky", "reached", "greedy")}
        rec["harm"] = D1.flips(base_harm, meas["harm"])
        rec["kl"] = meas["kl"]
        rec["minutes"] = round((time.time() - t0) / 60, 1)
        nights.append(rec)
        print(f"[dl3] {arm} s{seed} night {d}: {json.dumps(rec)}", flush=True)
    del m
    if s.dev == "cuda":
        s.torch.cuda.empty_cache()
    return {"arm": arm, "seed": seed, "nights": nights}


def score(res: dict) -> dict:
    """The registered marks (PASSMARKS.md)."""
    L0, R0 = res["base"]["lucky"], res["base"]["reached"]
    by = {(r["arm"], r["seed"]): r["nights"] for r in res["arms"]}
    seeds = sorted({r["seed"] for r in res["arms"]})
    fin = {k: v[-1] for k, v in by.items()}
    a_lost = [fin[("A", sd)]["harm"]["lost"] for sd in seeds]
    s_lost = [fin[("S", sd)]["harm"]["lost"] for sd in seeds]
    a_luck = [fin[("A", sd)]["test"]["lucky"] for sd in seeds]
    s_luck = [fin[("S", sd)]["test"]["lucky"] for sd in seeds]
    high = sum(1 for sd in seeds for n in by[("A", sd)] if n["harm"]["lost"] > 15)
    worse = 0
    for sd in seeds:
        seq = [L0] + [n["test"]["lucky"] for n in by[("A", sd)]]
        worse += sum(1 for x, y in zip(seq, seq[1:]) if y < 0.85 * x)
    m = {"L0": L0, "reached0": R0, "A_final_lost": a_lost, "S_final_lost": s_lost, "A_final_lucky": a_luck,
         "S_final_lucky": s_luck, "A_nights_lost_over_15": high, "A_worse_nights": worse,
         "A_final_reached": [fin[("A", sd)]["test"]["reached"] for sd in seeds]}
    m["F1 forgetting cut: A final lost <= 0.5 x S final lost (sums), and each A seed < each S seed"] = \
        sum(a_lost) <= 0.5 * sum(s_lost) and max(a_lost) < min(s_lost)
    m["F2 low forgetting all week: A nights with lost > 15 <= 1 of 14"] = high <= 1
    m["F3 still learns: A final lucky >= 2 x L0 on each seed, and A sum >= 0.85 x S sum"] = \
        all(x >= 2 * L0 for x in a_luck) and sum(a_luck) >= 0.85 * sum(s_luck)
    m["F4 nights rarely hurt the day's work: A nights with TEST lucky > 15% below the night before <= 1 of 14"] = \
        worse <= 1
    m["F5 variety kept: A final reached >= base on each seed"] = all(x >= R0 for x in m["A_final_reached"])
    keys = [k for k in m if k[:1] == "F" and k[1].isdigit()]
    m["verdict"] = ("INCONCLUSIVE" if L0 < 10 or sum(s_lost) < 20 else
                    ("PASS" if all(m[k] for k in keys) else "FAIL"))
    m["proved_wrong"] = all(x >= y for x, y in zip(a_lost, s_lost))
    return m


def run(a) -> None:
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    seeds = [int(x) for x in a.seeds.split(",")]
    keys = {(tuple(p["nums"]), p["target"]) for sd in seeds for d in range(1, a.nights + 1)
            for p in B2.puzzles(D1.DAY_SEED + a.seed_shift + 100 * sd + d, a.n_day)}
    test = [p for p in B2.puzzles(TEST_SEED + a.seed_shift, a.n_test + 300)
            if (tuple(p["nums"]), p["target"]) not in keys][:a.n_test]
    panel = D1.harm_panel()[:a.n_harm]
    pool = make_pool(s, a.n_ask, POOL_SEED + a.seed_shift)
    res = {"config": {k: v for k, v in vars(a).items() if k != "model"}, "n_test": len(test), "n_harm": len(panel),
           "temp": D1.TEMP, "test_seed": TEST_SEED, "pool_size": len(pool)}
    (out / "replay_pool.json").write_text(json.dumps(pool, indent=0), encoding="utf-8")
    print(f"[dl3] replay pool: {len(pool)} pairs", flush=True)
    base = s.model
    replies = [(q, D1.free_answer(s, q, base, 40)) for q in
               (D1.CHAT_PROMPTS + [it["q"] for it in panel[::5]])[:a.n_kl]]
    bm = D1.measure(s, base, test, a.n_guess_test, panel)
    res["base"] = {k: bm[k] for k in ("lucky", "reached", "greedy")}
    res["base"]["harm_right"] = sum(bm["harm"])
    print(f"[dl3] base: {res['base']}", flush=True)
    res["arms"] = []
    for arm in a.arms.split(","):
        for sd in seeds:
            res["arms"].append(run_arm(s, arm, sd, a, test, panel, replies, bm["harm"], pool))
            (out / "dl3_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    if set(a.arms.split(",")) >= {"S", "A"}:
        res["marks"] = score(res)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "dl3_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res.get("marks", {}), indent=1))


def selftest() -> None:
    bad = panel_words()
    assert clean_question("What is the capital of Peru?", bad) is None
    assert clean_question("How many legs does a cat have?", bad) is None
    assert clean_question("What is 2 plus 2?", bad) is None
    assert clean_question("How do I make my bread rise better?", bad) == "How do I make my bread rise better?"
    assert clean_question("Tell me a joke.", bad) is None

    def arm(name, sd, lucky, lost, reached=40):
        return {"arm": name, "seed": sd, "nights": [{"test": {"lucky": v, "reached": reached},
                                                      "harm": {"lost": l}} for v, l in zip(lucky, lost)]}
    res = {"base": {"lucky": 60, "reached": 35},
           "arms": [arm("S", 4, [90, 100, 110, 120, 125, 130, 140], [5, 8, 12, 16, 18, 24, 26]),
                    arm("S", 5, [80, 95, 90, 110, 120, 128, 135], [6, 9, 11, 15, 20, 28, 25]),
                    arm("A", 4, [85, 100, 105, 118, 120, 125, 130], [3, 4, 6, 5, 7, 8, 9]),
                    arm("A", 5, [85, 92, 99, 110, 115, 120, 128], [4, 5, 4, 6, 8, 7, 10])]}
    m = score(res)
    assert m["verdict"] == "PASS" and not m["proved_wrong"], m
    res["arms"][2]["nights"][-1]["harm"]["lost"] = 26
    assert score(res)["verdict"] == "FAIL"
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--arms", default="S,A")
    ap.add_argument("--seeds", default="4,5")
    ap.add_argument("--nights", type=int, default=7)
    ap.add_argument("--n-day", type=int, default=150)
    ap.add_argument("--n-guess", type=int, default=30)
    ap.add_argument("--n-test", type=int, default=100)
    ap.add_argument("--n-guess-test", type=int, default=20)
    ap.add_argument("--n-harm", type=int, default=300)
    ap.add_argument("--n-kl", type=int, default=60)
    ap.add_argument("--n-ask", type=int, default=1500)
    ap.add_argument("--seed-shift", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dev", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.dev:
        a.nights, a.n_day, a.n_guess, a.n_test, a.n_guess_test, a.n_harm, a.n_kl, a.n_ask = 2, 4, 4, 3, 3, 12, 4, 30
        a.seed_shift, a.seeds = a.seed_shift or 60000, "4"
    run(a)


if __name__ == "__main__":
    main()
