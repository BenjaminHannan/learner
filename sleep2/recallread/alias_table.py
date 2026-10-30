"""D4: a nightly alias / entity table built by Claude (Batches) from the diary visible to a condition, used for zero-decode query expansion.

Triples (alias, entity, relation): 'alias' is how a person or thing is referred to via another name ("Kizibra's mentor"), 'entity' the proper
name it points to ("Kreilozho"), 'relation' a short label ("mentor"). Expansion: for a question, the entities of triples whose alias
shares a capitalised name with the question (or whose alias text occurs in the question), best match first, at most 4 keys.
One table is built from the full diary and one from the condition-W diary (hop-1 turns deleted); neither sees the questions.

  python -m sleep2.recallread.alias_table requests --dry-run [--w]
  python -m sleep2.recallread.alias_table requests --submit [--w] [--limit 2]     # lead only
  python -m sleep2.recallread.alias_table collect [--w]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from . import batchlib
from .world import FROZEN, load_world, norm, user_turns, words

MODEL = "claude-sonnet-5-5"
CHUNK = 60
SYS = "You extract a lookup table from a personal diary. Reply with one JSON list and nothing else."
MAX_KEYS = 4


def chunks(turns, size=CHUNK):
    return [turns[i:i + size] for i in range(0, len(turns), size)]


def request_for(chunk, i, tag):
    body = "\n".join(f"[{t['turn_id']}] {t['text']}" for t in chunk)
    u = ("Below are messages Sam wrote to his assistant. Extract every place where one named person or thing is tied to another "
         "(family, mentor, owner, employer, home, birthplace, nickname). For each, give a triple:\n"
         "  alias: how the first is referred to through the second, e.g. \"Kizibra's mentor\", \"owner of Tradepil\", \"Papirar's sibling\"\n"
         "  entity: the proper name it points to, copied exactly\n  relation: one or two words (mentor, owner, sibling, lives in, works at, born in, nickname)\n"
         "Use only what the messages say. Reply as [{\"alias\": \"...\", \"entity\": \"...\", \"relation\": \"...\"}, ...].\n\nMessages:\n" + body)
    return dict(custom_id=f"alias:{tag}:{i:03d}", params=batchlib.params(MODEL, SYS, u, 3000))


def requests_for(turns, tag):
    return [request_for(c, i, tag) for i, c in enumerate(chunks(turns))]


class AliasTable:
    def __init__(self, triples):
        self.triples = [t for t in triples if isinstance(t, dict) and t.get("alias") and t.get("entity")]
        self._names = [self._caps(t["alias"]) for t in self.triples]

    @staticmethod
    def _caps(s):
        return {w.casefold() for w in re.findall(r"\b[A-Z][a-zA-Z0-9]+", s)} - {"the", "my", "sam", "his", "her"}

    def expand(self, question: str, max_keys: int = MAX_KEYS) -> list[str]:
        qn = norm(question)
        qw = set(words(question))
        scored = []
        for i, (t, caps) in enumerate(zip(self.triples, self._names)):
            hit = len(caps & qw) + (2 if norm(t["alias"]) in qn else 0)
            if not hit or t["entity"].casefold() in qw:
                continue
            rel = 1 if any(w in qw for w in words(t.get("relation", ""))) else 0
            scored.append((-(hit + rel), i, t["entity"]))
        out = []
        for _, _, e in sorted(scored):
            if e not in out:
                out.append(e)
        return out[:max_keys]

    def __len__(self):
        return len(self.triples)


def load_table(path) -> AliasTable:
    return AliasTable(json.loads(Path(path).read_text())["triples"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["requests", "collect"])
    ap.add_argument("--w", action="store_true", help="the condition-W diary (hop-1 turns deleted)")
    ap.add_argument("--out", default=str(FROZEN))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    out, tag = Path(a.out), "W" if a.w else "full"
    turns = user_turns(load_world())
    if a.w:
        dele = set(json.loads((out / "items.json").read_text())["w_deleted_turns"])
        turns = [t for t in turns if t["turn_id"] not in dele]
    if a.cmd == "requests":
        reqs = requests_for(turns, tag)
        if a.submit and not a.dry_run:
            batchlib.submit(f"alias_{tag}", reqs, 1500, out / "batches.json", a.limit)
        else:
            batchlib.print_dry_run(f"alias_{tag}", reqs, 1500)
    else:
        st = json.loads((out / "batches.json").read_text())[f"alias_{tag}"]
        res = batchlib.collect(st[-1]["batch_id"])
        triples, bad = [], 0
        for k in sorted(res):
            j = batchlib.parse_json(res[k])
            if isinstance(j, list):
                triples += [t for t in j if isinstance(t, dict)]
            else:
                bad += 1
        (out / f"alias_table_{tag}.json").write_text(json.dumps(dict(tag=tag, n_chunks=len(res), bad_chunks=bad, triples=triples), indent=1))
        print(f"{len(triples)} triples from {len(res)} chunks ({bad} unparseable)")


if __name__ == "__main__":
    main()
