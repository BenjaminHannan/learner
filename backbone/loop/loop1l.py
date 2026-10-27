#!/usr/bin/env python3
"""Loop-1L (backbone/PREREG-loop1L.md): think by looping the middle layers (and a latent board) on LFM2.5-24B-A2B.

Arms (same data, same LoRA, same optimiser, same seed list):
  a  LoRA, no loop.
  b  LoRA + layers [loop_start, loop_start+loop_len) (16..23) applied `passes` (4) times per forward, trained that way.
  c  b + latent board (d=256 per position): h_in = h + W_in(z); after each pass z += sigmoid(W_g[z,h]) * tanh(W_up(h)).
Thinking is OFF: every assistant turn is rendered `<think></think>...` (training targets and eval prompts).
Primary metric M_tool: for every assistant turn of the 200 eval chats, given the gold history, greedy reply makes the same
tool calls (multiset of (name, normalised args)); a gold no-tool turn is right iff the reply makes no tool call.

  python loop1l.py --arm b --seed 0 --out out/loop/b_s0
  python loop1l.py --smoke            # tiny random lfm2_moe on CPU, all arms, every code path
  python loop1l.py --estimate         # token counts + projected A100 time (no model)
"""
from __future__ import annotations

import argparse, ast, collections, contextlib, copy, json, math, os, random, sys, time, unicodedata
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE.parent / "assistant_data" / "data"
MODEL_ID = "LiquidAI/LFM2.5-24B-A2B"
TC_START, TC_END, IM_START, IM_END = "<|tool_call_start|>", "<|tool_call_end|>", "<|im_start|>", "<|im_end|>"
ASSIST_PREFIX = IM_START + "assistant\n<think></think>"   # thinking OFF: every assistant turn starts like this


def log(*a):
    print(*a, flush=True)


# ----------------------------------------------------------------------------------------------------------------------
# chat template rendering (the model's real template, + `<think></think>` after every assistant header)
# ----------------------------------------------------------------------------------------------------------------------
def to_tpl_messages(msgs):
    """OpenAI-format -> what LFM's template wants: tool_calls[].function.arguments must be a mapping, not a JSON string."""
    out = []
    for m in msgs:
        m = dict(m)
        if m.get("tool_calls"):
            tcs = []
            for t in m["tool_calls"]:
                f = t["function"]
                a = f.get("arguments")
                if isinstance(a, str):
                    a = json.loads(a) if a.strip() else {}
                tcs.append({"type": "function", "function": {"name": f["name"], "arguments": a or {}}})
            m["tool_calls"] = tcs
        out.append(m)
    return out


def render(tok, tools, msgs, gen_prompt=False):
    """Full text for `msgs` (no BOS added again by tokenisation: the template emits <|startoftext|> itself)."""
    s = tok.apply_chat_template(to_tpl_messages(msgs), tools=tools, tokenize=False, add_generation_prompt=False)
    s = s.replace(IM_START + "assistant\n", ASSIST_PREFIX)
    if gen_prompt:
        s += ASSIST_PREFIX
    return s


def tokenize_chat(tok, row):
    """-> (ids, labels) with labels=-100 except on assistant content/tool-call tokens and their <|im_end|>."""
    s = render(tok, row["tools"], row["messages"])
    enc = tok(s, add_special_tokens=False, return_offsets_mapping=True)
    ids, offs = enc["input_ids"], enc["offset_mapping"]
    spans, p = [], 0
    while True:
        a = s.find(ASSIST_PREFIX, p)
        if a < 0:
            break
        a += len(ASSIST_PREFIX)
        b = s.find(IM_END, a)
        b = len(s) if b < 0 else b + len(IM_END)
        spans.append((a, b)); p = b
    labels = [-100] * len(ids)
    j = 0
    for i, (st, en) in enumerate(offs):
        while j < len(spans) and st >= spans[j][1]:
            j += 1
        if j < len(spans) and st >= spans[j][0] and en <= spans[j][1] and en > st:
            labels[i] = ids[i]
    return ids, labels


def gold_turns(row):
    """[(index of assistant message, [(name, args_dict)...])] for every assistant turn."""
    out = []
    for i, m in enumerate(row["messages"]):
        if m["role"] == "assistant":
            calls = []
            for t in m.get("tool_calls") or []:
                a = t["function"].get("arguments")
                a = json.loads(a) if isinstance(a, str) and a.strip() else (a or {})
                calls.append((t["function"]["name"], a))
            out.append((i, calls))
    return out


# ----------------------------------------------------------------------------------------------------------------------
# tool-call parsing + scoring
# ----------------------------------------------------------------------------------------------------------------------
_NAMES = {"true": True, "false": False, "null": None, "none": None}


def _lit(n):
    if isinstance(n, ast.Constant):
        if isinstance(n.value, (str, int, float, bool)) or n.value is None:
            return n.value
        raise ValueError("const")
    if isinstance(n, (ast.List, ast.Tuple)):
        return [_lit(e) for e in n.elts]
    if isinstance(n, ast.Dict):
        if any(k is None for k in n.keys):
            raise ValueError("dict **")
        return {str(_lit(k)): _lit(v) for k, v in zip(n.keys, n.values)}
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
        v = _lit(n.operand)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("unary")
        return -v if isinstance(n.op, ast.USub) else v
    if isinstance(n, ast.Name) and n.id.lower() in _NAMES:
        return _NAMES[n.id.lower()]
    raise ValueError("unsupported " + type(n).__name__)


def _py_calls(seg):
    node = ast.parse(seg.strip(), mode="eval").body
    items = node.elts if isinstance(node, (ast.List, ast.Tuple)) else [node]
    out = []
    for c in items:
        if not isinstance(c, ast.Call):
            raise ValueError("not a call")
        f = c.func
        name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
        if name is None or c.args:
            raise ValueError("bad call head / positional args")
        args = {}
        for kw in c.keywords:
            if kw.arg is None:
                raise ValueError("**kwargs")
            args[kw.arg] = _lit(kw.value)
        out.append((name, args))
    return out


def _json_calls(obj):
    items = obj if isinstance(obj, list) else [obj]
    out = []
    for it in items:
        if not isinstance(it, dict):
            raise ValueError("json item")
        f = it.get("function") if isinstance(it.get("function"), dict) else it
        name = f.get("name")
        a = f.get("arguments", f.get("parameters", {}))
        if isinstance(a, str):
            a = json.loads(a) if a.strip() else {}
        if not isinstance(name, str) or not isinstance(a, dict):
            raise ValueError("json shape")
        out.append((name, a))
    return out


def parse_reply(text):
    """-> (made_call, parsed_ok, calls). Pythonic calls between the tool-call markers (LFM format); JSON also accepted
    (inside the markers, or as the whole reply when it has the name/arguments shape)."""
    text = text.replace(IM_END, "").strip()
    if TC_START in text:
        calls, ok, rest = [], True, text
        while TC_START in rest:
            rest = rest.split(TC_START, 1)[1]
            seg, _, rest = rest.partition(TC_END)       # missing end marker (cut at max tokens): take the rest
            try:
                try:
                    calls += _json_calls(json.loads(seg))
                except (ValueError, TypeError, AttributeError, KeyError):
                    calls += _py_calls(seg)
            except Exception:
                ok = False
        return True, ok, calls if ok else []
    if text[:1] in "[{":
        try:
            return True, True, _json_calls(json.loads(text))
        except Exception:
            pass
    return False, True, []


def _norm(v):
    if isinstance(v, str):
        return unicodedata.normalize("NFKC", v.strip()).casefold()
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, float):
        return int(v) if math.isfinite(v) and v == int(v) else v
    if isinstance(v, int):
        return v
    if isinstance(v, (list, tuple)):
        return [_norm(x) for x in v]
    if isinstance(v, dict):
        return {_norm(k): _norm(x) for k, x in v.items()}
    return str(v)


def canon_calls(calls):
    return collections.Counter((_norm(n), json.dumps(_norm(a), sort_keys=True, ensure_ascii=False)) for n, a in calls)


def score_turn(reply_text, gold_calls):
    made, ok, calls = parse_reply(reply_text)
    if not gold_calls:
        return not made
    return made and ok and canon_calls(calls) == canon_calls(gold_calls)


# ----------------------------------------------------------------------------------------------------------------------
# model: LoRA'd Lfm2Moe + loop + board, with its own forward (so the looped block can be re-applied and cached)
# ----------------------------------------------------------------------------------------------------------------------
class Board(nn.Module):
    def __init__(self, d_model, d_board=256):
        super().__init__()
        self.z0 = nn.Parameter(torch.randn(d_board))
        self.w_in = nn.Linear(d_board, d_model, bias=False)       # zero-init: arm c starts as exactly arm b
        self.w_up = nn.Linear(d_model, d_board)
        self.w_g = nn.Linear(d_board + d_model, d_board)
        nn.init.zeros_(self.w_in.weight)
        nn.init.normal_(self.w_up.weight, std=0.02); nn.init.zeros_(self.w_up.bias)
        nn.init.normal_(self.w_g.weight, std=0.02); nn.init.zeros_(self.w_g.bias)

    def init_state(self, B, T):
        return self.z0.float()[None, None, :].expand(B, T, -1)

    def read(self, h, z):
        return h + self.w_in(z).to(h.dtype)

    def write(self, h_out, z):
        ho = h_out.float()
        ho = ho * torch.rsqrt(ho.pow(2).mean(-1, keepdim=True) + 1e-6)   # parameter-free rms norm (h has a large scale)
        gate = torch.sigmoid(self.w_g(torch.cat([z, ho], -1)))
        return z + gate * torch.tanh(self.w_up(ho))


class LoopLM(nn.Module):
    def __init__(self, core, loop_start=16, loop_len=8, passes=4, board=None, grad_ckpt=True):
        super().__init__()
        self.core, self.board = core, board
        self.loop_start, self.loop_len, self.passes, self.grad_ckpt = loop_start, loop_len, passes, grad_ckpt
        self.cfg = core.config
        self.n_layers = self.cfg.num_hidden_layers
        self.zero_board = False
        self._ucfg = {}

    # ---- cache plumbing: the looped block gets one cache slot per pass ("unrolled" layer list) ----
    def unrolled_index(self, i, p, P):
        s, L = self.loop_start, self.loop_len
        if i < s: return i
        if i < s + L: return s + p * L + (i - s)
        return i + (P - 1) * L

    def unrolled_config(self, P):
        if P in self._ucfg: return self._ucfg[P]
        c = copy.deepcopy(self.cfg)
        lt = list(self.cfg.layer_types)
        s, L = self.loop_start, self.loop_len
        c.layer_types = lt[:s] + lt[s:s + L] * P + lt[s + L:]
        c.num_hidden_layers = len(c.layer_types)
        self._ucfg[P] = c
        return c

    def new_cache(self, P):
        from transformers import DynamicCache
        return DynamicCache(config=self.unrolled_config(P))

    def _set_idx(self, layer, idx):
        if layer.is_attention_layer: layer.self_attn.layer_idx = idx
        else: layer.conv.layer_idx = idx

    def hidden(self, input_ids, attention_mask=None, position_ids=None, cache=None, passes=None, use_loop=True):
        from transformers.masking_utils import create_causal_mask, create_recurrent_attention_mask
        m = self.core.model
        P = (passes or self.passes) if use_loop else 1
        emb = m.embed_tokens(input_ids)
        if position_ids is None:
            off = cache.get_seq_length() if cache is not None else 0
            position_ids = (torch.arange(emb.shape[1], device=emb.device) + off).unsqueeze(0)
        cfg = self.unrolled_config(P) if cache is not None else self.cfg
        kw = dict(config=cfg, inputs_embeds=emb, attention_mask=attention_mask, past_key_values=cache, position_ids=position_ids)
        masks = {"full_attention": create_causal_mask(**kw), "conv": create_recurrent_attention_mask(**kw)}
        pe = m.pos_emb(emb, position_ids=position_ids)
        h = emb
        s, L = self.loop_start, self.loop_len
        train_ckpt = self.grad_ckpt and torch.is_grad_enabled() and cache is None

        def run(i, x, uidx):
            layer = m.layers[i]
            if cache is not None: self._set_idx(layer, uidx)
            f = lambda y: layer(y, attention_mask=masks[self.cfg.layer_types[i]], position_ids=position_ids,
                                past_key_values=cache, position_embeddings=pe)
            return checkpoint(f, x, use_reentrant=False) if train_ckpt else f(x)

        for i in range(0, s):
            h = run(i, h, i)
        use_board = self.board is not None and use_loop and not self.zero_board
        z = self.board.init_state(h.shape[0], h.shape[1]) if use_board else None
        for p in range(P):
            if use_board: h = self.board.read(h, z)
            for j in range(L):
                h = run(s + j, h, self.unrolled_index(s + j, p, P))
            if use_board and p < P - 1: z = self.board.write(h, z)
        for i in range(s + L, self.n_layers):
            h = run(i, h, self.unrolled_index(i, 0, P))
        return m.embedding_norm(h)

    def lm_loss(self, input_ids, labels, attention_mask=None, **kw):
        """sum of CE over label tokens, and the label-token count."""
        h = self.hidden(input_ids, attention_mask, **kw)
        tgt = labels[:, 1:]
        sel = tgt != -100
        logits = self.core.lm_head(h[:, :-1][sel]).float()
        return F.cross_entropy(logits, tgt[sel], reduction="sum"), int(sel.sum())

    @torch.inference_mode()
    def generate(self, ids_list, tok, max_new=256, passes=None, use_loop=True, pad_id=0, eos_id=None):
        """Greedy, batched (left padded), cached. -> list of generated id lists (up to and excluding eos)."""
        dev = next(self.core.parameters()).device
        B = len(ids_list); T = max(len(x) for x in ids_list)
        inp = torch.full((B, T), pad_id, dtype=torch.long); am = torch.zeros((B, T), dtype=torch.long)
        for b, x in enumerate(ids_list):
            inp[b, T - len(x):] = torch.tensor(x); am[b, T - len(x):] = 1
        inp, am = inp.to(dev), am.to(dev)
        pos = (am.cumsum(-1) - 1).clamp(min=0)
        P = (passes or self.passes) if use_loop else 1
        cache = self.new_cache(P)
        h = self.hidden(inp, am, pos, cache, passes=P, use_loop=use_loop)
        nxt = self.core.lm_head(h[:, -1]).argmax(-1)
        out = [[] for _ in range(B)]; done = [False] * B
        last = pos[:, -1]
        for step in range(max_new):
            for b, t in enumerate(nxt.tolist()):
                if not done[b]:
                    if t == eos_id: done[b] = True
                    else: out[b].append(t)
            if all(done) or step == max_new - 1: break
            am = torch.cat([am, torch.ones((B, 1), dtype=am.dtype, device=dev)], 1)
            last = last + 1
            h = self.hidden(nxt[:, None], am, last[:, None], cache, passes=P, use_loop=use_loop)
            nxt = self.core.lm_head(h[:, -1]).argmax(-1)
        return out

    @torch.no_grad()
    def generate_nocache(self, ids, max_new, passes=None, use_loop=True, eos_id=None):
        """Reference implementation (full re-forward each step, batch 1) used by the smoke test to check the cache."""
        dev = next(self.core.parameters()).device
        x = torch.tensor([ids], device=dev); out = []
        for _ in range(max_new):
            h = self.hidden(x, passes=passes, use_loop=use_loop)
            t = int(self.core.lm_head(h[:, -1]).argmax(-1))
            if t == eos_id: break
            out.append(t); x = torch.cat([x, torch.tensor([[t]], device=dev)], 1)
        return out


LORA_REGEX = r".*\.layers\.\d+\.(self_attn\.(q_proj|k_proj|v_proj|out_proj)|conv\.(in_proj|out_proj)|feed_forward\.(w1|w2|w3))"


def build_model(args, device):
    from transformers import AutoModelForCausalLM, AutoTokenizer, Lfm2MoeConfig, Lfm2MoeForCausalLM
    tok = AutoTokenizer.from_pretrained(args.model)
    if args.smoke:
        lt = ["conv", "conv", "full_attention", "conv", "full_attention", "conv", "conv", "full_attention"]
        cfg = Lfm2MoeConfig(vocab_size=128000, hidden_size=64, intermediate_size=128, moe_intermediate_size=32,
                            num_hidden_layers=len(lt), layer_types=lt, num_attention_heads=4, num_key_value_heads=2,
                            num_dense_layers=1, num_experts=4, num_experts_per_tok=2, pad_token_id=tok.pad_token_id,
                            bos_token_id=tok.bos_token_id, eos_token_id=tok.eos_token_id,
                            rope_parameters={"rope_theta": 10000.0, "rope_type": "default"}, max_position_embeddings=8192)
        torch.manual_seed(1234)
        model = Lfm2MoeForCausalLM(cfg).float()
        model.generation_config.eos_token_id = tok.eos_token_id
    else:
        model = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16, device_map={"": 0})
    model.config.use_cache = False
    return model, tok


def parse_args(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--arm", choices=["a", "b", "c"])
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--model", default=MODEL_ID)
    p.add_argument("--out", default="out/loop/run")
    p.add_argument("--data", default=str(DATA_DIR))
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--estimate", action="store_true")
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--board-lr", type=float, default=1e-3, help="lr for the new board params (arm c)")
    p.add_argument("--batch", type=int, default=8, help="effective batch in chats")
    p.add_argument("--micro", type=int, default=1, help="chats per micro-batch")
    p.add_argument("--max-len", type=int, default=4096)
    p.add_argument("--train-frac", type=float, default=1.0, help="use the first fraction of the (shuffled) train chats")
    p.add_argument("--rank", type=int, default=16)
    p.add_argument("--alpha", type=int, default=32)
    p.add_argument("--loop-start", type=int, default=16)
    p.add_argument("--loop-len", type=int, default=8)
    p.add_argument("--rand-passes", type=int, default=0, help="addendum 2: sample training passes from 1..K per step (0 = fixed --passes)")
    p.add_argument("--passes", type=int, default=4, help="passes of the looped block in training (arms b, c)")
    p.add_argument("--d-board", type=int, default=256)
    p.add_argument("--eval-passes", type=int, default=None, help="passes for the primary eval (default: the trained passes)")
    p.add_argument("--extra-passes", default="1,8", help="extra eval passes for arms b,c (lesion=1, more=8); '' to skip")
    p.add_argument("--extra-n", type=int, default=100, help="chats used for the extra evals (first N of eval.jsonl)")
    p.add_argument("--zero-board", action="store_true", help="primary eval with the board zeroed (arm c)")
    p.add_argument("--eval-n", type=int, default=0, help="limit eval chats (0 = all 200)")
    p.add_argument("--gen-bs", type=int, default=32)
    p.add_argument("--max-new", type=int, default=256)
    p.add_argument("--load-adapter", default=None, help="dir with adapter/ and board.pt: skip training, just evaluate")
    p.add_argument("--no-save", action="store_true")
    a = p.parse_args(argv)
    if a.smoke:
        a.out = a.out if a.out != "out/loop/run" else "/tmp/loop1l_smoke"
        a.loop_start, a.loop_len, a.passes = 1, 3, 4
    return a


# ----------------------------------------------------------------------------------------------------------------------
def read_jsonl(path, n=0):
    rows = [json.loads(l) for l in open(path) if l.strip()]
    return rows[:n] if n else rows


def collate(batch, pad_id, dev):
    T = max(len(i) for i, _ in batch)
    ids = torch.full((len(batch), T), pad_id, dtype=torch.long); lab = torch.full((len(batch), T), -100, dtype=torch.long)
    am = torch.zeros((len(batch), T), dtype=torch.long)
    for b, (i, l) in enumerate(batch):
        ids[b, :len(i)] = torch.tensor(i); lab[b, :len(l)] = torch.tensor(l); am[b, :len(i)] = 1
    return ids.to(dev), lab.to(dev), am.to(dev)


def sync():
    if torch.cuda.is_available(): torch.cuda.synchronize()


def eval_loss(lm, tok_rows, pad_id, dev, passes, use_loop):
    lm.eval(); tot, n = 0.0, 0
    with torch.no_grad():
        for ids, lab in tok_rows:
            x, y, am = collate([(ids, lab)], pad_id, dev)
            s, c = lm.lm_loss(x, y, None, passes=passes, use_loop=use_loop)
            tot += float(s); n += c
    return tot / max(n, 1), n


def eval_gen(lm, tok, rows, args, passes, use_loop, dev, tag):
    """M_tool over all assistant turns of `rows`. Returns the summary dict (+ per-turn records)."""
    pad_id, eos_id = tok.pad_token_id, tok.convert_tokens_to_ids(IM_END)
    turns = []   # (chat idx, msg idx, prompt ids, gold calls, scenario)
    for ci, row in enumerate(rows):
        for mi, gold in gold_turns(row):
            s = render(tok, row["tools"], row["messages"][:mi], gen_prompt=True)
            turns.append((ci, mi, tok(s, add_special_tokens=False).input_ids, gold, row["scenario"]))
    order = sorted(range(len(turns)), key=lambda k: len(turns[k][2]))
    recs = [None] * len(turns); gen_tokens = 0; t0 = time.time(); sync()
    for bi in range(0, len(order), args.gen_bs):
        idx = order[bi:bi + args.gen_bs]
        outs = lm.generate([turns[k][2] for k in idx], tok, args.max_new, passes, use_loop, pad_id, eos_id)
        for k, o in zip(idx, outs):
            text = tok.decode(o, skip_special_tokens=False)
            ci, mi, _, gold, sc = turns[k]
            made, ok, calls = parse_reply(text)
            recs[k] = {"chat": ci, "msg": mi, "scenario": sc, "gold_tool": bool(gold), "made_call": made, "parse_ok": ok,
                       "correct": bool(score_turn(text, gold)), "n_gen": len(o), "text": text[:600]}
            gen_tokens += len(o)
        if (bi // args.gen_bs) % 10 == 0:
            log(f"[gen {tag}] {min(bi + args.gen_bs, len(order))}/{len(order)} turns, {time.time() - t0:.0f}s")
    sync(); dt = time.time() - t0
    return summarize(recs, gen_tokens, dt), recs


def summarize(recs, gen_tokens, dt):
    def pct(rs): return 100.0 * sum(r["correct"] for r in rs) / len(rs) if rs else None
    tool = [r for r in recs if r["gold_tool"]]; notool = [r for r in recs if not r["gold_tool"]]
    by = {}
    for sc in sorted({r["scenario"] for r in recs}):
        rs = [r for r in recs if r["scenario"] == sc]
        by[sc] = {"n_turns": len(rs), "m_tool": pct(rs), "n_tool_turns": sum(r["gold_tool"] for r in rs)}
    return {"n_turns": len(recs), "m_tool": pct(recs), "m_tool_tool_turns": pct(tool), "m_tool_notool_turns": pct(notool),
            "n_tool_turns": len(tool), "n_notool_turns": len(notool), "by_scenario": by,
            "unparseable_calls": sum(1 for r in recs if r["made_call"] and not r["parse_ok"]),
            "gen_tokens": gen_tokens, "gen_seconds": dt, "gen_tok_per_s": gen_tokens / max(dt, 1e-9)}


def lr_at(step, total, lr, warm):
    if step < warm: return lr * (step + 1) / warm
    return lr * 0.5 * (1 + math.cos(math.pi * (step - warm) / max(1, total - warm)))


def train(lm, groups, tok_rows, args, pad_id, dev):
    params = [p for g in groups for p in g['params']]
    opt = torch.optim.AdamW(groups, betas=(0.9, 0.99), weight_decay=0.0)
    rng = random.Random(args.seed)
    order = list(range(len(tok_rows))); rng.shuffle(order)
    order = order[:max(args.batch, int(len(order) * args.train_frac))] if not args.smoke else order[:args.smoke_chats]
    steps = math.ceil(len(order) / args.batch); warm = max(1, round(0.03 * steps))
    log(f"[train] chats={len(order)} steps={steps} batch={args.batch} micro={args.micro} warmup={warm}")
    lm.train(); t0 = time.time(); losses = []; tok_seen = 0; proj = None
    for step in range(steps):
        grp = [tok_rows[i] for i in order[step * args.batch:(step + 1) * args.batch]]
        ntok = sum(sum(1 for t in l[1:] if t != -100) for _, l in grp)
        for g in opt.param_groups: g["lr"] = lr_at(step, steps, g["base_lr"], warm)
        tot = 0.0
        # addendum 2: random pass count per step (1..K, weight proportional to the count) so more passes keep helping
        P = rng.choices(range(1, args.rand_passes + 1), weights=range(1, args.rand_passes + 1))[0] if args.rand_passes and lm.passes > 1 else None
        for mb in range(0, len(grp), args.micro):
            x, y, am = collate(grp[mb:mb + args.micro], pad_id, dev)
            s, _ = lm.lm_loss(x, y, am, passes=P)
            (s / max(ntok, 1)).backward(); tot += float(s); tok_seen += int(am.sum())
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step(); opt.zero_grad(set_to_none=True)
        losses.append(tot / max(ntok, 1))
        if step % 10 == 0 or step == steps - 1 or args.smoke:
            log(f"[train] step {step + 1}/{steps} loss {losses[-1]:.4f} lr {opt.param_groups[0]['lr']:.2e} "
                f"{tok_seen / (time.time() - t0):.0f} tok/s elapsed {time.time() - t0:.0f}s")
        if step == min(5, steps - 1):
            sync(); proj = (time.time() - t0) / (step + 1) * steps
            log(f"[proj] ~{proj / 60:.1f} min to train this run ({(time.time() - t0) / (step + 1):.2f} s/step incl. warmup)")
    sync()
    return {"steps": steps, "chats": len(order), "train_seconds": time.time() - t0, "loss_first": losses[0], "loss_last": losses[-1],
            "loss_mean_last10": sum(losses[-10:]) / len(losses[-10:]), "train_tok_per_s": tok_seen / (time.time() - t0),
            "projected_train_seconds": proj}


def count_lora(model):
    return sum(p.numel() for n, p in model.named_parameters() if "lora_" in n)


def run(args):
    dev = torch.device("cuda" if torch.cuda.is_available() and not args.smoke else "cpu")
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    arm = args.arm
    torch.manual_seed(args.seed); random.seed(args.seed)
    log(f"== loop1l arm={arm} seed={args.seed} model={'SMOKE-tiny' if args.smoke else args.model} dev={dev}")
    model, tok = build_model(args, dev)
    pad_id = tok.pad_token_id
    assert model.config.model_type == "lfm2_moe"
    from peft import LoraConfig, get_peft_model
    for p in model.parameters(): p.requires_grad_(False)
    pm = get_peft_model(model, LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=0.0, bias="none", target_modules=LORA_REGEX))
    core = pm.base_model.model
    n_lora = count_lora(pm)
    log(f"[model] LoRA r={args.rank} alpha={args.alpha} params={n_lora / 1e6:.2f}M; router NOT adapted; MoE experts NOT adapted; "
        f"lora dtype {next(p.dtype for n, p in pm.named_parameters() if 'lora_' in n)}")
    nwrap = sum(1 for _, m in pm.named_modules() if hasattr(m, 'lora_A'))
    log(f'[model] LoRA wraps {nwrap} linear modules')
    board = Board(core.config.hidden_size, args.d_board).to(dev) if arm == "c" else None
    use_loop = arm in ("b", "c")
    # arm a must never loop (bug found in review: it used to train with args.passes and evaluate with 1)
    lm = LoopLM(core, args.loop_start, args.loop_len, args.passes if use_loop else 1, board, grad_ckpt=True)
    if board is not None: log(f"[model] board params {sum(p.numel() for p in board.parameters()) / 1e6:.2f}M (fp32), d_board={args.d_board}")
    if use_loop: log(f"[model] loop: layers {args.loop_start}..{args.loop_start + args.loop_len - 1} x{args.passes} "
                     f"(types {core.config.layer_types[args.loop_start:args.loop_start + args.loop_len]})")

    # ---- data ----
    train_rows = read_jsonl(Path(args.data) / "train.jsonl"); eval_rows = read_jsonl(Path(args.data) / "eval.jsonl")
    if args.smoke: train_rows = train_rows[:args.smoke_chats]; eval_rows = eval_rows[:args.eval_n or 3]
    elif args.eval_n: eval_rows = eval_rows[:args.eval_n]
    t0 = time.time(); tok_train, dropped = [], 0
    for r in train_rows:
        ids, lab = tokenize_chat(tok, r)
        if len(ids) > args.max_len: dropped += 1; continue
        tok_train.append((ids, lab))
    tok_eval, dropped_eval = [], 0
    for r in eval_rows:
        ids, lab = tokenize_chat(tok, r)
        if len(ids) > args.max_len: dropped_eval += 1; continue
        tok_eval.append((ids, lab))
    log(f"[data] train {len(tok_train)} kept, {dropped} dropped (> {args.max_len} tokens); eval-loss {len(tok_eval)} kept, "
        f"{dropped_eval} dropped; mean train len {sum(len(i) for i, _ in tok_train) / max(1, len(tok_train)):.0f}; tokenised in {time.time() - t0:.0f}s")
    if arm == "a" or args.seed == 0 or args.smoke:
        ex = eval_rows[0]
        s = render(tok, ex["tools"], ex["messages"]); i0 = s.find(IM_START + "user")
        log("[render] (system + tools elided) ...\n" + s[:300] + "\n   ...[tools json elided]...\n" + s[i0:i0 + 1800] + "\n[render] --- generation prompt for the last assistant turn:")
        log(repr(render(tok, ex["tools"], ex["messages"][:-1], gen_prompt=True)[-160:]))
        ids, lab = tokenize_chat(tok, ex)
        tr = "".join(tok.decode([i]) if l != -100 else "" for i, l in zip(ids, lab))
        log("[render] loss-masked (trained) text:\n" + tr[:1200])

    result = {"arm": arm, "seed": args.seed, "model": args.model if not args.smoke else "smoke-tiny-lfm2_moe", "smoke": args.smoke,
              "args": {k: v for k, v in vars(args).items()}, "n_train_kept": len(tok_train), "n_train_dropped_overlen": dropped,
              "n_eval_loss_dropped_overlen": dropped_eval, "lora_params": n_lora, "lora_target": LORA_REGEX, "router_adapted": False,
              "experts_adapted": False, "board_params": sum(p.numel() for p in board.parameters()) if board is not None else 0}

    # ---- train ----
    params_lora = [p for n, p in pm.named_parameters() if "lora_" in n]
    for p in params_lora: p.requires_grad_(True)
    if args.load_adapter:
        from peft import set_peft_model_state_dict
        from safetensors.torch import load_file
        sd = load_file(str(Path(args.load_adapter) / "adapter" / "adapter_model.safetensors"))
        log("[load]", set_peft_model_state_dict(pm, sd).__class__.__name__)
        if board is not None: board.load_state_dict(torch.load(Path(args.load_adapter) / "board.pt", map_location=dev))
    else:
        groups = [{"params": params_lora, "base_lr": args.lr, "lr": args.lr}]
        if board is not None: groups.append({"params": list(board.parameters()), "base_lr": args.board_lr, "lr": args.board_lr})
        result["train"] = train(lm, groups, tok_train, args, pad_id, dev)
        if not args.no_save:
            pm.save_pretrained(out / "adapter")
            if board is not None: torch.save(board.state_dict(), out / "board.pt")
            log(f"[save] adapter -> {out / 'adapter'}" + (" + board.pt" if board is not None else ""))
    for p in params_lora: p.requires_grad_(False)

    # ---- eval ----
    def one_eval(tag, passes, loop_on, zero_board, rows, loss_rows):
        lm.zero_board = zero_board
        loss, nt = eval_loss(lm, loss_rows, pad_id, dev, passes, loop_on)
        summ, recs = eval_gen(lm, tok, rows, args, passes, loop_on, dev, tag)
        lm.zero_board = False
        summ.update({"tag": tag, "passes": passes if loop_on else 1, "zero_board": zero_board, "eval_loss": loss, "eval_loss_tokens": nt,
                     "n_chats": len(rows)})
        log(f"[result] {arm} s{args.seed} {tag}: M_tool {summ['m_tool']:.1f}% (tool turns {summ['m_tool_tool_turns']}, no-tool turns "
            f"{summ['m_tool_notool_turns']}) loss {loss:.4f} gen {summ['gen_tok_per_s']:.1f} tok/s over {summ['n_turns']} turns")
        return summ, recs
    P = (args.eval_passes or args.passes) if use_loop else 1
    main_tag = f"{arm}_p{P}" + ("_noboard" if args.zero_board else "")
    t_ev = time.time()
    main, recs = one_eval(main_tag, P, use_loop, args.zero_board and arm == "c", eval_rows, tok_eval)
    result["eval"] = main; result["turns"] = recs
    extras = {}
    if use_loop and args.extra_passes:
        sub = eval_rows[:args.extra_n]; sub_loss = tok_eval[:args.extra_n] if not args.smoke else tok_eval
        sub_set = {r["chat"] for r in recs if r["chat"] < len(sub)}
        main_sub = [r for r in recs if r["chat"] < len(sub)]
        extras["main_on_subset"] = summarize(main_sub, sum(r["n_gen"] for r in main_sub), 1.0)
        for q in [int(x) for x in args.extra_passes.split(",") if x]:
            if q == P and not (args.zero_board and arm == "c"): continue
            extras[f"p{q}"], _ = one_eval(f"{arm}_p{q}", q, True, False, sub, sub_loss)
        if arm == "c" and not args.zero_board:
            extras["noboard"], _ = one_eval(f"{arm}_p{P}_noboard", P, True, True, sub, sub_loss)
    result["extras"] = extras
    result["eval_seconds"] = time.time() - t_ev
    # compact numbers for label_report.py (percent values)
    ln = {"m": main["m_tool"]}
    for k, v in extras.items():
        if k != "main_on_subset": ln[k] = v["m_tool"]
    if extras: ln["sub"] = extras["main_on_subset"]["m_tool"]
    result["m_tool_acc"] = main["m_tool"] / 100.0
    result["label_nums"] = {k: round(v, 1) for k, v in ln.items() if v is not None}
    tr = result.get("train", {}).get("train_seconds", 0)
    result["total_seconds"] = tr + result["eval_seconds"]
    log(f"[result] {arm} s{args.seed} DONE: train {tr / 60:.1f} min + eval {result['eval_seconds'] / 60:.1f} min; "
        f"this run x12 = {12 * result['total_seconds'] / 3600:.2f} h")
    (out / f"result_{arm}_s{args.seed}.json").write_text(json.dumps(result, indent=1))
    return result


# ----------------------------------------------------------------------------------------------------------------------
def self_checks(tok, args):
    """Template / parser checks that need no model. Run in --smoke (and cheap enough to always run)."""
    # 1. template: our string == the stock template string once <think></think> is removed, and tool args are mappings
    for fn in ("train.jsonl", "eval.jsonl"):
        rows = read_jsonl(Path(args.data) / fn)[:60]
        for r in rows:
            ours = render(tok, r["tools"], r["messages"]).replace("<think></think>", "")
            ref = tok.apply_chat_template(to_tpl_messages(r["messages"]), tools=r["tools"], tokenize=False)
            assert ours == ref, "render mismatch"
    # 2. every gold tool-call turn of train+eval: render -> parse -> same multiset (parser + normaliser round trip)
    n = bad = 0
    for fn in ("train.jsonl", "eval.jsonl"):
        for r in read_jsonl(Path(args.data) / fn):
            s = render(tok, r["tools"], r["messages"])
            segs = [x.split(IM_END)[0] for x in s.split(ASSIST_PREFIX)[1:]]
            for (mi, gold), seg in zip(gold_turns(r), segs):
                n += 1
                if not score_turn(seg, gold): bad += 1; log("[selfcheck] gold round-trip FAIL:", seg[:200], gold)
    log(f"[selfcheck] gold render->parse round trip: {n - bad}/{n} assistant turns score correct")
    assert bad == 0
    # 3. parser behaviour
    g = [("read_file", {"path": "~/a b.txt", "max_lines": 5})]
    assert score_turn(f"{TC_START}[read_file(path='~/A B.txt ', max_lines=5.0)]{TC_END}{IM_END}", g)
    assert score_turn('<|tool_call_start|>[{"name": "read_file", "arguments": {"path": "~/a b.txt", "max_lines": 5}}]<|tool_call_end|>', g)
    assert score_turn('{"name": "read_file", "arguments": {"path": "~/a b.txt", "max_lines": 5}}', g)
    assert not score_turn(f"{TC_START}[read_file(path='~/a b.txt')]{TC_END}", g)
    assert not score_turn("Sure, I will read it.", g)
    assert score_turn("Sure, I will read it.", []) and not score_turn(f"{TC_START}[read_file(path='x')]{TC_END}", [])
    assert not score_turn(f"{TC_START}[read_file(path='x'{TC_END}", [])          # unparseable call still counts as a call
    assert score_turn(f"{TC_START}[b(x=1), a(y=[true, 'Z'])]{TC_END}", [("a", {"y": [True, "z"]}), ("b", {"x": 1})])
    assert not score_turn(f"{TC_START}[__import__('os').system('x')]{TC_END}", [("a", {})])   # never evaluated
    log("[selfcheck] parser unit checks passed")


def smoke_equivalence(lm, tok, label, passes_list, args):
    """cached batched generation == full re-forward generation; and passes=1 / no loop == stock HF forward."""
    eos = tok.convert_tokens_to_ids(IM_END)
    rows = read_jsonl(Path(args.data) / "eval.jsonl")[:2]
    prompts = []
    for r in rows:
        mi = gold_turns(r)[0][0]
        prompts.append(tok(render(tok, r["tools"], r["messages"][:mi], gen_prompt=True), add_special_tokens=False).input_ids[-90:])
    prompts = [prompts[0], prompts[1][-60:]]    # different lengths -> exercises left padding
    for P in passes_list:
        got = lm.generate(prompts, tok, 10, P, True, tok.pad_token_id, eos)
        ref = [lm.generate_nocache(p, 10, P, True, eos) for p in prompts]
        assert got == ref, f"{label} cached != no-cache at passes={P}: {got} vs {ref}"
        log(f"[smoke] {label}: cached batched (left-padded) greedy == full re-forward at passes={P}: {got[0][:6]}...")
    dev = next(lm.core.parameters()).device
    for P in passes_list:     # logits: prefill + 3 teacher-forced decode steps through the cache vs one full forward
        seq = torch.tensor([prompts[0][-40:] + [5, 77, 1234]], device=dev)
        with torch.no_grad():
            full = lm.core.lm_head(lm.hidden(seq, passes=P))
            cache = lm.new_cache(P); n0 = seq.shape[1] - 3
            lg = [lm.core.lm_head(lm.hidden(seq[:, :n0], None, None, cache, passes=P))]
            for t in range(3):
                lg.append(lm.core.lm_head(lm.hidden(seq[:, n0 + t:n0 + t + 1], None, None, cache, passes=P)))
            inc = torch.cat(lg, 1)
        d = (full - inc).abs().max().item()
        assert d < 1e-3, d
        log(f"[smoke] {label}: cached incremental logits == full-forward logits at passes={P} (max abs diff {d:.2e})")
    ids = torch.tensor([prompts[0]], device=dev)
    with torch.no_grad():
        a = lm.core(input_ids=ids).logits[:, -1].float(); b = lm.core.lm_head(lm.hidden(ids, use_loop=False)[:, -1]).float()
    assert torch.allclose(a, b, atol=1e-3, rtol=1e-3), (a - b).abs().max()
    log(f"[smoke] {label}: no-loop custom forward == stock HF forward (max abs diff {(a - b).abs().max():.2e})")


def estimate(args):
    """Token counts from the real tokenizer + analytic A100 time per arm (assumptions printed)."""
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.model)
    tr = [tokenize_chat(tok, r) for r in read_jsonl(Path(args.data) / "train.jsonl")]
    ev = read_jsonl(Path(args.data) / "eval.jsonl")
    lens = [len(i) for i, _ in tr]; keep = [l for l in lens if l <= args.max_len]
    lab = sum(sum(1 for t in l if t != -100) for (i, l), n in zip(tr, lens) if n <= args.max_len)
    n_turns = 0; prompt_tok = 0
    for r in ev:
        for mi, _ in gold_turns(r):
            n_turns += 1; prompt_tok += len(tok(render(tok, r["tools"], r["messages"][:mi], gen_prompt=True), add_special_tokens=False).input_ids)
    tot = sum(keep)
    log(f"[estimate] train chats {len(lens)} (dropped >{args.max_len}: {len(lens) - len(keep)}), tokens {tot / 1e6:.2f}M (mean {tot / len(keep):.0f}), "
        f"trained label tokens {lab / 1e3:.0f}k; eval assistant turns {n_turns}, mean prompt {prompt_tok / n_turns:.0f} tokens")
    N_act = 2.3e9; loop_share = args.loop_len / 40
    mfu, peak, step_s, tail = 0.22, 312e12, 0.065, 120
    log(f"[estimate] assumptions: A100 bf16 peak 312 TFLOPs, MFU {mfu:.0%} for training (HF MoE + LoRA + grad-ckpt), 2.3B non-embedding "
        f"active params/token, train cost 8*N*tokens (fwd+bwd+recompute), loop block {loop_share:.0%} of layers; generation: batch {args.gen_bs}, "
        f"{step_s * 1000:.0f} ms per decode step (x loop factor), slowest reply per batch ~{tail} tokens; 2 min model load. UNMEASURED: check the [proj] lines.")
    chat_frac = lambda n: min(n, 200) / 200

    def mins(arm, fr, ev_n, ex_n):
        f = 1 + (args.passes - 1) * loop_share if arm != "a" else 1.0
        train_s = 8 * N_act * tot * f / (peak * mfu) * fr
        turns = n_turns * chat_frac(ev_n)
        pre = 2 * N_act * prompt_tok * chat_frac(ev_n) * f / (peak * 0.3)
        dec = math.ceil(turns / args.gen_bs) * tail * step_s * f
        n_extra = 0 if arm == "a" else (2 + (1 if arm == "c" else 0))
        ext = n_extra * (chat_frac(ex_n) / max(chat_frac(ev_n), 1e-9)) * (pre + dec)
        return (train_s + pre + dec + ext + 120 + 30) / 60

    def total_h(fr, ev_n, ex_n):
        return 4 * sum(mins(a, fr, ev_n, ex_n) for a in "abc") / 60
    for arm in "abc":
        log(f"[estimate] arm {arm} full (train-frac 1, eval 200, extras {args.extra_n}): {mins(arm, 1.0, 200, args.extra_n):.0f} min per seed")
    log("[estimate] projected total for all 12 runs (hours):  train-frac x (eval chats / extra-eval chats)")
    for fr in (1.0, 0.5, 0.35, 0.25, 0.15):
        log("[estimate]   --train-frac %.2f: " % fr + "   ".join(f"{e}/{x}: {total_h(fr, e, x):.1f}h" for e, x in ((200, 100), (200, 50), (100, 50), (100, 30), (60, 30))))
    fits = [(fr, e, x) for fr in (1.0, 0.75, 0.5, 0.35, 0.25, 0.15) for e, x in ((200, 100), (200, 50), (100, 50), (100, 30), (60, 30)) if total_h(fr, e, x) <= 3.0]
    log(f"[estimate] this run's settings (train-frac {args.train_frac}, eval {args.eval_n or 200}, extras {args.extra_n}): "
        f"{total_h(args.train_frac, args.eval_n or 200, args.extra_n):.1f} h for 12 runs")
    log("[estimate] settings that fit 3 h (train-frac, eval chats, extra chats): " + (str(fits[:4]) if fits else "none"))


def main():
    args = parse_args()
    if args.estimate:
        return estimate(args)
    if args.smoke:
        args.smoke_chats = 16
        args.batch, args.micro, args.max_new, args.eval_n, args.extra_n = 8, 2, 12, 3, 3
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(args.model)
        self_checks(tok, args)
        shutil_rm = __import__("shutil").rmtree
        shutil_rm(args.out, ignore_errors=True)
        summary = {}
        for arm in "abc":
            a = copy.copy(args); a.arm = arm; a.out = f"{args.out}/{arm}_s0"; a.seed = 0
            r = run(a)
            summary[arm] = r["label_nums"]
            # cache-vs-no-cache equivalence on a freshly built tiny model with non-trivial (random) loop/board weights
        # equivalence tests
        model, tok = build_model(args, torch.device("cpu"))
        from peft import LoraConfig, get_peft_model
        for p in model.parameters(): p.requires_grad_(False)
        core = get_peft_model(model, LoraConfig(r=4, lora_alpha=8, target_modules=LORA_REGEX)).base_model.model
        for n, p in core.named_parameters():
            if "lora_B" in n: nn.init.normal_(p, std=0.05)
        board = Board(core.config.hidden_size, args.d_board)
        nn.init.normal_(board.w_in.weight, std=0.02)
        for pm_ in board.parameters(): pm_.requires_grad_(False)
        lm = LoopLM(core, args.loop_start, args.loop_len, args.passes, board).eval()
        smoke_equivalence(lm, tok, "arm c (board+loop+LoRA)", [1, 2, 4, 8], args)
        lm.board = None
        smoke_equivalence(lm, tok, "arm b (loop+LoRA)", [4], args)
        a = copy.copy(args); a.arm = "c"; a.seed = 0; a.out = f"{args.out}/c_reload"; a.load_adapter = f"{args.out}/c_s0"; a.no_save = True
        r2 = run(a)
        assert abs(r2["eval"]["eval_loss"] - json.load(open(f"{args.out}/c_s0/result_c_s0.json"))["eval"]["eval_loss"]) < 1e-3
        log("[smoke] --load-adapter reproduces the trained arm-c eval loss")
        log("[smoke] all arms ran; label nums:", json.dumps(summary))
        log("[smoke] OK")
        return
    assert args.arm, "--arm required"
    run(args)


if __name__ == "__main__":
    main()
