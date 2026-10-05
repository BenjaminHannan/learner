"""Faster greedy decoding for PlainTF / PlainTFSteps (no lesions): rows are grouped by prompt length so a whole group shares
positions, the prompt is run once, and each new token reuses cached keys/values instead of re-running the whole sequence.
Same weights and the same greedy choice as model.generate(); `check()` compares the two on sample rows."""
import torch
import torch.nn.functional as F
from custom_io.data import BOS, EOS, SEP, N_SPECIAL, MAX_ANS, Dataset, collate
from custom_io.models.plain_tf_steps import PlainTFSteps, MAX_NEW, final_answer


def _block(blk, x, cache, li):
    B, T, D = x.shape
    q, k, v = blk.qkv(blk.ln1(x)).view(B, T, 3, blk.h, D // blk.h).permute(2, 0, 3, 1, 4)
    if li in cache:
        k, v = torch.cat([cache[li][0], k], 2), torch.cat([cache[li][1], v], 2)
    cache[li] = (k, v)
    a = F.scaled_dot_product_attention(q, k, v, is_causal=T > 1)   # T == 1: the new position sees every cached one
    x = x + blk.proj(a.transpose(1, 2).reshape(B, T, D))
    return x + blk.out(F.gelu(blk.fc(blk.ln2(x))))


@torch.no_grad()
def _group(model, prompt_ids, max_new):
    """prompt_ids [B, L] (all the same length L) -> list of decoded strings."""
    assert model.n_loops == 1 and not model.has_place
    B, L = prompt_ids.shape
    dev = prompt_ids.device
    seq = torch.cat([torch.full((B, 1), BOS, device=dev), prompt_ids, torch.full((B, 1), SEP, device=dev)], 1)
    cache, pos = {}, 0
    x = model.tok(seq) + model.pos(torch.arange(seq.shape[1], device=dev))
    toks, done = [], torch.zeros(B, dtype=torch.bool, device=dev)
    for t in range(max_new):
        for li, blk in enumerate(model.blocks):
            x = _block(blk, x, cache, li)
        pos += x.shape[1]
        nxt = model.logits(model.ln_f(x[:, -1])).argmax(-1)
        toks.append(nxt)
        done |= nxt == EOS
        if done.all() or t == max_new - 1:
            break
        x = model.tok(nxt[:, None]) + model.pos(torch.tensor([pos], device=dev))
    out = []
    for row in torch.stack(toks, 1).tolist():
        s = ''
        for c in row:
            if c == EOS:
                break
            if c >= N_SPECIAL:
                s += model.vocab.itos[c]
        out.append(s)
    return out


@torch.no_grad()
def generate(model, rows, device='cpu', group=256):
    """-> {row id: answer string}, exactly what model.generate() returns for each row."""
    steps = isinstance(model, PlainTFSteps)
    max_new = MAX_NEW if steps else MAX_ANS + 1
    was = model.training
    model.eval()
    ds = Dataset(rows, model.vocab, strict=False)
    by_len = {}
    for i in range(len(rows)):
        by_len.setdefault(len(ds[i][0]), []).append(i)
    out = {}
    for L, idx in sorted(by_len.items()):
        for s in range(0, len(idx), group):
            part = idx[s:s + group]
            p = torch.tensor([list(ds[i][0]) for i in part], dtype=torch.long, device=device)
            for i, txt in zip(part, _group(model, p, max_new)):
                out[rows[i]['id']] = final_answer(txt) if steps else txt
    model.train(was)
    return out


def check(model, rows, device='cpu'):
    """-> number of rows where this decoder and model.generate() disagree (should be 0)."""
    fast = generate(model, rows, device)
    batch = {k: (v.to(device) if torch.is_tensor(v) else v) for k, v in collate([Dataset(rows, model.vocab, strict=False)[i] for i in range(len(rows))]).items()}
    slow = model.generate(batch)
    return sum(fast[r['id']] != s for r, s in zip(rows, slow))
