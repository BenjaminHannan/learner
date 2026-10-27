#!/usr/bin/env python3
"""Experiment 52: LIVE SLEEP -- the proven Experiment-46 install recipe fed by episodes
MINED FROM REAL CONVERSATION LOGS (synthetic 200-turn logs generated from the notebook
contract, with small talk, corrections, ambiguity and unanswered turns).

WHAT IS NEW vs EXPERIMENT 46
  Exp 46 was handed perfect toy episodes: 20 (person, word, answer) triples built straight
  from the village.  Here sleep must FIND the episodes itself in a noisy conversation log,
  decide which relation chains are worth installing by FREQUENCY (never by model choice),
  run the SAME install recipe, and prove afterwards that nothing old moved: old skills
  bit-identical, notebook hash chain intact, taught facts unchanged, and a 60-start audit
  on every installed word.  A written sleep report row (source tag ``sleep-derived``) is
  appended to the notebook after every sleep.

EPISODE MINER -- pure rules, no model, no judgement (documented, in order):
  1. STATUS RULE.  Only an ``ask`` turn whose RECORDED contract status is OK can ever
     become an episode.  AMBIGUOUS, MISSING_FACT, BROKEN_CHAIN, UNKNOWN_ENTITY and
     clarifications are never episodes.
  2. PAIR RULE.  An ask becomes an episode only if the IMMEDIATELY next turn is a
     ``confirm`` carrying the same pair id.  The episode's answer is the CONFIRMED value
     (what the teacher said), not the system's answer -- a teacher may confirm wrongly.
  3. SUPERSEDE RULE.  A later ``correct`` turn for the same (start, chain) replaces the
     standing episode; only the latest stands.  The log keeps every turn (append-only);
     the miner simply stops using the old standing value.
  4. FALL-THROUGH RULE.  Anything else between ask and confirm (small talk, a teach, a
     stray confirm, another ask) breaks the pair; the ask stays unconfirmed and is never
     an episode.
  5. ANSWER-IN-VOCAB RULE.  A standing episode whose confirmed answer is not a person in
     the village is dropped (it cannot be a training target).

CANDIDATE-CHAIN COUNTER -- frequency rule, again no model, no choice:
  A chain (tuple of base relations) is a candidate word iff (a) its length is >= 2
  (length 1 is already a base skill) and (b) it has >= FREQ_MIN (=20) standing confirmed
  episodes after all supersessions.  Candidates are visited in sorted order.  A candidate
  whose chain matches no word slot, or is longer than the slot's stage count, is REFUSED
  and recorded -- never forced.

INSTALL RECIPE -- Experiment 46, unchanged, imported read-only:
  ``import fable_hardgate46`` activates it: robust loss -log((1-eps)p + eps/N) with
  eps=0.10, and the router hardened to its argmax chain (+/-30 logits) after EVERY fold
  fit and the refit.  Gate unchanged: 4-fold CV OOF >= 0.80, refit agreement >= 0.90,
  base answers unchanged, weights-only reload identical.  Every installed word then gets
  the 60-start audit (evaluation only).  Wrong install = Exp 46's definition:
  installed AND (audit disagreements > 0 OR fresh accuracy < 0.99).
  Every night trains from the FROZEN original wake snapshot (base state), exactly as
  Exp 46 did; the live state only accumulates installed words for auditing.

POST-SLEEP AUDIT -- all must hold or ``accepted`` is False:
  * old skills BIT-IDENTICAL: in every saved install, every parameter except the target
    word slot equals the frozen snapshot byte-for-byte; in the live state the token
    routing table still equals the original base; the 900-question base probe answers
    answer-for-answer unchanged; words installed on earlier nights are untouched unless
    they are targets again tonight.
  * notebook hash chain: the pre-sleep events.jsonl bytes remain an exact PREFIX after
    the sleep report row is appended, and a fresh reload of the log verifies the chain.
  * taught facts: every taught fact active before sleep is active after with the same
    value; no taught row superseded, retracted or added (sleep cannot write ``taught``).
  * 60-start audit per installed word: 0 disagreements with the true chain.

SLEEP REPORT ROW: one FACT, actor=sleep, source=sleep-derived, relation=sleep_report,
appended to the notebook after the audits (a contract write right of sleep).

USAGE
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B \\
      fable_livesleep52.py --selftest
  ... fable_livesleep52.py --seed 5201 --out artifacts/fable-livesleep52-20260921/runs
  ... fable_livesleep52.py --score --out artifacts/fable-livesleep52-20260921/runs
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import torch

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C               # noqa: E402
import fable_reasoner44 as R44                    # noqa: E402
import fable_hardgate46 as H                      # noqa: E402  (activates Exp 46 on import)

assert H.HARD_LOGIT == 30.0
assert H.N.ARM == "robust"

# ----------------------------------------------------------------- constants
TURNS = 200
EPISODES_PER_CHAIN = 20
FREQ_MIN = 20                    # frequency rule: standing confirmed episodes needed
MIN_CHAIN_LEN = 2                # length 1 is already a base skill
CORRECTIONS_PER_CHAIN = 2        # supersede events exercised per chain per log
DECOY_CHAIN = ("mother", "father")   # confirmed only DECOY_CONFIRMED times -> refused
DECOY_CONFIRMED = 8
WRONG_LEVELS = (0, 2, 4)         # corrupted STANDING teachings of 20, per chain
REGISTERED_SEEDS = (5201, 5202, 5203)
DEV_SEED = 9999
SHARED_ALIAS = "T_buddy"
SLEEP_RELATION = "sleep_report"
SLEEP_ENTITY_NAME = "SLEEP"
SMALLTALK = (
    "hello there", "thanks", "ok", "got it", "nice weather", "what did you say?",
    "hmm", "one moment", "please go on", "that is funny", "see you", "really?",
    "wow", "interesting", "hold on", "say that again", "great", "noted", "cool",
    "anyway", "right", "sure", "ok done", "perfect", "hm", "wait", "yes yes", "no no",
)
MISSING_CHAINS = (("mother",), ("father",), ("mother", "father"), ("spouse", "boss"))
SCRATCH = Path("/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/opencode")


# ----------------------------------------------------------------- the miner
@dataclass(frozen=True)
class Episode:
    start: str
    chain: tuple
    answer: str
    origin: str            # "pair" (ask+confirm) | "correct" (superseding correction)
    origin_status: str     # recorded contract status of the originating ask / "correct"
    turn: int


@dataclass
class MineResult:
    standing: dict = field(default_factory=dict)      # (start, chain) -> Episode
    chain_counts: Counter = field(default_factory=Counter)
    candidates: list = field(default_factory=list)     # sorted list of chain tuples
    stats: dict = field(default_factory=dict)


def mine_episodes(turns, vocab=None) -> MineResult:
    """Rules 1-5 above, applied left to right over the log.  Pure: same log -> same mine."""
    standing: dict = {}
    stats: Counter = Counter()
    kind_counts = Counter(t.get("kind") for t in turns)
    supersessions = 0
    dropped_answer = 0
    prev_ask: dict | None = None
    for raw in turns:
        t = dict(raw)
        kind = t.get("kind")
        if kind == "ask":
            stats["asks"] += 1
            if t.get("status") != C.OK:                       # rule 1
                stats["ask_not_ok"] += 1
                prev_ask = None
            else:
                stats["ask_ok"] += 1
                prev_ask = t
        elif kind == "confirm":
            stats["confirms"] += 1
            if prev_ask is not None and t.get("pair_id") == prev_ask.get("pair_id"):   # rule 2
                key = (prev_ask["start"], tuple(prev_ask["chain"]))
                standing[key] = Episode(prev_ask["start"], tuple(prev_ask["chain"]),
                                        str(t.get("value", "")), "pair",
                                        prev_ask.get("status", ""), int(t.get("turn", -1)))
                stats["paired"] += 1
            else:
                stats["confirm_unmatched"] += 1
            prev_ask = None
        elif kind == "correct":
            stats["corrections"] += 1
            key = (t.get("start", ""), tuple(t.get("chain", ())))
            if key in standing:                               # rule 3
                supersessions += 1
            standing[key] = Episode(str(t.get("start", "")), tuple(t.get("chain", ())),
                                    str(t.get("value", "")), "correct", "correct",
                                    int(t.get("turn", -1)))
            prev_ask = None
        else:                                                  # rule 4
            stats[f"break_{kind}"] += 1
            prev_ask = None
    if vocab is not None:                                      # rule 5
        kept = {k: ep for k, ep in standing.items() if ep.answer in vocab}
        dropped_answer = len(standing) - len(kept)
        standing = kept
    counts = Counter(ep.chain for ep in standing.values())
    candidates = sorted(ch for ch, n in counts.items()
                        if len(ch) >= MIN_CHAIN_LEN and n >= FREQ_MIN)
    stats_out = {
        "turns": len(turns),
        "kinds": dict(sorted(kind_counts.items())),
        "superseded": supersessions,
        "dropped_answer_not_in_vocab": dropped_answer,
        "standing": len(standing),
        **{k: int(v) for k, v in stats.items()},
    }
    return MineResult(standing=standing, chain_counts=counts,
                      candidates=candidates, stats=stats_out)


# ----------------------------------------------------------------- the log generator
def _other_name(v, true: str, rng) -> str:
    bad = v.names[rng.randrange(v.n)]
    while bad == true:
        bad = v.names[rng.randrange(v.n)]
    return bad


def generate_log(v, nb: C.Notebook, eids: dict, seed: int, wrong: int) -> list:
    """A 200-turn conversation log, generated FROM THE CONTRACT (every ask status and
    every teach status is whatever the real notebook returned).  Pure + deterministic
    given (seed, wrong).  `wrong` = corrupted STANDING teachings of 20 per chain."""
    assert wrong in WRONG_LEVELS
    rng = R44.make_rng(f"livesleep52/log/{wrong}", seed)
    main_units: list[list[dict]] = []
    corrections: list[tuple[str, dict]] = []      # (pair_id, turn) -- inserted later

    for w, chain in enumerate(R44.WORD_CHAINS):
        pool = list(R44.episode_pool(v, w))
        rng.shuffle(pool)
        chosen = pool[:EPISODES_PER_CHAIN]
        assert len(chosen) == EPISODES_PER_CHAIN, f"pool too small for word {w}"
        order = list(range(EPISODES_PER_CHAIN))
        rng.shuffle(order)
        wrong_slots = set(order[:wrong])
        corr_slots = set(order[wrong:wrong + CORRECTIONS_PER_CHAIN])
        for slot, person in enumerate(chosen):
            asked = nb.ask(person, list(chain))
            true = R44.walk(v, person, chain)
            assert asked.status == C.OK and asked.detail.get("answer") == true, \
                f"ask not OK for pool person {person} {chain}"
            pair = f"w{w}s{slot}"
            confirm_value = true
            if slot in wrong_slots or slot in corr_slots:
                confirm_value = _other_name(v, true, rng)     # teacher may confirm wrongly
            main_units.append([
                {"kind": "ask", "pair_id": pair, "start": person, "chain": list(chain),
                 "status": asked.status, "answer": asked.detail["answer"]},
                {"kind": "confirm", "pair_id": pair, "value": confirm_value},
            ])
            if slot in corr_slots:
                corrections.append((pair, {"kind": "correct", "start": person,
                                           "chain": list(chain), "value": true}))

    decoy_pool = [x for x in v.names if R44.walk(v, x, DECOY_CHAIN) is not None]
    rng.shuffle(decoy_pool)
    assert len(decoy_pool) >= DECOY_CONFIRMED
    for i, person in enumerate(decoy_pool[:DECOY_CONFIRMED]):
        asked = nb.ask(person, list(DECOY_CHAIN))
        assert asked.status == C.OK
        pair = f"decoy{i}"
        main_units.append([
            {"kind": "ask", "pair_id": pair, "start": person, "chain": list(DECOY_CHAIN),
             "status": asked.status, "answer": asked.detail["answer"]},
            {"kind": "confirm", "pair_id": pair, "value": asked.detail["answer"]},
        ])

    for i in range(8):                                            # ambiguity: never episodes
        asked = nb.ask(SHARED_ALIAS, ["mother"])
        assert asked.status == C.AMBIGUOUS, asked.status
        main_units.append([{"kind": "ask", "pair_id": f"amb{i}", "start": SHARED_ALIAS,
                            "chain": ["mother"], "status": asked.status, "answer": None}])

    missing_found = 0
    for person in v.names:                                       # unanswered: never episodes
        for chain in MISSING_CHAINS:
            if missing_found >= 8:
                break
            asked = nb.ask(person, list(chain))
            if asked.status in (C.MISSING_FACT, C.BROKEN_CHAIN):
                main_units.append([{"kind": "ask", "pair_id": f"miss{missing_found}",
                                    "start": person, "chain": list(chain),
                                    "status": asked.status, "answer": None}])
                missing_found += 1
        if missing_found >= 8:
            break
    assert missing_found == 8, f"only {missing_found} unanswered asks found"

    for i in range(4):                                            # OK ask, never confirmed
        person = next(x for x in v.names if nb.ask(x, ["mother"]).status == C.OK)
        asked = nb.ask(person, ["mother"])
        main_units.append([{"kind": "ask", "pair_id": f"unconf{i}", "start": person,
                            "chain": ["mother"], "status": asked.status,
                            "answer": asked.detail.get("answer")}])

    facts = sorted(v.facts)
    rng.shuffle(facts)
    for i in range(6):                                            # teach noise: no episodes
        x, rel = facts[i]
        if i % 2 == 0:
            res = nb.assert_fact(f"nb52-dup{i}", "listening", "taught", eids[x], rel,
                                 {"entity": eids[v.facts[(x, rel)]]})
        else:
            other = next(n for n in v.names if n != v.facts[(x, rel)])
            res = nb.assert_fact(f"nb52-conf{i}", "listening", "taught", eids[x], rel,
                                 {"entity": eids[other]})
        assert res.status in (C.DUPLICATE_OK, C.CONFLICT), res.status
        main_units.append([{"kind": "teach", "status": res.status, "relation": rel}])

    for i in range(4):                                            # stray confirms: ignored
        main_units.append([{"kind": "confirm", "pair_id": f"stray{i}",
                            "value": v.names[rng.randrange(v.n)]}])

    for text in SMALLTALK[:28]:
        main_units.append([{"kind": "smalltalk", "text": text}])

    rng.shuffle(main_units)
    flat: list[dict] = [t for unit in main_units for t in unit]
    rng.shuffle(corrections)
    for pair_id, corr in corrections:                             # rule 3 must fire
        idx = next(i for i, t in enumerate(flat)
                   if t.get("kind") == "confirm" and t.get("pair_id") == pair_id)
        # insert only at unit boundaries (right after some confirm, or at the end) so
        # no OTHER ask/confirm pair is ever split
        boundaries = [i + 1 for i, t in enumerate(flat) if t.get("kind") == "confirm"]
        boundaries.append(len(flat))
        choices = [b for b in boundaries if b > idx]
        flat.insert(choices[rng.randrange(len(choices))], corr)
    assert len(flat) == TURNS, len(flat)
    for i, t in enumerate(flat):
        t["turn"] = i
    return flat


# ----------------------------------------------------------------- notebook builder
def build_notebook(v, root: Path):
    """A real contract notebook over the training village: every village fact taught by
    LISTENING, one shared alias (two people -> AMBIGUOUS), one SLEEP entity for reports."""
    if root.exists():
        for stale in root.iterdir():
            if stale.is_file():
                stale.unlink()
    nb = C.Notebook(root)
    for rel in R44.RELATIONS:
        nb.declare_relation(f"nb52-rel-{rel}", rel, True)
    eids: dict = {}
    for i, name in enumerate(v.names):
        made = nb.new_entity(f"nb52-ent-{i}", name)
        assert made.status == C.SAVED
        eids[name] = made.detail["entity_id"]
    n_taught = 0
    for i, ((x, rel), y) in enumerate(sorted(v.facts.items())):
        res = nb.assert_fact(f"nb52-fact-{i}", "listening", "taught", eids[x], rel,
                             {"entity": eids[y]})
        assert res.status == C.SAVED, res.status
        n_taught += 1
    pair = sorted(v.names)[:2]
    nb.add_alias("nb52-alias-0", eids[pair[0]], SHARED_ALIAS)
    nb.add_alias("nb52-alias-1", eids[pair[1]], SHARED_ALIAS)
    sleep_eid = nb.new_entity("nb52-ent-sleep", SLEEP_ENTITY_NAME).detail["entity_id"]
    assert nb.resolve(SHARED_ALIAS).status == C.AMBIGUOUS
    return nb, eids, sleep_eid, n_taught


def taught_snapshot(nb: C.Notebook) -> dict:
    """Every taught fact: fact_id -> (subject, relation, value, active).  Pure read."""
    out = {}
    for fid, fact in nb.facts.items():
        if fact["source"] != "taught":
            continue
        out[fid] = (fact["subject"], fact["relation"], json.dumps(fact["value"], sort_keys=True),
                    nb.active(fid))
    return out


# ----------------------------------------------------------------- the Sleeper
class LiveSleeper:
    """Implements fable_agent_loop.Sleeper: sleep(experience, notebook) -> {'accepted': bool, ...}.
    ``experience`` is the full turn log; called only when the log is full.  The model never
    proposes rules and never chooses what to store: mining is rules, install is arithmetic."""

    def __init__(self, *, base_state, train_v, m_train, fresh_v, m_fresh,
                 probe_qs, before, fresh_qs_by_word, seed, out, sleep_eid,
                 night: int = 0) -> None:
        self.base_state = {k: v.detach().clone() for k, v in base_state.items()}
        self.live_state = {k: v.detach().clone() for k, v in base_state.items()}
        self.train_v, self.m_train = train_v, m_train
        self.fresh_v, self.m_fresh = fresh_v, m_fresh
        self.probe_qs, self.before = probe_qs, before
        self.fresh_qs_by_word = fresh_qs_by_word
        self.seed, self.out, self.sleep_eid = int(seed), Path(out), sleep_eid
        self.night = int(night)
        self.nights_served = 0

    # helpers ---------------------------------------------------------------
    def _slot_for(self, chain: tuple) -> int | None:
        if len(chain) > R44.STAGES:
            return None
        try:
            return R44.WORD_CHAINS.index(chain)
        except ValueError:
            return None

    def _episodes_for(self, w: int, mined: MineResult) -> list:
        eps = []
        for (start, chain), ep in mined.standing.items():
            if chain == R44.WORD_CHAINS[w] and ep.answer in self.train_v.idx:
                eps.append(R44.Question(start, (R44.R + w,), ep.answer))
        return eps

    # the protocol ----------------------------------------------------------
    def sleep(self, experience: list, notebook) -> dict:
        t0 = time.time()
        mined = mine_episodes(experience, vocab=set(self.train_v.names))
        bytes_before = notebook.path.read_bytes()
        n_events_before = len(notebook.events)
        taught_before = taught_snapshot(notebook)

        installs: list = []
        installed_keys: set = set()
        for chain in mined.candidates:
            w = self._slot_for(chain)
            if w is None:
                installs.append({"chain": list(chain), "installed": False,
                                 "reason": "no word slot for this chain (refused)"})
                continue
            eps = self._episodes_for(w, mined)
            mode = f"live-w{self.night}"
            rec = R44.sleep_word(self.base_state, w, eps, self.train_v, self.m_train,
                                 self.seed, mode, self.before, self.probe_qs,
                                 self.fresh_v, self.m_fresh, self.fresh_qs_by_word[w],
                                 self.out)
            rec.pop("installed_logits", None)
            rec["chain"] = list(chain)
            rec["path"] = str(self.out / f"word-seed{self.seed}-{mode}-"
                                       f"{R44.WORD_NAMES[w]}-ep{len(eps)}.pt")
            state = torch.load(rec["path"], map_location="cpu", weights_only=True)
            others_ok = all(torch.equal(state[k], self.base_state[k])
                            for k in self.base_state if k != f"words.{w}")
            rec["old_params_bit_identical"] = bool(others_ok)
            rec = H.audit(rec, w, self.train_v, self.m_train)
            rec["wrong_install"] = bool(rec.get("installed") and (
                rec.get("audit_disagree_of_60", 0) > 0
                or rec.get("fresh_accuracy", 1.0) < 0.99))
            installs.append(rec)
            if rec.get("installed"):
                installed_keys.add(f"words.{w}")
                self.live_state[f"words.{w}"].copy_(state[f"words.{w}"])

        # ---- post-sleep audits -------------------------------------------
        token_ok = torch.equal(self.live_state["token_logits"],
                               self.base_state["token_logits"])
        others_live_ok = all(torch.equal(self.live_state[k], self.base_state[k])
                             for k in self.base_state if k not in installed_keys)
        probe_model = R44.Reasoner()
        probe_model.load_state_dict(self.live_state)
        probe_after = R44.predict(probe_model, self.fresh_v, self.m_fresh, self.probe_qs)
        probe_ok = probe_after == self.before

        bytes_mid = notebook.path.read_bytes()
        prefix_before_write = bytes_mid[:len(bytes_before)] == bytes_before

        summary = {
            "seed": self.seed, "night": self.night,
            "log_turns": len(experience),
            "candidates": [list(c) for c in mined.candidates],
            "installs": [{"chain": r.get("chain"), "word": r.get("word"),
                          "installed": bool(r.get("installed")),
                          "fresh_accuracy": r.get("fresh_accuracy"),
                          "audit_disagree_of_60": r.get("audit_disagree_of_60"),
                          "wrong_install": bool(r.get("wrong_install"))}
                         for r in installs],
            "seconds": round(time.time() - t0, 3),
        }
        report = notebook.assert_fact(
            f"nb52-sleep-{self.seed}-w{self.night}", "sleep", "sleep-derived",
            self.sleep_eid, SLEEP_RELATION, {"literal": json.dumps(summary, sort_keys=True)},
            raw="sleep report row")
        report_ok = report.status in (C.SAVED, C.DUPLICATE_OK)
        bytes_after = notebook.path.read_bytes()
        prefix_ok = bytes_after[:len(bytes_before)] == bytes_before
        taught_after = taught_snapshot(notebook)
        taught_ok = taught_after == taught_before
        chain_ok = False
        try:
            reloaded = C.Notebook(notebook.root)
            chain_ok = (not reloaded.torn_tail
                        and len(reloaded.events) == n_events_before + 1
                        and reloaded.last_sha == notebook.last_sha
                        and taught_snapshot(reloaded) == taught_before)
        except C.LogCorrupt:
            chain_ok = False

        wrong_installs = sum(1 for r in installs if r.get("wrong_install"))
        safety = bool(wrong_installs == 0 and token_ok and others_live_ok and probe_ok
                      and prefix_ok and chain_ok and taught_ok and report_ok
                      and all(r.get("old_params_bit_identical", True) for r in installs))
        audits = {
            "old_skills_bit_identical": bool(token_ok and others_live_ok),
            "base_probe_unchanged": bool(probe_ok),
            "notebook_prefix_unchanged": bool(prefix_ok and prefix_before_write),
            "notebook_chain_valid_after": bool(chain_ok),
            "taught_facts_unchanged": bool(taught_ok),
            "taught_facts": len(taught_before),
            "report_row_source": "sleep-derived" if report_ok else None,
            "wrong_installs": int(wrong_installs),
            "installs_total": len(installs),
            "installs_made": sum(1 for r in installs if r.get("installed")),
        }
        self.nights_served += 1
        return {"accepted": safety, "log_size": len(experience),
                "night": self.night, "candidates": [list(c) for c in mined.candidates],
                "chain_counts": {"/".join(k): int(n) for k, n in mined.chain_counts.items()},
                "mine": mined.stats, "installs": installs, "audits": audits,
                "seconds": round(time.time() - t0, 3), "summary": summary}


# ----------------------------------------------------------------- driver
def prepare_seed(seed: int, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    if not (out / f"base-seed{seed}.pt").exists():
        R44.stage_base(seed, out, False)
    train_v = R44.make_village("train60", seed, R44.TRAIN_N, "T")
    fresh_v = R44.make_village("fresh60", seed, R44.TRAIN_N, "F")
    m_train, m_fresh = R44.notebook_matrices(train_v), R44.notebook_matrices(fresh_v)
    base_state = torch.load(out / f"base-seed{seed}.pt", map_location="cpu",
                            weights_only=True)["state"]
    base_model = R44.Reasoner()
    base_model.load_state_dict(base_state)
    probe_qs = R44.base_probe(fresh_v, seed, R44.EVAL_PER_SET)
    before = R44.predict(base_model, fresh_v, m_fresh, probe_qs)
    fresh_qs = {w: R44.sample_set(fresh_v, f"eval/word{w}/fresh60", seed,
                                  R44.EVAL_PER_SET, (1,), "resolvable",
                                  vocab=(R44.R + w,)) for w in range(R44.N_WORDS)}
    return train_v, fresh_v, m_train, m_fresh, base_state, probe_qs, before, fresh_qs


def standing_wrong(mined: MineResult, v) -> dict:
    """Evaluation only (the sleeper never sees truth): per candidate chain, how many
    standing confirmed answers disagree with the village walk."""
    out = {}
    for chain in mined.candidates:
        eps = [ep for ep in mined.standing.values() if ep.chain == chain]
        out["/".join(chain)] = sum(ep.answer != R44.walk(v, ep.start, chain) for ep in eps)
    return out


def run_seed(seed: int, out: Path) -> dict:
    (train_v, fresh_v, m_train, m_fresh, base_state,
     probe_qs, before, fresh_qs) = prepare_seed(seed, out)
    nb, eids, sleep_eid, n_taught = build_notebook(train_v, out / f"notebook-seed{seed}")
    sleeper = LiveSleeper(base_state=base_state, train_v=train_v, m_train=m_train,
                          fresh_v=fresh_v, m_fresh=m_fresh, probe_qs=probe_qs,
                          before=before, fresh_qs_by_word=fresh_qs, seed=seed,
                          out=out, sleep_eid=sleep_eid, night=0)
    rows = []
    for wrong in WRONG_LEVELS:
        sleeper.night = wrong
        turns = generate_log(train_v, nb, eids, seed, wrong)
        assert len(turns) == TURNS
        outcome = sleeper.sleep(turns, nb)
        mined = mine_episodes(turns, vocab=set(train_v.names))
        swrong = standing_wrong(mined, train_v)
        manipulation_ok = all(n == wrong for n in swrong.values()) and \
            len(mined.candidates) == R44.N_WORDS
        row = {"seed": seed, "wrong": wrong, "turns": len(turns),
               "candidates": [list(c) for c in mined.candidates],
               "chain_counts": {"/".join(k): int(n) for k, n in mined.chain_counts.items()},
               "mine": mined.stats, "standing_wrong": swrong,
               "manipulation_ok": bool(manipulation_ok),
               "installs": outcome["installs"], "audits": outcome["audits"],
               "accepted": outcome["accepted"], "seconds": outcome["seconds"],
               "taught_facts_notebook": n_taught}
        rows.append(row)
        print(json.dumps({"seed": seed, "wrong": wrong, "candidates": len(row["candidates"]),
                          "installs": row["audits"]["installs_made"],
                          "wrong_installs": row["audits"]["wrong_installs"],
                          "accepted": row["accepted"], "seconds": row["seconds"],
                          "manipulation_ok": manipulation_ok}))
    report = {"seed": seed, "rows": rows,
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out / f"livesleep-seed{seed}.json").write_text(json.dumps(report, indent=1))
    return report


# ----------------------------------------------------------------- scoring
def score(out: Path) -> int:
    files = sorted(out.glob("livesleep-seed*.json"))
    if not files:
        print("no livesleep-seed*.json found")
        return 1
    rows = [r for f in files for r in json.loads(f.read_text())["rows"]]
    cells = [c for r in rows for c in r["installs"]]
    installed = [c for c in cells if c.get("installed")]
    wrong = [c for c in cells if c.get("wrong_install")]
    le2 = [c for r in rows if r["wrong"] <= 2 for c in r["installs"]]
    le2_installed = [c for c in le2 if c.get("installed")]
    m3 = all(r["audits"]["taught_facts_unchanged"] and r["audits"]["notebook_prefix_unchanged"]
             and r["audits"]["notebook_chain_valid_after"] for r in rows)
    m4 = max(r["seconds"] for r in rows)
    m5 = all(r["mine"]["turns"] == TURNS and len(r["candidates"]) == R44.N_WORDS
             and r["manipulation_ok"]
             and all(r["chain_counts"]["/".join(c)] == EPISODES_PER_CHAIN
                     for c in map(tuple, r["candidates"]))
             and r["chain_counts"].get("/".join(DECOY_CHAIN)) == DECOY_CONFIRMED
             and "/".join(DECOY_CHAIN) not in {"/".join(c) for c in r["candidates"]}
             and r["mine"]["superseded"] == R44.N_WORDS * CORRECTIONS_PER_CHAIN
             and r["mine"]["standing"] == R44.N_WORDS * EPISODES_PER_CHAIN + DECOY_CONFIRMED
             for r in rows)
    m6 = all(r["audits"]["old_skills_bit_identical"] and r["audits"]["base_probe_unchanged"]
             for r in rows)
    per_seed = {}
    for r in rows:
        s = per_seed.setdefault(r["seed"], {"0": [0, 0], "2": [0, 0], "4": [0, 0]})
        s[str(r["wrong"])][1] += len(r["installs"])
        s[str(r["wrong"])][0] += sum(1 for c in r["installs"] if c.get("installed"))
    print("per-seed installs (made/attempts) by standing-wrong level:")
    for seed, s in sorted(per_seed.items()):
        print(f"  seed {seed}: 0-wrong {s['0'][0]}/{s['0'][1]}   "
              f"2-wrong {s['2'][0]}/{s['2'][1]}   4-wrong {s['4'][0]}/{s['4'][1]}")
    print(f"cells: {len(cells)}   installed: {len(installed)}   wrong installs: {len(wrong)}")
    marks = [
        ("M1 zero wrong installs", len(wrong) == 0, f"{len(wrong)} wrong of {len(cells)}"),
        ("M2 installs >= 15/18 at <=2 wrong", len(le2_installed) >= 15,
         f"{len(le2_installed)}/{len(le2)}"),
        ("M3 taught facts + chain + prefix 100%", m3,
         f"{sum(r['audits']['taught_facts_unchanged'] for r in rows)}/{len(rows)} sleeps"),
        ("M4 each sleep < 600 s", m4 < 600, f"max {m4:.1f} s"),
        ("M5 miner exact 9/9", m5, "all logs" if m5 else "see rows"),
        ("M6 old skills bit-identical 9/9", m6, "all sleeps" if m6 else "see rows"),
    ]
    ok = True
    for name, passed, detail in marks:
        print(f"{'PASS' if passed else 'FAIL'}  {name}  ({detail})")
        ok = ok and passed
    print("SCORE", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ----------------------------------------------------------------- selftest
def selftest(out: Path) -> int:
    """Dev only (throwaway seed 9999).  Miner rules, generator roundtrip, full plumbing."""
    out.mkdir(parents=True, exist_ok=True)
    fails = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if detail else ""))
        if not cond:
            fails.append(name)

    def ask(pair, start, chain, status, answer=None):
        return {"kind": "ask", "pair_id": pair, "start": start, "chain": list(chain),
                "status": status, "answer": answer}

    def conf(pair, value):
        return {"kind": "confirm", "pair_id": pair, "value": value}

    chain = ("mother", "father")
    r = mine_episodes([ask("p", "A", chain, C.OK, "B"), conf("p", "B")])
    check("miner: OK ask + adjacent confirm = 1 episode",
          len(r.standing) == 1 and r.standing[("A", chain)].answer == "B")
    r = mine_episodes([ask("p", "A", chain, C.OK, "B"),
                       {"kind": "smalltalk", "text": "hi"}, conf("p", "B")])
    check("miner: small talk between ask and confirm = 0 episodes", len(r.standing) == 0)
    for bad in (C.AMBIGUOUS, C.MISSING_FACT, C.BROKEN_CHAIN, C.UNKNOWN_ENTITY):
        r = mine_episodes([ask("p", "A", chain, bad, None), conf("p", "B")])
        check(f"miner: status {bad} never an episode", len(r.standing) == 0)
    turns = [ask("p", "A", chain, C.OK, "B"), conf("p", "B"),
             {"kind": "correct", "start": "A", "chain": list(chain), "value": "C"}]
    r = mine_episodes(turns)
    check("miner: correction supersedes", r.standing[("A", chain)].answer == "C"
          and r.stats["superseded"] == 1)
    turns = turns + [{"kind": "correct", "start": "A", "chain": list(chain), "value": "D"}]
    r = mine_episodes(turns)
    check("miner: latest correction wins", r.standing[("A", chain)].answer == "D"
          and r.stats["superseded"] == 2)
    r = mine_episodes([{"kind": "confirm", "pair_id": "stray", "value": "X"}])
    check("miner: stray confirm ignored", len(r.standing) == 0)
    turns = [ask("p", "A", chain, C.OK, "B"),
             {"kind": "correct", "start": "Z", "chain": list(chain), "value": "Q"},
             conf("p", "B")]
    r = mine_episodes(turns)
    check("miner: correction between ask and confirm breaks the pair",
          ("A", chain) not in r.standing and ("Z", chain) in r.standing)
    turns = []
    for i in range(19):
        turns += [ask(f"p{i}", f"S{i}", chain, C.OK, f"A{i}"), conf(f"p{i}", f"A{i}")]
    r = mine_episodes(turns)
    check("frequency: 19 standing < FREQ_MIN -> no candidate", r.candidates == [])
    turns = turns + [ask("p19", "S19", chain, C.OK, "A19"), conf("p19", "A19")]
    r = mine_episodes(turns)
    check("frequency: 20 standing -> candidate", r.candidates == [chain])
    turns = []
    for i in range(20):
        turns += [ask(f"m{i}", f"S{i}", ("mother",), C.OK, f"A{i}"), conf(f"m{i}", f"A{i}")]
    r = mine_episodes(turns)
    check("frequency: length-1 chain never a candidate", r.candidates == [])
    r = mine_episodes([ask("p", "A", chain, C.OK, "B"), conf("p", "B")], vocab={"B"})
    check("miner: answer-in-vocab keeps known answer", len(r.standing) == 1)
    r = mine_episodes([ask("p", "A", chain, C.OK, "B"), conf("p", "B")], vocab={"C"})
    check("miner: answer-in-vocab drops unknown answer",
          len(r.standing) == 0 and r.stats["dropped_answer_not_in_vocab"] == 1)

    # ---- generator roundtrip against the real contract (dev seed 9999) ----
    v = R44.make_village("train60", DEV_SEED, R44.TRAIN_N, "T")
    nb, eids, sleep_eid, n_taught = build_notebook(v, out / "notebook-dev")
    check("notebook: all village facts taught", n_taught == len(v.facts))
    turns = generate_log(v, nb, eids, DEV_SEED, 2)
    check("generator: exactly 200 turns", len(turns) == TURNS, str(len(turns)))
    mined = mine_episodes(turns, vocab=set(v.names))
    check("generator: exactly 3 candidate chains",
          mined.candidates == sorted(R44.WORD_CHAINS), str(mined.candidates))
    check("generator: each candidate has exactly 20 standing",
          all(mined.chain_counts[c] == EPISODES_PER_CHAIN for c in mined.candidates))
    check("generator: decoy chain counted at 8 and refused",
          mined.chain_counts[DECOY_CHAIN] == DECOY_CONFIRMED
          and DECOY_CHAIN not in mined.candidates)
    check("generator: 6 supersessions", mined.stats["superseded"] == 6,
          str(mined.stats["superseded"]))
    check("generator: standing = 60 true + 8 decoy",
          mined.stats["standing"] == 68, str(mined.stats["standing"]))
    swrong = standing_wrong(mined, v)
    check("generator: standing wrong == 2 per chain",
          all(n == 2 for n in swrong.values()), str(swrong))
    check("generator: noise present",
          mined.stats["kinds"].get("smalltalk", 0) >= 20
          and mined.stats["ask_not_ok"] >= 16
          and mined.stats["confirm_unmatched"] >= 4, str(mined.stats["kinds"]))

    # ---- full plumbing: smoke base + one real sleep on the dev log ----
    torch.set_num_threads(1)
    (train_v, fresh_v, m_train, m_fresh, base_state,
     probe_qs, before, fresh_qs) = prepare_seed(DEV_SEED, out)
    sleeper = LiveSleeper(base_state=base_state, train_v=train_v, m_train=m_train,
                          fresh_v=fresh_v, m_fresh=m_fresh, probe_qs=probe_qs,
                          before=before, fresh_qs_by_word=fresh_qs, seed=DEV_SEED,
                          out=out, sleep_eid=sleep_eid, night=0)
    check("protocol: sleep is callable and returns a dict with accepted",
          callable(getattr(sleeper, "sleep", None)))
    ta0 = taught_snapshot(nb)
    outcome = sleeper.sleep(turns, nb)
    check("sleep: returns accepted (bool) + log_size",
          isinstance(outcome.get("accepted"), bool) and outcome.get("log_size") == TURNS)
    check("sleep: audits present",
          all(k in outcome["audits"] for k in
              ("old_skills_bit_identical", "base_probe_unchanged", "notebook_prefix_unchanged",
               "notebook_chain_valid_after", "taught_facts_unchanged", "wrong_installs")))
    check("sleep: report row written with source sleep-derived",
          outcome["audits"]["report_row_source"] == "sleep-derived")
    report_rows = [e for e in nb.events
                   if e.get("kind") == "FACT" and e.get("source") == "sleep-derived"]
    check("sleep: exactly one sleep-derived fact in the notebook", len(report_rows) == 1)
    check("sleep: taught facts unchanged", taught_snapshot(nb) == ta0)
    check("sleep: old skills bit-identical", outcome["audits"]["old_skills_bit_identical"])
    check("sleep: notebook chain valid after reload",
          outcome["audits"]["notebook_chain_valid_after"])
    check("sleep: base probe unchanged", outcome["audits"]["base_probe_unchanged"])
    check("sleep: 3 install cells attempted", outcome["audits"]["installs_total"] == 3,
          str(outcome["audits"]["installs_total"]))

    print()
    if fails:
        print(f"SELFTEST FAIL ({len(fails)}): {fails}")
        return 1
    print("SELFTEST PASS")
    return 0


# ----------------------------------------------------------------- CLI
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Experiment 52: live sleep on real logs")
    p.add_argument("--seed", type=int, help="registered seed (5201/5202/5203)")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--score", action="store_true")
    a = p.parse_args(argv)
    torch.set_num_threads(1)
    if a.selftest:
        return selftest(a.out)
    if a.score:
        return score(a.out)
    if a.seed is None:
        p.error("--seed required unless --selftest or --score")
    run_seed(a.seed, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
