"""CPU test for train_smol.py with a random tiny Llama (no download) and a char tokenizer stub.
  python -m pytest scripts/wordprob/test_train_smol.py -q     (or: python scripts/wordprob/test_train_smol.py)
"""
import json
import random
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import train_smol as S  # noqa: E402
import train_wp as W  # noqa: E402
from test_train_wp import make_row  # noqa: E402

CHARS = "0123456789+-*/=().,:%$ \n" + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ?!'"


class CharTok:
    pad_token_id, eos_token_id = 0, 1

    def encode(self, s, add_special_tokens=False):
        return [2 + CHARS.index(c) if c in CHARS else 2 for c in s]

    def decode(self, ids, skip_special_tokens=True):
        return "".join(CHARS[i - 2] for i in ids if i >= 2 and i - 2 < len(CHARS))


def tiny_model():
    from transformers import LlamaConfig, LlamaForCausalLM
    torch.manual_seed(0)
    return LlamaForCausalLM(LlamaConfig(vocab_size=2 + len(CHARS), hidden_size=32, intermediate_size=64,
                                        num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2,
                                        max_position_embeddings=512, pad_token_id=0, eos_token_id=1))


def fixture(d, n=400, m=300):
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(1)
    for k, (split, cnt) in enumerate((("train", n), ("dev", m), ("heldout_template", m), ("heldout_structure", m))):
        with open(d / f"{split}.jsonl", "w") as f:
            for i in range(cnt):
                r = make_row(rng, i, f"t{k}")
                r["n_steps"] = rng.choice([2, 3])
                f.write(json.dumps(r) + "\n")
    return d


def test_loss_mask_target_only(tmp_path):
    d = fixture(tmp_path / "d")
    rows = W.read_jsonl(d / "train.jsonl")
    tok = CharTok()
    exs = [S.encode_example(tok, r, 1) for r in rows[:4]]
    x, am, lab = S.make_batch(exs, 0)
    for b, (ids, npr) in enumerate(exs):
        sel = lab[b][lab[b] != -100].tolist()
        assert sel == ids[npr:] and sel[-1] == 1                  # scratchpad + EOS, nothing else
        assert tok.decode(sel[:-1]) == rows[b]["scratchpad"]
        assert (lab[b, :npr] == -100).all() and (lab[b, len(ids):] == -100).all()
    loss, n = S.lm_loss_sum(tiny_model(), x, am, lab)
    assert n == sum(len(i) - p for i, p in exs) and torch.isfinite(loss)


def test_train_eval_final_json(tmp_path):
    d = fixture(tmp_path / "d")
    args = S.parse_args(["--data", str(d), "--out", str(tmp_path / "o"), "--device", "cpu", "--max-steps", "5",
                         "--batch", "8", "--micro", "4", "--warmup", "2", "--eval-n", "40", "--max-new", "12",
                         "--log-every", "1"])
    S.train(args, tiny_model(), CharTok())
    fj = json.loads((tmp_path / "o" / "final.json").read_text())
    assert fj["arm"] == "smol_steps" and fj["steps"] == 5
    for sp in W.SPLITS:
        assert fj["eval_n"][sp] == 40 and sp in fj["accuracy"]
        assert set(fj["by_n_steps"][sp]) <= {"2", "3"}
        assert sum(v["n"] for v in fj["by_n_steps"][sp].values()) == 40
        rows = W.read_jsonl(d / f"{sp}.jsonl")
        orig = W.greedy
        W.greedy = lambda *a, **k: [""] * 40
        try:
            _, samples = W.evaluate(None, None, rows, "cpu", 40, 0)       # train_wp's own sampling
        finally:
            W.greedy = orig
        mine = [r["id"] for r in S.sample_rows(rows, 40, 0)]
        assert [s["id"] for s in samples] == mine[:10]
        assert [s["id"] for s in fj["samples"][sp]] == mine[:10]


if __name__ == "__main__":
    import tempfile
    for t in (test_loss_mask_target_only, test_train_eval_final_json):
        t(Path(tempfile.mkdtemp()))
        print("ok", t.__name__)
