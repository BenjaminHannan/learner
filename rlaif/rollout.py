"""Multi-turn sandbox rollouts with Qwen3 chat format, and token-level log-prob / KL helpers."""
import json, re
import torch
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint
from sandbox import TOOLS, World
from checks import run_checks

SYSTEM = ("You are a personal assistant with tools for the user's files, email, calendar, notes and reminders. Today is {today}. "
          "Use tools when you need information or must act. Never send an email unless the user clearly asked you to send it; "
          "if the request is ambiguous or missing a key detail, or an action is irreversible and unconfirmed, ask the user instead of guessing. "
          "When finished, reply to the user briefly.")
TOOL_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.S)
GEN_PROMPT = "<|im_start|>assistant\n<think>\n\n</think>\n\n"  # Qwen3 generation prompt with enable_thinking=False


def hint_block(task, critique):
    ref = "\n".join(f"{c['name']}({json.dumps(c['arguments'])})" for c in task["reference"])
    return ("PRIVILEGED HINTS (only you can see these): reference solution: "
            f"{ref}\nthen reply: {task['reference_reply']}; feedback on a weak attempt: {critique or 'none'}")


def build_messages(task, c=None):
    m = [{"role": "system", "content": SYSTEM.format(today=task["state"].get("today", "2026-10-24"))}]
    if c:
        m.append({"role": "system", "content": c})
    return m + [{"role": "user", "content": task["user"]}]


def prompt_ids(tok, task, c=None):
    return tok.apply_chat_template(build_messages(task, c), tools=TOOLS, add_generation_prompt=True, enable_thinking=False, tokenize=True,
                                   return_dict=True)["input_ids"]


class Episode:
    def __init__(self, task, ids, c=None):
        self.task, self.ids, self.mask, self.prompt_len, self.c = task, list(ids), [0] * len(ids), len(ids), c
        self.world, self.transcript, self.final, self.done, self.turns, self.logps = World.from_json(task["state"]), [], "", False, 0, []
        self.transcript.append({"role": "user", "content": task["user"]})

    def checks(self):
        return run_checks(self.task, self.world, self.final)

    def check_frac(self):
        r = self.checks()
        return sum(r) / len(r)

    def view(self, new_prompt):
        """Same episode tokens behind a different prompt (teacher <-> student). Returns (ids, positions of model tokens)."""
        ids = list(new_prompt) + self.ids[self.prompt_len:]
        return ids, [len(new_prompt) + i for i, m in enumerate(self.mask[self.prompt_len:]) if m]


def tool_piece(results):
    s = "<|im_start|>user" + "".join(f"\n<tool_response>\n{r}\n</tool_response>" for r in results) + "<|im_end|>\n" + GEN_PROMPT
    return s


@torch.no_grad()
def rollout(model, tok, jobs, max_turns=6, max_new=384, max_total=2048, gen_batch=16, greedy=False, record_logps=False, log=None):
    """jobs: list of (task, c_or_None). max_total counts tokens after the prompt (generated + tool results).
    Returns list of Episode. Sampling is plain temperature-1 (no top-k/top-p) so recomputed log-probs match."""
    dev = next(model.parameters()).device
    eos = tok.convert_tokens_to_ids("<|im_end|>")
    pad = tok.pad_token_id if tok.pad_token_id is not None else eos
    eps = [Episode(t, prompt_ids(tok, t, c), c) for t, c in jobs]
    was_training = model.training
    model.eval()
    for turn in range(max_turns):
        active = [e for e in eps if not e.done]
        if not active:
            break
        for i in range(0, len(active), gen_batch):
            batch = active[i:i + gen_batch]
            for e in batch:
                e.budget = min(max_new, max_total - (len(e.ids) - e.prompt_len))
            for e in batch:
                e.done = e.done or e.budget <= 0
            batch = [e for e in batch if not e.done]
            if not batch:
                continue
            L = max(len(e.ids) for e in batch)
            x = torch.tensor([[pad] * (L - len(e.ids)) + e.ids for e in batch], device=dev)
            am = torch.tensor([[0] * (L - len(e.ids)) + [1] * len(e.ids) for e in batch], device=dev)
            kw = dict(do_sample=not greedy, max_new_tokens=max(e.budget for e in batch), pad_token_id=pad, eos_token_id=eos,
                      return_dict_in_generate=True, output_logits=record_logps)
            if not greedy:
                kw.update(temperature=1.0, top_k=0, top_p=1.0)
            out = model.generate(input_ids=x, attention_mask=am, **kw)
            gen = out.sequences[:, L:]
            for b, e in enumerate(batch):
                g = gen[b].tolist()[:e.budget]
                ended = eos in g
                if ended:
                    g = g[:g.index(eos) + 1]
                if record_logps:
                    lp = torch.stack([F.log_softmax(out.logits[t][b].float(), -1)[g[t]] for t in range(len(g))]).tolist()
                    e.logps += lp
                e.ids += g
                e.mask += [1] * len(g)
                e.turns += 1
                text = tok.decode(g[:-1] if ended else g, skip_special_tokens=False)
                e.transcript.append({"role": "assistant", "content": text})
                calls = TOOL_RE.findall(text)
                e.final = TOOL_RE.sub("", text).strip()
                if not calls or not ended or e.turns >= max_turns:
                    e.done = True
                    continue
                res = []
                for c in calls:
                    try:
                        d = json.loads(c)
                        res.append(e.world.call(d["name"], d.get("arguments", {})))
                    except Exception:
                        res.append("error: could not parse tool call; expected JSON with name and arguments")
                for r in res:
                    e.transcript.append({"role": "tool", "content": r})
                piece = tok("\n" + tool_piece(res), add_special_tokens=False)["input_ids"]
                e.ids += piece
                e.mask += [0] * len(piece)
        if log:
            log(f"turn {turn + 1}: {sum(not e.done for e in eps)} episodes still active")
    if was_training:
        model.train()
    return eps


# ---- log-probs and KL (full vocab, chunked, checkpointed) ----
def _hidden(model, ids, pos):
    base = model.get_base_model() if hasattr(model, "get_base_model") else model
    x = torch.tensor([ids], device=next(model.parameters()).device)
    h = base.model(input_ids=x, use_cache=False).last_hidden_state[0]
    return h[torch.tensor(pos, device=h.device) - 1], base.lm_head.weight  # position p is predicted from p-1


def _lp(h, W, tgt):
    return F.log_softmax((h @ W.T).float(), -1).gather(-1, tgt[:, None])[:, 0]


def _lp_kl(h, W, hq, tgt):
    lp = F.log_softmax((h @ W.T).float(), -1)
    lq = F.log_softmax((hq @ W.T).float(), -1)
    return lp.gather(-1, tgt[:, None])[:, 0], (lp.exp() * (lp - lq)).sum(-1)


def seq_terms(model, ids, pos, other=None, chunk=256):
    """Per model-token log pi(a_t | view) (with grad) and, if other=(ids2,pos2), KL(pi_view || sg pi_other) per token."""
    h, W = _hidden(model, ids, pos)
    tgt = torch.tensor([ids[p] for p in pos], device=h.device)
    if other is not None:
        with torch.no_grad():
            hq, _ = _hidden(model, *other)
    lps, kls = [], []
    for i in range(0, len(pos), chunk):
        if other is None:
            lps.append(checkpoint(_lp, h[i:i + chunk], W, tgt[i:i + chunk], use_reentrant=False))
        else:
            a, b = checkpoint(_lp_kl, h[i:i + chunk], W, hq[i:i + chunk], tgt[i:i + chunk], use_reentrant=False)
            lps.append(a); kls.append(b)
    return torch.cat(lps), (torch.cat(kls) if kls else None)


@torch.no_grad()
def recompute_logps(model, ep):
    pos = [i for i, m in enumerate(ep.mask) if m]
    lp, _ = seq_terms(model, ep.ids, pos)
    return lp.tolist()
