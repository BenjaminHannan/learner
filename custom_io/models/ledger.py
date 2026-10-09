"""B (Ledger-lite): shared CharReader -> 27-slot int64 workspace (16 prompt numbers, constants 1 2 10 100, 7 result slots) ->
a looped controller Z [B,17,d] (8 control tokens + 9 register tokens tied to the reader's place rows 0..8) that writes up to
7 (op, ptr, ptr) steps, run by a parameter-free exact int64 executor -> talker with no reasoning: NUM prints the value of the
slot the answer pointer picks, WORD copies word k of the CURRENT row (keys are content-free: Lin(sin(word index, word start))
+ E[word length]), GEN reads the 9 register tokens with a per-register linear readout tied to the char table (units first).
Iteration t = 0..n_loops-1: controller blocks (cross-attn to [workspace; reader output], self-attn, MLP); at t = 1..7 control
token 0 picks the op and both operands and result slot t-1 is written (K iterations = K-1 writes). After the last iteration
control token 1 gives the mode, the answer pointer and the word pointer. Loss is teacher-forced on programs parsed from `steps`
(models/progparse.py). Lesions: noexec (every result invalid), opswap (ADD and SUB swapped in the executor).
Sizes (vocab 108): plain_tf S 3,244,544 / M 10,775,040.
S = dict(d=256, n_heads=4, reader_layers=2, blocks=2, n_loops=8, mlp=4.8)      # 3,252,368 params (+0.2%)
M = dict(d=384, n_heads=6, reader_layers=2, blocks=3, n_loops=8, mlp=6.0)      # 10,814,968 params (+0.4%)
extra_evals marks: noexec.program_families = noexec exact over NUM rows whose gold answer slots are all result slots (verify_claim and
compare_numbers excluded: they can be answered without the executor); noexec.all_program_families = the old 14-family number.
opswap.swap_match = chain-5 rows right when intact whose swap changes the pointed value (invalid swapped replays counted separately).
chain5_lesions = chain-5 under loops:1 / loops:2 / noexec for all rows, NUM-mode rows and the story_chain3 WORD rows (coin-flip floor).
Deviation from the design text (switch off with "wpos": false): the word key also sees the word's start char (content-free), so the
pointer can be learned from the reader's positions instead of having to count words.
B2 = B + `copy=True` (design/design-B2.md; default False = exactly B): the new modules are created last (same seed -> every shared weight starts
as in B). WORD keys += k_wc(ln_wc(mean of the reader output X over the word's chars)); GEN becomes a pointer-generator: p = g * softmax(readout(R))
+ (1 - g) * (attention of q_cp(ln_t(R)) over k_cp(X) of the CURRENT batch's prompt, scattered onto the prompt's chars), g = sigmoid(g_cp(ln_t(R))),
trained by -log(p[target] + 1e-6), decoded by argmax p (fp32). Lesions: 'nocopy' (g = 1), 'nowordc' (no content term in the WORD keys).
copy=True size (vocab 108, S cfg) = 3,302,481 (+1.79% vs plain_tf S). extra_evals adds copy_gate (per family mean 1 - g on target-char registers).
span=True (design/B1-students.md; default False = exactly B / B2): the WORD talker copies a run of up to `span_max` (12) words of the CURRENT row, picked by a start
pointer (lword) and an end pointer (lwend = ptr(q_wend(zf)) over the same word keys; q_wend is created last, state() appends lwend). Targets are every (s, e) whose
en_norm text equals en_norm(answer) (the taught string); NUM rows stay NUM, yes/no and unmatched answers are GEN (answer[:GEN_MAX], the register targets never change
with data.MAX_ANS). Loss -log sum p_start(s) p_end(e) over the targets; decode = argmax log p_start(s) + log p_end(e) with s <= e < s + span_max inside the row's words.
B2 + span, vocab 108, M cfg = 10,914,681 params (B2 M 10,890,041 + q_wend 24,640).
EG arms (design/EG2-embedding.md; both default off = exactly B2). The frozen EmbeddingGemma 2 text part (models/eg.py, 271,002,624 params) is held in a
plain list: never trained, counted in n_params() or saved. eg_embed=True: every char's reader input embedding also gets eg_proj(ln_eg(H)), H = the
768-d EmbeddingGemma state of the token holding that char (per-token states, spread over the token's chars); the conv blocks, controller and talker
are unchanged and the CURRENT rows' prompt is embedded in run() and in talk() alike. eg_proj is zero-initialised, so at step 0 the model computes exactly
what B2 computes. eg_teach=w > 0: training-only meaning teacher, loss += w * (1 - cos(mt_head(ln_mt(mean of the 8 control tokens after iteration t = 1)),
EmbeddingGemma's pooled vector of the TRAINING prompt cut to 256 dims and re-normalised)); never run at eval, and ln_mt / mt_head are dropped from
the shipped size. Both arms' modules are created last (after copy / span), so every B2 weight starts identical at the same seed. size() reports
trainable, discarded and frozen-borrowed params and the whole-model size (borrowed parts counted).
round_readout=w > 0 (PASS-MARKS.md addendum 5, Test LR; default 0 = exactly B2): in training only, after every iteration t with L + 1 <= t <= n_loops - 2
(L = the row's gold program steps, so its program is written; the last iteration is the normal readout) the same talker heads read the state and get
the final readout's losses (mode, answer pointer, word pointer / span, GEN with the copy path); each row's mean over its rounds is added with weight w.
No new parameters; eval is unchanged.
letters_in=False (PASS-MARKS.md addendum 7, EGO; needs eg_embed; default True = B2): the reader's input is position + place code + the EmbeddingGemma
term only, with no letter embedding, so with reader_layers=0 EmbeddingGemma alone reads the prompt for the thinker. The letter table stays: the talker
uses it as its output alphabet (the GEN readout is tied to it). Same parameters as with letters_in=True.
eg_adapter='mlp' (PASS-MARKS.md addendum 8, EGM; default 'linear' = the arms above): the adapter between EmbeddingGemma and the reader input is
LayerNorm -> Linear(768, d) -> GELU -> Linear(d, d) (the last one zero-initialised) instead of LayerNorm -> Linear(768, d); +65,792 params at d = 256.
eg_adapter='none' (addendum 9, EGW; needs d = 768): no adapter. The thinker is built at EmbeddingGemma's width, so each char's input is
LayerNorm(EmbeddingGemma state) + position + place code, then the reader's final LayerNorm; the thinker's own first layers do the adapting.
eg_thinker=True (PASS-MARKS.md addendum 14, EGK; needs eg_embed with the linear adapter; default False = EGE): the reader runs twice with the same weights.
The run with the EmbeddingGemma term feeds only the controller's cross-attention to the reader output; the number slots, the WORD content keys and the
GEN copy keys (everything the talker reads, and the workspace) take B2's own reader output, without EmbeddingGemma. No new parameters (EGE's 3,500,881).
tok_think=True (TOKENS-EXPERIMENT-2026-10-09.md arms TK / TKN; needs eg_embed, not eg_thinker; default False = exactly EGE): the thinker's cross-attention reads one
spot per EmbeddingGemma token instead of one per letter. The reader is unchanged (letter level); in run() the letters of each token (FrozenEG.align char -> token,
compacted per row to 0..n_tok-1 in order of first appearance, so a first token that merges with the prompt prefix is token 0) are pooled by a learned attention
pool: score = tok_pool(x) per letter (nn.Linear(d, 1), weight and bias ZERO, so it starts as a plain mean), softmax over the letters of the same token, weighted
sum; index ops only (scatter max / index_add over B * n_tok_max segments), no dense [B, tokens, T] matrix. These spots (Xk) and their mask (km) feed ONLY the
controller's cross-attention K/V and its mask; the number pool, word_content, gen_copy, out['X'] / out['xm'], talk and the round readout stay letter-level.
tok_pool is created after every other module (same seed -> every other weight identical); +d + 1 params. Counters _tk_letters / _tk_spots (python ints, training
passes only) are the valid letters and token spots seen by run(); train.py writes them to RESULT.json as tok_think."""
import math
import numpy as np
import torch
from custom_io import capcount
import torch.nn as nn
import torch.nn.functional as F
from custom_io.data import EOS, word_spans
from custom_io.models.base import Model
from custom_io.models.reader import CharReader
from custom_io.models import progparse as pp

N_NUM, N_RES, M, R0, W_MAX, OPS, COMM = pp.N_NUM, pp.N_RES, pp.M, pp.R0, pp.W_MAX, pp.OPS, pp.COMM
N_CTRL, N_REG, BIG = 8, 9, 10 ** 9
GEN_MAX = N_REG - 1        # GEN register targets: 8 chars + EOS, whatever data.MAX_ANS is
ADD, SUB = 1, 2
OMEGA = 0.03 * 1.6 ** torch.arange(10.)


def value_code(v, valid):
    """Exact code of int64 values [..] -> [.., 93]: 9 LSB-first digit one-hots, sign, valid flag, log10 magnitude."""
    a = v.abs().clamp(max=BIG - 1)
    digs = torch.stack([(a // 10 ** k) % 10 for k in range(9)], -1)
    oh = F.one_hot(digs, 10).flatten(-2).float()
    return torch.cat([oh * valid[..., None], torch.stack([(v < 0).float(), valid.float(), torch.log10(a.float() + 1) / 9], -1)], -1)


def execute(op, a, b):
    """Exact int64 executor, op [B] long (index into OPS), a/b [B] -> (value, valid). DIV is valid only when exact."""
    bz = b == 0
    bs = torch.where(bz, torch.ones_like(b), b)
    res = torch.stack([torch.zeros_like(a), a + b, a - b, a * b, torch.div(a, bs, rounding_mode='floor'), torch.remainder(a, bs),
                       torch.minimum(a, b), torch.maximum(a, b), torch.sign(a - b)], 1)
    v = res.gather(1, op[:, None])[:, 0]
    ok = (op != 0) & (a.abs() < BIG) & (b.abs() < BIG) & (v.abs() < BIG)
    ok &= ~(((op == 4) | (op == 5)) & bz)
    ok &= ~((op == 4) & (torch.remainder(a, bs) != 0))
    return torch.where(ok, v, torch.zeros_like(v)), ok


def replay(vals, valid, ops, a, b, swap=False):
    """Re-run a logged program (ops/a/b [B,L]) from the prompt+constant part of vals [B,M]; -> (vals, valid). swap: ADD<->SUB."""
    vals, valid = vals.clone(), valid.clone()
    vals[:, R0:], valid[:, R0:] = 0, False
    for s in range(ops.shape[1]):
        op = ops[:, s]
        if swap:
            op = torch.where(op == ADD, SUB, torch.where(op == SUB, ADD, op))
        v, ok = execute(op, vals.gather(1, a[:, s:s + 1])[:, 0], vals.gather(1, b[:, s:s + 1])[:, 0])
        vals[:, R0 + s], valid[:, R0 + s] = v, ok
    return vals, valid


class CBlock(nn.Module):
    """Controller block: cross-attention to [workspace; reader output] (the reader half's K/V computed once), self-attention, MLP."""

    def __init__(self, d, h, hidden):
        super().__init__()
        self.h = h
        self.ln_m, self.ln_c, self.ln_s, self.ln_f = (nn.LayerNorm(d) for _ in range(4))
        self.q, self.kv, self.o = nn.Linear(d, d), nn.Linear(d, 2 * d), nn.Linear(d, d)
        self.qkv, self.p = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.fc, self.out = nn.Linear(d, hidden), nn.Linear(hidden, d)

    def kv_of(self, mem):
        B, T, D = mem.shape
        return self.kv(self.ln_m(mem)).view(B, T, 2, self.h, D // self.h).permute(2, 0, 3, 1, 4)

    def forward(self, Z, kvs, kvx, mask):
        B, N, D = Z.shape
        q = self.q(self.ln_c(Z)).view(B, N, self.h, D // self.h).transpose(1, 2)
        k, v = torch.cat([kvs[0], kvx[0]], 2), torch.cat([kvs[1], kvx[1]], 2)
        Z = Z + self.o(F.scaled_dot_product_attention(q, k, v, attn_mask=mask[:, None, None, :]).transpose(1, 2).reshape(B, N, D))
        q, k, v = self.qkv(self.ln_s(Z)).view(B, N, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        Z = Z + self.p(F.scaled_dot_product_attention(q, k, v).transpose(1, 2).reshape(B, N, D))
        return Z + self.out(F.gelu(self.fc(self.ln_f(Z))))


class Ledger(Model):
    LESIONS = ['shuffle_state', 'zero_state', 'noexec', 'opswap']
    no_slots = False        # N1 (B3 sets it): no number slots; spans() then skips the regex number spans

    def __init__(self, vocab, d=256, n_heads=4, reader_layers=2, blocks=2, n_loops=8, mlp=4.8, dk=64, w_noop=0.1, wpos=True, copy=False, span=False, span_max=12,
                 eg_embed=False, eg_teach=0.0, eg_path=None, round_readout=0.0, letters_in=True, eg_adapter='linear', eg_thinker=False, tok_think=False, no_place=False, bytes=False):
        super().__init__(vocab)
        self.is_bytes = bool(bytes)
        assert self.is_bytes == bool(getattr(vocab, 'is_bytes', False)), f"cfg bytes={bool(bytes)} but the vocab is {type(vocab).__name__}: V1 needs ByteVocab, and ByteVocab needs bytes"
        self.no_place = bool(no_place)
        self.d, self.n_loops, self.dk, self.w_noop, self.wpos, self.copy = d, n_loops, dk, w_noop, wpos, copy
        self.span, self.span_max = span, span_max
        self.eg_embed, self.eg_teach = bool(eg_embed), float(eg_teach)
        assert eg_adapter in ('linear', 'mlp', 'none'), eg_adapter
        self.eg_adapter = eg_adapter
        self.eg_thinker = bool(eg_thinker)
        assert not self.eg_thinker or (self.eg_embed and eg_adapter == 'linear' and letters_in), 'eg_thinker needs eg_embed, the linear adapter and letters'
        self.tok_think = bool(tok_think)
        assert not self.tok_think or (self.eg_embed and not self.eg_thinker), 'tok_think needs eg_embed and is not combined with eg_thinker'
        self.round_readout = float(round_readout)
        assert letters_in or eg_embed, 'letters_in=False needs eg_embed (the reader input would carry no content)'
        self.reader = CharReader(len(vocab), d, reader_layers, letters=bool(letters_in), no_place=self.no_place, by_bytes=self.is_bytes)
        self.vcode = nn.Linear(93, d)
        self.stype, self.ordinal, self.op_emb, self.step_emb, self.src, self.ctrl = (
            nn.Embedding(n, d) for n in (3, N_NUM, len(OPS), n_loops, 2, N_CTRL))
        self.res_from_z = nn.Linear(d, d)
        self.core = nn.ModuleList(CBlock(d, n_heads, int(mlp * d)) for _ in range(blocks))
        self.ln_z, self.ln_k, self.ln_t = nn.LayerNorm(d), nn.LayerNorm(d), nn.LayerNorm(d)
        self.op_head, self.mode_head = nn.Linear(d, len(OPS)), nn.Linear(d, 3)
        self.q_a, self.q_b, self.q_ans, self.q_word, self.k_slot = (nn.Linear(d, dk) for _ in range(5))
        self.k_word, self.len_emb = nn.Linear(OMEGA.numel() * (4 if wpos else 2), dk), nn.Embedding(24, dk)
        self.bias = nn.Parameter(torch.zeros(len(vocab)))
        for m in self.modules():        # the reader's own embeddings are re-initialised too: they are tied to the register codes and the readout
            if isinstance(m, (nn.Linear, nn.Embedding)):
                nn.init.normal_(m.weight, std=0.02)
                if getattr(m, 'bias', None) is not None:
                    nn.init.zeros_(m.bias)
        for b in self.core:
            for lin in (b.o, b.p, b.out):
                nn.init.normal_(lin.weight, std=0.02 / math.sqrt(3 * blocks * n_loops))
        self._spans = {}
        if copy:        # created LAST: no RNG draw above changes, so every weight shared with B starts identical at the same seed
            self.LESIONS = Ledger.LESIONS + ['nocopy', 'nowordc']
            self.ln_wc = nn.LayerNorm(d)
            self.k_wc, self.q_cp, self.k_cp, self.g_cp = nn.Linear(d, dk), nn.Linear(d, dk), nn.Linear(d, dk), nn.Linear(d, 1)
            for m in (self.k_wc, self.q_cp, self.k_cp, self.g_cp):
                nn.init.normal_(m.weight, std=0.02)
                nn.init.zeros_(m.bias)
        if span:        # created after the copy modules, so every other weight starts as in B / B2 at the same seed
            self._span_t = {}
            self.q_wend = nn.Linear(d, dk)
            nn.init.normal_(self.q_wend.weight, std=0.02)
            nn.init.zeros_(self.q_wend.bias)
        if self.eg_embed or self.eg_teach:      # created after every other module, so every B / B2 / span weight starts identical at the same seed
            from custom_io.models.eg import EG_DIM, MT_DIM, FrozenEG
            self._eg = [FrozenEG(eg_path, by_bytes=self.is_bytes)]      # a list, not a submodule: never trained, counted or saved
        if self.eg_embed:       # zero-initialised, so the extra input term is 0 at step 0 (building the Linear draws RNG, after every B2 weight)
            if self.eg_adapter == 'none':       # addendum 9: the thinker is EmbeddingGemma's width, so its states go in through a LayerNorm only
                assert d == EG_DIM, f"eg_adapter='none' needs d = {EG_DIM}, got {d}"
                self.ln_eg = nn.LayerNorm(EG_DIM)
            elif self.eg_adapter == 'mlp':        # addendum 8: LayerNorm -> Linear(768, d) -> GELU -> eg_proj; the reader's own final LayerNorm normalises the sum
                self.ln_eg, self.eg_hid, self.eg_proj = nn.LayerNorm(EG_DIM), nn.Linear(EG_DIM, d), nn.Linear(d, d)
            else:
                self.ln_eg, self.eg_proj = nn.LayerNorm(EG_DIM), nn.Linear(EG_DIM, d)
            if self.eg_adapter != 'none':
                nn.init.zeros_(self.eg_proj.weight)
                nn.init.zeros_(self.eg_proj.bias)
        if self.eg_teach:
            self.ln_mt, self.mt_head = nn.LayerNorm(d), nn.Linear(d, MT_DIM)
            nn.init.normal_(self.mt_head.weight, std=0.02)
            nn.init.zeros_(self.mt_head.bias)
        if self.tok_think:      # created after every other module: no RNG draw (zeros), and every other weight starts identical at the same seed
            self.tok_pool = nn.Linear(d, 1)
            nn.init.zeros_(self.tok_pool.weight)
            nn.init.zeros_(self.tok_pool.bias)
            self._tk_letters = self._tk_spots = 0

    # ---- hand-written number / word tokenizer (prompt text only; cached per prompt) ----
    def spans(self, prompt):
        hit = self._spans.get(prompt)
        if hit is None:
            if len(self._spans) > 20000:
                self._spans.clear()
            ns, ne, nv, ws, we = (np.zeros(n, np.int64) for n in (N_NUM, N_NUM, N_NUM, W_MAX, W_MAX))
            n_found = 0
            for k, m in enumerate(() if self.no_slots else pp.NUM_RE.finditer(prompt)):
                n_found += 1
                if k < N_NUM:
                    ns[k], ne[k], nv[k] = m.start(), m.end(), min(int(m.group()), 10 ** 18)
                    if int(m.group()) > 10 ** 18:
                        capcount.hit('number_clipped')
            if n_found > N_NUM:
                capcount.hit('numbers_over')
            sp = word_spans(prompt)
            if len(sp) > W_MAX:
                capcount.hit('words_over')
            for k, (s, e) in enumerate(sp[:W_MAX]):
                ws[k], we[k] = s, e
            off = self.vocab.offsets(prompt)        # ByteVocab on non-ASCII text: char offsets -> byte offsets (every position of X is a byte)
            if off is not None:
                ns, ne, ws, we = off[ns], off[ne], off[ws], off[we]
            hit = self._spans[prompt] = (ns, ne, nv, ws, we)
        return hit

    def tokenize(self, batch):
        dev = batch['prompt_ids'].device
        arr = [np.stack(x) for x in zip(*(self.spans(r['prompt']) for r in batch['rows']))]
        return [torch.from_numpy(x).to(dev) for x in arr]       # ns ne nv ws we

    def word_keys(self, ws, we):
        """[B,W,dk], content-free: Lin(sin/cos of word index [and word start char]) + E[word length]. Depends on lengths only."""
        B = ws.shape[0]
        om = OMEGA.to(ws.device)
        feats = [torch.arange(W_MAX, device=ws.device).float().expand(B, -1)] + ([ws.float()] if self.wpos else [])
        f = torch.cat([g(x[..., None] * om) for x in feats for g in (torch.sin, torch.cos)], -1)
        return self.k_word(f) + self.len_emb((we - ws).clamp(0, 23))

    def ptr(self, q, k, ok):
        with torch.autocast(q.device.type, enabled=False):          # pointers in fp32
            return (torch.einsum('bk,bmk->bm', q.float(), k.float()) / math.sqrt(self.dk)).masked_fill(~ok, -1e9)

    def word_content(self, X, ws, we):
        """[B,W,dk] B2 content term of the WORD keys: k_wc(ln_wc(mean of the reader output X over the word's chars [ws, we))); zero for empty words."""
        t_ix = torch.arange(X.shape[1], device=X.device)
        inw = (t_ix >= ws[..., None]) & (t_ix < we[..., None])                                       # [B,W,T]
        cnt = inw.sum(-1)
        pool = torch.bmm(inw.to(X.dtype), X) / cnt.clamp(min=1)[..., None]
        return self.k_wc(self.ln_wc(pool)) * (cnt > 0)[..., None]

    def gen_copy(self, R, X, xm, ids, nocopy=False):
        """B2 pointer-generator over the 9 GEN registers, fp32. R [B,9,d], X [B,T,d] reader output and xm [B,T] mask of the CURRENT batch's prompt,
        ids [B,T] its char ids. -> (p [B,9,V] = g * softmax(readout(R)) + (1 - g) * copy, g [B,9,1]); nocopy forces g = 1."""
        with torch.autocast(R.device.type, enabled=False):
            R, X = R.float(), X.float()
            h = self.ln_t(R)
            p_vocab = (F.linear(h, self.reader.tok.weight.float()) + self.bias.float()).softmax(-1)
            gate = torch.ones_like(h[..., :1]) if nocopy else torch.sigmoid(self.g_cp(h))
            a = (torch.einsum('bid,btd->bit', self.q_cp(h), self.k_cp(X)) / math.sqrt(self.dk)).masked_fill(~xm[:, None, :], -1e9).softmax(-1)
            p_copy = torch.zeros_like(p_vocab).scatter_add_(2, ids[:, None, :].expand(-1, R.shape[1], -1), a)
            return gate * p_vocab + (1 - gate) * p_copy, gate

    # ---- EmbeddingGemma arms ----
    def eg(self):
        return self._eg[0]

    def read(self, batch, talker=False):
        """The reader on `batch` -> (X [B,T,d], mask). eg_embed: the input embedding also gets eg_proj(ln_eg(H)), H = EmbeddingGemma's state of the
        token holding each char of THIS batch's prompts. talker=True with eg_thinker: B2's own reader output, without EmbeddingGemma."""
        if not self.eg_embed or (talker and self.eg_thinker):
            return self.reader(batch)
        ids = batch['prompt_ids']
        H, _ = self.eg().encode([r['prompt'] for r in batch['rows']], ids.shape[1], ids.device)
        h = self.ln_eg(H.float())       # H is bf16 on cuda; fp32 here works with or without autocast
        if self.eg_adapter == 'none':
            return self.reader(batch, extra=h)
        if self.eg_adapter == 'mlp':
            h = F.gelu(self.eg_hid(h))
        return self.reader(batch, extra=self.eg_proj(h))

    def tok_spots(self, X, xm, batch):
        """tok_think: pool the letters of each EmbeddingGemma token into one spot. X [B,T,d], xm [B,T] -> (Xk [B,K,d], km [B,K] bool), K = the batch's
        most tokens. Token ids come from align() (call after read(): the tokenizer is loaded), compacted per row in order of first appearance. Softmax
        over the valid letters of a token (fp32, max detached), weighted sum by index_add; a plain mean while tok_pool is zero."""
        B, T, d = X.shape
        tk, nt, nl = np.zeros((B, T), np.int64), np.zeros(B, np.int64), 0
        for b, r in enumerate(batch['rows']):
            c = np.asarray(self.eg().align(r['prompt'])[1][:T], np.int64)
            u, first, inv = np.unique(c, return_index=True, return_inverse=True)
            tk[b, :len(c)] = np.argsort(np.argsort(first))[inv.reshape(-1)]
            nt[b], nl = len(u), nl + len(c)
        K = int(nt.max())
        if self.training:
            self._tk_letters += nl
            self._tk_spots += int(nt.sum())
        gid = (torch.from_numpy(tk).to(X.device) + K * torch.arange(B, device=X.device)[:, None])[xm]       # [N] segment of each valid letter
        xv = X[xm]
        sc = self.tok_pool(xv).float()[:, 0]
        with torch.no_grad():
            mx = torch.full((B * K,), -float('inf'), device=X.device).scatter_reduce(0, gid, sc, 'amax', include_self=False)
        e = torch.exp(sc - mx[gid])
        w = e / torch.zeros(B * K, device=X.device).index_add_(0, gid, e)[gid]
        Xk = torch.zeros(B * K, d, device=X.device).index_add_(0, gid, w[:, None] * xv.float())
        return Xk.to(X.dtype).view(B, K, d), torch.arange(K, device=X.device)[None, :] < torch.from_numpy(nt).to(X.device)[:, None]

    def size(self):
        """{trainable, discarded (training-only heads, not shipped), frozen_borrowed (EmbeddingGemma 2 text part, eg_embed only), shipped_trainable, whole}."""
        from custom_io.models.eg import N_TEXT
        tr = self.n_params()
        disc = sum(p.numel() for m in (getattr(self, 'ln_mt', None), getattr(self, 'mt_head', None)) if m is not None for p in m.parameters())
        fz = N_TEXT if self.eg_embed else 0
        return dict(trainable=tr, discarded=disc, frozen_borrowed=fz, shipped_trainable=tr - disc, whole=tr - disc + fz)

    # ---- reasoner ----
    def run(self, batch, loops=None, gold=None, lesion=None, rounds=False):
        """One pass. gold (training) = dict(op [B,L], a/b [B,L,M] bool) teacher-forces every written step. lesion: 'noexec' / 'opswap' / 'nowordc' / 'ctl27'
        (test only, not in LESIONS: zero controls 2-7 after every iteration).
        -> dict(R registers [B,9,d], vals [B,M] int64, valid, lmode, lans, lword, steps [(op, a, b logits)], prog (ops, a, b [B,L]);
        copy=True adds X [B,T,d] and xm [B,T] (reader output and prompt mask) so that loss() does not run the reader twice).
        rounds=True (round_readout training) adds 'rounds' [(t, Z[:,1], registers, Rs, valid) after iterations 1..n-2], S0 and Kw."""
        X, xm = self.read(batch, talker=True)
        Xt = self.read(batch)[0] if self.eg_thinker else X       # eg_thinker: only the controller's cross-attention sees EmbeddingGemma
        ns, ne, nv, ws, we = self.tokenize(batch)
        B, T, dev = X.shape[0], X.shape[1], X.device
        t_ix = torch.arange(T, device=dev)
        inn = (t_ix >= ns[..., None]) & (t_ix < ne[..., None])                       # [B,16,T] digit span of each number
        cnt = inn.sum(-1)
        pool = torch.bmm(inn.to(X.dtype), X) / cnt.clamp(min=1)[..., None]
        consts = torch.tensor(pp.CONSTS, device=dev).expand(B, -1)
        vals = torch.cat([nv, consts, torch.zeros(B, N_RES, dtype=torch.long, device=dev)], 1)
        valid = torch.cat([cnt > 0, torch.ones_like(consts, dtype=torch.bool), torch.zeros(B, N_RES, dtype=torch.bool, device=dev)], 1)
        S0 = self.vcode(value_code(vals[:, :R0], valid[:, :R0])) * valid[:, :R0, None]
        S0 = torch.cat([S0[:, :N_NUM] + pool + self.ordinal.weight + self.stype.weight[0], S0[:, N_NUM:] + self.stype.weight[1]], 1)
        S0 = S0 * valid[:, :R0, None]
        Rs = torch.zeros(B, N_RES, self.d, device=dev, dtype=S0.dtype)
        Kw, wvalid = self.word_keys(ws, we), we > ws
        if self.copy and lesion != 'nowordc':
            Kw = Kw + self.word_content(X, ws, we)
        Xk, km = self.tok_spots(X, xm, batch) if self.tok_think else (Xt, xm)       # tok_think: token spots for the thinker's cross-attention only
        kvx = [b.kv_of(Xk + self.src.weight[1]) for b in self.core]
        P = self.reader.place.weight[:N_REG]
        Z = torch.cat([self.ctrl.weight, P]).expand(B, -1, -1)
        steps, prog, snaps = [], [], []
        n = self.n_loops if loops is None else loops
        for t in range(n):
            ts = min(t, self.n_loops - 1)
            S = torch.cat([S0, Rs], 1)
            kvs = [b.kv_of(S + self.src.weight[0]) for b in self.core]
            mask = torch.cat([valid, km], 1)
            Z = Z + self.step_emb.weight[ts]
            for b, kx, ks in zip(self.core, kvx, kvs):
                Z = b(Z, ks, kx, mask)
            if lesion == 'ctl27':         # read-only test lesion: controls 2-7 (read by no head) carry nothing between iterations
                Z = torch.cat([Z[:, :2], torch.zeros_like(Z[:, 2:N_CTRL]), Z[:, N_CTRL:]], 1)
            if t == 1 and self.eg_teach:
                z1 = Z[:, :N_CTRL].mean(1)       # the meaning teacher's input: the 8 control tokens after iteration t = 1
            if not 1 <= t <= N_RES:
                continue
            z = self.ln_z(Z[:, 0])
            ks_ = self.k_slot(self.ln_k(torch.cat([S0, Rs], 1)))
            lop, la, lb = self.op_head(z), self.ptr(self.q_a(z), ks_, valid), self.ptr(self.q_b(z), ks_, valid)
            steps.append((lop, la, lb))
            if gold is None:
                op, a, b = lop.argmax(-1), la.argmax(-1), lb.argmax(-1)
            else:
                op = gold['op'][:, t - 1]
                a = la.detach().masked_fill(~gold['a'][:, t - 1], -1e9).argmax(-1)
                b = lb.detach().masked_fill(~gold['b'][:, t - 1], -1e9).argmax(-1)
            prog.append((op, a, b))
            xop = torch.where(op == ADD, SUB, torch.where(op == SUB, ADD, op)) if lesion == 'opswap' else op
            v, ok = execute(xop, vals.gather(1, a[:, None])[:, 0], vals.gather(1, b[:, None])[:, 0])
            if lesion == 'noexec':
                ok = torch.zeros_like(ok)
            vals, valid = vals.clone(), valid.clone()
            vals[:, R0 + t - 1], valid[:, R0 + t - 1] = v, ok
            new = (self.vcode(value_code(v, ok)) + self.stype.weight[2] + self.op_emb(op) + self.step_emb.weight[ts] + self.res_from_z(z)) * ok[:, None]
            Rs = torch.cat([Rs[:, :t - 1], new[:, None].to(Rs.dtype), Rs[:, t:]], 1)
            if rounds and t <= n - 2:
                snaps.append((t, Z[:, 1], Z[:, N_CTRL:], Rs, valid))
        zf = self.ln_z(Z[:, 1])
        ks_ = self.k_slot(self.ln_k(torch.cat([S0, Rs], 1)))
        out = dict(R=Z[:, N_CTRL:], vals=vals, valid=valid, lmode=self.mode_head(zf), steps=steps, wvalid=wvalid,
                   lans=self.ptr(self.q_ans(zf), ks_, valid), lword=self.ptr(self.q_word(zf), Kw, wvalid))
        L = N_RES
        pad = lambda i: torch.stack([x[i] for x in prog] + [torch.zeros(B, dtype=torch.long, device=dev)] * (L - len(prog)), 1)
        out['prog'] = tuple(pad(i) for i in range(3))
        if self.span:
            out['lwend'] = self.ptr(self.q_wend(zf), Kw, wvalid)
        if self.copy:
            out['X'], out['xm'] = X, xm
        if self.eg_teach and n > 1:
            out['z1'] = z1
        if rounds:
            out['rounds'], out['S0'], out['Kw'] = snaps, S0, Kw
        return out

    def state(self, batch, loops=None, lesion=None):
        o = self.run(batch, loops, lesion=lesion)
        st = (o['R'], o['vals'], o['valid'], o['lmode'], o['lans'], o['lword'])
        return st + (o['lwend'],) if self.span else st

    # ---- talker ----
    def readout(self, R):
        return F.linear(self.ln_t(R), self.reader.tok.weight) + self.bias

    def span_pick(self, lword, lwend, nw):
        """[B,W] start / end logits of the state, nw [B] word count of the CURRENT rows -> (s, e [B] long, ok [B] bool): the (s, e) with
        s <= e < s + span_max, e < nw (and both pointers valid in the state) that maximises log p_start(s) + log p_end(e)."""
        W = lword.shape[1]
        ls, le = lword.float().log_softmax(-1), lwend.float().log_softmax(-1)
        ix = torch.arange(W, device=lword.device)
        band = (ix[None, :] >= ix[:, None]) & (ix[None, :] < ix[:, None] + self.span_max)                       # [s, e]
        okp = (lword > -1e8)[:, :, None] & (lwend > -1e8)[:, None, :] & band[None] & (ix[None, None, :] < nw[:, None, None])
        sc = (ls[:, :, None] + le[:, None, :]).masked_fill(~okp, -float('inf')).flatten(1)
        best = sc.argmax(-1)
        return best // W, best % W, okp.flatten(1).any(-1)

    def talk(self, state, batch, lesion=None, return_modes=False):
        """lesion (B2 only): 'nocopy'. The GEN copy keys come from the reader run on `batch` (the CURRENT rows, also under a donor swap).
        span: mode 1 prints prompt[ws[s]:we[e]] of the CURRENT row, s <= e < s + span_max, e < its word count; no valid pair: GEN.
        return_modes: also the decoded mode of every row (0 NUM, 1 WORD / SPAN, 2 GEN; GEN also when a NUM / WORD pointer is invalid)."""
        R, vals, valid, lmode, lans, lword, *rest = state
        if self.copy:
            X, xm = self.read(batch, talker=True)
            ids = self.gen_copy(R, X, xm, batch['prompt_ids'], lesion == 'nocopy')[0].argmax(-1)
        else:
            ids = self.readout(R).argmax(-1)
        gen = [self.vocab.decode(r)[::-1] for r in ids.tolist()]     # registers are units-first
        mode, k, w = lmode.argmax(-1).tolist(), lans.argmax(-1).tolist(), lword.argmax(-1).tolist()
        sps = [word_spans(row['prompt'])[:W_MAX] for row in batch['rows']]
        if self.span:
            ss, ee, okk = (x.tolist() for x in self.span_pick(lword, rest[0], torch.tensor([len(sp) for sp in sps], device=lword.device)))
        vals, valid, out, modes = vals.tolist(), valid.tolist(), [], []
        for i, row in enumerate(batch['rows']):
            sp = sps[i]
            if mode[i] == 0 and valid[i][k[i]]:
                out.append(str(vals[i][k[i]])); modes.append(0)
            elif mode[i] == 1 and self.span and okk[i]:
                out.append(row['prompt'][sp[ss[i]][0]:sp[ee[i]][1]]); modes.append(1)       # the CURRENT row is the copy source
            elif mode[i] == 1 and not self.span and w[i] < len(sp):
                out.append(row['prompt'][sp[w[i]][0]:sp[w[i]][1]]); modes.append(1)         # the CURRENT row is the copy source
            else:
                out.append(gen[i]); modes.append(2)
        return (out, modes) if return_modes else out

    @torch.no_grad()
    def generate(self, batch, lesion=None):
        if lesion in ('noexec', 'opswap', 'ctl27') or (self.copy and lesion == 'nowordc'):
            return self.talk(self.state(batch, lesion=lesion), batch)
        if self.copy and lesion == 'nocopy':
            return self.talk(self.state(batch), batch, lesion=lesion)
        return super().generate(batch, lesion)

    # ---- loss ----
    def span_mode(self, r, t, grid):
        """span: the row's mode (NUM stays NUM; yes/no or no matching run of the prompt's words: GEN; else 1) and its (s, e) targets written into grid [W,W]."""
        from custom_io.english import en_norm, word_runs
        if t['mode'] == 0:
            return 0
        key = (r.get('id'), r['prompt'], r['answer'])
        runs = self._span_t.get(key)
        if runs is None:
            if len(self._span_t) > 20000:
                self._span_t.clear()
            tn = en_norm(r['answer'])
            runs = self._span_t[key] = [] if tn in ('yes', 'no') else word_runs(r['prompt'], tn, self.span_max, W_MAX)
        for s_, e_ in runs:
            grid[s_, e_] = True
        return 1 if runs else 2

    def gold(self, rows, dev):
        """Teacher-forcing tensors from the rows' steps (no search): op [B,L], a/b [B,L,M] bool, mode [B], ans [B,M], word [B,W], gen [B,9]."""
        B, L = len(rows), N_RES
        op, A, Bm = np.zeros((B, L), np.int64), np.zeros((B, L, M), bool), np.zeros((B, L, M), bool)
        ans, word, mode, gen = np.zeros((B, M), bool), np.zeros((B, W_MAX), bool), np.zeros(B, np.int64), np.full((B, N_REG), -100, np.int64)
        span = np.zeros((B, W_MAX, W_MAX), bool) if self.span else None
        for i, r in enumerate(rows):
            t = pp.row_targets(r)
            if self.span:
                t = dict(t, mode=self.span_mode(r, t, span[i]))
            for s, (o, ca, cb, _) in enumerate(t['prog']):
                op[i, s], A[i, s, list(ca)], Bm[i, s, list(cb)] = o, True, True
            mode[i], ans[i, list(t['ans'])], word[i, list(t['word'])] = t['mode'], True, True
            if t['mode'] == 2:
                if self.vocab.length(r['answer']) > GEN_MAX:
                    capcount.hit('gen_answer_over')
                ids = self.vocab.encode(self.vocab.clip(r['answer'], GEN_MAX)[::-1]) + [EOS]
                gen[i, :len(ids)] = ids
        A[:, :, 0] |= ~A.any(-1)
        Bm[:, :, 0] |= ~Bm.any(-1)
        g = dict(op=op, a=A, b=Bm, mode=mode, ans=ans, word=word, gen=gen, has=np.array([bool(pp.row_targets(r)['prog']) for r in rows]))
        if self.span:
            g['span'] = span
        return {k: torch.from_numpy(v).to(dev) for k, v in g.items()}

    def span_loss(self, o, g):
        """-log sum over the target (s, e) of p_start(s) p_end(e), fp32, summed over the mode-1 rows and divided by B."""
        grid = o['lword'].float().log_softmax(-1)[:, :, None] + o['lwend'].float().log_softmax(-1)[:, None, :]
        lp = torch.logsumexp(grid.masked_fill(~g['span'], -1e9).flatten(1), -1)
        return torch.where(g['mode'] == 1, -lp, torch.zeros_like(lp)).sum() / lp.shape[0]

    def round_loss(self, o, g, batch):
        """Test LR: the final readout's losses per row, at every snapshot round t >= L + 1 (L = gold program steps); mean over each row's rounds,
        summed over rows / B (rows with no such round add 0)."""
        B = g['mode'].shape[0]
        L = (g['op'] > 0).sum(1)
        n_t = (g['gen'] >= 0).sum(1).clamp(min=1)
        acc = torch.zeros(B, device=L.device)
        cnt = torch.zeros(B, device=L.device)
        rowmarg = lambda lg, m, sel: torch.where(sel, -(torch.logsumexp(lg.masked_fill(~m, -1e9), -1) - torch.logsumexp(lg, -1)), torch.zeros_like(lg[:, 0]))
        for t, z1, R, Rs, valid in o['rounds']:
            sel = L + 1 <= t
            if not sel.any():
                continue
            zf = self.ln_z(z1)
            ks_ = self.k_slot(self.ln_k(torch.cat([o['S0'], Rs], 1)))
            lm = F.cross_entropy(self.mode_head(zf).float(), g['mode'], reduction='none')
            la = rowmarg(self.ptr(self.q_ans(zf), ks_, valid), g['ans'], g['mode'] == 0)
            lw_ = self.ptr(self.q_word(zf), o['Kw'], o['wvalid'])
            if self.span:
                grid = lw_.float().log_softmax(-1)[:, :, None] + self.ptr(self.q_wend(zf), o['Kw'], o['wvalid']).float().log_softmax(-1)[:, None, :]
                lp = torch.logsumexp(grid.masked_fill(~g['span'], -1e9).flatten(1), -1)
                lw = torch.where(g['mode'] == 1, -lp, torch.zeros_like(lp))
            else:
                lw = rowmarg(lw_, g['word'], g['mode'] == 1)
            if self.copy:
                p, _ = self.gen_copy(R, o['X'], o['xm'], batch['prompt_ids'])
                tg = g['gen']
                ce = -torch.log(p.gather(2, tg.clamp(min=0)[..., None])[..., 0] + 1e-6).masked_fill(tg < 0, 0.0)
            else:
                ce = F.cross_entropy(self.readout(R).float().flatten(0, 1), g['gen'].flatten(), ignore_index=-100, reduction='none').view(B, -1)
            lg = (ce.sum(1) / n_t) * (g['mode'] == 2)
            acc = acc + (lm + la + lw + lg) * sel
            cnt = cnt + sel
        return (acc / cnt.clamp(min=1)).sum() / B

    def loss(self, batch):
        dev, B = batch['prompt_ids'].device, len(batch['rows'])
        g = self.gold(batch['rows'], dev)
        o = self.run(batch, gold=g, rounds=self.round_readout > 0)
        w_row = torch.where(g['has'], 1.0, self.w_noop)
        comm = torch.isin(g['op'], torch.tensor(COMM, device=dev))
        lop = lptr = 0.0
        hits = tot = 0
        for s, (lg, la, lb) in enumerate(o['steps']):
            lg = lg.float()
            lop = lop + (F.cross_entropy(lg, g['op'][:, s], reduction='none') * w_row).mean()
            pa, pb = la.log_softmax(-1), lb.log_softmax(-1)
            ga, gb = g['a'][:, s], g['b'][:, s]
            lab = torch.logsumexp(pa.masked_fill(~ga, -1e9), -1) + torch.logsumexp(pb.masked_fill(~gb, -1e9), -1)
            lba = torch.logsumexp(pa.masked_fill(~gb, -1e9), -1) + torch.logsumexp(pb.masked_fill(~ga, -1e9), -1)
            nll = -torch.where(comm[:, s], torch.logaddexp(lab, lba), lab)       # operand order is free for commutative ops
            lptr = lptr + (nll * (g['op'][:, s] > 0)).sum() / B
            hits += ((lg.argmax(-1) == g['op'][:, s]) & g['has']).sum()
            tot += g['has'].sum()
        marg = lambda lg, m, sel: torch.where(sel, -(torch.logsumexp(lg.masked_fill(~m, -1e9), -1) - torch.logsumexp(lg, -1)), torch.zeros_like(lg[:, 0])).sum() / B
        lmode = F.cross_entropy(o['lmode'].float(), g['mode'])
        lans, lword = marg(o['lans'], g['ans'], g['mode'] == 0), (self.span_loss(o, g) if self.span else marg(o['lword'], g['word'], g['mode'] == 1))
        n_t = (g['gen'] >= 0).sum(1).clamp(min=1)
        if self.copy:       # pointer-generator: -log p[target] (fp32), the same masking and normalisation as the vocabulary CE below
            p, gate = self.gen_copy(o['R'], o['X'], o['xm'], batch['prompt_ids'])
            tg = g['gen']
            ce = -torch.log(p.gather(2, tg.clamp(min=0)[..., None])[..., 0] + 1e-6).masked_fill(tg < 0, 0.0)
        else:
            ce = F.cross_entropy(self.readout(o['R']).float().flatten(0, 1), g['gen'].flatten(), ignore_index=-100, reduction='none').view(B, -1)
        lgen = (ce.sum(1) / n_t).mul(g['mode'] == 2).sum() / B
        aux = dict(prog=lop + lptr, op_acc=hits / tot.clamp(min=1), mode=lmode, ans=lans, word=lword, gen=lgen)
        if self.copy:       # mean copy share (1 - g) over the registers that hold a target char (not the EOS slot) of GEN rows
            tm = (g['gen'] >= 0) & (g['gen'] != EOS) & (g['mode'] == 2)[:, None]
            aux['copy_share'] = ((1 - gate[..., 0]) * tm).sum() / tm.sum().clamp(min=1)
        total = lop + lptr + lmode + lans + lword + lgen
        if self.round_readout:
            lrr = self.round_loss(o, g, batch)
            total = total + self.round_readout * lrr
            aux['rounds'] = lrr
        if self.eg_teach:   # training prompts only: loss() never runs on dev rows
            from custom_io.models.eg import teacher_vec
            _, pooled = self.eg().encode([r['prompt'] for r in batch['rows']], batch['prompt_ids'].shape[1], dev, chars=False)
            head = self.mt_head(self.ln_mt(o['z1'])).float()
            lmt = (1 - F.cosine_similarity(head, teacher_vec(pooled), dim=-1)).mean()
            total = total + self.eg_teach * lmt
            aux['meaning'] = lmt
        return total, {k: v.detach() for k, v in aux.items()}

    # ---- extra evals (train.py --final-eval) ----
    @torch.no_grad()
    def extra_evals(self, ctx):
        """coverage of the parser on the dev rows; teacher-forced vs free-run op accuracy on a held-out slice; noexec on the program
        families; opswap: % of outputs equal to the swapped program's value (the intact model's own program, run with ADD<->SUB)."""
        import os
        from custom_io.data import collate, Dataset, load_rows, to_device
        from custom_io.evalx import CHAIN5, evaluate, is_hit, subsample
        was = self.training
        self.eval()
        root = ctx.get('big') or ctx['data']
        rows = load_rows(os.path.join(root, 'dev', 'in_dist.jsonl'))
        dev, bs, amp = ctx['device'], ctx['batch_size'], ctx['amp']
        cov = pp.coverage(rows)
        fams = sorted(f for f, c in cov['by_family'].items() if c['prog'] >= 50)
        prows = [r for r in rows if pp.row_targets(r)['prog']]
        out = dict(coverage=cov, program_families=fams, n_dev=len(rows), n_prog=len(prows))

        def batches(rs, size=bs):
            for s in range(0, len(rs), size):
                yield to_device(collate([Dataset(rs[s:s + size], self.vocab, strict=False)[i] for i in range(len(rs[s:s + size]))]), dev)

        # teacher-forced vs free-run op accuracy (steps 1..7, NOOP after the program counts) and full-program match
        sl = subsample(prows, 400)
        tf = dict(ops=0, steps=0, prog=0)
        fr = dict(ops=0, steps=0, prog=0, ans=0)
        for b in batches(sl):
            g = self.gold(b['rows'], dev)
            for name, gd, acc in (('tf', g, tf), ('fr', None, fr)):
                with amp():
                    o = self.run(b, gold=gd)
                pad = lambda x: torch.cat([x, x.new_zeros(x.shape[0], N_RES - x.shape[1])], 1)
                ops, a, bb = (pad(torch.stack([st[i].argmax(-1) for st in o['steps']], 1)) for i in range(3))     # what the heads chose
                okop = ops == g['op']
                oka = g['a'].gather(2, a[..., None])[..., 0] & g['b'].gather(2, bb[..., None])[..., 0]
                okc = (g['b'].gather(2, a[..., None])[..., 0] & g['a'].gather(2, bb[..., None])[..., 0]) & torch.isin(g['op'], torch.tensor(COMM, device=dev))
                step_ok = okop & ((g['op'] == 0) | oka | okc)
                acc['ops'] += okop.sum().item(); acc['steps'] += okop.numel(); acc['prog'] += step_ok.all(1).sum().item()
                if name == 'fr':
                    with amp():
                        acc['ans'] += sum(is_hit(p, r) for p, r in zip(self.generate(b), b['rows']))
        n = len(sl)
        out['op_acc'] = dict(n=n, teacher_forced=dict(op=100 * tf['ops'] / tf['steps'], program=100 * tf['prog'] / n),
                             free_run=dict(op=100 * fr['ops'] / fr['steps'], program=100 * fr['prog'] / n, answer=100 * fr['ans'] / n))
        # noexec: the mark ('program_families') uses rows whose printed digits MUST come from the executor (all gold answer slots are
        # result slots); verify_claim (GEN yes/no) and compare_numbers (answer is a prompt slot) can survive noexec without it, so they
        # are excluded there. The old all-family number is kept as all_program_families.
        tg = {r['id']: pp.row_targets(r) for r in rows}
        fr_rows = subsample([r for r in rows if r['family'] in fams], 3000)
        ex_rows = [r for r in fr_rows if tg[r['id']]['mode'] == 0 and all(x >= R0 for x in tg[r['id']]['ans'])]
        with amp():
            ne = evaluate(self, fr_rows, bs, dev, 'noexec')
            it = evaluate(self, fr_rows, bs, dev, None, return_preds=True)
            nx = evaluate(self, ex_rows, bs, dev, 'noexec') if ex_rows else dict(exact=None, n=0)
        ix = [is_hit(it['preds'][r['id']], r) for r in ex_rows]
        out['noexec'] = dict(program_families=nx['exact'], n=nx['n'], intact=100 * sum(ix) / max(len(ix), 1),
                             exec_families=sorted({r['family'] for r in ex_rows}), all_program_families=ne['exact'], all_intact=it['exact'],
                             n_all=ne['n'], by_family=ne['by_family'], families=fams)
        # chain-5 under lesions: all rows, NUM-mode rows only, and the story_chain3 WORD rows (a two-name coin flip is ~4.9 chain-5 points)
        c5 = [r for r in rows if r['family'] in CHAIN5]
        if c5:
            c5n = [r for r in c5 if tg[r['id']]['mode'] == 0]
            c5w = [r for r in c5 if tg[r['id']]['mode'] == 1]
            les = {}
            for name in ('intact', 'loops:1', 'loops:2', 'noexec'):
                les[name] = {}
                for tag, rs in (('all', c5), ('num', c5n), ('word', c5w)):
                    if rs:
                        with amp():
                            les[name][tag] = evaluate(self, rs, bs, dev, None if name == 'intact' else name)['exact']
            out['chain5_lesions'] = dict(n_all=len(c5), n_num=len(c5n), n_word=len(c5w), **les)
            out['noexec']['chain5'] = les['noexec']['all']
        # opswap: rows the intact model got right, answered by a NUM pointer. affected = the swap changes the pointed value (replay valid);
        # chain-5 only is the mark (swap_match); pooled over all program families kept as swap_match_all.
        def swap_stats(rs):
            with amp():
                ip = evaluate(self, rs, bs, dev, None, return_preds=True)['preds']
            sm = dict(n=0, aff=0, match=0, invalid=0, unchanged=0, intact=0)
            for b in batches([r for r in rs if is_hit(ip[r['id']], r)]):
                with amp():
                    o = self.run(b)
                    outs = self.talk(self.state(b, lesion='opswap'), b)
                ops, a, bb = o['prog']
                v2, ok2 = replay(o['vals'], o['valid'], ops, a, bb, swap=True)
                k = o['lans'].argmax(-1, keepdim=True)
                num = ((o['lmode'].argmax(-1) == 0) & o['valid'].gather(1, k)[:, 0]).tolist()
                ok_sw = ok2.gather(1, k)[:, 0].tolist()
                chg = (v2.gather(1, k)[:, 0] != o['vals'].gather(1, k)[:, 0]).tolist()
                want = [str(x) for x in v2.gather(1, k)[:, 0].tolist()]
                for i in range(len(want)):
                    if not num[i]:
                        continue
                    sm['n'] += 1
                    if not ok_sw[i]:
                        sm['invalid'] += 1
                    elif not chg[i]:
                        sm['unchanged'] += 1
                    else:
                        sm['aff'] += 1; sm['match'] += outs[i] == want[i]; sm['intact'] += is_hit(outs[i], b['rows'][i])
            return sm
        pc = lambda x, n: 100 * x / max(n, 1)
        s5, sa = swap_stats(c5), swap_stats(fr_rows)
        out['opswap'] = dict(swap_match=pc(s5['match'], s5['aff']), n_affected=s5['aff'], n_invalid_swap=s5['invalid'], n_unchanged=s5['unchanged'],
                             stays_intact=pc(s5['intact'], s5['aff']), chain5=dict(swap_match=pc(s5['match'], s5['aff']), n=s5['aff']),
                             swap_match_all=pc(sa['match'], sa['aff']), n_all=sa['aff'], n_all_invalid=sa['invalid'])
        if self.copy:
            out['copy_gate'] = self.copy_gate_eval(rows, ctx)
        if self.eg_embed or self.eg_teach:
            out['size'] = self.size()
        self.train(was)
        return out

    @torch.no_grad()
    def copy_gate_eval(self, rows, ctx):
        """copy_gate: per family mean of (1 - g) over the GEN registers that hold a target char (not the EOS slot), on the GEN-mode rows of `rows`
        (dev in_dist; at most 3000, spread evenly). 1 = the register copies from the prompt, 0 = it reads the vocabulary. {by_family, n_regs, overall, n_rows}."""
        from custom_io.data import collate, Dataset, to_device
        from custom_io.evalx import subsample
        gen_rows = subsample([r for r in rows if pp.row_targets(r)['mode'] == 2], 3000)
        dev, bs, amp = ctx['device'], ctx['batch_size'], ctx['amp']
        tot, cnt = {}, {}
        for s in range(0, len(gen_rows), bs):
            rs = gen_rows[s:s + bs]
            b = to_device(collate([Dataset(rs, self.vocab, strict=False)[i] for i in range(len(rs))]), dev)
            with amp():
                o = self.run(b)
                _, gate = self.gen_copy(o['R'], o['X'], o['xm'], b['prompt_ids'])
            tgt = self.gold(rs, dev)['gen']
            hold = (tgt >= 0) & (tgt != EOS)
            share = ((1 - gate[..., 0]) * hold).sum(1).tolist()
            for i, r in enumerate(rs):
                f = r['family']
                tot[f], cnt[f] = tot.get(f, 0.0) + share[i], cnt.get(f, 0) + int(hold[i].sum())
        return dict(by_family={f: tot[f] / cnt[f] for f in sorted(cnt) if cnt[f]}, n_regs={f: cnt[f] for f in sorted(cnt)},
                    overall=sum(tot.values()) / max(sum(cnt.values()), 1), n_rows=len(gen_rows))
