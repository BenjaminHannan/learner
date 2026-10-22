#!/usr/bin/env python3
"""Stage 1 ideation in words (TRIAL2-PLAN-OPUS.md section 4): 12 lenses x {Opus, Sonnet} -> idea cards.

All calls go through GuardedClient (Batch API, no caching, no tools): Stage 1 cap $5.00, stop $4.50
(pricing.json). Pass 1 = 24 calls. The "far" pass (12 calls: the 6 lenses with the least overlap with
the other lenses' cores, told the cores found so far) runs only if the guard allows its worst case.
Gate G1: >= 60 parseable cards stating fits_interface yes. Nothing after Stage 1 is run here.

Usage: python ideate.py            # prints the plan and worst cases, sends nothing
       python ideate.py --fake     # whole pipeline against a fake client in a temp ledger (no network, $0)
       python ideate.py --go       # the real run (needs ANTHROPIC_API_KEY)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from guarded import GuardedClient  # noqa: E402
from money import Guard, MoneyStop  # noqa: E402

SHINKA = HERE.parent
OUT = SHINKA / "results" / "trial2"
STAGE = "1"
MODELS = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5"}
MAX_TOKENS = 24000
EFFORT = "high"
G1_MIN_CARDS = 60
FIELDS = ("core_operation", "mechanism", "why_novel_names", "nearest_known", "prediction", "fits_interface")

LENSES = [
    "hippocampal indexing and pattern separation",
    "linguistics: argument structure, which slot is the agent",
    "information theory: what is cheapest to transmit about a line",
    "error-correcting codes",
    "immune-system recognition of the never-seen",
    "signal processing: onset and contrast detectors",
    "databases: how a key is formed when the key value has never been seen",
    "physics: symmetry breaking and conserved quantities",
    "evolution and ecology",
    "cryptography: keyed permutations",
    "compilers: type inference for an unseen identifier",
    "inversion: list precisely what multi-head pooling cannot do for an unseen name, then design for that",
]

TASK = """\
THE TASK (a small CPU toy, described in words)
A visit is 8 lines. Each line states one fact: (person, relation, value). A line is 10 tokens: 3 content tokens
(person name, relation, value) at random positions among 7 filler tokens. 4 people, 4 relations, 24 values appear per
visit. A frozen random "reader" turns each line's tokens into 32-number states; each state is lightly mixed with its
neighbours' content, so the person's identity at the value token is only a weak trace.
You design the CARD WRITER: it sees ONE line's reader states [10 tokens x 32 numbers] (no token ids, no roles, no other
line, no other visit) and outputs one card = a key (16 numbers) and a value (32 numbers). The writer may store at most
20,000 numbers. A fixed, unchanged answerer then reads a question "<person> <relation>?", scores the 8 cards by the
cosine of the question vector with each key, soft-reads the values, and decodes the value token. Training is
answer-only cross-entropy (no labels for which token is the person). The decoys guarantee that a card which keeps only
the relation, or only the person, must guess among at least two cards.
THE SCORE: held-out accuracy averaged over FAMILIAR names (16 seen in training) and NOVEL names (8 names whose token
vectors were never seen in training). The headroom is on novel names: the best known writer reaches about 0.57 on novel
names (familiar 0.98); an oracle that is TOLD which token is the person reaches 0.945. The best known writer sends about 43% of
novel-name questions to another person's card (it keeps the value but loses WHO the fact is about).
A probe on the reader states (with enough training names) finds the person's position on unseen names about 97% of the
time, so the information is present in the states. A writer trained on only 16 names may still learn a rule that depends
on those names; an idea that needs name-independent structure is welcome, an idea that stores name identity is not.
"""

RULES = """\
KNOWN ITEMS (an idea whose core operation is one of these, or a direct combination of two of them, is KNOWN and is
wasted: do not propose it):
{known}

Trial 1 evolved code for this toy and every finalist was the same known idea (deflation pursuit = matching pursuit on
attention pooling, plus novelty/echo/leverage pools). Do not propose deflation, multi-pool pursuit, novelty-subspace
pools, ridge-leverage pools or "echo into the key".
"""

OUTPUT = """\
OUTPUT. Reply with ONE JSON object and nothing after it: {"cards": [ ... 5 cards ... ]}. Each card has exactly these
string fields: "core_operation" (one sentence), "mechanism" (at most 150 words, concrete enough to implement),
"why_novel_names" (why it helps an UNSEEN person token specifically), "nearest_known" (the nearest KNOWN item or paper,
and the exact difference), "prediction" (a number it should move on the toy, e.g. person-lost errors on novel names),
"fits_interface" ("yes" only if it is a per-line function of the 10x32 states, no token ids, at most 20,000 numbers, and
trainable by answer-only cross-entropy; else "no"). The 5 cards must have different core operations.
"""


def known_text() -> str:
    short = (SHINKA / "KNOWN_SHORT.md").read_text().strip()
    full = (SHINKA / "KNOWN.md").read_text()
    sec_c = full[full.index("## C. How to use this list"):].strip()
    return short + "\n\n" + sec_c


def system_prompt() -> str:
    return TASK + "\n" + RULES.format(known=known_text()) + "\n" + OUTPUT


def user_prompt(lens: str, found: list[str] | None) -> str:
    base = (f"LENS for this call: {lens}.\nThink like a specialist in that field. Write 5 idea cards for the card writer, each "
            "starting from this lens, none of them KNOWN.")
    if found:
        base += ("\n\nFAR PASS. Cores already found (do not repeat or lightly vary any of them; propose something unlike all of them):\n"
                 + "\n".join(f"- {c}" for c in found))
    return base


def params(model_key: str, lens: str, found: list[str] | None = None) -> dict:
    return {"model": MODELS[model_key], "max_tokens": MAX_TOKENS, "system": system_prompt(),
            "messages": [{"role": "user", "content": user_prompt(lens, found)}],
            "output_config": {"effort": EFFORT}}


def parse_cards(text: str) -> list[dict]:
    """Cards from the last JSON object with a "cards" list; only well-formed cards are kept (all six fields, strings)."""
    dec, found, i = json.JSONDecoder(), None, text.find("{")
    while i != -1:
        try:
            obj, end = dec.raw_decode(text, i)
        except json.JSONDecodeError:
            i = text.find("{", i + 1)
            continue
        if isinstance(obj, dict) and isinstance(obj.get("cards"), list):
            found = obj["cards"]
        i = text.find("{", end)
    ok = []
    for c in found or []:
        if isinstance(c, dict) and all(isinstance(c.get(f), str) and c[f].strip() for f in FIELDS):
            ok.append({f: c[f].strip() for f in FIELDS})
    return ok


def words(s: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", s.lower()))


def pick_far_lenses(cards: list[dict], k: int = 6) -> list[str]:
    """The k lenses whose cores overlap least (mean over their cards of the best Jaccard with another lens's cards)."""
    def jac(a, b):
        return len(a & b) / max(1, len(a | b))
    score = {}
    for lens in LENSES:
        mine = [words(c["core_operation"]) for c in cards if c["lens"] == lens]
        others = [words(c["core_operation"]) for c in cards if c["lens"] != lens]
        if mine and others:
            score[lens] = sum(max(jac(m, o) for o in others) for m in mine) / len(mine)
    return sorted(score, key=lambda l: (score[l], LENSES.index(l)))[:k]


def run_batch(gc: GuardedClient, tag: str, jobs: list[tuple[str, str, list[str] | None]], poll_s: float):
    requests, meta, models = [], {}, {}
    for n, (mk, lens, found) in enumerate(jobs):
        cid = f"{tag}-{n:02d}"
        requests.append({"custom_id": cid, "params": params(mk, lens, found)})
        meta[cid], models[cid] = (mk, lens), MODELS[mk]
    batch, hold = gc.batch_submit(STAGE, tag, requests)
    print(f"[{tag}] submitted {len(requests)} calls, batch {batch.id}", flush=True)
    results = gc.batch_collect(STAGE, tag, batch, hold, models, poll_s=poll_s)
    cards, lost = [], []
    for cid, msg in results.items():
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        got = parse_cards(text)
        mk, lens = meta[cid]
        for c in got:
            cards.append({**c, "lens": lens, "model": mk, "pass": tag, "custom_id": cid})
        if not got:
            lost.append({"custom_id": cid, "stop_reason": msg.stop_reason, "tail": text[-200:]})
    missing = sorted(set(meta) - set(results))
    return cards, {"submitted": len(requests), "returned": len(results), "no_cards": lost, "not_returned": missing}


def g1(cards: list[dict]) -> dict:
    yes = [c for c in cards if c["fits_interface"].strip().lower().startswith("yes")]
    return {"parseable_cards": len(cards), "fits_interface_yes": len(yes), "min_required": G1_MIN_CARDS,
            "G1_pass": len(yes) >= G1_MIN_CARDS}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true", help="the real run (spends money, within the guard)")
    ap.add_argument("--fake", action="store_true", help="fake client, temp ledger, no network")
    ap.add_argument("--poll", type=float, default=30.0)
    a = ap.parse_args()

    if a.fake:
        import fake_client
        guard = Guard(ledger=Path(tempfile.mkdtemp()) / "ledger.jsonl")
        gc = GuardedClient(fake_client.FakeClient(), guard)
        a.poll = 0.0
    else:
        guard = Guard()
        pass1 = [(mk, lens, None) for lens in LENSES for mk in ("opus", "sonnet")]
        gc_probe = GuardedClient(None, guard)
        worst1 = sum(gc_probe.worst(params(mk, lens)) for mk, lens, _ in pass1)
        print(f"Stage 1: cap ${guard.stage_cap(STAGE):.2f}, stop ${guard.stage_stop(STAGE):.2f}, spent+held so far "
              f"${guard.spent(STAGE):.4f}; pass 1 = {len(pass1)} calls, summed worst case ${worst1:.3f}")
        if not a.go:
            print("dry run: nothing sent. Re-run with --go to launch.")
            return
        import prosecute
        gc = prosecute.make_client(guard)

    pass1 = [(mk, lens, None) for lens in LENSES for mk in ("opus", "sonnet")]
    OUT.mkdir(parents=True, exist_ok=True)
    cards, info, stopped = [], {}, None
    try:
        c1, info["pass1"] = run_batch(gc, "s1-pass1", pass1, a.poll)
        cards += c1
        far = pick_far_lenses(cards)
        info["far_lenses"] = far
        found = [c["core_operation"] for c in cards]
        c2, info["far"] = run_batch(gc, "s1-far", [(mk, l, found) for l in far for mk in ("opus", "sonnet")], a.poll)
        cards += c2
    except MoneyStop as e:
        stopped = str(e)
        print("MONEY STOP:", e, flush=True)
    tag = "fake" if a.fake else "real"
    (OUT / f"stage1_cards_{tag}.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cards))
    summary = {"mode": tag, "money_stop": stopped, "stage1_spent_usd": guard.spent(STAGE), "calls_info": info, **g1(cards),
               "cards_by_lens": {l: sum(c["lens"] == l for c in cards) for l in LENSES}}
    (OUT / f"stage1_summary_{tag}.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != "cards_by_lens"}, indent=2))


if __name__ == "__main__":
    main()
