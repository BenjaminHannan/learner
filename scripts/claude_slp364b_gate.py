#!/usr/bin/env python3
"""slp-364b: self-check gate, version 2 (Fix-sleep thread, 2026-09-25). Follows the slp-364 registered FAIL.

slp-364 caught 13/20 faulty nights. The misses, and what v2 adds for each (every 364 check is kept as it was):
  1. silent no-ops (0/3): the sleeper said it learned a word but nothing changed. v2 adds
       C  claim check: for every word the sleeper reports as installed, at least 80% of that word's questions
          (people whose chain is complete in the taught notebook) must now be answered right, and there must be
          at least one such question.
  2. faults that only hurt people taught AFTER the sleep (0/3). v2 adds
       P  new-people check: inside a sandbox, teach 3 invented people for each word that was just installed or was
          already answered right before the night (up to 4 words), then ask the word and the first hop. Any
          wrong/other/abstain on the word (at most 1 in 3 allowed), any wrong one-hop answer, or any name that is
          not the truth rejects the night. The sandbox copies the notebook folder and the notebook objects before,
          and puts both back after (the probes' own rows are moved to undo361/probes364b/, never deleted).
  3. a made-up answer missed because lures were filled word by word and the cap ran out (budget bug). v2 gives
     every word its own budget (W 20, L 8 per word).
  4. a night that wrote to the main notebook. v2 adds
       M  the main notebook log's bytes before the night and after it must be identical.
Optional (only when the caller passes rebuild=):
       R  restart check: copy the state folder, build a fresh loop from the copy, ask the claimed words' questions
          and 30 taught questions; the named answer and grade must match the live loop's.
Nothing here writes to the notebook outside the sandbox. A rejected night is undone by slp-361.
"""
from __future__ import annotations

import copy
import hashlib
import re
import shutil
import tempfile
from pathlib import Path

import claude_slp361_undo as U361
import claude_slp364_gate as G

W_PER_WORD = 20
L_PER_WORD = 8
P_PEOPLE = 3
P_MAX_WORDS = 4
NEW_PEOPLE364B = ["Pelqorin", "Maxuvet", "Tobrelia", "Quisandor", "Veltroma", "Horvanti", "Zemmelyn", "Brastovik",
                  "Olquendra", "Firnavel", "Sutharion", "Kelvatrix", "Drommelin", "Yastrevel", "Invorra", "Gavrenthe",
                  "Plomirax", "Cendrovil", "Wystabel", "Norquell", "Ebrastine", "Tarnovex", "Lumquessa", "Rovindel",
                  "Askelvar", "Merrowint", "Juvastra", "Kolbrenny", "Selvaquor", "Trimbolax", "Udrevan", "Fesquilla",
                  "Harlomyr", "Vosquanne", "Brelloven", "Orquisti"]


def build_probes_b(loop) -> list[dict]:
    nb = G._nb(loop)
    words, chains = G._words()
    names = {nb.entities[e] for e in nb.entities}
    probes = [p for p in G.build_probes(loop) if p["kind"] == "T"]          # T exactly as 364
    people = G._people(nb)
    for wi, word in enumerate(words):
        w_n = l_n = 0
        for eid in people:
            end = G._walk(nb, eid, chains[wi])
            q = f"Who is {nb.entities[eid]}'s {word.replace('_', ' ')}?"
            path = G._path(nb, eid, chains[wi])
            if end is not None and w_n < W_PER_WORD:
                probes.append({"kind": "W", "word": word, "q": q, "want": [nb.entities[end]], "ok": path[:-1]})
                w_n += 1
            elif end is None and path and l_n < L_PER_WORD:
                probes.append({"kind": "L", "word": word, "q": q, "want": [], "ok": path})
                l_n += 1
        for fake in G.INVENTED364:
            if fake not in names:
                probes.append({"kind": "L", "word": word, "q": f"Who is {fake}'s {word.replace('_', ' ')}?",
                               "want": []})
    return probes


def _digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


def _nb_objects(loop) -> list:
    out, seen = [], set()
    for o in (loop.nb, getattr(loop.nb, "nb", None)):
        if o is not None and id(o) not in seen:
            out.append(o)
            seen.add(id(o))
    return out


def new_people_check(loop, words: list[str], used: set[str], tag: str) -> tuple[list[str], dict]:
    """Teach invented people inside a full sandbox (notebook included) and grade the word and first hop."""
    _, chains = G._words()
    allw = G._words()[0]
    root = Path(loop.dir)
    nbdir = root / "notebook"
    nb_files = {p.relative_to(nbdir).as_posix(): p.read_bytes() for p in nbdir.rglob("*") if p.is_file()}
    nb_state = [(o, copy.deepcopy(o.__dict__)) for o in _nb_objects(loop)]
    log = nbdir / "events.jsonl"
    main0 = _digest(log)
    files = U361._files(root, {"notebook", U361.UNDO_DIR361})
    saved = {rel: p.read_bytes() for rel, p in files.items()}
    mem = U361._mem_snapshot(loop)
    old_threshold = loop.sleep_threshold
    loop.sleep_threshold = 10 ** 9
    pool = [n for n in NEW_PEOPLE364B if n not in used]
    reasons, rows = [], []
    try:
        for word in words:
            chain = chains[allw.index(word)]
            right = 0
            for k in range(P_PEOPLE):
                if len(pool) < len(chain) + 1:
                    break
                ppl = [pool.pop(0) for _ in range(len(chain) + 1)]
                for a, rel, b in zip(ppl, chain, ppl[1:]):
                    loop.turn(f"{a}'s {rel.replace('_', ' ')} is {b}.")
                names = set(G._nb(loop).entities.values())
                wq = {"kind": "P", "q": f"Who is {ppl[0]}'s {word.replace('_', ' ')}?", "want": [ppl[-1]],
                      "ok": ppl[1:-1]}
                hq = {"kind": "P", "q": f"Who is {ppl[0]}'s {chain[0].replace('_', ' ')}?", "want": [ppl[1]]}
                for pr in (wq, hq):
                    rep = " ".join(loop.turn(pr["q"]))
                    gr = G._grade(rep, pr, names, ppl[0])
                    rows.append({"q": pr["q"], "reply": rep, "grade": gr})
                    if pr is hq and gr != "right":
                        reasons.append(f"P: new person's taught fact not answered right: {pr['q']}")
                    if gr == "wrong":
                        reasons.append(f"P: wrong name for a new person: {pr['q']}")
                right += int(rows[-2]["grade"] == "right")
            if right < P_PEOPLE - 1:
                reasons.append(f"P: word '{word}' right for only {right}/{P_PEOPLE} people taught after the night")
    finally:
        moved = root / U361.UNDO_DIR361 / f"probes364b-{tag}"
        for p in list(nbdir.rglob("*")):
            if p.is_file():
                rel = p.relative_to(nbdir).as_posix()
                if nb_files.get(rel) != p.read_bytes():
                    dest = moved / "notebook" / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, dest)            # the probes' version is kept aside
                    if rel in nb_files:
                        p.write_bytes(nb_files[rel])
                    else:
                        p.replace(dest)
        for rel, p in U361._files(root, {"notebook", U361.UNDO_DIR361}).items():
            if rel not in saved:
                dest = moved / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                p.replace(dest)
        for rel, data in saved.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_bytes(data)
        for o, d in nb_state:
            o.__dict__.clear()
            o.__dict__.update(d)
        U361._mem_restore(loop, mem)
        loop.sleep_threshold = old_threshold
    ok = _digest(log) == main0
    if not ok:
        reasons.append("X: the new-people sandbox could not restore the notebook")
    return reasons, {"rows": rows, "restored": ok}


def _named(reply: str, names: set[str]) -> tuple:
    return tuple(sorted(n for n in names if G._mentions(reply, n)))


class Gate364b(G.Gate364):
    def __init__(self, rebuild=None) -> None:
        super().__init__()
        self.rebuild = rebuild

    def pre(self, loop) -> None:
        self.probes = build_probes_b(loop)
        self.before = G.ask_all(loop, self.probes)
        self.main0 = _digest(Path(loop.dir) / "notebook" / "events.jsonl")

    def judge(self, loop, event) -> bool:
        reasons = []
        outcome = (event.get("detail") or {}).get("outcome") or {}
        self.sleeper_accepted = bool((event.get("detail") or {}).get("accepted"))
        recipe = outcome.get("recipe") if isinstance(outcome, dict) else None
        if isinstance(outcome, dict) and outcome.get("accepted") is False:
            reasons.append("N: the sleeper's own audit failed")
        if isinstance(recipe, dict) and recipe.get("attempted") is False and recipe.get("reason"):
            reasons.append(f"N: sleep did not run ({str(recipe.get('reason'))[:80]})")
        if _digest(Path(loop.dir) / "notebook" / "events.jsonl") != self.main0:
            reasons.append("M: the main notebook changed during the night")
        after = G.ask_all(loop, self.probes)
        for b, a in zip(self.before, after):
            if a["kind"] == "T" and a["reply"] != b["reply"]:
                reasons.append(f"T: taught answer changed: {a['q']}")
            elif a["kind"] == "W" and a["grade"] in ("wrong", "other") and a["reply"] != b["reply"]:
                reasons.append(f"W: wrong word answer: {a['q']}")
            elif a["kind"] == "L" and a["grade"] in ("wrong", "right") and a["reply"] != b["reply"]:
                reasons.append(f"L: made-up answer: {a['q']}")
            if b["grade"] == "right" and a["grade"] != "right":
                reasons.append(f"K: lost a right answer: {a['q']}")
        reasons += [f"N: {a['q']}" for a in after[len(self.before):]]
        # C: claims must show up in the replies
        claimed = [str(w.get("word")) for w in ((recipe or {}).get("words") or []) if w.get("installed")]
        for word in claimed:
            idx = [i for i, p in enumerate(self.probes) if p["kind"] == "W" and p.get("word") == word]
            got = sum(1 for i in idx if after[i]["grade"] == "right")
            if not idx or got < 0.8 * len(idx):
                reasons.append(f"C: sleep says it learned '{word}' but only {got}/{len(idx)} of its questions are right")
        # P: people taught after the night
        known_before = []
        for word in G._words()[0]:
            idx = [i for i, p in enumerate(self.probes) if p["kind"] == "W" and p.get("word") == word]
            if idx and sum(1 for i in idx if self.before[i]["grade"] == "right") >= 0.8 * len(idx):
                known_before.append(word)
        pwords = (claimed + [w for w in known_before if w not in claimed])[:P_MAX_WORDS]
        used = set(G._nb(loop).entities.values())
        p_reasons, p_info = new_people_check(loop, pwords, used, f"n{self._n()}") if pwords else ([], {"rows": []})
        reasons += p_reasons
        # R: live vs restarted from the saved folder
        r_info = None
        if self.rebuild is not None:
            r_reasons, r_info = self._restart_check(loop, after, claimed)
            reasons += r_reasons
        self.last = {"probes": len(self.probes), "kinds": {k: sum(p["kind"] == k for p in self.probes)
                                                          for k in "TWL"},
                     "claimed": claimed, "p_words": pwords, "p_rows": len(p_info.get("rows", [])),
                     "p_restored": p_info.get("restored"), "restart": r_info,
                     "reasons": reasons[:40], "n_reasons": len(reasons), "kept": not reasons}
        return not reasons

    def _n(self) -> int:
        self._count = getattr(self, "_count", 0) + 1
        return self._count

    def _restart_check(self, loop, after, claimed):
        idx = [i for i, p in enumerate(self.probes)
               if (p["kind"] == "W" and p.get("word") in claimed)][:60]
        idx += [i for i, p in enumerate(self.probes) if p["kind"] == "T"][:30]
        tmp = Path(tempfile.mkdtemp(prefix="gate364b-restart-"))
        reasons, diffs = [], 0
        try:
            clone = tmp / "state"
            shutil.copytree(loop.dir, clone, ignore=shutil.ignore_patterns(U361.UNDO_DIR361))
            loop2 = self.rebuild(str(clone))
            sub = [self.probes[i] for i in idx]
            res2 = G.ask_all(loop2, sub)
            names = set(G._nb(loop).entities.values())
            for i, r2 in zip(idx, res2):
                a = after[i]
                if (a["grade"], _named(a["reply"], names)) != (r2["grade"], _named(r2["reply"], names)):
                    diffs += 1
                    if diffs <= 5:
                        reasons.append(f"R: live and restarted answers differ: {a['q']}")
            if diffs > 5:
                reasons.append(f"R: {diffs} answers differ after a restart")
            del loop2
        finally:
            shutil.rmtree(tmp, ignore_errors=True)          # our own temp copy
        return reasons, {"asked": len(idx), "differ": diffs}


def install_gate364b(loop, rebuild=None) -> Gate364b:
    gate = Gate364b(rebuild)
    U361.install_undo361(loop, judge=gate.judge)
    staged = loop._sleep_tick

    def sleep364b():
        gate.pre(loop)
        return staged()

    loop._sleep_tick = sleep364b
    loop.gate364b = gate
    loop.notes.append("slp-364b: a night is kept only if the self-check (v2) finds nothing wrong")
    return gate
