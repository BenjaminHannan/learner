"""Opt-in faster generation for the sleep nights (Lang.generate and sleepb.generate_p). Default OFF: nothing changes until install() is called.

  import fastgen; fastgen.install(compact=True, seg=8, dedupe=True, pad_multiple=1)   # before Brain runs; fastgen.uninstall() undoes it
  or  SLEEP_FASTGEN=1 python speed/dreamgen/run_sleepb_fast.py <the usual sleepb.py args>

What it changes (outputs: greedy identical up to float noise from a different batch size; sampling: same distribution, other RNG stream):
 1. compact: decode in segments of `seg` tokens through the SAME HF generate (past_key_values handed on); after each segment rows that hit an
    end id are dropped from the batch and from the cache (Cache.reorder_cache = index_select; covers DeltaNet conv/recurrent state), so a batch
    whose longest dream runs 400 tokens no longer pays 32 rows for the 300 tokens that most rows were already done.
 2. dedupe (greedy only): identical prompts are generated once.
 3. pad_multiple m>1: the batch's left-padded length is rounded up to a multiple of m (masked pad, exact) so fewer distinct shapes reach the
    kernels (suggested fix if the ~6 s 'prefill' constant seen in the RTX PRO 6000 bench is a per-shape triton/JIT warm-up; see NOTES.md).
"""
import sys
import torch

CFG = dict(compact=True, seg=8, dedupe=True, pad_multiple=1)
_ORIG = {}


def _eos_list(eos):
    return [eos] if isinstance(eos, int) else list(eos)


def _plain(model):  # True when HF generate with a cache handed on is safe: a real HF model, text-only (no cached mrope rope_deltas)
    m = model
    for _ in range(4):
        if getattr(m, "rope_deltas", None) is not None:
            return False
        m = getattr(m, "base_model", None) or getattr(m, "model", None) or getattr(m, "get_base_model", lambda: None)()
        if m is None:
            break
    return hasattr(model, "generate") and hasattr(model, "config")


@torch.no_grad()
def run_batch(model, ids, mask, max_new, pad, eos, gen_kw, seg=8, want_p0=False):
    """Left-padded batch -> (list of new-token lists as HF would return them [row ends at its first end id, then pad up to the longest row], p0 or None).
    p0[r] = softmax prob of row r's first generated token (generate_p)."""
    B, n = ids.shape
    eos_ids = _eos_list(eos)
    toks = [[] for _ in range(B)]
    done = [False] * B
    alive = list(range(B))
    seq, am, cache, steps, p0 = ids, mask, None, 0, [None] * B
    while alive and steps < max_new:
        T = min(seg, max_new - steps)
        first = steps == 0
        kw = dict(output_scores=True) if (want_p0 and first) else {}
        out = model.generate(input_ids=seq, attention_mask=am, max_new_tokens=T, past_key_values=cache, pad_token_id=pad, eos_token_id=eos,
                             return_dict_in_generate=True, use_cache=True, **gen_kw, **kw)
        new = out.sequences[:, seq.shape[1]:]
        cache = out.past_key_values
        if want_p0 and first:
            pr = torch.softmax(out.scores[0].float(), -1)
            for k, r in enumerate(alive):
                p0[r] = float(pr[k, new[k, 0]])
        rows = new.tolist()
        keep = []
        for k, r in enumerate(alive):
            row = rows[k]
            cut = next((i for i, t in enumerate(row) if t in eos_ids), None)
            if cut is not None:
                toks[r] += row[:cut + 1]
                done[r] = True
            else:
                toks[r] += row
                keep.append(k)
        steps += new.shape[1]
        if not keep or steps >= max_new:
            break
        seq, am = torch.cat([seq, new], 1), torch.cat([am, am.new_ones(am.shape[0], new.shape[1])], 1)
        if len(keep) < len(alive):  # drop finished rows from the batch and the cache
            ix = torch.tensor(keep, device=seq.device)
            seq, am = seq[ix], am[ix]
            cache.reorder_cache(ix)
        alive = [alive[k] for k in keep]
    width = max((len(t) for t in toks), default=0)
    return [t + [pad] * (width - len(t)) for t in toks], (p0 if want_p0 else None)


def _tensors(L, enc, pm):
    n = max(map(len, enc))
    n = -(-n // pm) * pm if pm > 1 else n
    pad = 0 if L.smoke else (L.tok.pad_token_id if L.tok.pad_token_id is not None else L.eos)
    ids = torch.full((len(enc), n), pad, dtype=torch.long)
    mask = torch.zeros((len(enc), n), dtype=torch.long)
    for r, e in enumerate(enc):
        ids[r, n - len(e):] = torch.tensor(e)
        mask[r, n - len(e):] = 1
    return ids.to(L.device), mask.to(L.device), pad


def fast_generate(L, model, prompts, max_new=20, bs=8, sample=False, temp=0.8, eos=None, want_p0=False, cfg=None):
    cfg = cfg or CFG
    if not cfg["compact"] or not _plain(model):
        return None  # caller falls back to the original
    kw = dict(do_sample=True, temperature=temp, top_p=0.95, top_k=0) if sample else dict(do_sample=False)
    eos = L.eos if eos is None else eos
    uniq, back = list(range(len(prompts))), list(range(len(prompts)))
    if cfg["dedupe"] and not sample:
        first = {}
        uniq = [i for i in range(len(prompts)) if first.setdefault(prompts[i], i) == i]
        back = [first[p] for p in prompts]
    order = sorted(uniq, key=lambda i: len(prompts[i]))  # same key as Lang.generate
    outs, ps = {}, {}
    for st in range(0, len(order), bs):
        idx = order[st:st + bs]
        ids, mask, pad = _tensors(L, [L.ids(prompts[i]) for i in idx], cfg["pad_multiple"])
        n = ids.shape[1]
        toks, p0 = run_batch(model, ids, mask, max_new, pad, eos, kw, cfg["seg"], want_p0)
        for r, i in enumerate(idx):
            outs[i] = L.decode(toks[r]).strip()
            if want_p0:
                ps[i] = p0[r]
    o = [outs[back[i]] for i in range(len(prompts))]
    return (o, [ps[back[i]] for i in range(len(prompts))]) if want_p0 else o


def install(sleepb=None, **cfg):
    """Patch Lang.generate (sleep1) and generate_p (sleepb module, pass it in or it is found in sys.modules)."""
    CFG.update(cfg)
    import sleep1
    if "Lang.generate" not in _ORIG:
        _ORIG["Lang.generate"] = sleep1.Lang.generate
        orig = sleep1.Lang.generate

        @torch.no_grad()
        def generate(self, model, prompts, max_new=20, bs=8, sample=False, temp=0.8, eos=None):
            r = fast_generate(self, model, prompts, max_new, bs, sample, temp, eos)
            return orig(self, model, prompts, max_new=max_new, bs=bs, sample=sample, temp=temp, eos=eos) if r is None else r
        sleep1.Lang.generate = generate
    sb = sleepb or next((m for k, m in sys.modules.items() if k.split(".")[-1] in ("sleepb", "__main__") and hasattr(m, "generate_p")), None)
    if sb is not None and "generate_p" not in _ORIG:
        _ORIG["generate_p"], _ORIG["sb"] = sb.generate_p, sb
        orig_p = sb.generate_p

        @torch.no_grad()
        def generate_p(L, model, prompts, max_new=20, bs=8):
            r = fast_generate(L, model, prompts, max_new, bs, want_p0=True)
            return orig_p(L, model, prompts, max_new, bs) if r is None else r
        sb.generate_p = generate_p
    return CFG


def uninstall():
    import sleep1
    if "Lang.generate" in _ORIG:
        sleep1.Lang.generate = _ORIG.pop("Lang.generate")
    if "generate_p" in _ORIG:
        _ORIG.pop("sb").generate_p = _ORIG.pop("generate_p")
