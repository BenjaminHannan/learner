"""Binding toy: does a card writer keep WHO a fact is about, or only the value?

Fixed harness for the ShinkaEvolve trial (research/shinka/CARD.md). Nothing in
here is evolved; only `CardWriter` in the candidate program is.

One episode is a "visit" of C lines. Each line states one fact
(person, relation, value) with the three content tokens at random positions
among filler tokens. A frozen random "reader" turns tokens into contextual
states; the person signal at the value token is weak, as measured in
PremonitionMini (person readable 16-23% at the value word).

The candidate writer turns each line's states into one card (key, value).
A fixed question encoder reads "person relation" into a query, cards are
scored by kappa * cos(query, key), and the soft-read value is decoded into a
value-token guess. Training is answer-only cross-entropy, the setting in which
PremonitionMini's single-pool writer puts ~98% of its pool on the value token.

Decoys make binding necessary: the asked card always has at least one card for
the same person with another relation and one for the same relation with another
person, so a writer that keeps only the relation (or only the person) must guess
among two or more cards, and one that keeps only the value is near chance (1/C).

Score = mean of held-out accuracy on familiar names and on NOVEL names (entity
tokens never seen in training), so memorising particular names does not help.
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass(frozen=True)
class ToyConfig:
    d: int = 32            # reader state width
    dk: int = 16           # key width
    n_ent_train: int = 16  # names seen in training
    n_ent_novel: int = 8   # names only seen at test
    n_rel: int = 4
    n_val: int = 24
    n_fill: int = 40
    cards: int = 8         # lines per visit
    persons: int = 4       # distinct people per visit
    line_len: int = 10
    reader_mix: float = 0.35   # strength of the frozen reader's context mixing
    reader_decay: float = 0.6  # per-token decay of that mixing
    steps: int = 700
    batch: int = 64
    lr: float = 3e-3
    eval_visits: int = 1024
    max_writer_params: int = 20000   # numbers stored in the writer, of any kind
    max_seconds: float = 150.0       # per seed: writer start-up, training and eval incl. transfer; a slower writer fails


class Vocab:
    def __init__(self, c: ToyConfig):
        self.ent0 = 0
        self.rel0 = c.n_ent_train + c.n_ent_novel
        self.val0 = self.rel0 + c.n_rel
        self.fill0 = self.val0 + c.n_val
        self.size = self.fill0 + c.n_fill


def make_visits(c: ToyConfig, v: Vocab, n: int, novel: bool, g: torch.Generator):
    """Return (lines [n,C,L] token ids, roles [n,C,L] 0=fill 1=person 2=rel 3=val,
    facts [n,C,3] (person, rel, value) ids, q_card [n] index of the asked card)."""
    C, L = c.cards, c.line_len
    lines = torch.empty(n, C, L, dtype=torch.long)
    roles = torch.zeros(n, C, L, dtype=torch.long)
    facts = torch.empty(n, C, 3, dtype=torch.long)
    pool_lo = c.n_ent_train if novel else 0
    pool_n = c.n_ent_novel if novel else c.n_ent_train
    q_card = torch.empty(n, dtype=torch.long)
    for i in range(n):
        people = pool_lo + torch.randperm(pool_n, generator=g)[: c.persons]
        # C distinct (person, relation) pairs out of persons * n_rel; the asked card
        # must have both decoys (same person + other relation, same relation + other person)
        while True:
            pairs = torch.randperm(c.persons * c.n_rel, generator=g)[:C]
            pp, rr = pairs // c.n_rel, pairs % c.n_rel
            ok = [j for j in range(C)
                  if ((pp == pp[j]).sum() > 1) and ((rr == rr[j]).sum() > 1)]
            if ok:
                q_card[i] = ok[int(torch.randint(len(ok), (1,), generator=g))]
                break
        for j in range(C):
            p = int(people[pairs[j] // c.n_rel])
            r = int(pairs[j] % c.n_rel)
            val = int(torch.randint(c.n_val, (1,), generator=g))
            facts[i, j] = torch.tensor([p, r, val])
            toks = v.fill0 + torch.randint(c.n_fill, (L,), generator=g)
            pos = torch.randperm(L, generator=g)[:3]
            toks[pos[0]] = v.ent0 + p
            toks[pos[1]] = v.rel0 + r
            toks[pos[2]] = v.val0 + val
            roles[i, j, pos[0]], roles[i, j, pos[1]], roles[i, j, pos[2]] = 1, 2, 3
            lines[i, j] = toks
    return lines, roles, facts, q_card


class FrozenReader(nn.Module):
    """h_t = LayerNorm(E[x_t] + P_t + mix * sum_{s != t} decay^|t-s| M E[x_s]), no training."""

    def __init__(self, c: ToyConfig, vocab_size: int, g: torch.Generator):
        super().__init__()
        d = c.d
        self.emb = nn.Parameter(torch.randn(vocab_size, d, generator=g), requires_grad=False)
        self.pos = nn.Parameter(0.5 * torch.randn(c.line_len, d, generator=g), requires_grad=False)
        q, _ = torch.linalg.qr(torch.randn(d, d, generator=g))
        self.mix = nn.Parameter(q, requires_grad=False)
        idx = torch.arange(c.line_len)
        dist = (idx[:, None] - idx[None, :]).abs().float()
        kern = c.reader_mix * c.reader_decay ** dist
        kern.fill_diagonal_(0.0)
        self.kern = nn.Parameter(kern, requires_grad=False)
        self.norm = nn.LayerNorm(d, elementwise_affine=False)

    def forward(self, toks: torch.Tensor) -> torch.Tensor:
        e = self.emb[toks]                                   # [..., L, d]
        n = toks.shape[-1]
        ctx = torch.einsum("ts,...sd->...td", self.kern[:n, :n], e @ self.mix)
        return self.norm(e + self.pos[: toks.shape[-1]] + ctx)


class Answerer(nn.Module):
    """Fixed (not evolved) question encoder, card scorer and value decoder."""

    def __init__(self, c: ToyConfig):
        super().__init__()
        self.q = nn.Sequential(nn.Linear(2 * c.d, 2 * c.d), nn.GELU(), nn.Linear(2 * c.d, c.dk))
        self.kappa = nn.Parameter(torch.tensor(10.0))
        self.out = nn.Linear(c.d, c.n_val)

    def forward(self, q_states, keys, values):
        query = F.normalize(self.q(q_states.flatten(-2)), dim=-1)          # [B, dk]
        keys = F.normalize(keys, dim=-1)                                     # [B, C, dk]
        att = torch.softmax(self.kappa * torch.einsum("bk,bck->bc", query, keys), dim=-1)
        read = torch.einsum("bc,bcd->bd", att, values)
        return self.out(read), att


def question_tokens(v: Vocab, facts, q_card):
    f = facts[torch.arange(facts.shape[0]), q_card]                         # [B, 3]
    return torch.stack([v.ent0 + f[:, 0], v.rel0 + f[:, 1]], dim=1), f[:, 2]


SALT_FILE = Path(__file__).resolve().parent.parent / "results" / ".shuffle_salt"


def _shuffle_seed(seed: int) -> int:
    """Secret but reproducible: the line shuffle is seeded from a salt kept in a file the
    candidate never receives (not committed), plus the run seed."""
    import hashlib
    import os
    SALT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SALT_FILE.exists():
        # write a complete temp file, then hard-link it into place: the salt file appears
        # only fully written, and when processes race the first link wins for all of them
        tmp = SALT_FILE.with_name(f".salt.{os.getpid()}.tmp")
        tmp.write_bytes(os.urandom(16))
        try:
            os.link(tmp, SALT_FILE)
        except FileExistsError:
            pass
        finally:
            tmp.unlink()
    salt = SALT_FILE.read_bytes()
    if len(salt) != 16:
        raise RuntimeError(f"shuffle salt file {SALT_FILE} is corrupt; delete it to regenerate")
    h = hashlib.blake2b(salt + seed.to_bytes(8, "little", signed=True), digest_size=8)
    return int.from_bytes(h.digest(), "little") >> 1


class IsolatedWriter:
    """Parent-side handle to a CardWriter running in its own child process (worker.py).

    - The child gets reader states only. The parent keeps the answerer, the loss, the
      metrics and all writer checks, so candidate code cannot alter the score.
    - Arrays go to the child as numpy copies (no shared memory), and replies come back
      as raw bytes in a fixed format (no unpickling of child data).
    - On every call the B*C lines are shuffled across visits with a secret permutation
      and un-shuffled afterwards. A writer that obeys the one-line-one-card rule gives
      the same cards; one that mixes lines only mixes unrelated lines.
    - API keys and tokens are removed from the environment the child inherits."""

    TIMEOUT = 120.0  # seconds per message

    def __init__(self, path: str, cls_name: str, seed: int, c: ToyConfig, trusted: bool = False):
        import multiprocessing as mp
        import os
        import worker
        self.c = c
        self.deadline = time.time() + c.max_seconds
        self.closed = False
        self.shuffle = torch.Generator().manual_seed(_shuffle_seed(seed))
        saved = {k: os.environ.pop(k) for k in list(os.environ)
                 if any(t in k.upper() for t in ("API_KEY", "TOKEN", "SECRET", "PASSWORD"))}
        try:
            ctx = mp.get_context("spawn")
            self.conn, child = ctx.Pipe()
            self.proc = ctx.Process(target=worker.serve, args=(child,), daemon=True)
            self.proc.start()
            child.close()
        finally:
            os.environ.update(saved)
        try:
            self.n_numbers = self._int(("init", path, cls_name, seed + 7, c.d, c.dk, c.lr, trusted))
        except BaseException:
            self.close()
            raise

    def _call(self, msg) -> bytes:
        self.conn.send(msg)
        wait = min(self.TIMEOUT, self.deadline - time.time())
        if wait <= 0 or not self.conn.poll(wait):
            self.close()
            raise TimeoutError(f"writer did not answer {msg[0]!r} in time "
                               f"(limit {self.c.max_seconds:.0f}s per seed)")
        try:
            reply = self.conn.recv_bytes(1 << 30)
        except (EOFError, OSError):
            raise RuntimeError("writer process died") from None
        if reply[:1] == b"E":
            raise RuntimeError("writer failed: " + reply[1:].decode("utf-8", "replace"))
        return reply

    def _int(self, msg) -> int:
        import struct
        reply = self._call(msg)
        if reply[:1] != b"I" or len(reply) != 9:
            raise RuntimeError("bad reply from writer process")
        return struct.unpack("<q", reply[1:])[0]

    def count(self) -> int:
        return self._int(("count",))

    def forward(self, states, mask, train: bool, roles=None):
        import struct
        b, cards = states.shape[:2]
        perm = torch.randperm(b * cards, generator=self.shuffle)
        inv = torch.empty_like(perm)
        inv[perm] = torch.arange(b * cards)

        def shuf(t):
            return t.reshape(b * cards, *t.shape[2:])[perm].reshape(t.shape).numpy().copy()

        msg = ("fwd", shuf(states), shuf(mask), train, None if roles is None else shuf(roles))
        reply = self._call(msg)
        nk, nv = (struct.unpack("<qq", reply[1:17]) if reply[:1] == b"F" and len(reply) >= 17 else (-1, -1))
        if nk != b * cards * self.c.dk or nv != b * cards * self.c.d or len(reply) != 17 + 4 * (nk + nv):
            raise ValueError(f"bad writer output: keys must be [B, C, {self.c.dk}], values [B, C, {self.c.d}]")
        flat = torch.frombuffer(bytearray(reply[17:]), dtype=torch.float32)
        keys = flat[:nk].reshape(b * cards, self.c.dk)[inv].reshape(b, cards, self.c.dk)
        values = flat[nk:].reshape(b * cards, self.c.d)[inv].reshape(b, cards, self.c.d)
        if not (torch.isfinite(keys).all() and torch.isfinite(values).all()):
            raise FloatingPointError("non-finite writer output")
        self._last_perm = perm
        return keys, values

    def step(self, dkeys, dvalues):
        b, cards = dkeys.shape[:2]
        perm = self._last_perm

        def shuf(t):
            return t.reshape(b * cards, -1)[perm].reshape(t.shape).numpy().copy()

        if self._call(("step", shuf(dkeys), shuf(dvalues))) != b"S":
            raise RuntimeError("bad reply from writer process")

    def close(self):
        if getattr(self, "closed", True):
            return
        self.closed = True
        try:
            self.conn.send(("stop",))
        except (OSError, BrokenPipeError):
            pass
        proc = getattr(self, "proc", None)
        if proc is not None:
            proc.join(2)
            if proc.is_alive():
                proc.kill()
                proc.join(2)
        self.conn.close()


def check_writer(w: IsolatedWriter, states, mask, g: torch.Generator) -> None:
    """Behavioural checks from the parent, in eval mode, at the eval batch size:
    - pure: f(x1), f(x2), f(x1) - the two f(x1) must agree, so no state is kept between calls;
    - per line: changing 16 random lines changes no other card, so a card cannot use
      other lines or other visits."""
    k1, v1 = w.forward(states, mask, train=False)
    other = states[torch.randperm(states.shape[0], generator=g)]
    w.forward(other, mask, train=False)
    k2, v2 = w.forward(states, mask, train=False)
    if not (torch.allclose(k1, k2, atol=1e-5) and torch.allclose(v1, v2, atol=1e-5)):
        raise ValueError("writer output changed between identical calls (state kept between calls, "
                         "or not deterministic in eval mode)")
    alt = states.clone()
    b, cards = states.shape[:2]
    flat = torch.randperm(b * cards, generator=g)[:16]
    vi, li = flat // cards, flat % cards
    alt[vi, li] = alt[vi, li].flip(-2) + 0.5 * torch.randn(alt[vi, li].shape, generator=g)
    k3, v3 = w.forward(alt, mask, train=False)
    keep = torch.ones(b, cards, dtype=torch.bool)
    keep[vi, li] = False
    if not (torch.allclose(k1[keep], k3[keep], atol=1e-5) and torch.allclose(v1[keep], v3[keep], atol=1e-5)):
        raise ValueError("a card depends on other lines or visits; each card must use only its own line")


CACHE_DIR = SALT_FILE.parent / ".batch_cache"
USE_CACHE = True   # confirm.py turns this off: the confirmation never reads cached data


def _training_batches(c: ToyConfig, v: Vocab, g: torch.Generator, seed: int):
    """The c.steps training batches for this seed, from a parent-only disk cache when
    present. They depend only on the seed and the config; `g` must be the generator
    that made the reader, and is advanced exactly as if the batches were generated."""
    import hashlib
    import os
    if not USE_CACHE:
        return [make_visits(c, v, c.batch, novel=False, g=g) for _ in range(c.steps)]
    # the key covers the harness source and torch version, so a code change never
    # serves stale batches
    src = Path(__file__).read_bytes()
    key = hashlib.blake2b(repr((c, seed, torch.__version__)).encode() + src, digest_size=8).hexdigest()
    path = CACHE_DIR / f"{key}.pt"
    if path.exists():
        try:
            data = torch.load(path, weights_only=True)
            g.set_state(data["g_state"])
            return [tuple(b) for b in data["batches"]]
        except Exception:  # noqa: BLE001 - a bad cache file is just regenerated
            pass
    batches = [make_visits(c, v, c.batch, novel=False, g=g) for _ in range(c.steps)]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    torch.save({"batches": [list(b) for b in batches], "g_state": g.get_state()}, tmp)
    os.replace(tmp, path)
    return batches


def run_seed(spec, seed: int, c: ToyConfig = ToyConfig()) -> dict:
    """Train writer + answerer from scratch on one seed; return held-out metrics.

    spec = (path, class_name, trusted). The writer always runs in a fresh child process.
    trusted=True is only for the calibration references (it lets the oracle receive roles)."""
    path, cls_name, trusted = spec
    t0 = time.time()
    torch.manual_seed(seed)
    g = torch.Generator().manual_seed(10_000 + seed)
    v = Vocab(c)
    reader = FrozenReader(c, v.size, g)
    # all training data is made before the writer's clock starts, so its time limit
    # does not count data generation; it depends only on the seed, so it is cached
    batches = _training_batches(c, v, g, seed)
    w = IsolatedWriter(path, cls_name, seed, c, trusted)  # closes itself if init fails
    try:
        if w.n_numbers > c.max_writer_params:
            raise ValueError(f"writer stores {w.n_numbers} numbers > cap {c.max_writer_params}")
        ans = Answerer(c)
        opt = torch.optim.Adam(ans.parameters(), lr=c.lr)
        mask_all = torch.ones(c.batch, c.cards, c.line_len, dtype=torch.bool)

        for lines, roles, facts, q_card in batches:
            qt, target = question_tokens(v, facts, q_card)
            with torch.no_grad():
                states, q_states = reader(lines), reader(qt)
            keys, values = w.forward(states, mask_all, train=True, roles=roles if trusted else None)
            keys.requires_grad_(True)
            values.requires_grad_(True)
            logits, _ = ans(q_states, keys, values)
            loss = F.cross_entropy(logits, target)
            if not torch.isfinite(loss):
                raise FloatingPointError("non-finite training loss")
            opt.zero_grad()
            loss.backward()
            opt.step()
            w.step(keys.grad, values.grad)

        n_end = w.count()
        if n_end > c.max_writer_params:
            raise ValueError(f"writer stores {n_end} numbers after training > cap {c.max_writer_params}")
        out = {"seed": seed, "writer_params": max(w.n_numbers, n_end)}
        g_eval = torch.Generator().manual_seed(20_000 + seed)
        with torch.no_grad():
            for split, novel in (("familiar", False), ("novel", True)):
                lines, roles, facts, q_card = make_visits(c, v, c.eval_visits, novel=novel, g=g_eval)
                qt, target = question_tokens(v, facts, q_card)
                states, q_states = reader(lines), reader(qt)
                mask = torch.ones(lines.shape, dtype=torch.bool)
                r = roles if trusted else None
                if not trusted:
                    # own generator, so the checks do not shift the eval data stream
                    check_writer(w, states, mask, torch.Generator().manual_seed(30_000 + seed + novel))
                keys, values = w.forward(states, mask, train=False, roles=r)
                if keys.shape[-1] != c.dk:
                    raise ValueError(f"keys must have width dk={c.dk}")
                logits, att = ans(q_states, keys, values)
                pred = logits.argmax(-1)
                out[f"acc_{split}"] = float((pred == target).float().mean())
                # which card got the most attention, and what kind of mistake is it
                pick = att.argmax(-1)
                ar = torch.arange(len(pick))
                pf, qf = facts[ar, pick], facts[ar, q_card]
                right = pick == q_card
                same_rel_other_person = (~right) & (pf[:, 1] == qf[:, 1])
                same_person_other_rel = (~right) & (pf[:, 0] == qf[:, 0])
                out[f"pick_{split}"] = float(right.float().mean())
                out[f"err_person_lost_{split}"] = float(same_rel_other_person.float().mean())
                out[f"err_relation_lost_{split}"] = float(same_person_other_rel.float().mean())
                if split == "familiar":
                    out.update(sensitivity(w, reader, v, c, lines[:256], roles[:256], g_eval, trusted))
    finally:
        w.close()
    out["score"] = 0.5 * (out["acc_familiar"] + out["acc_novel"])
    out["seconds"] = time.time() - t0
    return out


def sensitivity(w: IsolatedWriter, reader, v: Vocab, c: ToyConfig, lines, roles, g, trusted) -> dict:
    """Behaviour descriptor: how much the key / value move when one role's token is replaced.
    Normalised so the 4 key numbers (and the 4 value numbers) sum to 1."""
    mask = torch.ones(lines.shape, dtype=torch.bool)
    r = roles if trusted else None
    k0, v0 = w.forward(reader(lines), mask, train=False, roles=r)
    k0 = F.normalize(k0, dim=-1)
    lo = {1: (v.ent0, c.n_ent_train), 2: (v.rel0, c.n_rel), 3: (v.val0, c.n_val), 0: (v.fill0, c.n_fill)}
    res = {}
    for role, name in ((1, "person"), (2, "rel"), (3, "val"), (0, "fill")):
        alt = lines.clone()
        sel = roles == role
        if role == 0:  # change one filler token per line
            first = sel.float().cumsum(-1) == 1
            sel = sel & first
        base, n = lo[role]
        cur = alt[sel] - base
        alt[sel] = base + (cur + 1 + torch.randint(n - 1, cur.shape, generator=g)) % n
        k1, v1 = w.forward(reader(alt), mask, train=False, roles=r)
        res[f"dk_{name}"] = float((F.normalize(k1, dim=-1) - k0).norm(dim=-1).mean())
        res[f"dv_{name}"] = float((v1 - v0).norm(dim=-1).mean() / (v0.norm(dim=-1).mean() + 1e-8))
    for pre in ("dk_", "dv_"):
        tot = sum(res[pre + n] for n in ("person", "rel", "val", "fill")) + 1e-8
        for n in ("person", "rel", "val", "fill"):
            res[pre + n] = res[pre + n] / tot
    return res


def run(spec, seeds, c: ToyConfig = ToyConfig()) -> dict:
    torch.set_num_threads(1)
    per = [run_seed(spec, s, c) for s in seeds]
    keys = [k for k in per[0] if k != "seed"]
    mean = {k: sum(p[k] for p in per) / len(per) for k in keys}
    return {"mean": mean, "per_seed": per}
