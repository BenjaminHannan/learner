"""Tests for train_wp.py on a synthetic fixture (same schema as data/wordprob-v1). CPU only.
  python -m pytest scripts/wordprob/test_train_wp.py -q     (or: python scripts/wordprob/test_train_wp.py)
"""
import json
import random
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import train_wp as T  # noqa: E402


def make_row(rng, i, tid):
    a, b, c = rng.randint(10, 60), rng.randint(10, 60), rng.randint(1, 9)
    ans = a + b - c
    return {"id": f"r{i}", "template_id": tid,
            "question": f"Sam has {a} apples and gets {b} more, then eats {c}. How many apples now?",
            "answer": ans, "scratchpad": f"{a} + {b} = {a + b}. {a + b} - {c} = {ans}. Answer: {ans}", "steps": 2, "topic": "fruit"}


def write_fixture(d, n=300):
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(1)
    for k, (split, cnt) in enumerate((("train", n), ("dev", 20), ("heldout_template", 20), ("heldout_structure", 20))):
        with open(d / f"{split}.jsonl", "w") as f:
            for i in range(cnt):
                f.write(json.dumps(make_row(rng, i, f"t{k}")) + "\n")
    (d / "MANIFEST.json").write_text(json.dumps({"fixture": True}))
    return d


def test_tokenizer_round_trip(tmp_path):
    d = write_fixture(tmp_path / "d")
    rows = T.read_jsonl(d / "train.jsonl")
    tok = T.Tok(T.build_vocab(rows))
    for r in rows[:20]:
        s = r["question"] + "\n" + r["scratchpad"]
        assert tok.decode(tok.encode(s)) == s
    assert tok.encode("~")[0] == T.UNK
    assert tok.decode(tok.encode("12") + [T.EOS] + tok.encode("99")) == "12"
    for ch in "0123456789+-*/=":
        assert ch in tok.idx


def test_loss_mask_only_target(tmp_path):
    d = write_fixture(tmp_path / "d")
    rows = T.read_jsonl(d / "train.jsonl")
    tok = T.Tok(T.build_vocab(rows))
    for arm in ("answer", "steps"):
        exs = [T.encode_example(tok, r, arm) for r in rows[:4]]
        x, y, m = T.make_batch(exs, 512)
        for b, (ids, npr) in enumerate(exs):
            sel = y[b][m[b]].tolist()
            assert sel == ids[npr:], arm                       # exactly the target tokens + EOS
            assert sel[-1] == T.EOS
            assert tok.decode(sel) == T.target_text(rows[b], arm)
            assert not m[b, : npr - 1].any()                   # question tokens carry no loss
            assert not m[b, len(ids) - 1:].any()               # padding carries no loss


def test_answer_parser():
    assert T.parse_answer("Answer: 74") == 74
    assert T.parse_answer("37 + 46 = 83. 83 - 9 = 74. Answer: 74") == 74
    assert T.parse_answer("Answer: 5. Answer: -12") == -12
    assert T.parse_answer("Answer:7") == 7
    assert T.parse_answer("no answer here 5") is None
    assert T.parse_answer("Answer: ") is None


def tiny_args(d, out, arm="steps", steps=30, **kw):
    argv = ["--data", str(d), "--arm", arm, "--out", str(out), "--steps", str(steps), "--device", "cpu", "--d", "64",
            "--layers", "2", "--heads", "2", "--ctx", "128", "--tokens-per-step", "2048", "--micro-tokens", "1024",
            "--warmup", "5", "--lr", "3e-3", "--eval-n", "16", "--log-every", "10"]
    for k, v in kw.items():
        argv += [f"--{k.replace('_', '-')}", str(v)]
    return T.parse_args(argv)


def test_cpu_steps_lower_loss(tmp_path, capsys):
    d = write_fixture(tmp_path / "d")
    args = tiny_args(d, tmp_path / "o", steps=30)
    T.train(args)
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("step ")]
    first, last = float(lines[0].split()[3]), float(lines[-1].split()[3])
    assert last < first - 0.5, (first, last)


def test_eval_writes_final_json(tmp_path):
    d = write_fixture(tmp_path / "d")
    args = tiny_args(d, tmp_path / "o", arm="answer", steps=10)
    T.train(args)
    j = json.loads((tmp_path / "o" / "final.json").read_text())
    for k in ("arm", "steps", "params", "tokens_seen", "accuracy", "by_steps", "samples", "manifest_sha256", "wall_seconds"):
        assert k in j
    assert j["arm"] == "answer" and j["steps"] == 10 and j["tokens_seen"] > 0
    for s in T.SPLITS:
        assert 0 <= j["accuracy"][s] <= 1
        assert len(j["samples"][s]) == 10
        assert "2" in j["by_steps"][s]
    assert len(j["manifest_sha256"]) == 64
    assert (tmp_path / "o" / "ckpt-3.pt").exists() or (tmp_path / "o" / "ckpt-2.pt").exists()
    assert (tmp_path / "o" / "final.pt").exists()


def test_kv_cache_matches_full_recompute():
    torch.manual_seed(0)
    model = T.GPT(30, d=32, layers=2, heads=2, ctx=64).eval()
    tok = T.Tok(T.SPECIALS + [chr(ord("a") + i) for i in range(27)])
    prompts = ["abc", "abcdefgh", "ab", "abcdef"]
    got = T.greedy(model, tok, prompts, "cpu", max_new=6, bs=4)
    for p, g in zip(prompts, got):
        ids = tok.encode(p)
        for _ in range(6):
            nxt = int(model(torch.tensor([ids]))[0, -1].argmax())
            if nxt == T.EOS:
                break
            ids.append(nxt)
        assert tok.decode(ids[len(tok.encode(p)):]) == g, (p, g)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
