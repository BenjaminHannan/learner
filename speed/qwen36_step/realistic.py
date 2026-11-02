"""Night-shaped training examples from a week file (tokenizer only): shared by padding_stats.py and profile_step.py. See padding_stats.py for the assumptions."""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parents[1] / "backbone" / "sleep" / "brain"
sys.path[:0] = [str(BRAIN), str(BRAIN.parent), str(BRAIN.parent.parent)]


def pools(tokenizer, week=str(BRAIN / "data" / "week1.json"), day=5, seed=0):
    """-> (draw(rng, bsz, rem) -> [(ids, loss_start)], replay [(ids, loss_start)], mean lengths). Dream mix as sleepb.dream_ex: 50% text, 50% Q&A (half open-book, diary-test prompt);
    REM steps 70% Q&A. Replay = generic prompt + 16..48 reply tokens (the real replies are the base model's own, <= 48 new tokens)."""
    import sleepb as sb
    from sleep1 import Lang, generic_prompts
    from transformers import AutoTokenizer
    L = Lang(tokenizer if not isinstance(tokenizer, str) else AutoTokenizer.from_pretrained(tokenizer), False, "cpu")
    wk = json.load(open(week))
    diary, rng = sb.Diary(wk), random.Random(seed)
    qs = [(t["q"], t["target"]) for k in ("forward", "reverse") for t in wk["tests"][k]]
    items = [it["text"] for it in wk["items"] if it.get("text")]
    ob = [sb.ex_qa_ob(L, diary, q, ans, day) for q, ans in qs]
    cb = [sb.ex_qa(L, q, ans) for q, ans in qs]
    tx = [sb.ex_text(L, t + " " + rng.choice(items)[:60]) for t in items]
    rep = [(L.ids(L.render(None, g)) + [rng.randint(1000, 9000) for _ in range(rng.randint(16, 48))] + [L.eos], len(L.ids(L.render(None, g)))) for g in generic_prompts()]
    mean = lambda xs: sum(len(e) for e, _ in xs) / len(xs)  # noqa: E731
    lens = {"closed_book": mean(cb), "open_book": mean(ob), "text": mean(tx), "replay": mean(rep)}

    def draw(r, bsz, rem=False):
        return [r.choice(ob if r.random() < 0.5 else cb) if r.random() < (0.7 if rem else 0.5) else r.choice(tx) for _ in range(bsz)]
    return draw, rep, lens, L
