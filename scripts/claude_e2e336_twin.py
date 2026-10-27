#!/usr/bin/env python3
"""336 plain twin: the same MiniCPM5-1B that Premonition's reader and mouth are built on,
with no notebook, no reader, no rules. It sees the whole chat so far (all days, kept across
restarts in its state dir, which is generous to the twin) and a fair instruction in the
style of exp 211: newer facts replace older ones, and say "I don't know" when not told.

New file only. Used by scripts/claude_e2e336_run.py as --arm twin --model <dir>.
Greedy decoding, max 160 new tokens, bf16 on CUDA if present, else float32 on CPU.
"""
from __future__ import annotations

import json
from pathlib import Path

SYSTEM = (
    "You are a friendly personal assistant chatting with one user. The user tells you "
    "about their life and the people in it. Remember what they tell you and answer their "
    "questions only from what they have told you in this chat. If they correct something, "
    "the newer information replaces the older. If they never told you something, say "
    "\"I don't know\" and do not guess. For small talk, just chat naturally. If they ask "
    "for ideas or a bit of writing, help, using what you know about them. Keep replies short."
)
MAX_NEW = 160

_CACHE: dict = {}


def _load(model_dir: str):
    if model_dir in _CACHE:
        return _CACHE[model_dir]
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if dev == "cuda" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(model_dir, torch_dtype=dtype,
                                                 trust_remote_code=True).to(dev).eval()
    _CACHE[model_dir] = (tok, model, dev)
    return _CACHE[model_dir]


class Twin336:
    def __init__(self, state_dir: str, model_dir: str):
        if not model_dir:
            raise SystemExit("336 twin: --model is required")
        self.path = Path(state_dir) / "twin336-history.json"
        self.history: list[dict] = []
        if self.path.exists():
            self.history = json.loads(self.path.read_text(encoding="utf-8"))
        self.tok, self.model, self.dev = _load(model_dir)

    def _prompt(self) -> str:
        msgs = [{"role": "system", "content": SYSTEM}] + self.history
        if getattr(self.tok, "chat_template", None):
            return self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        lines = [SYSTEM, ""]
        for m in self.history:
            lines.append(("User: " if m["role"] == "user" else "Assistant: ") + m["content"])
        lines.append("Assistant:")
        return "\n".join(lines)

    def turn(self, text: str) -> list[str]:
        import torch
        self.history.append({"role": "user", "content": text})
        ids = self.tok(self._prompt(), return_tensors="pt").to(self.dev)
        with torch.no_grad():
            out = self.model.generate(**ids, max_new_tokens=MAX_NEW, do_sample=False,
                                      pad_token_id=self.tok.eos_token_id)
        reply = self.tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
        reply = reply.split("\nUser:")[0].strip()
        self.history.append({"role": "assistant", "content": reply})
        self.path.write_text(json.dumps(self.history, ensure_ascii=False), encoding="utf-8")
        return [reply]

    def e2e_end_day(self) -> None:
        return None                      # no sleep; the history file is the whole memory


def build(state_dir: str, args) -> Twin336:
    return Twin336(state_dir, getattr(args, "model", ""))
