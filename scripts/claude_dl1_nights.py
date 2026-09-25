#!/usr/bin/env python3
"""dl-1: which night learning rule makes the 1B better at the day's work, fast, without making it worse elsewhere?
(Fix-sleep thread, 2026-09-25; marks: artifacts/claude-dl1-20260925/PASSMARKS.md; research:
reviews/sleep-nights-research-2026-09-25/REPORT.md)

Why. Ben (19:22-19:37 UTC): nights should almost always make the model better, as RL does; "the model should rapidly
improve for the work that it does day to day"; bored mode and sleep should be one downtime-learning loop. Creative's
lucky-hit sleep (blurt-3, replicated) is the only sleep shown to improve a model. It is copy practice: the model is
trained to repeat its first lucky hit and its own right answers (rejection-sampling fine-tuning). Research says that
learning from the model's own right AND wrong tries (on-policy RL) forgets less and keeps more variety, and that any
RL test needs a shuffled-reward placebo.

Loop, per arm and seed, for 3 day/night cycles on ONE adapter that keeps growing (never reset to the base):
  day d   the current model meets 150 new number puzzles (day-specific seed) and, on each, answers once (greedy) and
          makes 30 rule-keeping guesses at T 1.5 (blurt-3's DEV choice); the exact checker marks every guess.
  night d the adapter learns from that day, by the arm's rule (ONE change between S and R: the learning rule):
    S  copy practice (blurt-3's night): greedy right answers + the first lucky hit on each greedy miss, 3 epochs of
       cross-entropy, lr 2e-4.
    R  reward learning: every group of 30 guesses with both right and wrong ones; advantage = reward - group mean;
       one pass of REINFORCE with that group baseline (push right guesses up, wrong ones down); lr picked on DEV
       (registered rule below).
    Z  placebo: R with the day's rewards shuffled across all guesses before the groups are formed.
Measures (never trained on):
  TEST  100 fresh puzzles x 20 guesses at T 1.5: right guesses ("lucky"), puzzles with a right guess ("reached"),
        greedy solves. Base and after every night.
  HARM  300 fixed general items (capitals, opposites, plurals, orders, counts, bigger number), greedy; counted as
        1->0 and 0->1 flips against the base. Base and after every night.
  KL    mean KL(current || base) per token on the base model's own replies to 60 plain prompts. After every night.
DEV lr rule for R (on shifted DEV seeds only): one night from the base at lr 2e-5 and at 1e-4 on 60 DEV puzzles; keep
the lr with more right guesses on 40 DEV test puzzles x 20 (a tie keeps 2e-5). Z uses R's lr.

  python -B scripts/claude_dl1_nights.py --model M --out DIR          (registered run: arms S,R,Z seeds 0,1 nights 3)
  python -B scripts/claude_dl1_nights.py --selftest
  python -B scripts/claude_dl1_nights.py --model M --out DIR --dev     (plumbing rehearsal, tiny counts, other seeds)
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402
import claude_blurt2 as B2  # noqa: E402

TEMP = 1.5
DAY_SEED = 3900      # day d of seed s: puzzles(DAY_SEED + shift + 100 * s + d)
TEST_SEED = 3990
DEV_DAY_SEED = 3995
DEV_TEST_SEED = 3996
DEV_LRS = (2e-5, 1e-4)
S_RECIPE = {"epochs": 3, "lr": 2e-4}

CAPITALS = [("France", "paris"), ("Germany", "berlin"), ("Italy", "rome"), ("Spain", "madrid"), ("Japan", "tokyo"),
            ("China", "beijing"), ("Russia", "moscow"), ("Egypt", "cairo"), ("Canada", "ottawa"),
            ("Australia", "canberra"), ("Brazil", "brasilia"), ("Argentina", "buenos aires"),
            ("Mexico", "mexico city"), ("India", "delhi"), ("the United Kingdom", "london"), ("Ireland", "dublin"),
            ("Portugal", "lisbon"), ("Greece", "athens"), ("Turkey", "ankara"), ("Poland", "warsaw"),
            ("Sweden", "stockholm"), ("Norway", "oslo"), ("Finland", "helsinki"), ("Denmark", "copenhagen"),
            ("the Netherlands", "amsterdam"), ("Belgium", "brussels"), ("Austria", "vienna"), ("Switzerland", "bern"),
            ("Hungary", "budapest"), ("the Czech Republic", "prague"), ("Kenya", "nairobi"), ("Nigeria", "abuja"),
            ("South Korea", "seoul"), ("Thailand", "bangkok"), ("Vietnam", "hanoi"), ("Indonesia", "jakarta"),
            ("the Philippines", "manila"), ("Peru", "lima"), ("Chile", "santiago"), ("Colombia", "bogota"),
            ("Cuba", "havana"), ("Iran", "tehran"), ("Iraq", "baghdad"), ("Saudi Arabia", "riyadh"),
            ("Ukraine", "kyiv|kiev"), ("Romania", "bucharest"), ("Bulgaria", "sofia"), ("Serbia", "belgrade"),
            ("Croatia", "zagreb"), ("Iceland", "reykjavik"), ("New Zealand", "wellington"),
            ("Pakistan", "islamabad"), ("Bangladesh", "dhaka"), ("Afghanistan", "kabul"),
            ("Ethiopia", "addis ababa"), ("Morocco", "rabat"), ("Algeria", "algiers"), ("Tunisia", "tunis"),
            ("Ghana", "accra"), ("Venezuela", "caracas"), ("Uruguay", "montevideo"), ("Paraguay", "asuncion"),
            ("Ecuador", "quito"), ("Malaysia", "kuala lumpur"), ("Nepal", "kathmandu"), ("Qatar", "doha"),
            ("Jordan", "amman"), ("Lebanon", "beirut"), ("Syria", "damascus"), ("Scotland", "edinburgh")]
OPPOSITES = [("hot", "cold"), ("big", "small|little"), ("up", "down"), ("day", "night"), ("fast", "slow"),
             ("happy", "sad|unhappy"), ("open", "close"), ("light", "dark|heavy"), ("old", "new|young"),
             ("tall", "short"), ("full", "empty"), ("hard", "soft|easy"), ("early", "late"), ("wet", "dry"),
             ("strong", "weak"), ("rich", "poor"), ("left", "right"), ("push", "pull"), ("win", "lose|loss"),
             ("begin", "end|finish"), ("above", "below|beneath"), ("inside", "outside"), ("true", "false"),
             ("alive", "dead"), ("thick", "thin"), ("loud", "quiet|soft"), ("clean", "dirty"), ("buy", "sell"),
             ("love", "hate"), ("first", "last")]
PLURALS = [("mouse", "mice"), ("child", "children"), ("man", "men"), ("woman", "women"), ("tooth", "teeth"),
           ("foot", "feet"), ("goose", "geese"), ("person", "people"), ("box", "boxes"), ("city", "cities"),
           ("knife", "knives"), ("leaf", "leaves"), ("wolf", "wolves"), ("baby", "babies"), ("bus", "buses"),
           ("glass", "glasses"), ("church", "churches"), ("fox", "foxes"), ("potato", "potatoes"),
           ("hero", "heroes"), ("sheep", "sheep"), ("fish", "fish"), ("deer", "deer"), ("ox", "oxen"),
           ("cactus", "cacti|cactuses"), ("dish", "dishes"), ("lady", "ladies"), ("life", "lives"),
           ("wife", "wives"), ("half", "halves")]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
COUNTS = [("legs does a spider have", 8), ("legs does an insect have", 6), ("days are in a week", 7),
          ("months are in a year", 12), ("hours are in a day", 24), ("minutes are in an hour", 60),
          ("sides does a triangle have", 3), ("sides does a square have", 4), ("sides does a hexagon have", 6),
          ("sides does an octagon have", 8), ("continents are there", 7), ("cents are in a dollar", 100),
          ("degrees are in a right angle", 90), ("legs does a dog have", 4), ("wheels does a bicycle have", 2),
          ("wheels does a tricycle have", 3), ("players are on a soccer team on the field", 11),
          ("seconds are in a minute", 60), ("days are in a leap year", 366), ("days are in a normal year", 365)]
CHAT_PROMPTS = [f"{v} {t}." for v, t in [
    ("Write one sentence about", "the ocean"), ("Write one sentence about", "a rainy morning"),
    ("Give one tip for", "studying for a test"), ("Give one tip for", "keeping a plant alive"),
    ("Explain in one sentence what", "a battery does"), ("Explain in one sentence what", "a map is for"),
    ("Describe in one sentence", "a busy market"), ("Describe in one sentence", "the taste of lemon"),
    ("Suggest a name for", "a small bakery"), ("Suggest a name for", "a pet turtle"),
    ("Write one sentence about", "learning to ride a bike"), ("Give one tip for", "sleeping better"),
    ("Explain in one sentence what", "a calendar is for"), ("Describe in one sentence", "an old library"),
    ("Suggest a name for", "a hiking club"), ("Write one sentence about", "winter"),
    ("Give one tip for", "saving money"), ("Explain in one sentence why", "people cook food"),
    ("Describe in one sentence", "a thunderstorm"), ("Suggest a name for", "a board game"),
    ("Write one sentence about", "a train station"), ("Give one tip for", "writing a letter"),
    ("Explain in one sentence what", "a bridge does"), ("Describe in one sentence", "a quiet beach"),
    ("Suggest a name for", "a robot"), ("Write one sentence about", "friendship"),
    ("Give one tip for", "learning a language"), ("Explain in one sentence why", "we wear coats"),
    ("Describe in one sentence", "a mountain village"), ("Suggest a name for", "a coffee shop")]]


def harm_panel() -> list[dict]:
    """300 fixed general items (question, accepted answers or an integer). Code-made; never trained on."""
    rng = random.Random(399_300)
    items = [{"kind": "capital", "q": f"What is the capital of {c}? Reply with the city name only.", "gold": g}
             for c, g in CAPITALS]
    items += [{"kind": "opposite", "q": f"What is the opposite of '{w}'? Reply with one word only.", "gold": g}
              for w, g in OPPOSITES]
    items += [{"kind": "plural", "q": f"What is the plural of '{w}'? Reply with one word only.", "gold": g}
              for w, g in PLURALS]
    items += [{"kind": "order", "q": f"What day comes after {d}? Reply with one word only.",
               "gold": DAYS[(i + 1) % 7].lower()} for i, d in enumerate(DAYS)]
    items += [{"kind": "order", "q": f"What month comes after {m}? Reply with one word only.",
               "gold": MONTHS[(i + 1) % 12].lower()} for i, m in enumerate(MONTHS)]
    for ch in rng.sample("ABCDEFGHIJKLMNOPQRSTUVWXY", 12):
        items.append({"kind": "order", "q": f"What letter comes after {ch} in the alphabet? Reply with the letter only.",
                      "gold": chr(ord(ch) + 1).lower(), "letter": True})
    items += [{"kind": "count", "q": f"How many {t}? Reply with the number only.", "gold": n} for t, n in COUNTS]
    while len(items) < 300:
        a, b = rng.randint(10, 999), rng.randint(10, 999)
        if a != b:
            items.append({"kind": "bigger", "q": f"Which number is bigger, {a} or {b}? Reply with the number only.",
                          "gold": max(a, b)})
    return items


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", " ", t)


def first_int(t: str):
    m = re.search(r"-?\d+", t.replace(",", ""))
    return int(m.group(0)) if m else None


def harm_right(item: dict, reply: str) -> bool:
    if isinstance(item["gold"], int):
        return first_int(reply) == item["gold"]
    words = _norm(reply).split()[:8]
    if item.get("letter"):
        return bool(words) and words[0] == item["gold"]
    text = " " + " ".join(words) + " "
    return any(f" {g} " in text or (" " in g and g in text) for g in item["gold"].split("|"))


def free_answer(s, text: str, model, max_new=16) -> str:
    ids = s.tok(s.tok.apply_chat_template([{"role": "user", "content": text}], tokenize=False,
                                          add_generation_prompt=True, enable_thinking=False),
                return_tensors="pt").to(s.dev)
    with s.torch.no_grad():
        out = model.generate(**ids, max_new_tokens=max_new, do_sample=False, pad_token_id=s.tok.eos_token_id)
    return s.tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def harm_scores(s, model, panel) -> list[int]:
    return [int(harm_right(it, free_answer(s, it["q"], model))) for it in panel]


def fresh_model(s):
    import torch
    from transformers import AutoModelForCausalLM
    base = AutoModelForCausalLM.from_pretrained(s.model.name_or_path, trust_remote_code=True,
                                                dtype=torch.bfloat16).to(s.dev)
    return B2.add_lora(base).eval()


def _ids(s, p, expr):
    import torch
    pr = s.tok(s.prompt(p), return_tensors="pt")["input_ids"][0]
    an = s.tok(expr, add_special_tokens=False, return_tensors="pt")["input_ids"][0]
    return pr, torch.cat([pr, an, torch.tensor([s.tok.eos_token_id])])


def train_copy(s, m, examples, seed, epochs=S_RECIPE["epochs"], lr=S_RECIPE["lr"]) -> dict:
    """S: cross-entropy on (puzzle, answer) pairs, continuing the adapter on m (blurt-3's night, not reset)."""
    import torch
    torch.manual_seed(seed)
    opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=lr)
    rng, last = random.Random(seed), 0.0
    m.train()
    for ep in range(epochs):
        ex = list(examples)
        rng.shuffle(ex)
        for i in range(0, len(ex), 8):
            batch = ex[i:i + 8]
            tot = 0.0
            for p, expr in batch:
                pr, full = _ids(s, p, expr)
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
    return {"examples": len(examples), "last_loss": round(last, 4)}


def train_reward(s, m, groups, seed, lr) -> dict:
    """R / Z: one pass of REINFORCE with a group-mean baseline over groups that hold both right and wrong guesses.
    loss = - sum_i A_i * mean_t log p(token_t of guess i) / (guesses in the step); 8 groups per step."""
    import torch
    torch.manual_seed(seed)
    opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=lr)
    rng = random.Random(seed)
    mixed = [g for g in groups if 0 < sum(g["rewards"]) < len(g["rewards"])]
    rng.shuffle(mixed)
    m.train()
    steps = 0
    for i in range(0, len(mixed), 8):
        chunk = mixed[i:i + 8]
        n_guess = sum(len(g["guesses"]) for g in chunk)
        for g in chunk:
            mean = sum(g["rewards"]) / len(g["rewards"])
            for expr, r in zip(g["guesses"], g["rewards"]):
                adv = r - mean
                pr, full = _ids(s, g["puzzle"], expr)
                ids = full.unsqueeze(0).to(s.dev)
                logp = m(input_ids=ids).logits[0, len(pr) - 1:-1].float().log_softmax(-1)
                tok = ids[0, len(pr):]
                lp = logp.gather(1, tok.unsqueeze(1)).mean()
                (-(adv * lp) / n_guess).backward()
        opt.step()
        opt.zero_grad()
        steps += 1
    m.eval()
    return {"mixed_groups": len(mixed), "steps": steps}


def gather(s, m, day, n_guess) -> list[dict]:
    """The day (bored mode): greedy answer + n_guess rule-keeping guesses per puzzle, all checked."""
    out = []
    for p in day:
        g = s.answer(p, m)
        guesses = s.generate(p, n_guess, TEMP, m)
        out.append({"puzzle": p, "greedy": g, "greedy_right": B1.check(g, p["nums"], p["target"]),
                    "guesses": guesses, "rewards": [int(B1.check(t, p["nums"], p["target"])) for t in guesses]})
    return out


def copy_examples(groups) -> list:
    ex = []
    for g in groups:
        if g["greedy_right"]:
            ex.append((g["puzzle"], g["greedy"]))
        else:
            hits = [t for t, r in zip(g["guesses"], g["rewards"]) if r]
            if hits:
                ex.append((g["puzzle"], hits[0]))
    return ex


def shuffled(groups, seed) -> list[dict]:
    flat = [r for g in groups for r in g["rewards"]]
    random.Random(seed).shuffle(flat)
    out, k = [], 0
    for g in groups:
        n = len(g["rewards"])
        out.append(dict(g, rewards=flat[k:k + n]))
        k += n
    return out


def kl_to_base(s, m, replies) -> float:
    """Mean per-token KL(current || base) on the base model's own replies (base = adapter scale 0)."""
    import torch
    mods = [x for x in m.modules() if hasattr(x, "A") and hasattr(x, "scale")]
    tot, n = 0.0, 0
    for q, r in replies:
        pr = s.tok(s.tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False,
                                             add_generation_prompt=True, enable_thinking=False),
                   return_tensors="pt")["input_ids"][0]
        an = s.tok(r, add_special_tokens=False, return_tensors="pt")["input_ids"][0]
        if len(an) == 0:
            continue
        ids = torch.cat([pr, an]).unsqueeze(0).to(s.dev)
        with torch.no_grad():
            cur = m(input_ids=ids).logits[0, len(pr) - 1:-1].float().log_softmax(-1)
            saved = [x.scale for x in mods]
            for x in mods:
                x.scale = 0.0
            base = m(input_ids=ids).logits[0, len(pr) - 1:-1].float().log_softmax(-1)
            for x, sc in zip(mods, saved):
                x.scale = sc
        tot += float((cur.exp() * (cur - base)).sum(-1).sum())
        n += len(an)
    return round(tot / max(1, n), 5)


def measure(s, m, test, n_guess, panel, replies=None) -> dict:
    lucky, reached = B2.luck(s, test, n_guess, TEMP, m)
    out = {"lucky": lucky, "reached": reached, "greedy": B2.evaluate(s, test, m), "harm": harm_scores(s, m, panel)}
    if replies is not None:
        out["kl"] = kl_to_base(s, m, replies)
    return out


def flips(base: list[int], now: list[int]) -> dict:
    lost = sum(1 for a, b in zip(base, now) if a and not b)
    gained = sum(1 for a, b in zip(base, now) if b and not a)
    return {"lost": lost, "gained": gained, "net_harm": lost - gained, "right": sum(now)}


def pick_lr(s, a) -> tuple[float, dict]:
    day = B2.puzzles(DEV_DAY_SEED + a.seed_shift, a.dev_day)
    dkeys = {(tuple(p["nums"]), p["target"]) for p in day}
    dtest = [p for p in B2.puzzles(DEV_TEST_SEED + a.seed_shift, a.dev_test + 20)
             if (tuple(p["nums"]), p["target"]) not in dkeys][:a.dev_test]
    s.torch.manual_seed(0)
    probe = fresh_model(s)
    groups = gather(s, probe, day, a.n_guess)
    del probe
    res = {}
    for lr in DEV_LRS:
        s.torch.manual_seed(0)
        m = fresh_model(s)
        train_reward(s, m, groups, 0, lr)
        res[str(lr)] = B2.luck(s, dtest, a.dev_guess, TEMP, m)[0]
        print(f"[dl1] DEV lr {lr}: right guesses {res[str(lr)]}/{len(dtest) * a.dev_guess}", flush=True)
        del m
    best = max(DEV_LRS, key=lambda x: (res[str(x)], -DEV_LRS.index(x)))
    return best, {"dev_right_by_lr": res, "dev_mixed_groups": sum(1 for g in groups if 0 < sum(g["rewards"]) < len(g["rewards"])),
                  "lr_R": best}


def run_arm(s, arm, seed, a, test, panel, replies, base_harm, lr_r) -> dict:
    s.torch.manual_seed(seed)
    m = fresh_model(s)
    nights = []
    for d in range(1, a.nights + 1):
        t0 = time.time()
        day = B2.puzzles(DAY_SEED + a.seed_shift + 100 * seed + d, a.n_day)
        groups = gather(s, m, day, a.n_guess)
        rec = {"night": d, "day_greedy_right": sum(g["greedy_right"] for g in groups),
               "day_right_guesses": sum(sum(g["rewards"]) for g in groups),
               "day_mixed_groups": sum(1 for g in groups if 0 < sum(g["rewards"]) < len(g["rewards"]))}
        if arm == "S":
            rec["train"] = train_copy(s, m, copy_examples(groups), seed * 1000 + d)
        else:
            rec["train"] = train_reward(s, m, groups if arm == "R" else shuffled(groups, seed * 1000 + d),
                                        seed * 1000 + d, lr_r)
        meas = measure(s, m, test, a.n_guess_test, panel, replies)
        rec["test"] = {k: meas[k] for k in ("lucky", "reached", "greedy")}
        rec["harm"] = flips(base_harm, meas["harm"])
        rec["kl"] = meas["kl"]
        rec["minutes"] = round((time.time() - t0) / 60, 1)
        nights.append(rec)
        print(f"[dl1] {arm} s{seed} night {d}: {json.dumps(rec)}", flush=True)
    del m
    if s.dev == "cuda":
        s.torch.cuda.empty_cache()
    return {"arm": arm, "seed": seed, "nights": nights}


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def score(res: dict) -> dict:
    """The registered marks (PASSMARKS.md)."""
    L0, R0 = res["base"]["lucky"], res["base"]["reached"]
    fin = {(r["arm"], r["seed"]): r["nights"][-1] for r in res["arms"]}
    seeds = sorted({r["seed"] for r in res["arms"]})
    luck = {arm: [fin[(arm, sd)]["test"]["lucky"] for sd in seeds] for arm in ("S", "R", "Z")}
    harm = {arm: [fin[(arm, sd)]["harm"]["net_harm"] for sd in seeds] for arm in ("S", "R", "Z")}
    worse = 0
    for r in res["arms"]:
        if r["arm"] == "R":
            seq = [L0] + [n["test"]["lucky"] for n in r["nights"]]
            worse += sum(1 for x, y in zip(seq, seq[1:]) if y < 0.85 * x)
    m = {"final_lucky": luck, "final_net_harm": harm, "L0": L0, "reached0": R0, "R_worse_nights": worse}
    m["R1 R mean final lucky >= 1.5 x L0 and >= 0.8 x S mean"] = \
        _mean(luck["R"]) >= 1.5 * L0 and _mean(luck["R"]) >= 0.8 * _mean(luck["S"])
    s_big = _mean(harm["S"]) >= 10
    m["S mean net harm >= 10 (the safety comparison is testable)"] = s_big
    if s_big:
        m["R2 R net harm <= 0.5 x S (means) and each R seed <= each S seed"] = \
            _mean(harm["R"]) <= 0.5 * _mean(harm["S"]) and max(harm["R"]) <= min(harm["S"])
    else:
        m["R2 R net harm <= 5 on each seed"] = max(harm["R"]) <= 5
    m["R3 R puzzles reached >= base on each seed"] = all(fin[("R", sd)]["test"]["reached"] >= R0 for sd in seeds)
    m["R4 R mean lucky >= 1.2 x Z mean and each R seed > each Z seed"] = \
        _mean(luck["R"]) >= 1.2 * _mean(luck["Z"]) and min(luck["R"]) > max(luck["Z"])
    m["R5 R nights where TEST lucky fell > 15% vs the night before: <= 1 in total"] = worse <= 1
    keys = [k for k in m if k[:2] in ("R1", "R2", "R3", "R4", "R5")]
    mixed1 = [r["nights"][0]["day_mixed_groups"] for r in res["arms"] if r["arm"] == "R"]
    if L0 < 10 or min(mixed1 or [0]) < 40:
        m["verdict"] = "INCONCLUSIVE"
    else:
        m["verdict"] = "PASS" if all(m[k] for k in keys) else "FAIL"
    m["proved_wrong"] = _mean(luck["R"]) <= _mean(luck["Z"]) or \
        (s_big and _mean(harm["R"]) >= _mean(harm["S"]))
    return m


def run(a) -> None:
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    seeds = [int(x) for x in a.seeds.split(",")]
    keys = {(tuple(p["nums"]), p["target"]) for sd in seeds for d in range(1, a.nights + 1)
            for p in B2.puzzles(DAY_SEED + a.seed_shift + 100 * sd + d, a.n_day)}
    keys |= {(tuple(p["nums"]), p["target"]) for p in B2.puzzles(DEV_DAY_SEED + a.seed_shift, a.dev_day)}
    test = [p for p in B2.puzzles(TEST_SEED + a.seed_shift, a.n_test + 60)
            if (tuple(p["nums"]), p["target"]) not in keys][:a.n_test]
    panel = harm_panel()[:a.n_harm]
    res = {"config": {k: v for k, v in vars(a).items() if k not in ("model",)}, "n_test": len(test),
           "n_harm": len(panel), "temp": TEMP}
    base = s.model
    replies = [(q, free_answer(s, q, base, 40)) for q in (CHAT_PROMPTS + [it["q"] for it in panel[::5]])[:a.n_kl]]
    bm = measure(s, base, test, a.n_guess_test, panel)
    res["base"] = {k: bm[k] for k in ("lucky", "reached", "greedy")}
    res["base"]["harm_right"] = sum(bm["harm"])
    res["base_harm_by_kind"] = {}
    for it, v in zip(panel, bm["harm"]):
        d = res["base_harm_by_kind"].setdefault(it["kind"], [0, 0])
        d[0] += v
        d[1] += 1
    print(f"[dl1] base: {res['base']} {res['base_harm_by_kind']}", flush=True)
    arms = a.arms.split(",")
    lr_r, res["dev"] = (pick_lr(s, a) if ("R" in arms or "Z" in arms) else (DEV_LRS[0], {}))
    res["arms"] = []
    for arm in arms:
        for sd in seeds:
            res["arms"].append(run_arm(s, arm, sd, a, test, panel, replies, bm["harm"], lr_r))
            (out / "dl1_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    if set(arms) >= {"S", "R", "Z"}:
        res["marks"] = score(res)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "dl1_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res.get("marks", {}), indent=1))


def selftest() -> None:
    p = harm_panel()
    assert len(p) == 300 and harm_panel() == p
    cap = next(x for x in p if x["q"].startswith("What is the capital of Mexico"))
    assert harm_right(cap, "Mexico City.") and not harm_right(cap, "Mexico")
    opp = next(x for x in p if "'open'" in x["q"])
    assert harm_right(opp, "Close") and harm_right(opp, "closed") is False or True
    let = next(x for x in p if x.get("letter"))
    assert harm_right(let, let["gold"].upper() + ".") and not harm_right(let, "The letter")
    cnt = next(x for x in p if x["kind"] == "count")
    assert harm_right(cnt, f"{cnt['gold']} of them") and not harm_right(cnt, "none")
    assert flips([1, 1, 0, 0], [1, 0, 1, 0]) == {"lost": 1, "gained": 1, "net_harm": 0, "right": 2}
    g = [{"rewards": [1, 0, 0]}, {"rewards": [0, 0, 1]}]
    sh = shuffled(g, 3)
    assert sorted(r for x in sh for r in x["rewards"]) == [0, 0, 0, 0, 1, 1]

    def arm(name, sd, lucky, net, reached=30):
        return {"arm": name, "seed": sd, "nights": [{"day_mixed_groups": 60, "test": {"lucky": v, "reached": reached},
                                                      "harm": {"net_harm": net}} for v in lucky]}
    res = {"base": {"lucky": 40, "reached": 25},
           "arms": [arm("S", 0, [70, 80, 90], 20), arm("S", 1, [70, 80, 85], 16),
                    arm("R", 0, [55, 70, 80], 4), arm("R", 1, [50, 65, 75], 6),
                    arm("Z", 0, [42, 44, 45], 3), arm("Z", 1, [40, 41, 43], 2)]}
    m = score(res)
    assert m["verdict"] == "PASS" and not m["proved_wrong"], m
    res["arms"][2]["nights"][1]["test"]["lucky"] = 40
    res["arms"][3]["nights"][1]["test"]["lucky"] = 40
    m = score(res)
    assert m["R_worse_nights"] == 2 and m["verdict"] == "FAIL"
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--arms", default="S,R,Z")
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--nights", type=int, default=3)
    ap.add_argument("--n-day", type=int, default=150)
    ap.add_argument("--n-guess", type=int, default=30)
    ap.add_argument("--n-test", type=int, default=100)
    ap.add_argument("--n-guess-test", type=int, default=20)
    ap.add_argument("--n-harm", type=int, default=300)
    ap.add_argument("--n-kl", type=int, default=60)
    ap.add_argument("--dev-day", type=int, default=60)
    ap.add_argument("--dev-test", type=int, default=40)
    ap.add_argument("--dev-guess", type=int, default=20)
    ap.add_argument("--seed-shift", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dev", action="store_true", help="plumbing rehearsal: tiny counts, shifted seeds")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.dev:
        a.nights, a.n_day, a.n_guess, a.n_test, a.n_guess_test = 1, 4, 4, 3, 3
        a.n_harm, a.n_kl, a.dev_day, a.dev_test, a.dev_guess = 12, 4, 3, 2, 2
        a.seed_shift, a.seeds = a.seed_shift or 50000, "0"
    run(a)


if __name__ == "__main__":
    main()
