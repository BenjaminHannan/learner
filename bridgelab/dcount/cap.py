"""Shared machinery: load v1 D + saved Bridge (frozen_ctx=True), official eval batches, and a capture wrapper around PremonitionMini.answer."""
import json, sys, glob, time
from contextlib import contextmanager
from pathlib import Path
import torch
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
torch.set_num_threads(2)
ROOT = Path("/tmp/claude-0/scratch/r0/root")
TOK = REPO / "data/tokenizer/premonition-tok-v2.json"
NUM = "zero one two three four".split()


def load(bridge_on=True, d_ckpt="/tmp/claude-0/w/D-final.pt", c_ckpt="/tmp/claude-0/w/W2.pt"):
    from premonition.model import PremonitionMini
    from premonition.train import mini_config_from
    from v1 import run as vrun
    from v1.joint import Bridge
    saved = torch.load(d_ckpt, map_location="cpu", weights_only=False)
    d = PremonitionMini(mini_config_from(saved["config"]))
    d.load_state_dict(saved["model"])
    c, _, _ = vrun.load_creative(c_ckpt, "cpu")
    bridge = Bridge(d.config.d_model, c.d).attach(d, c)
    bridge.load_state_dict(saved["bridge"])
    bridge.frozen_ctx = True
    bridge.enabled = bool(bridge_on)       # False = bridge_in returns zeros (v1's own "bridge-off lesion")
    d.eval()
    for p in list(d.parameters()) + list(bridge.parameters()):
        p.requires_grad_(False)
    return d, bridge


def question_info(split):
    info = {}
    for f in glob.glob(f"{ROOT}/{split}/shard-*.jsonl"):
        for l in open(f):
            r = json.loads(l)
            if r.get("kind") == "question":
                info[r["id"]] = r
    return info


@contextmanager
def capture(model, tok_ids=None):
    """Record, per answer() call: initial question rows, final episode rows (question / cards / registers), first-position decoder state+logits."""
    import torch.nn.functional as F
    box = {}
    o_start, o_greedy = model._start, model._greedy

    def start(batch, hidden, store, mentions):
        ep = o_start(batch, hidden, store, mentions)
        box["q0"] = ep.x[:, :model.config.question_rows].detach().float().clone()
        box["qvalid"] = ep.valid[:, :model.config.question_rows].clone()
        return ep

    def greedy(batch, ep, mentions, stop):
        cfg = model.config
        cb, cr = model._card_base, model._register_base
        box["q1"] = ep.x[:, :cfg.question_rows].detach().float().clone()
        box["cards"] = ep.x[:, cb:cb + cfg.cards].detach().float().clone()
        box["cvalid"] = ep.valid[:, cb:cb + cfg.cards].clone()
        box["regs"] = ep.x[:, cr:cr + cfg.registers].detach().float().clone()
        box["ncards"] = ep.count.clone()
        # first decoding position, exactly as _greedy does it
        seq = batch.tokens[batch.q_visit, batch.q_span[:, 1] - 1].unsqueeze(1)
        h = model._decode_logits(ep.x, ep.valid, seq)[:, -1]
        logits = F.linear(h, model.embed.weight).float()
        banned = torch.zeros_like(logits, dtype=torch.bool)
        if cfg.pointers:
            banned[:, cfg.vocab_size:] = ~mentions
        logits = logits.masked_fill(banned, float("-inf"))
        box["dec_h"] = h.detach().float().clone()
        box["top5"] = logits.topk(5, -1)
        if tok_ids is not None:
            box["num_logits"] = logits[:, tok_ids].clone()
        return o_greedy(batch, ep, mentions, stop)

    model._start, model._greedy = start, greedy
    try:
        yield box
    finally:
        del model._start, model._greedy
