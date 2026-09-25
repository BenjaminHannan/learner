#!/usr/bin/env python3
"""gram-362: a learned grammar critic picks the cleanest of the 1B's chat drafts (grammar thread, 2026-09-25).

Why: gram-361 (VERIFY-361.md) showed the 1B's chat replies stay ~90% clean even at low temperature; the misses look
like the 1B's own ceiling. But 338 already samples 4 drafts per reply and keeps the first safe one, and ~82% of
drafts are clean, so picking well has room.

What (one change): before 338's guards see the drafts, they are ordered by a learned critic, best first; 338 then
keeps the first draft that passes its guards exactly as today. The critic is a small logistic head on the 1B's own
hidden states (the same loaded model, no new model): mean of two layers over the draft's tokens, read in the chat
context. It was trained only on the 1B's drafts for 320 training prompts (never a test panel), labelled clean or
not by blind Opus graders. Like an inner critic: the language model hears its own drafts and keeps the one that
sounds right. Nothing else changes: guards, history, temperature 0.7, 4 samples, creative, notebook.

  install: CriticGen362(gen338, critic) stands in for the Gen338 passed to install_chat338b.
  features: critic_features(one_b, msgs, draft) -> 1-D tensor.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
HEAD362 = ROOT / "artifacts" / "claude-gram362-20260925" / "critic_head.json"
LAYERS362 = (-8, -1)                     # a middle-late layer and the last layer


def render_with_draft(tok, msgs: list[dict], draft: str) -> tuple[str, str]:
    kw = {"tokenize": False, "add_generation_prompt": True, "enable_thinking": False}
    try:
        prompt = tok.apply_chat_template(msgs, **kw)
    except Exception:  # noqa: BLE001  (a template without a system role, as Gen338._render)
        first = dict(msgs[1]) if len(msgs) > 1 else {"role": "user", "content": ""}
        first["content"] = msgs[0]["content"] + "\n\n" + first["content"]
        prompt = tok.apply_chat_template([first] + msgs[2:], **kw)
    return prompt, draft


def critic_features(one_b, msgs: list[dict], draft: str):
    """Mean hidden state of the draft's tokens at LAYERS362, read after the chat context."""
    torch = one_b.torch
    prompt, d = render_with_draft(one_b.tok, msgs, draft)
    p_ids = one_b.tok(prompt, return_tensors="pt")["input_ids"]
    d_ids = one_b.tok(d, add_special_tokens=False, return_tensors="pt")["input_ids"]
    ids = torch.cat([p_ids, d_ids], dim=1).to(one_b.dev)
    with torch.no_grad():
        hs = one_b.model(input_ids=ids, output_hidden_states=True).hidden_states
    n = d_ids.shape[1]
    parts = [hs[layer][0, -n:, :].float().mean(0) if n else hs[layer][0, -1, :].float() for layer in LAYERS362]
    return torch.cat(parts).cpu()


STATS362 = ("log_tokens", "mean_lp", "min_lp", "lp_3rd_lowest", "frac_below_2", "n_below_4", "n_below_6",
            "worst_window5", "ends_list_number", "no_end_mark", "repeated_trigrams", "repeated_sentences")


def critic_stats(one_b, msgs: list[dict], draft: str):
    """Token-probability and shape signals of a draft, from one pass of the 1B (temperature 1).
    Garbled phrases and invented words show up as tokens the 1B itself found unlikely."""
    import math
    import re
    torch = one_b.torch
    prompt, d = render_with_draft(one_b.tok, msgs, draft)
    p_ids = one_b.tok(prompt, return_tensors="pt")["input_ids"]
    d_ids = one_b.tok(d, add_special_tokens=False, return_tensors="pt")["input_ids"]
    ids = torch.cat([p_ids, d_ids], dim=1).to(one_b.dev)
    n = d_ids.shape[1]
    with torch.no_grad():
        logits = one_b.model(input_ids=ids).logits[0, -n - 1:-1, :].float()
    lp = torch.log_softmax(logits, -1).gather(1, ids[0, -n:].unsqueeze(1)).squeeze(1).cpu() if n else torch.zeros(1)
    srt = lp.sort().values
    win = lp.unfold(0, 5, 1).mean(1).min() if len(lp) >= 5 else lp.mean()
    words = re.findall(r"[a-z']+", d.lower())
    tri = [tuple(words[i:i + 3]) for i in range(len(words) - 2)]
    sents = [x.strip().lower() for x in re.split(r"(?<=[.!?])\s+", d) if x.strip()]
    v = [math.log(1 + n), float(lp.mean()), float(srt[0]), float(srt[min(2, len(srt) - 1)]),
         float((lp < -2).float().mean()), float((lp < -4).sum()), float((lp < -6).sum()), float(win),
         float(bool(re.search(r"(^|\s)\d+\.$", d))), float(not re.search(r"[.!?\"')]$", d)),
         float(len(tri) - len(set(tri))), float(len(sents) - len(set(sents)))]
    return torch.tensor(v)


class Critic362:
    """Logistic head: P(clean) = sigmoid(w . standardise(x) + b). The head file names its feature sets in order:
    "stats" = critic_stats, "feats" = critic_features."""

    def __init__(self, one_b, path: Path = HEAD362):
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        t = one_b.torch
        self.one_b = one_b
        self.mu, self.sd = t.tensor(d["mu"]), t.tensor(d["sd"])
        self.w, self.b = t.tensor(d["w"]), float(d["b"])
        self.features = d.get("features", ["feats"])

    def score(self, msgs: list[dict], draft: str) -> float:
        fn = {"stats": critic_stats, "feats": critic_features}
        x = self.one_b.torch.cat([fn[f](self.one_b, msgs, draft) for f in self.features])
        x = (x - self.mu) / self.sd
        return float(self.one_b.torch.sigmoid(x @ self.w + self.b))


class CriticGen362:
    """Wraps a Gen338: same drafts, ordered best first by the critic. 338's guards then pick as before."""

    def __init__(self, gen, critic: Critic362):
        self.gen, self.critic = gen, critic
        self.last_scores: list[float] = []

    def sample_chat(self, msgs: list[dict], n: int) -> list[str]:
        import claude_chat338_agent as C38
        drafts = self.gen.sample_chat(msgs, n)
        scored = [(self.critic.score(msgs, C38.trim(c)), i, c) for i, c in enumerate(drafts)]
        scored.sort(key=lambda s: (-s[0], s[1]))
        self.last_scores = [s[0] for s in scored]
        return [c for _s, _i, c in scored]


def run_chat_component(model_dir: str, turns: list[dict], use_critic: bool, seed: int, tmp: str,
                       head: Path = HEAD362) -> list[dict]:
    """One arm of the component test (as gram-361's): 338b's chat layer on a stub agent that always gives up."""
    import random

    import torch

    import claude_chat338_agent as C38
    import claude_chat338b_agent as C38B
    import claude_cre333_agent as C
    import claude_cre333b_agent as C333B
    import claude_gram361 as G361
    C._facts = lambda loop: []
    one_b = C333B.Gen333b(model_dir)
    gen = C38.Gen338(share=one_b)                               # 338's own settings (0.7, 4 drafts)
    if use_critic:
        gen = CriticGen362(gen, Critic362(one_b, head))
    out, convs = [], {}
    for t in turns:
        convs.setdefault(t["conv_id"], []).append(t)
    for ci, cid in enumerate(sorted(convs)):
        d = Path(tmp) / f"{cid}-{int(use_critic)}"
        d.mkdir(parents=True, exist_ok=True)
        loop = G361._GiveUp(str(d))
        C38B.install_chat338b(loop, gen)
        for t in sorted(convs[cid], key=lambda x: x["turn_index"]):
            torch.manual_seed(seed + ci * 100 + t["turn_index"])
            random.seed(seed + ci * 100 + t["turn_index"])
            reply = " ".join(p for p in loop.turn(t["user_text"]) if p)
            out.append({"conv_id": cid, "turn_index": t["turn_index"], "kind": t["kind"], "reply": reply})
        out[-1]["stats"] = dict(loop.chat338_stats, **loop.chat338b_stats)
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--gen-model", required=True)
    ap.add_argument("--critic", action="store_true")
    ap.add_argument("--seed", type=int, default=3620)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tmp", required=True)
    a = ap.parse_args()
    turns = [json.loads(x) for x in Path(a.panel).read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = run_chat_component(a.gen_model, turns, a.critic, a.seed, a.tmp)
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"rows": len(rows), "critic": a.critic}))
