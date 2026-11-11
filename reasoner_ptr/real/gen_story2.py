"""Fresh story set for the real-pipeline pointer test (round 2 of the two-doors work).
Same story shapes as ../gen_story.py, new word split, new eval draw, and fresh eval-only wording added to every frame
(none of these frames appears in training or in round 1's eval)."""
import json, random, collections
import gen_story as G

G.SPLIT_SEED, G.EVAL_SEED = 20261004, 4242
FRESH = {
    "open": ["One night,", "After school,"],
    "take": ["{p} lifted the {o}.", "{p} seized the {o}."],
    "go": ["{p} visited the {l}.", "{p} strolled to the {l}."],
    "give": ["{p} let {q} have the {o}.", "{q} received the {o} from {p}."],
    "q_taker": ["Who was the first to take the {o}?"],
    "q_went": ["Which place did {p} visit?"],
    "q_what": ["Which object did {p} grab?"],
    "q_holder": ["Who holds the {o} at last?"],
    "q_where_obj": ["Which place has the {o} now?"],
}
for k, v in FRESH.items():
    G.W[k]["new"] = list(v)  # eval-only wording for this round: all fresh


_tok = None


def fits(text, cap=49):
    """the real core's query cap: at most 49 tokens including EOS"""
    global _tok
    if _tok is None:
        from transformers import AutoTokenizer
        _tok = AutoTokenizer.from_pretrained("LiquidAI/LFM2.5-1.2B-Instruct", revision="0f604ada3f766f9f257460c4c9f0b5d6f69d431b")
    return len(_tok.encode(text, add_special_tokens=False)) + 1 <= cap


def eval_form():
    """48 per cell, stories longer than the core's cap are redrawn (same rng stream)."""
    sp = G.split(); r = random.Random(G.EVAL_SEED); rows = []
    for ans_cell in ("seen", "unseen"):
        words = {k: v["train" if ans_cell == "seen" else "heldout"] for k, v in sp.items()}
        for wording in ("train", "new"):
            for hop, kinds in (("one", G.ONE_HOP), ("two", G.TWO_HOP)):
                i = 0
                while i < 48:
                    s = G.story(r, words, wording, kinds[i % len(kinds)])
                    if not fits(s["text"]):
                        continue
                    s.update(cell=f"{ans_cell}-{wording}-{hop}", id=f"{ans_cell}-{wording}-{hop}-{i:02d}")
                    rows.append(s); i += 1
    return rows


def stream(seed, n, exclude):
    sp = G.split()
    out = G.stream(seed, int(n * 1.05) + 64, {k: v["train"] for k, v in sp.items()}, exclude)
    out = [x for x in out if fits(x["text"])]
    assert len(out) >= n, (len(out), n)
    return out[:n]


if __name__ == "__main__":
    import sys
    form = eval_form()
    assert len({x["text"] for x in form}) == len(form)
    print(collections.Counter(x["cell"] for x in form))
    for x in form[200:203] + form[-2:]: print(x)
    if len(sys.argv) > 1: open(sys.argv[1], "w").write(json.dumps(form, indent=0))
