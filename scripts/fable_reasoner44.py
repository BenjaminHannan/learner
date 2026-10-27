#!/usr/bin/env python3
"""Experiment 44: the reasoner as callable skills + router, over a notebook village.

WHAT THIS IS
  A "village" of N people and R=8 base relations lives in a NOTEBOOK (a plain dict of
  (person, relation) -> person, about 15% of entries missing).  Nothing about any person
  is ever stored in trained weights.

  SKILL r  = "look up relation r in the current notebook".  It is a matrix built AT RUN
  TIME from the notebook: M_r[x, y] = 1 when the fact (x, r, y) is written down, and
  M_r[x, SINK] = 1 when it is missing.  SINK absorbs (M_r[SINK, SINK] = 1).  The tape is
  a probability row vector over the N people plus the sink.  These matrices are NOT trained.

  THINKING (learned)  = an R x R logit table.  A question is a start person plus a
  sequence of relation TOKENS; the table turns each token into a soft choice over the R
  skills (direct logits, random init -- the 43G lesson was that unbounded similarity
  scores saturate, a direct logit table does not).  Supervision is ONLY the final answer
  (or "unknown"); never the intermediate hops, never which skill to use.

  The hop loop is HARD-CODED: one routed skill call per token, halt when the token tape
  is empty.  Nothing counts, nothing learns to stop.

  ANSWER RULE (hard-coded): answer = argmax person if its probability >= 0.9, else
  "unknown".

  SLEEP (learned, the 43H procedure) = a NEW relation word is taught only by raw episodes
  (person, new_word, answer).  Everything is frozen except that word's 3 x (R+1) routing
  logits ("keep" plus the R skills).  The checkpoint is chosen by 4-fold cross-validation
  with a 0.80 exact-match floor; it is installed only if the gate passes; the reload is
  weights-only.  Nothing proposes a rule; sleep is gradient arithmetic on 27 numbers.

  After sleep the new word is an ordinary token and may appear inside longer questions.

Additive, offline, CPU, one thread per process.  Reads nothing but this file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path

import torch
from torch import Tensor, nn

# ----------------------------------------------------------------- the world
RELATIONS = ("mother", "father", "spouse", "boss", "best_friend", "neighbour", "doctor", "teacher")
R = len(RELATIONS)
MISSING_RATE = 0.15
TRAIN_N = 60
BIG_N = 200

WORDS = (
    ("maternal_grandmother", ("mother", "mother")),
    ("boss_of_spouse", ("spouse", "boss")),
    ("doctor_of_mothers_friend", ("mother", "best_friend", "doctor")),
)
WORD_NAMES = tuple(w for w, _ in WORDS)
WORD_CHAINS = tuple(c for _, c in WORDS)
N_WORDS = len(WORDS)
STAGES = 3

# ----------------------------------------------------------------- given by hand
ANSWER_THRESHOLD = 0.9
UNKNOWN = "unknown"

# ----------------------------------------------------------------- training knobs
BASE_UPDATES = 4000
BASE_BATCH = 128
BASE_LR = 0.05
INIT_STD = 0.5
SLEEP_LR = 0.05
SLEEP_BATCH = 24
FOLDS = 4
CHECKPOINTS = (0, 50, 100, 200, 400, 800)
CV_FLOOR = 0.80
AGREEMENT_FLOOR = 0.90
EVAL_PER_SET = 300
HONESTY_SET = 400
DEPTHS = (4, 6, 8, 10)

LETTERS = "abcdefghijklmnopqrstuvwxyz"


def make_rng(tag: str, seed: int) -> random.Random:
    digest = hashlib.sha256(f"reasoner44/{tag}/{seed}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


@dataclass
class Village:
    names: tuple
    facts: dict          # THE NOTEBOOK: (person, relation) -> person

    @property
    def n(self) -> int:
        return len(self.names)

    @property
    def idx(self) -> dict:
        return self._idx

    def __post_init__(self) -> None:
        self._idx = {name: i for i, name in enumerate(self.names)}


def make_village(tag: str, seed: int, n: int, prefix: str) -> Village:
    """A fresh random village.  `prefix` keeps the name pools of different villages disjoint."""
    rng = make_rng(f"village/{tag}", seed)
    names: set = set()
    while len(names) < n:
        names.add(prefix + "_" + "".join(rng.choice(LETTERS) for _ in range(7)))
    names_t = tuple(sorted(names))
    facts: dict = {}
    for rel in RELATIONS:
        for x in names_t:
            if rng.random() < MISSING_RATE:
                continue                                  # ~15% of facts are simply not written down
            y = names_t[rng.randrange(n)]
            while y == x:
                y = names_t[rng.randrange(n)]
            facts[(x, rel)] = y
    return Village(names_t, facts)


def notebook_matrices(v: Village) -> Tensor:
    """Built at run time FROM THE NOTEBOOK.  [R+1, n+1, n+1]; row 0 is the identity ("keep")."""
    n, sink = v.n, v.n
    m = torch.zeros(R + 1, n + 1, n + 1)
    m[0] = torch.eye(n + 1)
    for r, rel in enumerate(RELATIONS):
        for i, x in enumerate(v.names):
            y = v.facts.get((x, rel))
            m[r + 1, i, v.idx[y] if y is not None else sink] = 1.0
        m[r + 1, sink, sink] = 1.0
    return m


# ----------------------------------------------------------------- questions
PAD_STAGE = R + STAGES * N_WORDS
N_STAGE_ROWS = PAD_STAGE + 1


def token_stages(t: int) -> tuple:
    if t < R:
        return (t,)
    w = t - R
    return tuple(R + STAGES * w + s for s in range(STAGES))


def expand_tokens(tokens) -> list:
    out: list = []
    for t in tokens:
        if t < R:
            out.append(RELATIONS[t])
        else:
            out.extend(WORD_CHAINS[t - R])
    return out


def walk(v: Village, start: str, relations) -> str | None:
    cur = start
    for rel in relations:
        cur = v.facts.get((cur, rel))
        if cur is None:
            return None
    return cur


@dataclass
class Question:
    start: str
    tokens: tuple
    answer: str | None


def sample_question(v: Village, rng: random.Random, n_tokens: int, want: str,
                    vocab=None, force_word=None) -> Question | None:
    vocab = tuple(range(R)) if vocab is None else vocab
    for _ in range(500):
        start = v.names[rng.randrange(v.n)]
        tokens = [vocab[rng.randrange(len(vocab))] for _ in range(n_tokens)]
        if force_word is not None:
            tokens[rng.randrange(n_tokens)] = R + force_word
        tokens = tuple(tokens)
        ans = walk(v, start, expand_tokens(tokens))
        if want == "any" or (want == "resolvable" and ans is not None) or (want == "missing" and ans is None):
            return Question(start, tokens, ans)
    return None


def sample_set(v: Village, tag: str, seed: int, count: int, lengths, want: str,
               vocab=None, force_words=None) -> list:
    rng = make_rng(tag, seed)
    qs = []
    i = 0
    while len(qs) < count:
        n_tokens = lengths[i % len(lengths)]
        fw = None if force_words is None else force_words[i % len(force_words)]
        q = sample_question(v, rng, n_tokens, want, vocab, fw)
        i += 1
        if q is not None:
            qs.append(q)
        if i > 400 * count:
            raise RuntimeError(f"could not sample {count} questions for {tag}")
    return qs


def encode(v: Village, qs) -> tuple:
    seqs = [[s for t in q.tokens for s in token_stages(t)] for q in qs]
    length = max(len(s) for s in seqs)
    stages = torch.full((len(qs), length), PAD_STAGE, dtype=torch.long)
    for i, s in enumerate(seqs):
        stages[i, :len(s)] = torch.tensor(s, dtype=torch.long)
    starts = torch.tensor([v.idx[q.start] for q in qs], dtype=torch.long)
    targets = torch.tensor([v.idx[q.answer] if q.answer is not None else v.n for q in qs], dtype=torch.long)
    return starts, stages, targets


# ----------------------------------------------------------------- the model
class Reasoner(nn.Module):
    """64 base numbers (token -> skill) plus 27 numbers per sleepable word."""

    def __init__(self) -> None:
        super().__init__()
        self.token_logits = nn.Parameter(torch.zeros(R, R))
        self.words = nn.ParameterList([nn.Parameter(torch.zeros(STAGES, R + 1)) for _ in range(N_WORDS)])

    def stage_table(self) -> Tensor:
        """[stage row, keep+skills] -- each row is a probability over the R+1 callable options."""
        base = torch.cat((torch.zeros(R, 1), self.token_logits.softmax(-1)), 1)   # base tokens never "keep"
        words = torch.stack([w.softmax(-1) for w in self.words]).reshape(N_WORDS * STAGES, R + 1)
        pad = torch.zeros(1, R + 1)
        pad[0, 0] = 1.0                                                            # padding = keep = identity
        return torch.cat((base, words, pad), 0)

    def effective(self, m: Tensor) -> Tensor:
        return torch.einsum("sc,cij->sij", self.stage_table(), m)


def run_tape(e: Tensor, starts: Tensor, stages: Tensor, n: int) -> Tensor:
    x = nn.functional.one_hot(starts, n + 1).float()
    for h in range(stages.shape[1]):
        x = torch.bmm(x.unsqueeze(1), e[stages[:, h]]).squeeze(1)
    return x


def decode(v: Village, x: Tensor) -> list:
    p = x[:, :v.n]
    conf, best = p.max(-1)
    return [v.names[b] if c >= ANSWER_THRESHOLD else UNKNOWN
            for b, c in zip(best.tolist(), conf.tolist())]


@torch.inference_mode()
def predict(model: Reasoner, v: Village, m: Tensor, qs, chunk: int = 128) -> list:
    e = model.effective(m)
    preds: list = []
    for i in range(0, len(qs), chunk):
        starts, stages, _ = encode(v, qs[i:i + chunk])
        preds.extend(decode(v, run_tape(e, starts, stages, v.n)))
    return preds


def truth(qs) -> list:
    return [q.answer if q.answer is not None else UNKNOWN for q in qs]


def accuracy(qs, preds) -> float:
    return sum(p == t for p, t in zip(preds, truth(qs))) / len(qs)


# ----------------------------------------------------------------- evaluation suites
def eval_world(model: Reasoner, v: Village, m: Tensor, tag: str, seed: int, per_set: int) -> dict:
    out: dict = {}
    shallow: list = []
    for hops in (1, 2, 3):
        qs = sample_set(v, f"eval/{tag}/hop{hops}", seed, per_set, (hops,), "resolvable")
        out[f"hop{hops}"] = accuracy(qs, predict(model, v, m, qs))
        shallow.extend(qs)
    out["hop1to3"] = accuracy(shallow, predict(model, v, m, shallow))
    for d in DEPTHS:
        qs = sample_set(v, f"eval/{tag}/depth{d}", seed, per_set, (d,), "resolvable")
        out[f"depth{d}"] = accuracy(qs, predict(model, v, m, qs))
    return out


def eval_honesty(model: Reasoner, v: Village, m: Tensor, tag: str, seed: int, count: int) -> dict:
    qs = sample_set(v, f"eval/{tag}/missing", seed, count, (1, 2, 3, 4), "missing")
    preds = predict(model, v, m, qs)
    unknown = sum(p == UNKNOWN for p in preds) / len(qs)
    return {"count": len(qs), "unknown_rate": unknown, "confident_wrong": sum(p != UNKNOWN for p in preds)}


def base_probe(v: Village, seed: int, per_set: int) -> list:
    """The fixed base-relation question set used for the R7 'unchanged' check."""
    qs: list = []
    for hops in (1, 2, 3):
        qs.extend(sample_set(v, f"eval/fresh60/hop{hops}", seed, per_set, (hops,), "resolvable"))
    return qs


# ----------------------------------------------------------------- stage: base
def stage_base(seed: int, out: Path, smoke: bool) -> None:
    train_v = make_village("train60", seed, TRAIN_N, "T")
    fresh_v = make_village("fresh60", seed, TRAIN_N, "F")
    big_v = make_village("big200", seed, BIG_N, "B")
    assert not (set(train_v.names) & set(fresh_v.names)), "train/fresh names overlap"
    assert not (set(train_v.names) & set(big_v.names)), "train/big names overlap"

    m_train = notebook_matrices(train_v)
    torch.manual_seed(int.from_bytes(hashlib.sha256(f"reasoner44/init/{seed}".encode()).digest()[:4], "big"))
    model = Reasoner()
    nn.init.normal_(model.token_logits, std=INIT_STD)                 # random init: seeds start differently
    opt = torch.optim.Adam([model.token_logits], lr=BASE_LR)

    updates = 200 if smoke else BASE_UPDATES
    per_set = 40 if smoke else EVAL_PER_SET
    t0 = time.time()
    loss = torch.tensor(0.0)
    for step in range(updates):
        rng = make_rng(f"base/batch/{step}", seed)
        qs = [sample_question(train_v, rng, rng.randint(1, 3), "any") for _ in range(BASE_BATCH)]
        starts, stages, targets = encode(train_v, qs)
        x = run_tape(model.effective(m_train), starts, stages, train_v.n)
        loss = -x.clamp_min(1e-12).log().gather(1, targets[:, None]).mean()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
    seconds = round(time.time() - t0, 1)

    m_fresh, m_big = notebook_matrices(fresh_v), notebook_matrices(big_v)
    routing = model.token_logits.detach().softmax(-1)
    report = {
        "seed": seed, "smoke": smoke, "updates": updates, "train_seconds": seconds,
        "final_loss": float(loss.detach()),
        "trainable_parameters_base": model.token_logits.numel(),
        "trainable_parameters_per_word": model.words[0].numel(),
        "fresh60": eval_world(model, fresh_v, m_fresh, "fresh60", seed, per_set),
        "big200": eval_world(model, big_v, m_big, "big200", seed, per_set),
        "honesty_fresh60": eval_honesty(model, fresh_v, m_fresh, "fresh60", seed,
                                        40 if smoke else HONESTY_SET),
        "honesty_big200": eval_honesty(model, big_v, m_big, "big200", seed,
                                       40 if smoke else HONESTY_SET),
        "routed_skill": {RELATIONS[t]: RELATIONS[int(routing[t].argmax())] for t in range(R)},
        "routing_weight": {RELATIONS[t]: round(float(routing[t].max()), 6) for t in range(R)},
        "routing_is_identity": all(int(routing[t].argmax()) == t for t in range(R)),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / f"base-seed{seed}.json").write_text(json.dumps(report, indent=1))
    torch.save({"seed": seed, "state": model.state_dict()}, out / f"base-seed{seed}.pt")
    print(json.dumps({"stage": "base", "seed": seed, "seconds": seconds,
                      "fresh_hop1to3": round(report["fresh60"]["hop1to3"], 4),
                      "fresh_depth10": round(report["fresh60"]["depth10"], 4),
                      "big_depth10": round(report["big200"]["depth10"], 4),
                      "unknown_rate": round(report["honesty_fresh60"]["unknown_rate"], 4)}))


# ----------------------------------------------------------------- stage: sleep
def episode_pool(v: Village, w: int) -> list:
    chain = WORD_CHAINS[w]
    return [x for x in v.names if walk(v, x, chain) is not None]


def make_episodes(v: Village, w: int, count: int, seed: int, mode: str) -> tuple:
    """Raw episodes (person, new_word, answer).  A teacher states facts they know."""
    rng = make_rng(f"episodes/{w}/{mode}/{count}", seed)
    pool = episode_pool(v, w)
    people = list(pool)
    rng.shuffle(people)
    if count <= len(people):
        chosen = people[:count]
    else:
        chosen = people + [pool[rng.randrange(len(pool))] for _ in range(count - len(people))]
    eps = [Question(x, (R + w,), walk(v, x, WORD_CHAINS[w])) for x in chosen]
    if mode == "random":
        for e in eps:
            e.answer = v.names[rng.randrange(v.n)]
    elif mode == "noisy":
        for i in rng.sample(range(len(eps)), min(2, len(eps))):
            bad = v.names[rng.randrange(v.n)]
            while bad == eps[i].answer:
                bad = v.names[rng.randrange(v.n)]
            eps[i].answer = bad
    return eps, len(set(chosen))


def fit_word(base_state: dict, w: int, eps, v: Village, m: Tensor, updates: int,
             seed: int, tag: str, snapshots=()) -> tuple:
    model = Reasoner()
    model.load_state_dict(base_state)
    model.requires_grad_(False)
    model.words[w].requires_grad_(True)
    opt = torch.optim.Adam([model.words[w]], lr=SLEEP_LR)
    saved = {0: model.words[w].detach().clone()} if 0 in snapshots else {}
    starts, stages, targets = encode(v, eps)
    batch = min(SLEEP_BATCH, len(eps))
    for step in range(updates):
        rng = make_rng(f"sleep/{tag}/{step}", seed)
        pick = torch.tensor([rng.randrange(len(eps)) for _ in range(batch)], dtype=torch.long)
        x = run_tape(model.effective(m), starts[pick], stages[pick], v.n)
        loss = -x.clamp_min(1e-12).log().gather(1, targets[pick][:, None]).mean()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_([model.words[w]], 1.0)
        opt.step()
        if step + 1 in snapshots:
            saved[step + 1] = model.words[w].detach().clone()
    return model, saved


@torch.inference_mode()
def word_nll(model: Reasoner, v: Village, m: Tensor, eps) -> float:
    starts, stages, targets = encode(v, eps)
    x = run_tape(model.effective(m), starts, stages, v.n)
    return float(-x.clamp_min(1e-12).log().gather(1, targets[:, None]).mean())


def sleep_word(base_state: dict, w: int, eps, v: Village, m: Tensor, seed: int, mode: str,
               before: list, probe_qs: list, fresh_v: Village, m_fresh: Tensor,
               fresh_qs: list, out: Path) -> dict:
    t0 = time.time()
    people = sorted({e.start for e in eps})
    make_rng(f"folds/{w}/{mode}", seed).shuffle(people)
    fold_of = {p: i % FOLDS for i, p in enumerate(people)}
    oof = {t: {} for t in CHECKPOINTS}
    oof_nll = {t: [] for t in CHECKPOINTS}
    for f in range(FOLDS):
        held = [e for e in eps if fold_of[e.start] == f]
        train = [e for e in eps if fold_of[e.start] != f]
        if not held or not train:
            continue
        _, saved = fit_word(base_state, w, train, v, m, max(CHECKPOINTS), seed,
                            f"{mode}/w{w}/fold{f}", CHECKPOINTS)
        probe = Reasoner()
        probe.load_state_dict(base_state)
        held_idx = [i for i, e in enumerate(eps) if fold_of[e.start] == f]
        for t in CHECKPOINTS:
            probe.words[w].data.copy_(saved[t])
            for i, p in zip(held_idx, predict(probe, v, m, held)):
                oof[t][i] = p
            oof_nll[t].append(word_nll(probe, v, m, held) * len(held))
    want = truth(eps)
    table = {t: {"match": sum(oof[t].get(i) == want[i] for i in range(len(eps))) / len(eps),
                 "nll": sum(oof_nll[t]) / len(eps)} for t in CHECKPOINTS}
    rec: dict = {"word": WORD_NAMES[w], "mode": mode, "episodes": len(eps),
                 "distinct_people": len({e.start for e in eps}),
                 "cv_table": {str(t): {k: round(val, 5) for k, val in row.items()} for t, row in table.items()}}
    eligible = [t for t in CHECKPOINTS if table[t]["match"] >= CV_FLOOR]
    if not eligible:
        rec.update(installed=False, reason=f"no checkpoint reached {CV_FLOOR} cross-validated exact match",
                   seconds=round(time.time() - t0, 1))
        return rec
    best = min(table[t]["nll"] for t in eligible)
    chosen = min(t for t in eligible if table[t]["nll"] <= best + 1e-9)
    model, _ = fit_word(base_state, w, eps, v, m, chosen, seed, f"{mode}/w{w}/refit")
    refit_pred = predict(model, v, m, eps)
    agreement = sum(refit_pred[i] == oof[chosen][i] for i in range(len(eps))) / len(eps)
    after = predict(model, fresh_v, m_fresh, probe_qs)
    base_unchanged = after == before
    path = out / f"word-seed{seed}-{mode}-{WORD_NAMES[w]}-ep{len(eps)}.pt"
    torch.save(model.state_dict(), path)
    reloaded = Reasoner()
    reloaded.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
    fresh_pred = predict(model, fresh_v, m_fresh, fresh_qs)
    reload_identical = predict(reloaded.eval(), fresh_v, m_fresh, fresh_qs) == fresh_pred
    installed = bool(agreement >= AGREEMENT_FLOOR and base_unchanged and reload_identical)
    p = model.words[w].detach().softmax(-1)
    rec.update(chosen_updates=chosen, refit_agreement=agreement, seen_accuracy=accuracy(eps, refit_pred),
               base_unchanged=base_unchanged, reload_identical=reload_identical, installed=installed,
               fresh_accuracy=accuracy(fresh_qs, fresh_pred),
               routing=[[round(val, 4) for val in row] for row in p.tolist()],
               routing_names=("keep",) + RELATIONS,
               routed_chain=[(("keep",) + RELATIONS)[int(row.argmax())] for row in p],
               seconds=round(time.time() - t0, 1))
    if installed:
        rec["installed_logits"] = model.words[w].detach().tolist()
    return rec


def stage_sleep(seed: int, episodes_n: int, out: Path) -> None:
    train_v = make_village("train60", seed, TRAIN_N, "T")
    fresh_v = make_village("fresh60", seed, TRAIN_N, "F")
    big_v = make_village("big200", seed, BIG_N, "B")
    m_train, m_fresh, m_big = (notebook_matrices(x) for x in (train_v, fresh_v, big_v))
    base_state = torch.load(out / f"base-seed{seed}.pt", map_location="cpu", weights_only=True)["state"]
    base_model = Reasoner()
    base_model.load_state_dict(base_state)

    probe_qs = base_probe(fresh_v, seed, EVAL_PER_SET)
    before = predict(base_model, fresh_v, m_fresh, probe_qs)
    before_acc = accuracy(probe_qs, before)

    report: dict = {"seed": seed, "episodes": episodes_n, "base_probe_accuracy_before": before_acc, "words": {}}
    installed_logits: dict = {}
    t0 = time.time()
    for w in range(N_WORDS):
        fresh_qs = sample_set(fresh_v, f"eval/word{w}/fresh60", seed, EVAL_PER_SET, (1,), "resolvable",
                              vocab=(R + w,))
        big_qs = sample_set(big_v, f"eval/word{w}/big200", seed, EVAL_PER_SET, (1,), "resolvable",
                            vocab=(R + w,))
        eps, _ = make_episodes(train_v, w, episodes_n, seed, "true")
        rec = sleep_word(base_state, w, eps, train_v, m_train, seed, "true", before, probe_qs,
                         fresh_v, m_fresh, fresh_qs, out)
        if rec.get("installed"):
            installed_logits[w] = torch.tensor(rec.pop("installed_logits"))
            probe = Reasoner()
            probe.load_state_dict(base_state)
            probe.words[w].data.copy_(installed_logits[w])
            rec["big200_accuracy"] = accuracy(big_qs, predict(probe, big_v, m_big, big_qs))
        report["words"][WORD_NAMES[w]] = {"true": rec}
        if episodes_n == 20:
            for mode in ("random", "noisy"):
                eps_c, _ = make_episodes(train_v, w, episodes_n, seed, mode)
                report["words"][WORD_NAMES[w]][mode] = sleep_word(
                    base_state, w, eps_c, train_v, m_train, seed, mode, before, probe_qs,
                    fresh_v, m_fresh, fresh_qs, out)

    # ---- all installed words together: reuse inside longer questions
    combo = Reasoner()
    combo.load_state_dict(base_state)
    for w, logits in installed_logits.items():
        combo.words[w].data.copy_(logits)
    report["all_words_installed"] = len(installed_logits) == N_WORDS
    reuse_qs = sample_set(fresh_v, "eval/reuse/fresh60", seed, EVAL_PER_SET, (2, 3, 4), "resolvable",
                          vocab=tuple(range(R)), force_words=tuple(range(N_WORDS)))
    reuse_big = sample_set(big_v, "eval/reuse/big200", seed, EVAL_PER_SET, (2, 3, 4), "resolvable",
                           vocab=tuple(range(R)), force_words=tuple(range(N_WORDS)))
    report["reuse_fresh60"] = accuracy(reuse_qs, predict(combo, fresh_v, m_fresh, reuse_qs))
    report["reuse_big200"] = accuracy(reuse_big, predict(combo, big_v, m_big, reuse_big))
    after_all = predict(combo, fresh_v, m_fresh, probe_qs)
    report["base_probe_unchanged_after_all"] = after_all == before
    report["base_probe_accuracy_after_all"] = accuracy(probe_qs, after_all)
    combo_path = out / f"combined-seed{seed}-ep{episodes_n}.pt"
    torch.save(combo.state_dict(), combo_path)
    reloaded = Reasoner()
    reloaded.load_state_dict(torch.load(combo_path, map_location="cpu", weights_only=True))
    report["combined_reload_identical"] = predict(reloaded.eval(), fresh_v, m_fresh, reuse_qs) == \
        predict(combo, fresh_v, m_fresh, reuse_qs)
    report["sleep_seconds"] = round(time.time() - t0, 1)
    report["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (out / f"sleep-seed{seed}-ep{episodes_n}.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({"stage": "sleep", "seed": seed, "episodes": episodes_n,
                      "installed": {w: report["words"][w]["true"]["installed"] for w in WORD_NAMES},
                      "fresh": {w: round(report["words"][w]["true"].get("fresh_accuracy", -1), 4) for w in WORD_NAMES},
                      "reuse_fresh60": round(report["reuse_fresh60"], 4),
                      "seconds": report["sleep_seconds"]}))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--stage", choices=("base", "sleep"), required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--episodes", type=int, default=20)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--smoke", action="store_true", help="base only: 200 updates, small eval sets, no claim")
    a = p.parse_args()
    torch.set_num_threads(1)
    if a.stage == "base":
        stage_base(a.seed, a.out, a.smoke)
    else:
        stage_sleep(a.seed, a.episodes, a.out)


if __name__ == "__main__":
    main()
