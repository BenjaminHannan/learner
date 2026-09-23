#!/usr/bin/env python3
"""Experiment 138e -- officeholder rewrite-chain guard (mixin on loop138b).

Diagnosis (STEP 1, dev only: bench121-new, bench103-old-s2fresh, edit200,
bench132-4hop sealed loop138b rows + redteam143; 146 rewritten asks whose
winning chain touches the `officeholder` relation: 140 correct, 3 wrong
(025/073/149), 2 abstain never taken through the rewrite, 1 redteam143-F5
fix; full table in design/v3/30-modes/138e-officechain-muse.md):

  The 3 wrongs share one shape. A first-hop edit teach carrying a long
  "A and B" value ("Gran Turismo was developed by MIT Computer Science
  and Artificial Intelligence Laboratory", "Strawberry Fields Forever was
  created by National Aeronautics and Space Administration") is refused by
  the stacked value screen ("I can take one fact at a time -- could you
  split that?"). The notebook keeps the complete STALE branch plus a
  DANGLING edit branch (its officeholder compound, e.g.
  "director of MIT ...", unreachable from the seed). The 132 rewriter
  walks the reachable stale branch, verifies against the unchanged
  composers, and answers confidently but wrong. Base loop138 abstained.

  No answer-time-only feature separates them: sibling-compound divergence
  alone vetoes dozens of corrects (both branches often land fully and the
  last-taught edit branch wins, e.g. old-022), and verbatim/typed-word/
  qualifier counts overlap completely. The separator is teach history
  PLUS contradiction:

THE ONE RULE (this file only; no loop138b file edited):
  the rewriter's officeholder hop is used ONLY when the session has NO
  refused teach/correct that mentions the ask's entities, OR when every
  same-office sibling compound agrees on the holder. Concretely, veto
  (keep the base 113c clarify/abstain) iff ALL of:
  (a) the rewrite fires with `officeholder` in its rels;
  (b) this session recorded a refused teach/correct (an _act teach/correct
      returning kind==clarify) whose name/value mentions a seed entity of
      the ask or a same-office sibling-compound target (substring, lower);
  (c) a same-office-prefix sibling compound (different target) exists
      whose target is unreachable from the ask's seeds (triple BFS +
      containment island edges, the rewriter's own semantics) AND whose
      holder differs from the used compound's holder.
  Otherwise the 138b path runs unchanged.

  On dev this vetoes exactly 025/073/149 and keeps all 140 corrects
  (incl. bench132-105: refusal recorded, but the dangling sibling resolves
  to the SAME holder, Brian Epstein; and old-022: divergent dangling
  sibling, but zero refusals -- the edit teach landed and superseded).

No existing file is edited; everything new lives in this file (+
artifacts/fable-officechain138e-20260922/loop138e-config.json + drivers).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138e_agent.py --daemon --dir DIR \\
    --config artifacts/fable-officechain138e-20260922/loop138e-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (thresholds, read-only)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_qrewrite132 as Q132  # noqa: E402 (rewriter, read-only)


# ------------------------------------------------------------ run-time helpers
def _seed_entities(question: str, triples) -> set[str]:
    """Ask's seed entities: verbatim + decomposed-compound seeds, lowered."""
    out = set()
    try:
        for s in Q132._seed_subjects(question, triples):
            out.add(str(s).lower())
    except Exception:
        pass
    try:
        for s in Q132._decomp_subjects(question, triples):
            out.add(str(s).lower())
    except Exception:
        pass
    return {s for s in out if s}


def _reachable(seeds: set[str], triples) -> set[str]:
    """BFS from seeds over exact triple edges plus containment island
    edges (the rewriter's own semantics: a compound subject containing a
    reached entity is reached; its object is then reached)."""
    nodes = set(seeds)
    guard = 0
    changed = True
    norm_triples = [(str(s), str(r), str(o)) for s, r, o in triples]
    while changed and guard < 12:
        guard += 1
        changed = False
        for s, _r, o in norm_triples:
            if s in nodes and o not in nodes:
                nodes.add(o)
                changed = True
        for s2, _r2, o2 in norm_triples:
            parts = Q132._split_of(s2)
            if parts is None:
                continue
            tgt = parts[1]
            hit = (tgt in nodes or tgt.lower() in nodes
                   or any(n and (n in tgt.lower() or tgt.lower() in n)
                           for n in nodes))
            if hit and s2 not in nodes:
                nodes.add(s2)
                changed = True
            if s2 in nodes and o2 not in nodes:
                nodes.add(o2)
                changed = True
    return nodes


def _office_compounds(triples) -> dict[str, str]:
    off: dict[str, str] = {}
    for s, r, o in triples:
        if str(r) == "officeholder":
            off.setdefault(str(s), str(o))
    return off


def should_veto_officeholder(question: str, canonical: str,
                             rels: list[str], triples,
                             refusals: list[dict]) -> tuple[bool, str]:
    """The 138e rule. Returns (veto, reason). No gold labels used."""
    if "officeholder" not in list(rels):
        return False, "no-officeholder-hop"
    if not refusals:
        return False, "no-refusals"
    off = _office_compounds(triples)
    if not off:
        return False, "no-officeholder-triples"
    # Used compounds: notebook officeholder subjects named verbatim after
    # "officeholder of" in the canonical rewrite.
    canon_l = str(canonical).lower()
    used = [s for s in off
            if ("officeholder of " + s.lower()) in canon_l]
    if not used:
        return False, "used-compound-not-named"
    seeds = _seed_entities(question, triples)
    reach = _reachable(seeds, triples)
    lowered = {s.lower(): s for s in off}
    for u in used:
        parts = Q132._split_of(u)
        if parts is None:
            continue
        pre = Q132._typonorm(parts[0])
        used_holder = off[u]
        sib_targets = []
        for s, holder in off.items():
            if s == u:
                continue
            p2 = Q132._split_of(s)
            if p2 is None or Q132._typonorm(p2[0]) != pre:
                continue
            sib_targets.append((s, holder, p2[1]))
        if not sib_targets:
            continue
        # (b) refusal scoping: a refused teach/correct mentioning a seed
        # or a sibling target of THIS office prefix.
        scope_terms = set(seeds)
        for s, _h, t in sib_targets:
            scope_terms.add(t.lower())
        scoped = False
        for ref in refusals:
            txt = (str(ref.get("name", "")) + " "
                   + str(ref.get("value", ""))).lower()
            if any(term and (term in txt or txt in term)
                   for term in scope_terms):
                scoped = True
                break
        if not scoped:
            continue
        # (c) dangling + divergent sibling.
        for s, holder, tgt in sib_targets:
            tgt_l = tgt.lower()
            reached = (tgt in reach or tgt_l in reach
                       or any(n and (n in tgt_l or tgt_l in n)
                               for n in reach))
            if not reached and holder != used_holder:
                return True, (
                    f"dangling sibling {s!r}->{holder!r} contradicts "
                    f"used {u!r}->{used_holder!r} with a scoped refusal")
    return False, "no-dangling-contradiction"


# ------------------------------------------------------------ ears: the guard
class Loop138eEars(L138b.Loop138bEars):
    """Loop138bEars + the 138e officeholder veto (question side only).

    Teach side is inherited unchanged. _rewrite132 runs the veto BEFORE
    the base rewrite: on veto the original clarify stands (the base 113c
    answer/abstain), else the 138b rewrite path runs unchanged.
    """

    name = "loop138e-officechain"

    def hear(self, turn: str) -> list[dict]:
        actions = super().hear(turn)
        # Refusal ledger (hear side): a non-question turn the ears refuse
        # with a clarify (value/subject screen, "split that", unparseable
        # teach) means a taught fact did NOT land -- the notebook may be
        # incomplete. Record the raw text for the 138e rule's scoping.
        # Question turns (ending with "?"; the 151 twin already converted
        # no-"?" questions inside super().hear) are never recorded.
        try:
            text = " ".join(str(turn).split())
            if (text and not text.rstrip().endswith("?") and actions
                    and all(isinstance(a, dict)
                            and a.get("act") == "clarify"
                            for a in actions)):
                ledger = getattr(self, "refusals138e", None)
                if ledger is not None:
                    ledger.append({"name": text, "value": ""})
        except Exception:
            pass
        return actions

    def _rewrite132(self, actions: list[dict], turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        if not (text and text.rstrip().endswith("?")
                and getattr(self, "nb", None) is not None):
            return super()._rewrite132(actions, turn)
        if not actions or any((not isinstance(a, dict))
                              or a.get("act") != "clarify"
                              for a in actions):
            return super()._rewrite132(actions, turn)
        try:
            triples = L90.notebook_triples(self.nb)
            _newq, info = Q132.rewrite_question(text, triples)
        except Exception:
            return super()._rewrite132(actions, turn)
        if not info.get("fired"):
            return super()._rewrite132(actions, turn)
        rels = list(info.get("rels", []))
        refusals = list(getattr(self, "refusals138e", []) or [])
        veto, _reason = should_veto_officeholder(
            text, str(info.get("canonical", "")), rels, triples, refusals)
        if veto:
            try:
                self.last_stage, self.last_score = (
                    "loop138e-veto-officeholder", 1.0)
            except AttributeError:
                pass
            return actions
        return super()._rewrite132(actions, turn)


# ------------------------------------------------------------ loop (L2 frozen)
class Loop138eAgentLoop(L138b.Loop138bAgentLoop):
    """Loop138bAgentLoop + refusal ledger for the 138e rule.

    turn() is inherited VERBATIM (L2 router + Self99 live answers +
    decline rule unchanged). _act records refused teach/correct turns
    (kind==clarify results); everything else passes through.
    """

    def _act(self, action: dict) -> dict:
        if isinstance(action, dict) and action.get("act") in (
                "teach", "correct"):
            res = super()._act(action)
            # Refusal ledger (_act side): a teach/correct whose fact did NOT
            # land -- kind==clarify (screens, "split that") or a write that
            # is not an acceptance (correction-pending confirmations ask
            # first and store nothing yet). Duplicates and "Saved:" writes
            # are acceptances and are never recorded.
            try:
                if (isinstance(res, dict)
                        and hasattr(self, "refusals138e")):
                    txt = str(res.get("text", ""))
                    accepted = (res.get("kind") == "write" and (
                        txt.startswith("Saved:")
                        or txt.strip() == "I already have that."))
                    if not accepted:
                        self.refusals138e.append({
                            "name": str(action.get("name", "")),
                            "value": str(action.get("value", ""))})
            except Exception:
                pass
            return res
        return super()._act(action)


DEFAULT_CONFIG138E: dict = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
DEFAULT_CONFIG138E["ears"]["stand_in"] = (
    "Loop138eEars (loop138b + 138e officeholder veto: a rewrite through "
    "officeholder is skipped when a refused teach mentions the ask's "
    "entities and a same-office sibling compound dangles with a different "
    "holder; else the 138b path runs unchanged)")
DEFAULT_CONFIG138E["mouth"]["stand_in"] = L138b.DEFAULT_CONFIG138B["mouth"][
    "stand_in"]
DEFAULT_CONFIG138E["daemon"]["module"] = "Loop138eDaemon (this file)"


def build_agent138e(cfg: dict | None = None) -> Loop138eAgentLoop:
    """Build the loop138b shape with the 138e guard swapped in."""
    cfg = dict(DEFAULT_CONFIG138E, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    from fable_loop148b_agent import (  # noqa: E402 (read-only wrap)
        ScreenStatusReasoner148b)
    reasoner = ScreenStatusReasoner148b()
    from fable_wire51_adapters import HardGate46Sleeper  # noqa: E402
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop138eAgentLoop(
        state_dir, ears=Loop138eEars(Loop96Ears(chain)), mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    thinker, thinker_module = L90.build_thinker(loop.nb)
    loop.thinker = thinker
    loop.parts90 = {"ears": loop.ears, "mouth": mouth, "reasoner": reasoner,
                    "sleeper": sleeper, "thinker": thinker,
                    "thinker_module": thinker_module,
                    "tau_hat": dict(chain.tau), "tau_family": chain.family,
                    "tau_hat_used": chain.tau_hat,
                    "ears_chain_stages": list(chain.stage_names),
                    "config": cfg}
    loop._screen148b_tag = None
    loop.refusals138e = []
    try:
        loop.ears.refusals138e = loop.refusals138e
    except Exception:
        pass
    # L2 live-self state (Self99-shaped logs owned by the loop; turn()
    # maintains them exactly as loop138 -- frozen).
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep138e: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    return loop


# ------------------------------------------------------------ L4: daemon
class Loop138eDaemon(L138b.Loop138bDaemon):
    """Loop138bDaemon shape with the 138e agent inside.

    process_file / settle gate inherited unchanged from Loop138bDaemon;
    only the agent factory differs. Name ends in Daemon / starts with
    Loop so the marks123 loader picks this class.
    """

    def __init__(self, root, cfg: dict | None = None,
                idle_seconds: float = 30.0,
                sleep_threshold: int | None = None,
                grace_s: float | None = None) -> None:
        import fable_daemon108_run as D108  # noqa: E402 (read-only)
        import fable_daemon141_settle as D141  # noqa: E402 (read-only)
        import fable_daemon74_run as D74  # noqa: E402 (read-only)
        self.cfg = dict(cfg or {})
        if sleep_threshold is not None:
            self.cfg["sleep_threshold"] = sleep_threshold
        self.root = Path(root)
        self.inbox = self.root / "inbox"
        self.outbox = self.root / "outbox"
        self.done = self.root / "done"
        for sub in (self.inbox, self.outbox, self.done):
            sub.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root / "STOP"
        self.idle_seconds = float(idle_seconds)
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        import os as _os
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent138e(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(
            grace_s=D141.SETTLE_GRACE_S if grace_s is None else grace_s)


def atomic_write_text(path: Path, text: str) -> None:
    """Atomic-write client rule: write tmp in the same dir, then rename."""
    import os as _os
    tmp = Path(str(path) + ".tmp%d" % _os.getpid())
    tmp.write_text(text, encoding="utf-8")
    _os.replace(tmp, path)


def run_daemon138e(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop138eDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 138e officechain loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG138E to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG138E)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG138E)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon138e(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent138e(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
