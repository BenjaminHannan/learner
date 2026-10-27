"""Exp 238 step 1: harvest real assistant replies from today's run rows.

Measurement only. Walks artifacts/*-20260922/, skipping every TEST-ONLY panel
folder (any folder with 'panel' in its name, fable-naturalpanel208,
claude-tablepanel221, reading94/94b) and rows files named panel*/p1panel*.
Collects every string stored under a key named 'reply' (or a list under
'teach_replies' / 'replies'). Also reads outbox/*.txt files in run workdirs
(those are the literal replies the daemon wrote).
Writes artifacts/claude-grammar238-20260922/harvest.jsonl (reply, count,
bench_count = occurrences in files whose path says bench/mquake, sources).
"""
import json, os, sys, collections, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "artifacts"
OUT = ART / "claude-grammar238-20260922"
SKIP_NAMES = {"events.jsonl", "state.json", "receipts.jsonl", "daemon_status.json",
              "heartbeat.json", "daemon-config.json", "daemon.log.jsonl",
              "events.fix77.seal.json", "doubts146.json"}
PRUNE_DIRS = {"notebook", "inbox", "receipts", "__pycache__", ".git"}
# In-scope folders: runs of the accepted base 138i (and its 228-guarded copy),
# merge 138j, and the pieces waiting to merge.
SCOPE = {"fable-agent138i-20260922", "fable-agent138j-20260922", "claude-determinism228-20260922",
         "fable-selfname219-20260922", "claude-yesprefix230-20260922", "claude-namecheck230b-20260922",
         "claude-name227b-20260922", "claude-identity227c-20260922", "fable-cantdo223-20260922",
         "claude-decline224c-20260922", "fable-source226-20260922", "claude-polite233-20260922",
         "claude-smalltalk234-20260922", "claude-tableask221-20260922", "claude-qnorm221c-20260922",
         "claude-tableteach229-20260922", "claude-chain231-20260922"}
REPLY_KEYS = {"reply", "teach_replies", "replies", "agent_reply", "response"}


def excluded_dir(name):
    n = name.lower()
    return ("panel" in n or "reading94" in n or n == "fable-naturalpanel208-20260922"
            or n == "claude-tablepanel221-20260922" or n.startswith("claude-grammar238"))


def excluded_file(name):
    n = name.lower()
    return n.startswith("panel") or n.startswith("p1panel")


def walk_json(obj, found):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in REPLY_KEYS:
                if isinstance(v, str):
                    found.append(v)
                elif isinstance(v, list):
                    found.extend(x for x in v if isinstance(x, str))
                    for x in v:
                        if not isinstance(x, str):
                            walk_json(x, found)
                else:
                    walk_json(v, found)
            else:
                walk_json(v, found)
    elif isinstance(obj, list):
        for x in obj:
            walk_json(x, found)


def main():
    counts = collections.Counter()
    bench = collections.Counter()
    scope = collections.Counter()
    scope_bench = collections.Counter()
    srcs = collections.defaultdict(set)
    nfiles = 0
    for top in sorted(ART.iterdir()):
        if not top.is_dir() or not top.name.endswith("-20260922") or excluded_dir(top.name):
            continue
        for dp, dns, fns in os.walk(top):
            dns[:] = [d for d in dns if d not in PRUNE_DIRS and not excluded_dir(d)]
            base = Path(dp)
            for fn in fns:
                if fn in SKIP_NAMES or excluded_file(fn):
                    continue
                p = base / fn
                found = []
                if base.name == "outbox" and fn.endswith(".txt"):
                    try:
                        found = [p.read_text(errors="replace")]
                    except OSError:
                        continue
                elif fn.endswith(".json") or fn.endswith(".jsonl"):
                    try:
                        if p.stat().st_size > 30_000_000:
                            continue
                        txt = p.read_text(errors="replace")
                    except OSError:
                        continue
                    if '"reply' not in txt and '"replies' not in txt and '"response' not in txt and '"agent_reply' not in txt:
                        continue
                    if fn.endswith(".jsonl"):
                        for line in txt.splitlines():
                            try:
                                walk_json(json.loads(line), found)
                            except Exception:
                                pass
                    else:
                        try:
                            walk_json(json.loads(txt), found)
                        except Exception:
                            pass
                else:
                    continue
                if found:
                    nfiles += 1
                for r in found:
                    r = r.strip()
                    if not r:
                        continue
                    counts[r] += 1
                    if "bench" in str(p).lower() or "mquake" in str(p).lower():
                        bench[r] += 1
                    if top.name in SCOPE:
                        scope[r] += 1
                        if "bench" in str(p).lower() or "mquake" in str(p).lower():
                            scope_bench[r] += 1
                    if len(srcs[r]) < 3:
                        srcs[r].add(top.name)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "harvest.jsonl", "w") as f:
        for r, c in counts.most_common():
            f.write(json.dumps({"reply": r, "count": c, "bench_count": bench[r], "scope_count": scope[r], "scope_bench_count": scope_bench[r], "sources": sorted(srcs[r])}) + "\n")
    print(f"files_with_replies={nfiles} unique={len(counts)} total={sum(counts.values())}")


if __name__ == "__main__":
    main()
