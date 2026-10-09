"""Frozen EmbeddingGemma 2 (google/embeddinggemma-2, Apache 2.0), text part only, for B2's two EG arms (design/EG2-embedding.md).

Never trained and never saved: the Ledger holds it in a plain list, so it is not a submodule (not in parameters(), n_params(), the
optimizer or checkpoint.pt). Loaded on first use (bf16 on cuda, fp32 elsewhere; never fp16, the card says it overflows) and moved to
the device of the batch. Needs transformers >= 5.19 (EmbeddingGemma2Model). With vision_config / audio_config None the model is the
text backbone alone: 271,002,624 params (134,217,728 word table + 136,784,896 transformer and its 512 -> 768 projection).

Every prompt is embedded as PREFIX + prompt with the tokenizer's own <bos> ... <eos> (the model card's SentenceSimilarity prompt).
encode(prompts, T, device) -> (H, pooled):
  H [B, T, 768]: last_hidden_state (768-d per token, after the model's own projection) of the token that holds each prompt char
      (Gemma tokens carry their leading space, so every char of the prompt lies inside exactly one token); zeros past the prompt.
  pooled [B, 768] float: mean of last_hidden_state over every token, prefix and <bos>/<eos> included (sentence-transformers mean
      pooling with include_prompt), not normalised: the meaning teacher cuts it to MT_DIM and re-normalises (MRL).
The weights come from the Hugging Face cache at revision EG_REV, or from the folder in $CUSTOM_IO_EG2 / the Ledger's eg_path.
by_bytes (V1, ByteVocab): H and every alignment have one row per UTF-8 byte of the prompt (T counts bytes); a byte takes the Gemma token of the character it belongs to,
so a multi-byte character's bytes all share one token and an ASCII prompt gives exactly the character path's states.
  python -m custom_io.models.eg check     loads it, checks the size and compares 3 probe vectors with the ones taken on the build box."""
import os
import sys
import numpy as np
import torch

EG_ID, EG_REV = 'google/embeddinggemma-2', '914f7f89142e33e77833254d9c9b90c3cef7303b'
PREFIX = 'task: sentence similarity | query: '
EG_DIM, MT_DIM, N_TEXT = 768, 256, 271_002_624
# probe prompts for `check` (their 256-d teacher vectors from the build box are in eg_probe_ref.json)
PROBES = ['Echo: sune Give only the answer.', 'What is the first letter of perayu?', 'Tom has 12 apples and gives 345 away. How many are left?']


class FrozenEG:
    def __init__(self, path=None, by_bytes=False):
        self.path = path or os.environ.get('CUSTOM_IO_EG2') or EG_ID
        self.by_bytes = bool(by_bytes)
        self.m = self.tok = None
        self._align, self._last = {}, None

    def load(self, device):
        if self.m is None:
            import transformers
            from transformers import AutoModel, AutoTokenizer
            major, minor = (int(x) for x in transformers.__version__.split('.')[:2])
            assert (major, minor) >= (5, 19), f'EmbeddingGemma 2 needs transformers >= 5.19, found {transformers.__version__}'
            kw = {} if os.path.isdir(self.path) else dict(revision=EG_REV)
            self.tok = AutoTokenizer.from_pretrained(self.path, **kw)
            dt = torch.bfloat16 if device.type == 'cuda' else torch.float32
            m = AutoModel.from_pretrained(self.path, vision_config=None, audio_config=None, dtype=dt, **kw)
            self.m = m.language_model.eval().requires_grad_(False)
            n = sum(p.numel() for p in self.m.parameters())
            assert n == N_TEXT, f'EmbeddingGemma 2 text part has {n:,} params, expected {N_TEXT:,}'
        if next(self.m.parameters()).device != device:
            self.m.to(device)
        return self

    def align(self, prompt):
        """-> (token ids int32 [L], char -> token index int16 [len(prompt)]), cached per prompt. by_bytes: byte -> token index, [len(prompt.encode())]
        (each character's bytes take that character's token)."""
        hit = self._align.get(prompt)
        if hit is None:
            if len(self._align) > 400_000:
                self._align.clear()
            enc = self.tok(PREFIX + prompt, return_offsets_mapping=True)
            n0, c2t = len(PREFIX), np.full(len(prompt), -1, np.int64)
            for j, (s, e) in enumerate(enc['offset_mapping']):
                s, e = max(s - n0, 0), max(e - n0, 0)
                if e > s:
                    c2t[s:e] = j
            for i in range(len(prompt)):            # a char no token covers (never seen on the skills prompts): the token before it
                if c2t[i] < 0:
                    c2t[i] = c2t[i - 1] if i else next((j for j, (s, e) in enumerate(enc['offset_mapping']) if e > n0), 0)
            if self.by_bytes and not prompt.isascii():
                c2t = np.repeat(c2t, [len(c.encode('utf-8', errors='replace')) for c in prompt])
            hit = self._align[prompt] = (np.asarray(enc['input_ids'], np.int32), c2t.astype(np.int16))
        return hit

    @torch.no_grad()
    def encode(self, prompts, T, device, chars=True):
        """(H [B,T,768] in the model's dtype, pooled [B,768] float32); chars=False skips H (None). The last call is memoised, so
        Ledger.run and Ledger.talk on the same batch embed it once."""
        key = (tuple(prompts), T, str(device))
        if self._last is not None and self._last[0] == key and (self._last[1][0] is not None or not chars):
            return self._last[1]
        self.load(device)
        al = [self.align(p) for p in prompts]
        B, L = len(al), max(len(a[0]) for a in al)
        ids = np.full((B, L), self.tok.pad_token_id, np.int64)
        am = np.zeros((B, L), np.int64)
        for b, (t, _) in enumerate(al):
            ids[b, :len(t)], am[b, :len(t)] = t, 1
        ids, am = torch.from_numpy(ids).to(device), torch.from_numpy(am).to(device)
        with torch.autocast(device.type, enabled=False):
            Ht = self.m(input_ids=ids, attention_mask=am).last_hidden_state                          # [B, L, 768]
        w = am[..., None].float()
        pooled = (Ht.float() * w).sum(1) / w.sum(1)
        H = None
        if chars:
            c2t, cm = np.zeros((B, T), np.int64), np.zeros((B, T), bool)
            for b, (_, c) in enumerate(al):
                n = min(len(c), T)
                c2t[b, :n], cm[b, :n] = c[:n], True
            c2t, cm = torch.from_numpy(c2t).to(device), torch.from_numpy(cm).to(device)
            H = Ht.gather(1, c2t[..., None].expand(-1, -1, Ht.shape[-1])) * cm[..., None].to(Ht.dtype)
        out = (H, pooled)
        self._last = (key, out)
        return out


def teacher_vec(pooled):
    """MRL cut of the pooled vector to MT_DIM dims, re-normalised (the meaning teacher's target)."""
    return torch.nn.functional.normalize(pooled[:, :MT_DIM].float(), dim=-1)


def check(device=None):
    """Load, count, and compare the probe vectors with eg_probe_ref.json (taken on the build box, CPU fp32): cos >= 0.999 each
    (bf16 on cuda drifts a little)."""
    import json
    import transformers
    dev = torch.device(device or ('cuda' if torch.cuda.is_available() else 'cpu'))
    eg = FrozenEG().load(dev)
    v = teacher_vec(eg.encode(PROBES, 1, dev, chars=False)[1]).cpu()
    ref = json.load(open(REF_FILE))
    cos = (v * torch.tensor(ref['vectors'])).sum(-1).tolist()
    out = dict(device=str(dev), transformers=transformers.__version__, path=eg.path, n_text=N_TEXT,
               probe_cos_vs_build_box=[round(c, 5) for c in cos], ok=ref['prompts'] == PROBES and all(c >= 0.999 for c in cos))
    print(json.dumps(out))
    return out


REF_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eg_probe_ref.json')

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if cmd == 'ref':        # build box only: writes eg_probe_ref.json
        import json, transformers
        dev = torch.device('cpu')
        v = teacher_vec(FrozenEG().load(dev).encode(PROBES, 1, dev, chars=False)[1])
        json.dump(dict(prompts=PROBES, prefix=PREFIX, revision=EG_REV, transformers=transformers.__version__, dtype='float32', device='cpu',
                       vectors=[[round(x, 6) for x in r] for r in v.tolist()]), open(REF_FILE, 'w'))
        print('wrote', REF_FILE)
    else:
        sys.exit(0 if check(sys.argv[2] if len(sys.argv) > 2 else None)['ok'] else 1)
