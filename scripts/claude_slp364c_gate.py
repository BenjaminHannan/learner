#!/usr/bin/env python3
"""slp-364c: self-check gate, version 3 (Fix-sleep thread, 2026-09-25). Follows the slp-364b registered FAIL.

v2 (364b) caught 17/20 bad nights but broke the loop: after its new-people sandbox, teaching a new person saved
"B's spouse is B." on every honest night (P364b.5, 0/20 replies identical). v3 = v2 with three changes, all inside
the checks that v2 added (every v1/v2 rule is otherwise unchanged):
  1. The new-people check (P) runs in a FORKED copy of the process (os.fork). The real loop's memory is never touched;
     the child's file writes are put back afterwards exactly as v2 did (changed/new files moved to
     undo361/probes364c-*/, originals written back), and the main log's bytes are checked.
  2. P also makes one correction per word ("Actually, A's R is C.") and asks it back (v2 missed a night that broke
     corrections made after the sleep).
  3. The restart check (R) also asks the words that were right before the night (v2 missed a night whose word file
     kept only tonight's word), up to 80 word questions plus 30 taught questions.
Needs os.fork (Linux, macOS). On a system without fork the P check is skipped and says so in last["p_skipped"].
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import claude_slp361_undo as U361
import claude_slp364_gate as G
import claude_slp364b_gate as GB

R_MAX_W = 80


def _p_body(loop, words: list[str], used: set[str]) -> tuple[list[str], list[dict]]:
    allw, chains = G._words()
    loop.sleep_threshold = 10 ** 9
    pool = [n for n in GB.NEW_PEOPLE364B if n not in used]
    reasons, rows = [], []
    for word in words:
        chain = chains[allw.index(word)]
        right = 0
        last = None
        for _ in range(GB.P_PEOPLE):
            if len(pool) < len(chain) + 1:
                break
            ppl = [pool.pop(0) for _ in range(len(chain) + 1)]
            for a, rel, b in zip(ppl, chain, ppl[1:]):
                loop.turn(f"{a}'s {rel.replace('_', ' ')} is {b}.")
            names = set(G._nb(loop).entities.values())
            wq = {"q": f"Who is {ppl[0]}'s {word.replace('_', ' ')}?", "want": [ppl[-1]], "ok": ppl[1:-1]}
            hq = {"q": f"Who is {ppl[0]}'s {chain[0].replace('_', ' ')}?", "want": [ppl[1]]}
            for pr in (wq, hq):
                rep = " ".join(loop.turn(pr["q"]))
                gr = G._grade(rep, pr, names, ppl[0])
                rows.append({"q": pr["q"], "reply": rep, "grade": gr})
                if pr is hq and gr != "right":
                    reasons.append(f"P: new person's taught fact not answered right: {pr['q']}")
                if gr == "wrong":
                    reasons.append(f"P: wrong name for a new person: {pr['q']}")
            right += int(rows[-2]["grade"] == "right")
            last = ppl
        if right < GB.P_PEOPLE - 1:
            reasons.append(f"P: word '{word}' right for only {right}/{GB.P_PEOPLE} people taught after the night")
        if last is not None and len(last) >= 3:                       # one correction, asked back
            a, rel, new = last[0], chain[0].replace("_", " "), last[2]
            loop.turn(f"Actually, {a}'s {rel} is {new}.")
            names = set(G._nb(loop).entities.values())
            pr = {"q": f"Who is {a}'s {rel}?", "want": [new], "ok": []}
            rep = " ".join(loop.turn(pr["q"]))
            gr = G._grade(rep, pr, names, a)
            rows.append({"q": pr["q"], "reply": rep, "grade": gr, "correction": True})
            if gr != "right":
                reasons.append(f"P: a correction made after the night was not kept: {pr['q']}")
    return reasons, rows


def new_people_check_forked(loop, words: list[str], used: set[str], tag: str) -> tuple[list[str], dict]:
    if not hasattr(os, "fork"):
        return [], {"rows": [], "restored": True, "skipped": "no os.fork"}
    root = Path(loop.dir)
    nbdir = root / "notebook"
    nb_files = {p.relative_to(nbdir).as_posix(): p.read_bytes() for p in nbdir.rglob("*") if p.is_file()}
    log = nbdir / "events.jsonl"
    main0 = GB._digest(log)
    saved = {rel: p.read_bytes() for rel, p in U361._files(root, {"notebook", U361.UNDO_DIR361}).items()}
    rfd, wfd = os.pipe()
    pid = os.fork()
    if pid == 0:                                       # child: a throwaway copy of the whole process
        os.close(rfd)
        try:
            reasons, rows = _p_body(loop, words, used)
            data = json.dumps({"reasons": reasons, "rows": rows})
        except BaseException as exc:  # noqa: BLE001
            data = json.dumps({"reasons": [f"P: new-people check crashed ({type(exc).__name__}: {exc})"[:200]],
                               "rows": []})
        with os.fdopen(wfd, "w", encoding="utf-8") as fh:
            fh.write(data)
        os._exit(0)
    os.close(wfd)
    with os.fdopen(rfd, "r", encoding="utf-8") as fh:
        raw = fh.read()
    os.waitpid(pid, 0)
    moved = root / U361.UNDO_DIR361 / f"probes364c-{tag}"
    for p in list(nbdir.rglob("*")):
        if p.is_file():
            rel = p.relative_to(nbdir).as_posix()
            if nb_files.get(rel) != p.read_bytes():
                dest = moved / "notebook" / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dest)
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
        if not (root / rel).exists() or (root / rel).read_bytes() != data:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_bytes(data)
    try:
        got = json.loads(raw)
    except ValueError:
        got = {"reasons": ["P: new-people check returned nothing"], "rows": []}
    reasons = list(got.get("reasons", []))
    ok = GB._digest(log) == main0
    if not ok:
        reasons.append("X: the new-people sandbox could not restore the notebook")
    return reasons, {"rows": got.get("rows", []), "restored": ok}


class Gate364c(GB.Gate364b):
    def judge(self, loop, event) -> bool:
        real_p = GB.new_people_check
        GB.new_people_check = new_people_check_forked          # v2's judge calls this name
        try:
            return super().judge(loop, event)
        finally:
            GB.new_people_check = real_p

    def _restart_check(self, loop, after, claimed):
        known = [w for w in G._words()[0]
                 if (idx := [i for i, p in enumerate(self.probes) if p["kind"] == "W" and p.get("word") == w])
                 and sum(1 for i in idx if self.before[i]["grade"] == "right") >= 0.8 * len(idx)]
        want = list(dict.fromkeys(list(claimed) + known))
        keep = [i for i, p in enumerate(self.probes) if p["kind"] == "W" and p.get("word") in want][:R_MAX_W]
        return self._restart_wide(loop, after, keep)

    def _restart_wide(self, loop, after, widx):
        import tempfile
        idx = widx + [i for i, p in enumerate(self.probes) if p["kind"] == "T"][:30]
        tmp = Path(tempfile.mkdtemp(prefix="gate364c-restart-"))
        reasons, diffs = [], 0
        try:
            clone = tmp / "state"
            shutil.copytree(loop.dir, clone, ignore=shutil.ignore_patterns(U361.UNDO_DIR361))
            loop2 = self.rebuild(str(clone))
            res2 = G.ask_all(loop2, [self.probes[i] for i in idx])
            names = set(G._nb(loop).entities.values())
            for i, r2 in zip(idx, res2):
                a = after[i]
                if (a["grade"], GB._named(a["reply"], names)) != (r2["grade"], GB._named(r2["reply"], names)):
                    diffs += 1
                    if diffs <= 5:
                        reasons.append(f"R: live and restarted answers differ: {a['q']}")
            if diffs > 5:
                reasons.append(f"R: {diffs} answers differ after a restart")
            del loop2
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return reasons, {"asked": len(idx), "differ": diffs}


def install_gate364c(loop, rebuild=None) -> Gate364c:
    gate = Gate364c(rebuild)
    U361.install_undo361(loop, judge=gate.judge)
    staged = loop._sleep_tick

    def sleep364c():
        gate.pre(loop)
        return staged()

    loop._sleep_tick = sleep364c
    loop.gate364c = gate
    loop.notes.append("slp-364c: a night is kept only if the self-check (v3) finds nothing wrong")
    return gate
