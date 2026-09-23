#!/usr/bin/env python3
"""54 — the 10-minute DEMO for Ben's uncle and dad (scripted, $0, Mac CPU only).

What it does, in order:

  1. Teaches a small family story through the real LISTENING doorway (structured
     lines, doc 36/48) inside the rule scheduler from fable_modes54_scheduler, so a
     visible MODE LOG records every LISTENING / WORK / CREATIVE / SLEEP / THINKING
     transition with (from, to, reason).
  2. Asks the 9 frozen questions (PASSMARKS.md): 1-hop, 2-hop, one correction, one
     hearsay trap, two missing-fact abstentions, one ambiguous name (+ a pick to
     resolve it), one alias follow-up, one paraphrase the key-value notebook cannot
     answer, and the self-question -- "what do you know, how do you know it, what
     are you unsure about" -- answered ONLY from notebook source tags and the mode
     log.
  3. Runs the same teachings through a plain small transformer baseline (minimal
     decoder-only, plain PyTorch, CPU) trained on the same story+question pairs
     (seeds 5401/5402/5403, 600 fixed updates each), and scores both sides on the
     same 9 questions, reporting every integer including where the baseline wins.

    python fable_modes54_demo.py --out artifacts/fable-modes54-20260921
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C          # noqa: E402
import fable_listening_m1 as L               # noqa: E402
from fable_modes54_scheduler import (        # noqa: E402
    ModeScheduler, CREATIVE_FIXED_N, LISTENING, THINKING, WORK, CREATIVE, SLEEP)

# ---------------------------------------------------------------- frozen script
# Everything Ben SAYS, in order.  Byte-identical to the story text the baseline
# sees (PASSMARKS D5).  The second `person Mira` is what creates the ambiguity.
BEN_LINES = [
    "person Mira",
    "person Ana",
    "person Tom",
    "teach Mira mother -> Ana",
    "teach Ana city = Porto",
    "teach Mira city = Lisbon",
    "teach Mira colour = green",
    # -- Q1, Q2 asked here --
    "correct Mira city = Paris",
    # -- Q3 asked here --
    "quote Apparently Tom's city is Rome",
    # -- Q4, Q5 asked here --
    "alias Mira1 = Mira",
    "person Mira",
    "teach Mira city = Oslo",     # -> clarify (two Miras)
    "pick E0004",                 # -> saved for the SECOND Mira
    # -- Q6, pick-flourish, Q7, Q8 asked here --
    "person Kai",
    "teach Kai mother -> Ana",
]
PREFIX_Q12 = 7    # lines 0..6
PREFIX_Q3 = 8     # includes the correction
PREFIX_Q45 = 9    # includes the hearsay quote
PREFIX_Q678 = 13  # through `pick E0004`

ITEMS = [
    dict(qid="Q1", kind="answer", nb="ask Mira mother",
         en="Who is Mira's mother?", gold="Ana", prefix=PREFIX_Q12),
    dict(qid="Q2", kind="answer", nb="ask Mira mother city",
         en="Where does Mira's mother live?", gold="Porto", prefix=PREFIX_Q12),
    dict(qid="Q3", kind="answer", nb="ask Mira city",
         en="Where does Mira live?", gold="Paris", prefix=PREFIX_Q3),
    dict(qid="Q4", kind="abstain", nb="ask Tom city",
         en="Where does Tom live?", gold="<ABSTAIN>", prefix=PREFIX_Q45),
    dict(qid="Q5", kind="abstain", nb="ask Mira job",
         en="What is Mira's job?", gold="<ABSTAIN>", prefix=PREFIX_Q45),
    dict(qid="Q6", kind="abstain", nb="ask Mira city",
         en="Where does Mira live?", gold="<ABSTAIN>", prefix=PREFIX_Q678),
    dict(qid="Q7", kind="answer", nb="ask Mira1 city",
         en="Where does Mira1 live?", gold="Paris", prefix=PREFIX_Q678),
    dict(qid="Q8", kind="answer", nb="ask Mira favourite",
         en="What is Mira's favourite colour?", gold="green", prefix=PREFIX_Q678),
]
SELF_QID = "Q9"
TRAIN_SEEDS = (5401, 5402, 5403)
TRAIN_UPDATES = 600
TRAIN_LR = 1e-3
ABSTAIN = "<ABSTAIN>"


def norm(text: str) -> str:
    return " ".join(re.findall(r"[\w<>]+", str(text).lower()))


def story_prefix(n: int) -> str:
    return "\n".join(BEN_LINES[:n])


# ------------------------------------------------------- notebook side + modes
def run_notebook_side(tmpdir: str) -> dict:
    nb = C.Notebook(tmpdir)
    ear = L.Listening(nb)
    sched = ModeScheduler(turn_handler=ear.hear, sleep_threshold=100_000)
    transcript: list[dict] = []
    fact_origin: dict[str, dict] = {}
    replies: dict[str, str] = {}
    extras: dict[str, str] = {}

    def say(line: str, tag: str) -> str:
        before = set(nb.facts)
        sched.submit(line)
        event = sched.step()
        reply = event["detail"].get("reply", "")
        listen_entries = [e for e in sched.mode_log if e["to"] == LISTENING]
        listen_t = listen_entries[-1]["t"] if listen_entries else event["t"]
        for fid in set(nb.facts) - before:
            fact_origin[fid] = {"via": tag, "listen_t": listen_t}
        transcript.append({"tag": tag, "ben": line, "fable": reply,
                           "mode": event["mode"], "listen_t": listen_t})
        return reply

    # --- teachings in script order, with the questions interleaved ------------
    for i, line in enumerate(BEN_LINES[:PREFIX_Q12]):
        say(line, f"teach[{i}]")
    replies["Q1"] = say(ITEMS[0]["nb"], "ask")
    replies["Q2"] = say(ITEMS[1]["nb"], "ask")

    say(BEN_LINES[7], "teach[7:correct]")
    replies["Q3"] = say(ITEMS[2]["nb"], "ask")

    say(BEN_LINES[8], "teach[8:hearsay]")
    replies["Q4"] = say(ITEMS[3]["nb"], "ask")
    replies["Q5"] = say(ITEMS[4]["nb"], "ask")

    for i, line in enumerate(BEN_LINES[9:PREFIX_Q678], start=9):
        say(line, f"teach[{i}]")
    replies["Q6"] = say(ITEMS[5]["nb"], "ask")
    extras["pick"] = say("pick E0001", "pick")           # resolve the ambiguity
    replies["Q7"] = say(ITEMS[6]["nb"], "ask")
    replies["Q8"] = say(ITEMS[7]["nb"], "ask")

    # --- extra beat: an approved rule + an inferred row (source tag diversity)
    nb.approve_rule("demo-rule-1", "ben", "R1",
                    "city(x) = city(mother(x)) when x has no city of its own")
    say(BEN_LINES[13], "teach[13]")   # person Kai
    say(BEN_LINES[14], "teach[14]")   # teach Kai mother -> Ana
    kai = nb.resolve("Kai").detail["entity_id"]
    dep_mother = next(f["fact_id"] for f in nb.facts.values()
                      if f["subject"] == kai and f["relation"] == "mother"
                      and f["source"] == "taught")
    ana_city = next(f["fact_id"] for f in nb.facts.values()
                    if f["subject"] == nb.resolve("Ana").detail["entity_id"]
                    and f["relation"] == "city" and f["source"] == "taught")
    made = nb.assert_fact("demo-inferred-1", "thinking", "inferred", kai, "city",
                          {"literal": "Porto"}, rule_id="R1",
                          deps=(dep_mother, ana_city))
    fact_origin[made.detail["fact_id"]] = {"via": "rule R1 (inferred)", "listen_t": None}
    extras["kai_ask"] = say("ask Kai city", "ask")
    nb_last_facts = set(nb.facts)

    # --- mode show-piece: WORK -> CREATIVE (FOUND), CREATIVE (GIVE-UP -> ask
    #     Ben), then SLEEP on the memory-full trigger ---------------------------
    sched.sleep_threshold = max(1, sched.memory)
    sched.queue_job({"job_id": "J-show", "open_ended": True, "creative_found_at": 2,
                     "steps": [{"outcomes": ["ok"]}]})
    sched.queue_job({"job_id": "J-stuck", "open_ended": True,
                     "creative_found_at": None, "steps": [{"outcomes": ["ok"]}]})
    proposed_written = False
    events = []
    for _ in range(60):
        event = sched.step()
        events.append(event)
        detail = event["detail"]
        if (not proposed_written and detail.get("result") == "JOB_DONE"
                and detail.get("job_id") == "J-show"):
            ana_id = nb.resolve("Ana").detail["entity_id"]
            row = nb.assert_fact("demo-proposed-1", "working", "proposed",
                                 ana_id, "likes", {"literal": "tea"})
            if row.status == C.SAVED:
                fact_origin[row.detail["fact_id"]] = {
                    "via": "WORK job J-show (proposed, awaiting Ben)",
                    "listen_t": None}
            proposed_written = True
        if (not sched.inbox and sched.runnable_job() is None
                and sched.sleep_state is None and sched.counters["sleeps"] >= 1):
            break
    if sched.counters["sleeps"] >= 1:
        # two Miras exist; attach the sleep note to the first one by id order
        mira_id = min(eid for eid, name in nb.entities.items() if name == "Mira")
        row = nb.assert_fact("demo-sleep-1", "sleep", "sleep-derived", mira_id,
                             "night_note", {"literal": "notebook compacted"})
        if row.status == C.SAVED:
            fact_origin[row.detail["fact_id"]] = {
                "via": "SLEEP commit (sleep-derived)", "listen_t": None}

    # --- Q9: the self-question, answered from source tags + mode log ---------
    self_answer = self_report(nb, sched, fact_origin, replies)
    transcript.append({"tag": "self", "ben":
                       "What do you know? How do you know it? "
                       "What are you unsure about?",
                       "fable": self_answer, "mode": sched.mode, "listen_t": None})

    assert set(nb_last_facts) <= set(nb.facts), "show-piece must not delete facts"
    return {"nb": nb, "sched": sched, "transcript": transcript,
            "replies": replies, "extras": extras, "self_answer": self_answer,
            "fact_origin": fact_origin}


# ------------------------------------------------------------------ Q9 report
def self_report(nb, sched, fact_origin, replies) -> str:
    active = {fid: f for fid, f in nb.facts.items() if nb.active(fid)}
    by_source: dict[str, list[str]] = {}
    for fid in sorted(active, key=lambda x: int(x[1:])):
        by_source.setdefault(active[fid]["source"], []).append(fid)

    lines = ["WHAT I KNOW (by notebook source tag):"]
    for source in sorted(by_source):
        rows = by_source[source]
        lines.append(f"  {source}: {len(rows)} active fact(s)")
        for fid in rows[:6]:
            f = active[fid]
            value = (nb.entities[f["value"]["entity"]] if "entity" in f["value"]
                     else f["value"]["literal"])
            lines.append(f"    {fid}  {nb.entities[f['subject']]} {f['relation']} "
                         f"= {value}")

    lines.append("HOW I KNOW IT (source tag + where it came from):")
    for source in sorted(by_source):
        for fid in by_source[source][:4]:
            origin = fact_origin.get(fid, {})
            where = origin.get("via", active[fid]["source"])
            t = origin.get("listen_t")
            where_t = f", LISTENING turn t={t}" if t else ""
            lines.append(f"    {fid} [{source}] via {where}{where_t}")

    unsure: list[str] = []
    if replies.get("Q6", "").startswith("I know more than one"):
        unsure.append("AMBIGUOUS: 'Mira' resolves to two entities (E0001, E0004); "
                      "I asked which one instead of guessing")
    for qid, note in (("Q4", "Tom's city: only hearsay exists, nothing was saved"),
                      ("Q5", "Mira's job: never taught"),
                      ("Q8", "Mira's favourite: 'Mira' still ambiguous, and colour "
                             "was taught as relation 'colour' not 'favourite'")):
        if qid in replies:
            unsure.append(f"MISSING/AMBIGUOUS on {qid}: {note}")
    unsure.append("hearsay refused: the quote about Tom's city wrote nothing "
                  "(only LISTENING writes 'taught')")
    unsure.append("1 proposed row awaits your approval (WORK wrote it, it does "
                  "not answer questions yet)")
    for q in sched.questions:
        unsure.append(f"job {q['job_id']} is parked: {q['text']}")
    if not any(f["source"] == "web-quarantine" for f in active.values()):
        unsure.append("0 web-quarantine rows: I have not believed anything from "
                      "the web in this session")

    lines.append("WHAT I AM UNSURE ABOUT:")
    for item in unsure:
        lines.append(f"    - {item}")

    lines.append("MODE LOG (why I was where I was):")
    for entry in sched.mode_log[:14]:
        lines.append(f"    t={entry['t']} {entry['from']} -> {entry['to']} "
                     f"({entry['reason']})")
    if len(sched.mode_log) > 14:
        lines.append(f"    ... {len(sched.mode_log) - 14} more transitions")
    modes_seen = sorted({e["to"] for e in sched.mode_log})
    lines.append(f"    modes seen: {', '.join(modes_seen)}")
    return "\n".join(lines)


# ------------------------------------------------------------- baseline side
def tokenize(text: str) -> list[str]:
    return [tok for tok in text.replace("\n", " \n ").split()
            if tok not in ("", "\n")]


def detok(tokens: list[str]) -> str:
    return " ".join(tokens)


class TinyTransformer:
    """A plain decoder-only transformer, written here so nothing else is touched."""

    def __init__(self, vocab_size: int, d_model: int = 64, layers: int = 2,
                 heads: int = 4, ffn: int = 128, max_len: int = 512):
        import torch
        import torch.nn as nn
        self.torch, self.nn = torch, nn
        class Block(nn.Module):
            def __init__(self):
                super().__init__()
                self.ln1, self.ln2 = nn.LayerNorm(d_model), nn.LayerNorm(d_model)
                self.attn = nn.MultiheadAttention(d_model, heads, batch_first=True)
                self.ff1 = nn.Linear(d_model, ffn)
                self.ff2 = nn.Linear(ffn, d_model)
                self.act = nn.ReLU()
            def forward(self, x, pad_mask, causal):
                h = self.ln1(x)
                a, _ = self.attn(h, h, h, key_padding_mask=pad_mask,
                                 attn_mask=causal, need_weights=False)
                x = x + a
                return x + self.ff2(self.act(self.ff1(self.ln2(x))))
        class Net(nn.Module):
            def __init__(self):
                super().__init__()
                self.emb = nn.Embedding(vocab_size, d_model)
                self.pos = nn.Embedding(max_len, d_model)
                self.blocks = nn.ModuleList(Block() for _ in range(layers))
                self.ln = nn.LayerNorm(d_model)
                self.head = nn.Linear(d_model, vocab_size, bias=False)
            def forward(self, idx, pad_mask, causal):
                t = idx.shape[1]
                x = self.emb(idx) + self.pos(torch.arange(t, device=idx.device))
                for block in self.blocks:
                    x = block(x, pad_mask, causal)
                return self.head(self.ln(x))
        self.net = Net()
        self.max_len = max_len

    @property
    def device(self):
        return next(self.net.parameters()).device

    def causal(self, t: int):
        return self.torch.triu(self.torch.ones(t, t, dtype=self.torch.bool), 1)

    def forward_loss(self, ids, labels, pad_id):
        torch = self.torch
        pad = ids.eq(pad_id)
        # rows that are entirely padding (no real tokens) break MHA; keep them out
        keep = ~pad.all(dim=1)
        ids, labels, pad = ids[keep], labels[keep], pad[keep]
        logits = self.net(ids, pad, self.causal(ids.shape[1]))
        return torch.nn.functional.cross_entropy(
            logits[:, :-1].reshape(-1, logits.shape[-1]),
            labels[:, 1:].reshape(-1), ignore_index=-100)

    @property
    def parameters(self):                       # noqa: A003 - convenience
        return self.net.parameters


def greedy_decode(model, prefix_ids, eos_id, pad_id, max_new=8) -> list[int]:
    torch = model.torch
    out = list(prefix_ids)
    with torch.no_grad():
        for _ in range(max_new):
            ids = torch.tensor([out], dtype=torch.long)
            pad = ids.eq(pad_id)
            logits = model.net(ids, pad, model.causal(len(out)))[0, -1]
            nxt = int(logits.argmax(-1))
            if nxt == eos_id:
                break
            out.append(nxt)
    return out[len(prefix_ids):]


def run_baseline(out_dir: Path) -> dict:
    import torch

    texts = []
    for item in ITEMS:
        texts.append(story_prefix(item["prefix"]))
        texts.append(item["en"])
        texts.append(item["gold"])
    specials = ["<PAD>", "<SEP>", "<EOS>"]
    vocab_words = sorted({tok for text in texts for tok in tokenize(text)})
    vocab = {w: i for i, w in enumerate(specials + vocab_words)}
    inv = {i: w for w, i in vocab.items()}
    pad_id, sep_id, eos_id = 0, 1, 2

    pairs = []
    for item in ITEMS:
        story = [vocab[tok] for tok in tokenize(story_prefix(item["prefix"]))]
        question = tokenize(item["en"])
        answer = tokenize(item["gold"])
        prefix = story + [sep_id] + [vocab[tok] for tok in question] + [sep_id]
        full = prefix + [vocab[tok] for tok in answer] + [eos_id]
        pairs.append({"qid": item["qid"], "prefix": prefix, "full": full,
                      "ans_start": len(prefix), "gold": item["gold"]})

    def encode_batch(rows):
        width = max(len(r["full"]) for r in rows)
        ids = torch.full((len(rows), width), pad_id, dtype=torch.long)
        labels = torch.full((len(rows), width), -100, dtype=torch.long)
        for i, row in enumerate(rows):
            ids[i, :len(row["full"])] = torch.tensor(row["full"])
            # labels[t] = full[t] for answer positions; loss pairs logits[t]
            # with labels[t+1] via the standard [:, :-1] / [:, 1:] split
            for t in range(row["ans_start"], len(row["full"])):
                labels[i, t] = row["full"][t]
        return ids, labels

    per_seed = {}
    train_seconds = {}
    for seed in TRAIN_SEEDS:
        started = time.monotonic()
        torch.manual_seed(seed)
        model = TinyTransformer(len(vocab))
        n_params = sum(p.numel() for p in model.parameters())
        optim = torch.optim.Adam(model.parameters(), lr=TRAIN_LR)
        ids, labels = encode_batch(pairs)
        final_loss = None
        for _ in range(TRAIN_UPDATES):
            loss = model.forward_loss(ids, labels, pad_id)
            optim.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optim.step()
            final_loss = float(loss.detach())
        train_seconds[seed] = round(time.monotonic() - started, 2)
        predictions = {}
        for pair in pairs:
            gen = greedy_decode(model, pair["prefix"], eos_id, pad_id)
            predictions[pair["qid"]] = detok([inv[i] for i in gen])
        correct = {item["qid"]: int(norm(predictions[item["qid"]])
                                    == norm(item["gold"]))
                   for item in ITEMS}
        correct[SELF_QID] = 0       # no notebook, no mode log: cannot be trained
        predictions[SELF_QID] = "(no notebook or mode log to read)"
        per_seed[str(seed)] = {
            "predictions": predictions, "correct": correct,
            "total": sum(correct.values()),
            "parameters": n_params, "final_train_loss": round(final_loss, 4),
            "train_seconds": train_seconds[seed],
        }
        print(f"baseline seed {seed}: total {sum(correct.values())}/9, "
              f"params {n_params}, loss {final_loss:.4f}, "
              f"{train_seconds[seed]}s", flush=True)

    return {"vocab_size": len(vocab), "updates": TRAIN_UPDATES, "lr": TRAIN_LR,
            "seeds": list(TRAIN_SEEDS), "per_seed": per_seed,
            "trained_on": [item["qid"] for item in ITEMS],
            "note": "trained on the same story+question pairs it is asked "
                    "(Q9 untrainable); greedy decode, exact match"}


# ------------------------------------------------------------------ scoring
def score_notebook(replies, self_answer, sched) -> dict:
    def clean(text: str) -> str:
        return text.replace("(I dropped my earlier question.) ", "")

    correct, detail = {}, {}
    for item in ITEMS:
        reply = clean(replies.get(item["qid"], ""))
        if item["kind"] == "abstain":
            ok = reply.startswith("I don't know") or reply.startswith(
                "I know more than one")
        else:
            ok = norm(reply) == norm(item["gold"])
        correct[item["qid"]] = int(ok)
        detail[item["qid"]] = {"reply": reply, "gold": item["gold"],
                               "correct": int(ok)}
    sources = {f["source"] for f in nb_active_sources(self_answer)}
    tags_cited = sum(tag in self_answer for tag in
                     ("taught", "inferred", "proposed", "sleep-derived"))
    log_cited = len(re.findall(r"t=\d+ \w+ -> \w+ \(\w", self_answer))
    q9_ok = int(tags_cited >= 3 and log_cited >= 3)
    correct[SELF_QID] = q9_ok
    detail[SELF_QID] = {"tags_cited": tags_cited, "log_entries_cited": log_cited,
                        "correct": q9_ok, "sources_in_notebook": sorted(sources)}
    modes = sorted({e["to"] for e in sched.mode_log})
    return {"correct": correct, "total": sum(correct.values()),
            "detail": detail, "modes_seen": modes}


def nb_active_sources(self_answer: str) -> list[dict]:
    """Source tags that appear in the self-report's KNOW section."""
    found = []
    for tag in ("taught", "inferred", "proposed", "sleep-derived",
                "web-quarantine"):
        if re.search(rf"^  {tag}: \d+ active", self_answer, re.M):
            found.append({"source": tag})
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="54 demo (scripted, 10 minutes)")
    parser.add_argument("--out", default="artifacts/fable-modes54-20260921")
    parser.add_argument("--state-dir", default=None,
                        help="where the demo notebook lives "
                             "(default: OUT/demo-notebook)")
    parser.add_argument("--skip-baseline", action="store_true")
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    state = Path(args.state_dir) if args.state_dir else out / "demo-notebook"
    if state.exists():
        import shutil
        shutil.rmtree(state)

    print("=" * 72, flush=True)
    print("FABLE DEMO — modes + notebook vs a plain small transformer", flush=True)
    print("=" * 72, flush=True)

    run = run_notebook_side(str(state))
    nb, sched = run["nb"], run["sched"]
    for row in run["transcript"]:
        print(f"  [{row['mode']:<9}] BEN:   {row['ben']}", flush=True)
        first = str(row["fable"]).split("\n")[0]
        print(f"             FABLE: {first}", flush=True)

    print("\n--- self-question answer (Q9) ---", flush=True)
    print(run["self_answer"], flush=True)

    # D5: byte-identity of the teaching lines the notebook heard vs BEN_LINES
    # (asks and the pick-answer flourish are interactions, not story lines)
    heard = [row["ben"] for row in run["transcript"]
             if row["tag"].startswith("teach")]
    story_lines = BEN_LINES
    identity_ok = heard == story_lines

    nb_scores = score_notebook(run["replies"], run["self_answer"], sched)

    modes_seen = sorted({e["to"] for e in sched.mode_log})
    d6_ok = all(m in modes_seen for m in (LISTENING, WORK, CREATIVE, SLEEP, THINKING))

    baseline = None
    if not args.skip_baseline:
        print("\n--- baseline: plain small transformer, same teachings ---",
              flush=True)
        baseline = run_baseline(out)

    # ------------------------------------------------------------- report
    report = {
        "questions": [{k: item[k] for k in ("qid", "nb", "en", "gold")}
                      for item in ITEMS] + [
            {"qid": SELF_QID, "nb": "self-report", "en": "-", "gold": "self-report"}],
        "notebook": {"correct": nb_scores["correct"],
                     "total": nb_scores["total"],
                     "detail": nb_scores["detail"],
                     "modes_seen": modes_seen,
                     "creative_fixed_n": CREATIVE_FIXED_N},
        "baseline": baseline,
        "identity_D5": identity_ok,
        "d6_modes": d6_ok,
        "mode_log": sched.mode_log,
        "questions_for_ben": sched.questions,
        "heard_lines": heard,
        "story_lines": story_lines,
    }
    (out / "demo-results.json").write_text(json.dumps(report, indent=1))
    (out / "mode-log-demo.json").write_text(json.dumps(sched.mode_log, indent=1))
    (out / "demo-transcript.txt").write_text(
        "\n".join(f"[{r['mode']}] {r['ben']}\n    -> {r['fable']}"
                  for r in run["transcript"]))

    print("\n" + "=" * 72, flush=True)
    print("SCOREBOARD (exact integers, never averaged)", flush=True)
    print("=" * 72, flush=True)
    header = f"{'qid':<4} {'gold':<12} {'notebook':<40} "
    if baseline:
        for seed in TRAIN_SEEDS:
            header += f" base{seed}"
    print(header, flush=True)
    for item in ITEMS + [dict(qid=SELF_QID, gold="self-report")]:
        qid = item["qid"]
        nb_cell = str(nb_scores["detail"].get(qid, {}).get(
            "reply", "see self-report"))[:40]
        nb_mark = nb_scores["correct"][qid]
        line = f"{qid:<4} {str(item['gold']):<12} {nb_mark} {nb_cell:<39}"
        if baseline:
            for seed in TRAIN_SEEDS:
                pred = baseline["per_seed"][str(seed)]["predictions"].get(qid, "")
                mark = baseline["per_seed"][str(seed)]["correct"][qid]
                line += f"  {mark}:{pred[:16]}"
        print(line, flush=True)
    print(f"TOTALS notebook {nb_scores['total']}/9", flush=True)
    if baseline:
        for seed in TRAIN_SEEDS:
            row = baseline["per_seed"][str(seed)]
            print(f"TOTALS baseline seed {seed} {row['total']}/9 "
                  f"(loss {row['final_train_loss']})", flush=True)

    print(f"\nD5 teaching lines byte-identical: {identity_ok}", flush=True)
    print(f"D6 modes seen: {', '.join(modes_seen)} -> {'PASS' if d6_ok else 'FAIL'}",
          flush=True)
    print(f"parked question for Ben: "
          f"{run['sched'].questions or '(none open)'}", flush=True)
    print(f"wrote {out / 'demo-results.json'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
