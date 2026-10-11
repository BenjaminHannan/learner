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
encode_texts(texts, T, device) -> H: the same H as encode(..., chars=True)[0] but outside the last-call memo (the tape strings, read like the question).
by_bytes (V1, ByteVocab): H and every alignment have one row per UTF-8 byte of the prompt (T counts bytes); a byte takes the Gemma token of the character it belongs to,
so a multi-byte character's bytes all share one token and an ASCII prompt gives exactly the character path's states.
pre=True (the 30M / 100M no-plug front; Ben, 4:12 PM ET: "can you remove the converter plug and just have our model match gemma's"): H is Gemma's own
512-number state AFTER its final norm and BEFORE embedding_projection (taken with a forward hook on self.m.norm for the one forward call, removed
after it, also on error), [B, T, EG_PRE_DIM]; our model is 512 wide and reads those numbers with no learned 768 -> width plug. pooled is unchanged
(mean of the 768 last_hidden_state), so the meaning teacher is the same. pre=False is bit-identical to before. The memo key includes pre.
  python -m custom_io.models.eg check     loads it, checks the size and compares 3 probe vectors with the ones taken on the build box."""
import os
import sys
import numpy as np
import torch

EG_ID, EG_REV = 'google/embeddinggemma-2', '914f7f89142e33e77833254d9c9b90c3cef7303b'
PREFIX = 'task: sentence similarity | query: '
EG_DIM, MT_DIM, N_TEXT = 768, 256, 271_002_624
EG_PRE_DIM = 512        # Gemma's own width: the state after its final norm, before embedding_projection (512 -> 768)
# probe prompts for `check` (their 256-d teacher vectors from the build box are in eg_probe_ref.json)
PROBES = ['Echo: sune Give only the answer.', 'What is the first letter of perayu?', 'Tom has 12 apples and gives 345 away. How many are left?']


class FrozenEG:
    def __init__(self, path=None, by_bytes=False, pre=False):
        self.path = path or os.environ.get('CUSTOM_IO_EG2') or EG_ID
        self.by_bytes = bool(by_bytes)
        self.pre = bool(pre)
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
        """(H [B,T,768] (or [B,T,EG_PRE_DIM] with pre=True) in the model's dtype, pooled [B,768] float32); chars=False skips H (None). The last call is memoised, so
        Ledger.run and Ledger.talk on the same batch embed it once."""
        key = (tuple(prompts), T, str(device), self.pre)
        if self._last is not None and self._last[0] == key and (self._last[1][0] is not None or not chars):
            return self._last[1]
        out = self._compute(prompts, T, device, chars)
        self._last = (key, out)
        return out

    @torch.no_grad()
    def encode_texts(self, texts, T, device):
        """H [B,T,768]: exactly encode(texts, T, device, chars=True)[0], but it never reads or writes the last-call memo, so reading the calculator's replies
        (Ben's rule 1: every tape string is read by Gemma + the letter window like the question) does not evict the question's states between run and talk."""
        return self._compute(texts, T, device, True)[0]

    @torch.no_grad()
    def _compute(self, prompts, T, device, chars):
        self.load(device)
        al = [self.align(p) for p in prompts]
        B, L = len(al), max(len(a[0]) for a in al)
        ids = np.full((B, L), self.tok.pad_token_id, np.int64)
        am = np.zeros((B, L), np.int64)
        for b, (t, _) in enumerate(al):
            ids[b, :len(t)], am[b, :len(t)] = t, 1
        ids, am = torch.from_numpy(ids).to(device), torch.from_numpy(am).to(device)
        grab = []
        hook = self.m.norm.register_forward_hook(lambda mod, inp, out: grab.append(out)) if self.pre else None
        try:
            with torch.autocast(device.type, enabled=False):
                Ht = self.m(input_ids=ids, attention_mask=am).last_hidden_state                      # [B, L, 768]
        finally:
            if hook is not None:
                hook.remove()
        w = am[..., None].float()
        pooled = (Ht.float() * w).sum(1) / w.sum(1)
        if self.pre:
            assert len(grab) == 1, f'expected one call of the final norm, saw {len(grab)}'
            Ht = grab[0]                                                                               # [B, L, 512]
        H = None
        if chars:
            c2t, cm = np.zeros((B, T), np.int64), np.zeros((B, T), bool)
            for b, (_, c) in enumerate(al):
                n = min(len(c), T)
                c2t[b, :n], cm[b, :n] = c[:n], True
            c2t, cm = torch.from_numpy(c2t).to(device), torch.from_numpy(cm).to(device)
            H = Ht.gather(1, c2t[..., None].expand(-1, -1, Ht.shape[-1])) * cm[..., None].to(Ht.dtype)
        return (H, pooled)


def teacher_vec(pooled):
    """MRL cut of the pooled vector to MT_DIM dims, re-normalised (the meaning teacher's target)."""
    return torch.nn.functional.normalize(pooled[:, :MT_DIM].float(), dim=-1)


def check(device=None, pre=False):
    """Load, count, and compare the probe vectors with eg_probe_ref.json (taken on the build box, CPU fp32): cos >= 0.999 each
    (bf16 on cuda drifts a little). pre=True (`check cuda pre`, the 30M/100M no-plug front) also proves the pre state and gates on it;
    without it the check is the probe check alone, so the plugged 3M/10M setups never depend on the no-plug proof or its extra fp32 load."""
    import json
    import transformers
    dev = torch.device(device or ('cuda' if torch.cuda.is_available() else 'cpu'))
    eg = FrozenEG().load(dev)
    v = teacher_vec(eg.encode(PROBES, 1, dev, chars=False)[1]).cpu()
    # the pre state is what we say: 512 wide, and Gemma's own projection of it equals last_hidden_state.
    # Gate only on an fp32 comparison on CPU (<= 1e-4); the device (bf16 on cuda) number is printed, never gated.
    def pre_diff_on(e, d):
        pe = FrozenEG(pre=True)
        pe.m, pe.tok = e.m, e.tok
        Hp = pe.encode(PROBES, 64, d)[0]
        with torch.no_grad():
            Hf = e.encode(PROBES, 64, d)[0]
            proj = e.m.embedding_projection(Hp.to(next(e.m.parameters()).dtype))
        return Hp.shape[-1], (proj.float() - Hf.float()).abs().max().item()
    width = dev_diff = diff32 = pre_ok = None
    if pre:
        width, dev_diff = pre_diff_on(eg, dev)
        if dev.type == 'cpu' and next(eg.m.parameters()).dtype == torch.float32:
            width32, diff32 = width, dev_diff
        else:
            cpu = torch.device('cpu')
            e32 = FrozenEG(path=eg.path).load(cpu)          # fp32 copy on CPU
            width32, diff32 = pre_diff_on(e32, cpu)
            del e32
        pre_ok = width == EG_PRE_DIM and width32 == EG_PRE_DIM and diff32 <= 1e-4
    ref = json.load(open(REF_FILE))
    cos = (v * torch.tensor(ref['vectors'])).sum(-1).tolist()
    out = dict(device=str(dev), transformers=transformers.__version__, path=eg.path, n_text=N_TEXT,
               probe_cos_vs_build_box=[round(c, 5) for c in cos], pre_width=width, pre_projection_max_abs_diff_fp32=diff32,
               pre_projection_max_abs_diff_device=dev_diff if dev.type != 'cpu' else None, pre_ok=pre_ok,
               ok=ref['prompts'] == PROBES and all(c >= 0.999 for c in cos) and (pre_ok if pre else True))
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
        args = sys.argv[2:]
        sys.exit(0 if check(next((a for a in args if a != 'pre'), None), pre='pre' in args)['ok'] else 1)
