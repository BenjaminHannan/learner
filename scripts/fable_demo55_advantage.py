#!/usr/bin/env python3
"""55 — two ADDED demo beats for Ben's uncle-and-dad demo (Mac CPU, $0, additive only).

  Q10 "many facts, two hops"  — 40 people x 3 relations = 120 facts taught through the
      same LISTENING path as the modes54 demo (ModeScheduler + Listening + notebook
      contract), then 20 frozen two-hop questions. The notebook answers with the
      contract's hard-coded hop loop. The plain-transformer baseline is TRAINED ON THE
      SAME 120 TEACHING LINES (byte-identical, next-token language modeling) under
      modes54's budget rule, seeds 5401/5402/5403 reported per seed, and then asked
      the same 20 questions (it never sees a question during training).

  Q11 "learn after training"  — after training, 5 brand-new facts (5 new names) taught
      through LISTENING, then 5 questions. Notebook writes + answers (mark A3 = 5/5).
      Baseline reported twice per seed: FROZEN (not retrained — a frozen net cannot
      learn from one sentence) and a fair variant fine-tuned for at least the same
      wall-clock the notebook's Q11 beat needed (minimum 1 update).

Everything modes54 owns is IMPORTED, never edited: fable_modes54_demo (norm, tokenize,
detok, TinyTransformer, greedy_decode, TRAIN_SEEDS/TRAIN_UPDATES/TRAIN_LR),
fable_modes54_scheduler, fable_listening_m1, fable_notebook_contract.

The modes54 budget rule, as restated for this run (also frozen in PASSMARKS.md before
the registered run): plain-PyTorch TinyTransformer (2 layers, d_model 64, 4 heads,
FFN 128, word-level vocab over all demo texts, positional table widened 512 -> 768 to
fit the 600-token story), full-batch Adam lr 1e-3, grad-clip 1.0, exactly 600 fixed
updates, seeds 5401/5402/5403 reported separately and never averaged, greedy
decode <= 8 tokens, exact match after word normalization. Q10 training = one
full-batch next-token sequence over the exact 120 teaching lines (the same bytes the
notebook heard); the 20 questions appear only at evaluation. Q11 fine-tune: fresh
Adam lr 1e-3, full-batch next-token LM on the 5 new teaching lines, updates until
wall-clock >= the notebook's Q11 beat (minimum 1 update).

    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy \
      python -B scripts/fable_demo55_advantage.py --out artifacts/fable-demo55-20260921
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C          # noqa: E402
import fable_listening_m1 as L               # noqa: E402
from fable_modes54_scheduler import ModeScheduler        # noqa: E402
import fable_modes54_demo as D               # noqa: E402  (reused, never edited)

# ---------------------------------------------------------------- frozen data
# 40 uniquely named people; deterministic, frozen before any run.
PEOPLE = [
    "Ada", "Bo", "Cleo", "Dane", "Edda", "Finn", "Gale", "Hana", "Iris", "Jax",
    "Keir", "Lune", "Milo", "Naya", "Orin", "Pia", "Quinn", "Rosa", "Sven", "Tara",
    "Ugo", "Vera", "Wren", "Xiu", "Yara", "Zane", "Anya", "Bram", "Cora", "Dex",
    "Esme", "Fritz", "Gwen", "Hector", "Ilse", "Jonas", "Kai", "Lena", "Marek",
    "Nina",
]
assert len(PEOPLE) == 40 and len(set(PEOPLE)) == 40
CITIES = ["Porto", "Lisbon", "Oslo", "Paris", "Rome", "Bern",
          "Krakow", "Osaka", "Cairo", "Lima"]


def mother_idx(i: int) -> int:
    return (i + 1) % 40


def boss_idx(i: int) -> int:
    return (7 * i + 3) % 40          # bijection on Z/40 (gcd(7,40)=1), never i


def build_q10() -> tuple[list[str], list[dict]]:
    lines: list[str] = []
    for i, name in enumerate(PEOPLE):
        lines.append(f"teach {name} mother -> {PEOPLE[mother_idx(i)]}")
        lines.append(f"teach {name} boss -> {PEOPLE[boss_idx(i)]}")
        lines.append(f"teach {name} city = {CITIES[i % 10]}")
    assert len(lines) == 120
    items: list[dict] = []
    n = 0

    def add(i: int, rels: list[str], en: str, gold: str) -> None:
        nonlocal n
        n += 1
        items.append(dict(qid=f"Q10.{n}", nb=f"ask {PEOPLE[i]} {' '.join(rels)}",
                          en=en, gold=gold))

    for i in range(0, 7):            # boss of X's mother  (2 entity hops)
        add(i, ["mother", "boss"],
            f"Who is the boss of {PEOPLE[i]}'s mother?",
            PEOPLE[(7 * (i + 1) + 3) % 40])
    for i in range(7, 14):           # mother of X's boss
        add(i, ["boss", "mother"],
            f"Who is the mother of {PEOPLE[i]}'s boss?",
            PEOPLE[(boss_idx(i) + 1) % 40])
    for i in range(14, 20):          # city of X's mother (hop then literal)
        add(i, ["mother", "city"],
            f"Where does {PEOPLE[i]}'s mother live?",
            CITIES[(i + 1) % 10])
    assert len(items) == 20
    return lines, items


Q10_LINES, Q10_ITEMS = build_q10()

# Q11: 5 brand-new facts, 5 brand-new names (none of them among the 40).
Q11_LINES = [
    "teach Kip city = Bern",
    "teach Lark city = Lima",
    "teach Moth boss -> Kip",
    "teach Nyx mother -> Lark",
    "teach Opal city = Cairo",
]
Q11_ITEMS = [
    dict(qid="Q11.1", nb="ask Kip city", en="Where does Kip live?", gold="Bern"),
    dict(qid="Q11.2", nb="ask Lark city", en="Where does Lark live?", gold="Lima"),
    dict(qid="Q11.3", nb="ask Moth boss", en="Who is the boss of Moth?", gold="Kip"),
    dict(qid="Q11.4", nb="ask Nyx mother", en="Who is the mother of Nyx?",
         gold="Lark"),
    dict(qid="Q11.5", nb="ask Opal city", en="Where does Opal live?", gold="Cairo"),
]
_q11_names = {"Kip", "Lark", "Moth", "Nyx", "Opal"}
assert not (_q11_names & set(PEOPLE))

STORY10 = "\n".join(Q10_LINES)
STORY11 = "\n".join(Q10_LINES + Q11_LINES)
MAX_LEN = 768                      # 600 story tokens + question + answer + margin
A5_SECONDS = 600

BUDGET_RULE = (
    "modes54 budget rule (restated): plain-PyTorch TinyTransformer (2 layers, "
    "d_model 64, 4 heads, FFN 128, word-level vocab over all demo texts, "
    "positional table widened 512->768 to fit the 600-token story), full-batch "
    "Adam lr 1e-3, grad-clip 1.0, exactly 600 fixed updates, seeds "
    "5401/5402/5403 reported separately and never averaged, greedy decode <= 8 "
    "tokens, exact match after word normalization. Q10 training = one full-batch "
    "next-token sequence over the byte-identical 120 teaching lines the notebook "
    "heard; the same 20 questions are asked only at evaluation (never trained "
    "on). Q11 frozen = zero updates after Q10 training; Q11 fine-tune = fresh "
    "Adam lr 1e-3, full-batch next-token LM on the 5 new teaching lines, updates "
    "until wall-clock >= the notebook's Q11 beat (minimum 1 update)."
)


# ------------------------------------------------- notebook side (LISTENING path)
def run_notebook(state_dir: str) -> dict:
    """Teaches + asks through the same ModeScheduler+Listening path modes54 used.

    Also counts WRONG WRITES (mark A4): a teach/correct line must save exactly one
    fact whose stored ``raw`` equals the line; every other line must save none.
    """
    nb = C.Notebook(state_dir)
    ear = L.Listening(nb)
    sched = ModeScheduler(turn_handler=ear.hear, sleep_threshold=100_000)
    transcript: list[dict] = []
    wrong_writes: list[dict] = []
    replies: dict[str, str] = {}

    def say(line: str, tag: str) -> str:
        before = set(nb.facts)
        sched.submit(line)
        event = sched.step()
        reply = event["detail"].get("reply", "")
        new_ids = sorted(set(nb.facts) - before, key=lambda x: int(x[1:]))
        act = line.split()[0] if line.split() else ""
        if act in ("teach", "correct"):
            ok = (len(new_ids) == 1
                  and nb.facts[new_ids[0]].get("raw") == line)
        else:
            ok = not new_ids          # ask (and any non-teaching line) writes nothing
        if not ok:
            wrong_writes.append({
                "tag": tag, "line": line, "new_fact_ids": new_ids,
                "raws": [nb.facts[f].get("raw") for f in new_ids]})
        transcript.append({"tag": tag, "ben": line, "fable": reply,
                           "mode": event["mode"]})
        return reply

    # --- Q10: 120 teachings, then the 20 two-hop questions --------------------
    for i, line in enumerate(Q10_LINES):
        say(line, f"q10teach[{i}]")
    for item in Q10_ITEMS:
        replies[item["qid"]] = say(item["nb"], "q10ask")

    # --- Q11: 5 brand-new facts (wall-clock timed), then 5 questions ----------
    t_q11 = time.monotonic()
    for i, line in enumerate(Q11_LINES):
        say(line, f"q11teach[{i}]")
    for item in Q11_ITEMS:
        replies[item["qid"]] = say(item["nb"], "q11ask")
    t_nb_q11 = time.monotonic() - t_q11

    heard_q10 = [row["ben"] for row in transcript if row["tag"].startswith("q10teach")]
    heard_q11 = [row["ben"] for row in transcript if row["tag"].startswith("q11teach")]
    return {"nb": nb, "sched": sched, "transcript": transcript,
            "replies": replies, "wrong_writes": wrong_writes,
            "t_nb_q11": t_nb_q11, "heard_q10": heard_q10,
            "heard_q11": heard_q11}


def score(replies: dict, items: list[dict]) -> dict:
    correct, detail = {}, {}
    for item in items:
        reply = replies.get(item["qid"], "")
        ok = D.norm(reply) == D.norm(item["gold"])
        correct[item["qid"]] = int(ok)
        detail[item["qid"]] = {"reply": reply, "gold": item["gold"],
                               "correct": int(ok)}
    return {"correct": correct, "total": sum(correct.values()), "detail": detail}


# ------------------------------------------------------------ baseline side
def build_vocab() -> tuple[dict, dict, int, int, int, int]:
    texts = [STORY10, STORY11]
    for item in Q10_ITEMS + Q11_ITEMS:
        texts += [item["en"], item["gold"]]
    specials = ["<PAD>", "<SEP>", "<EOS>", "<UNK>"]
    vocab_words = sorted({tok for text in texts for tok in D.tokenize(text)})
    vocab = {w: i for i, w in enumerate(specials + vocab_words)}
    inv = {i: w for w, i in vocab.items()}
    return vocab, inv, 0, 1, 2, 3        # pad, sep, eos, unk


def make_rows(items: list[dict], story: str, vocab: dict,
              sep_id: int, eos_id: int, unk_id: int) -> tuple[list[dict], int]:
    story_ids = [vocab.get(tok, unk_id) for tok in D.tokenize(story)]
    oov = 0
    rows = []
    for item in items:
        q_ids = [vocab.get(t, unk_id) for t in D.tokenize(item["en"])]
        a_ids = [vocab.get(t, unk_id) for t in D.tokenize(item["gold"])]
        oov += sum(1 for t in D.tokenize(item["en"] + " " + item["gold"])
                   if t not in vocab)
        prefix = story_ids + [sep_id] + q_ids + [sep_id]
        full = prefix + a_ids + [eos_id]
        rows.append({"qid": item["qid"], "prefix": prefix, "full": full,
                     "ans_start": len(prefix), "gold": item["gold"]})
    return rows, oov


def train_loop(model, ids, labels, updates: int, lr: float, pad_id: int) -> float:
    """Full-batch Adam, grad-clip 1.0 — byte-for-byte modes54's training loop."""
    torch = model.torch
    optim = torch.optim.Adam(model.parameters(), lr=lr)
    final_loss = None
    for _ in range(updates):
        loss = model.forward_loss(ids, labels, pad_id)
        optim.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optim.step()
        final_loss = float(loss.detach())
    return final_loss


def encode_lm(model, token_ids: list[int], pad_id: int):
    """One full-batch next-token sequence; labels = ids (CE does the shift)."""
    torch = model.torch
    ids = torch.tensor([token_ids], dtype=torch.long)
    return ids, ids.clone()


def greedy_decode_batch(model, prefixes: list[list[int]], eos_id: int,
                        pad_id: int, max_new: int = 8) -> list[list[int]]:
    """Batched greedy decode, token-identical to D.greedy_decode (cross-checked).

    Right-padding cannot change a row's logits: causal masking already forbids a
    real position from attending to later (pad) positions, and pad keys are masked
    too, so logits[i, len_i-1] equals the unpadded run's.
    """
    torch = model.torch
    seqs = [list(p) for p in prefixes]
    done = [False] * len(seqs)
    gens: list[list[int]] = [[] for _ in seqs]
    for _ in range(max_new):
        active = [i for i in range(len(seqs)) if not done[i]]
        if not active:
            break
        width = max(len(seqs[i]) for i in active)
        ids = torch.full((len(active), width), pad_id, dtype=torch.long)
        for row, i in enumerate(active):
            ids[row, :len(seqs[i])] = torch.tensor(seqs[i])
        pad = ids.eq(pad_id)
        with torch.no_grad():
            logits = model.net(ids, pad, model.causal(width))
        for row, i in enumerate(active):
            last = len(seqs[i]) - 1
            nxt = int(logits[row, last].argmax(-1))
            if nxt == eos_id:
                done[i] = True
            else:
                seqs[i].append(nxt)
                gens[i].append(nxt)
    return gens


def decode_preds(model, rows, inv, eos_id, pad_id) -> tuple[dict, bool]:
    gens = greedy_decode_batch(model, [r["prefix"] for r in rows], eos_id, pad_id)
    ref = D.greedy_decode(model, rows[0]["prefix"], eos_id, pad_id, max_new=8)
    cross_ok = gens[0] == ref
    preds = {row["qid"]: D.detok([inv[i] for i in gens[n]])
             for n, row in enumerate(rows)}
    return preds, cross_ok


def run_baseline(seeds: tuple[int, ...], t_nb_q11: float) -> dict:
    import torch
    vocab, inv, pad_id, sep_id, eos_id, unk_id = build_vocab()
    rows10, oov10 = make_rows(Q10_ITEMS, STORY10, vocab, sep_id, eos_id, unk_id)
    rows11, oov11 = make_rows(Q11_ITEMS, STORY11, vocab, sep_id, eos_id, unk_id)
    # training sequences: the teaching lines only (byte-identical to what the
    # notebook heard through LISTENING); questions appear only at evaluation
    lm_story10 = [vocab.get(t, unk_id) for t in D.tokenize(STORY10)]
    lm_q11_lines = [vocab.get(t, unk_id)
                    for t in D.tokenize("\n".join(Q11_LINES))]

    per_seed = {}
    for seed in seeds:
        t_seed = time.monotonic()
        torch.manual_seed(seed)
        model = D.TinyTransformer(len(vocab), max_len=MAX_LEN)
        n_params = sum(p.numel() for p in model.parameters())

        # ---- Q10 training: next-token LM on the 120 teaching lines (modes54
        #      budget: full-batch Adam, 600 updates) — questions never trained on
        t0 = time.monotonic()
        lm_ids, lm_labels = encode_lm(model, lm_story10, pad_id)
        final_loss = train_loop(model, lm_ids, lm_labels, D.TRAIN_UPDATES,
                                D.TRAIN_LR, pad_id)
        train_s = time.monotonic() - t0
        preds10, cross10 = decode_preds(model, rows10, inv, eos_id, pad_id)
        correct10 = {it["qid"]: int(D.norm(preds10[it["qid"]]) == D.norm(it["gold"]))
                     for it in Q10_ITEMS}

        # ---- Q11 FROZEN (no updates) ----
        preds11f, cross11f = decode_preds(model, rows11, inv, eos_id, pad_id)
        correct11f = {it["qid"]: int(D.norm(preds11f[it["qid"]]) == D.norm(it["gold"]))
                      for it in Q11_ITEMS}

        # ---- Q11 fine-tune: >= the notebook's Q11 wall-clock, min 1 update,
        #      next-token LM on the 5 brand-new teaching lines ----
        optim = torch.optim.Adam(model.parameters(), lr=D.TRAIN_LR)
        ft_ids, ft_labels = encode_lm(model, lm_q11_lines, pad_id)
        ft_t0 = time.monotonic()
        ft_steps = 0
        ft_loss = None
        while time.monotonic() - ft_t0 < t_nb_q11 or ft_steps == 0:
            loss = model.forward_loss(ft_ids, ft_labels, pad_id)
            optim.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optim.step()
            ft_loss = float(loss.detach())
            ft_steps += 1
            if ft_steps > 100_000:          # safety valve, never expected
                break
        ft_s = time.monotonic() - ft_t0
        preds11t, cross11t = decode_preds(model, rows11, inv, eos_id, pad_id)
        correct11t = {it["qid"]: int(D.norm(preds11t[it["qid"]]) == D.norm(it["gold"]))
                      for it in Q11_ITEMS}

        per_seed[str(seed)] = {
            "parameters": n_params,
            "final_train_loss": round(final_loss, 6),
            "train_seconds": round(train_s, 2),
            "q10": {"predictions": preds10, "correct": correct10,
                    "total": sum(correct10.values())},
            "q11_frozen": {"predictions": preds11f, "correct": correct11f,
                           "total": sum(correct11f.values())},
            "fine_tune": {"steps": ft_steps, "seconds": round(ft_s, 3),
                          "notebook_wallclock": round(t_nb_q11, 4),
                          "final_loss": round(ft_loss, 6) if ft_loss else None},
            "q11_finetuned": {"predictions": preds11t, "correct": correct11t,
                              "total": sum(correct11t.values())},
            "decode_crosscheck": bool(cross10 and cross11f and cross11t),
            "seed_seconds": round(time.monotonic() - t_seed, 2),
        }
        row = per_seed[str(seed)]
        print(f"baseline seed {seed}: params {n_params}, Q10 train "
              f"{D.TRAIN_UPDATES} LM updates on the 120 teaching lines "
              f"{row['train_seconds']}s (loss {row['final_train_loss']}), "
              f"Q10 {row['q10']['total']}/20, "
              f"Q11 frozen {row['q11_frozen']['total']}/5, fine-tune "
              f"{ft_steps} step(s) {row['fine_tune']['seconds']}s "
              f"(notebook Q11 beat {t_nb_q11:.4f}s), Q11 finetuned "
              f"{row['q11_finetuned']['total']}/5", flush=True)

    return {"budget_rule": BUDGET_RULE, "seeds": list(seeds),
            "vocab_size": len(vocab), "oov_hits": oov10 + oov11,
            "updates": D.TRAIN_UPDATES, "lr": D.TRAIN_LR,
            "max_len": MAX_LEN, "per_seed": per_seed,
            "trained_on": "Q10: next-token LM on the byte-identical 120 teaching "
                          "lines (one 600-token full-batch sequence); the 20 "
                          "questions are never trained on, only asked at "
                          "evaluation"}


# ------------------------------------------------------------------- main
def main(argv=None) -> int:
    import shutil
    t_start = time.monotonic()
    parser = argparse.ArgumentParser(
        description="55 added demo beats: Q10 two-hop, Q11 learn-after-training")
    parser.add_argument("--out", default="artifacts/fable-demo55-20260921")
    parser.add_argument("--state-dir", default=None,
                        help="notebook location (default: OUT/demo55-notebook)")
    parser.add_argument("--skip-baseline", action="store_true")
    parser.add_argument("--seeds", default="5401,5402,5403",
                        help="baseline seeds (registered run uses the default)")
    args = parser.parse_args(argv)
    seeds = tuple(int(s) for s in args.seeds.split(","))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    state = Path(args.state_dir) if args.state_dir else out / "demo55-notebook"
    if state.exists():
        shutil.rmtree(state)

    print("=" * 72, flush=True)
    print("FABLE DEMO 55 — added beats: Q10 many-facts two-hop, Q11 learn-after-training",
          flush=True)
    print("=" * 72, flush=True)

    run = run_notebook(str(state))
    for row in run["transcript"]:
        print(f"  [{row['mode']:<9}] BEN:   {row['ben']}", flush=True)
        first = str(row["fable"]).split("\n")[0]
        print(f"             FABLE: {first}", flush=True)

    identity10 = run["heard_q10"] == Q10_LINES
    identity11 = run["heard_q11"] == Q11_LINES
    nb10 = score(run["replies"], Q10_ITEMS)
    nb11 = score(run["replies"], Q11_ITEMS)
    wrong_writes = run["wrong_writes"]
    t_nb = run["t_nb_q11"]
    print(f"\nnotebook Q10 {nb10['total']}/20, Q11 {nb11['total']}/5, "
          f"wrong writes {len(wrong_writes)}, notebook Q11 beat {t_nb:.4f}s, "
          f"story identity Q10={identity10} Q11={identity11}", flush=True)

    baseline = None
    if not args.skip_baseline:
        print("\n--- baseline: plain small transformer, modes54 budget rule ---",
              flush=True)
        baseline = run_baseline(seeds, t_nb)

    # ------------------------------------------------------------------ marks
    a1 = nb10["total"] >= 18
    a2 = bool(baseline) and set(baseline["per_seed"]) == {str(s) for s in seeds} and all(
        len(r["q10"]["correct"]) == 20 and len(r["q11_frozen"]["correct"]) == 5
        and len(r["q11_finetuned"]["correct"]) == 5 and r["decode_crosscheck"]
        for r in baseline["per_seed"].values())
    a3 = nb11["total"] == 5
    a4 = len(wrong_writes) == 0
    elapsed = time.monotonic() - t_start
    a5 = elapsed < A5_SECONDS
    marks = {
        "A1_notebook_q10_ge_18": {"pass": a1, "value": f"{nb10['total']}/20"},
        "A2_baseline_reported_per_seed": {
            "pass": a2,
            "value": ("3/3 seeds x (20+5+5) integers, decode cross-check ok"
                      if a2 else "incomplete report or cross-check failed")},
        "A3_notebook_q11_5_of_5": {"pass": a3, "value": f"{nb11['total']}/5"},
        "A4_wrong_writes_zero": {"pass": a4, "value": str(len(wrong_writes))},
        "A5_under_10_minutes": {"pass": a5, "value": f"{elapsed:.1f}s"},
    }

    # ------------------------------------------------------------------ report
    report = {
        "beats": ["Q10 many-facts two-hop", "Q11 learn-after-training"],
        "q10_items": Q10_ITEMS, "q11_items": Q11_ITEMS,
        "q10_lines": Q10_LINES, "q11_lines": Q11_LINES,
        "notebook": {"q10": nb10, "q11": nb11,
                     "wrong_writes": wrong_writes,
                     "wrong_write_rule": "teach/correct -> exactly one new fact "
                                          "whose stored raw equals the line; any "
                                          "other line -> zero new facts",
                     "t_q11_wallclock": t_nb,
                     "identity_q10": identity10, "identity_q11": identity11,
                     "modes_seen": sorted({e["to"] for e in run["sched"].mode_log})},
        "baseline": baseline,
        "marks": marks,
        "elapsed_seconds": round(elapsed, 1),
        "seeds": list(seeds),
        "registered": not args.skip_baseline,
    }
    (out / "demo55-results.json").write_text(json.dumps(report, indent=1))
    (out / "demo55-transcript.txt").write_text(
        "\n".join(f"[{r['mode']}] {r['ben']}\n    -> {r['fable']}"
                  for r in run["transcript"]))

    print("\n" + "=" * 72, flush=True)
    print("Q10 SCOREBOARD — 20 two-hop questions (exact integers, never averaged)",
          flush=True)
    print("=" * 72, flush=True)
    header = f"{'qid':<6} {'gold':<8} {'notebook':<10}"
    if baseline:
        for s in seeds:
            header += f" {'base' + str(s):<10}"
    print(header, flush=True)
    for n, item in enumerate(Q10_ITEMS):
        line = (f"{item['qid']:<6} {item['gold']:<8} "
                f"{nb10['correct'][item['qid']]} "
                f"{D.norm(nb10['detail'][item['qid']]['reply'])[:8]:<9}")
        if baseline:
            for s in seeds:
                cell = baseline["per_seed"][str(s)]
                pred = cell["q10"]["predictions"][item["qid"]]
                line += (f" {cell['q10']['correct'][item['qid']]} "
                         f"{D.norm(pred)[:8]:<8}")
        print(line, flush=True)
    tot = f"TOTAL  Q10     {nb10['total']}/20"
    if baseline:
        for s in seeds:
            tot += f"  {baseline['per_seed'][str(s)]['q10']['total']}/20"
    print(tot, flush=True)

    print("\n" + "=" * 72, flush=True)
    print("Q11 SCOREBOARD — 5 brand-new facts taught AFTER training", flush=True)
    print("=" * 72, flush=True)
    header = f"{'qid':<6} {'gold':<8} {'notebook':<10}"
    if baseline:
        for s in seeds:
            header += f" {'frz' + str(s):<8} {'ftn' + str(s):<8}"
    print(header, flush=True)
    for item in Q11_ITEMS:
        line = (f"{item['qid']:<6} {item['gold']:<8} "
                f"{nb11['correct'][item['qid']]} "
                f"{D.norm(nb11['detail'][item['qid']]['reply'])[:8]:<9}")
        if baseline:
            for s in seeds:
                cell = baseline["per_seed"][str(s)]
                fp = cell["q11_frozen"]["predictions"][item["qid"]]
                tp = cell["q11_finetuned"]["predictions"][item["qid"]]
                line += (f" {cell['q11_frozen']['correct'][item['qid']]} "
                         f"{D.norm(fp)[:6]:<6} "
                         f"{cell['q11_finetuned']['correct'][item['qid']]} "
                         f"{D.norm(tp)[:6]:<6}")
        print(line, flush=True)
    tot = f"TOTAL  Q11     {nb11['total']}/5"
    if baseline:
        for s in seeds:
            cell = baseline["per_seed"][str(s)]
            tot += (f"  frz {cell['q11_frozen']['total']}/5"
                    f" ftn {cell['q11_finetuned']['total']}/5"
                    f" ({cell['fine_tune']['steps']} ft-step(s), "
                    f"nb beat {cell['fine_tune']['notebook_wallclock']}s)")
    print(tot, flush=True)

    print("\n" + "=" * 72, flush=True)
    print("PASS MARKS (sealed in PASSMARKS.md before this registered run)", flush=True)
    print("=" * 72, flush=True)
    for key in sorted(marks):
        m = marks[key]
        print(f"  {key:<32} {'PASS' if m['pass'] else 'FAIL':<5} {m['value']}",
              flush=True)
    print(f"\nstory identity Q10={identity10} Q11={identity11}; wrong writes "
          f"counted={len(wrong_writes)}", flush=True)
    if wrong_writes:
        for w in wrong_writes:
            print(f"  WRONG WRITE: {w}", flush=True)
    if baseline:
        print(f"baseline vocab {baseline['vocab_size']}, oov hits "
              f"{baseline['oov_hits']}, seeds {baseline['seeds']}", flush=True)
        print(f"budget rule: {BUDGET_RULE}", flush=True)
    print(f"wrote {out / 'demo55-results.json'}", flush=True)
    print(f"TOTAL_ELAPSED_SECONDS {elapsed:.1f}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
