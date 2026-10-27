"""Exp 63 (doc 68): fetch Wikidata property labels/aliases/inverses, build alias tables.

Reads distinct relation_ids (P-numbers) from data/open/webred/frames/*.jsonl,
fetches one Special:EntityData doc per property (polite UA, 0.2 s gap), caches
raw JSON under data/open/wikidata-props/Pnnn.json, and writes:
  alias_table.json   norm(alias) -> canonical WebRED name (unique mappings only)
  inverse_table.json canonical name -> {inverse_name, inverse_relation_id}
  denylist.json      sorted list of norm(aliases) mapping to > 1 property
Only stdlib (urllib). If the network is blocked, prints NETWORK_BLOCKED and stops.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRAMES = ROOT / "data" / "open" / "webred" / "frames"
OUTDIR = ROOT / "data" / "open" / "wikidata-props"
UA = "fable-relcanon63/0.1 (research)"
GAP_S = float(os.environ.get("FABLE_RELCANON63_GAP", "0.2"))


def norm(text: str) -> str:
    return " ".join(str(text).strip().lower().split())


def load_pid_names() -> dict:
    pid2name: dict = {}
    for split in ("train", "dev", "heldout"):
        with open(FRAMES / f"{split}.jsonl", encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                n, p = r.get("relation"), r.get("relation_id")
                if n and p:
                    if p in pid2name and pid2name[p] != n:
                        print(f"WARN pid {p} maps to {pid2name[p]!r} and {n!r}; keeping first",
                              file=sys.stderr)
                    else:
                        pid2name[p] = n
    return pid2name


def fetch_prop(pid: str) -> dict | str | None:
    """Cached EntityData blob; 'MISSING' on HTTP 404 (deleted/merged property);
    None when the network itself is blocked."""
    path = OUTDIR / f"{pid}.json"
    if path.exists():
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
            if "entities" in blob and pid in blob["entities"]:
                return blob
        except ValueError:
            pass
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{pid}.json"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as ex:
        if ex.code == 404:
            print(f"MISSING property {pid} (HTTP 404: deleted or merged); recording and continuing.")
            return "MISSING"
        print(f"NETWORK_BLOCKED fetching {pid}: HTTPError {ex.code}: {ex}")
        return None
    except Exception as ex:  # noqa: BLE001 -- network may be blocked; caller stops
        print(f"NETWORK_BLOCKED fetching {pid}: {type(ex).__name__}: {ex}")
        return None
    path.write_text(raw, encoding="utf-8")
    return json.loads(raw)


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    pid2name = load_pid_names()
    print(f"distinct P-numbers in frames: {len(pid2name)}")
    try:
        vocab521 = set(json.loads((FRAMES / "relations.json").read_text(encoding="utf-8"))["counts"])
    except (OSError, ValueError):
        vocab521 = set(pid2name.values())

    alias_to_pids: dict[str, set] = {}
    pid_info: dict = {}
    missing_props: list = []
    fetched, failed = 0, []
    for i, pid in enumerate(sorted(pid2name)):
        blob = fetch_prop(pid)
        if blob is None:
            failed.append(pid)
            break  # network blocked: stop, do not write partial tables
        if blob == "MISSING":
            missing_props.append(pid)
            continue  # deleted/merged property: record and continue
        ent = blob["entities"][pid]
        labels = ent.get("labels", {})
        aliases = ent.get("aliases", {})
        terms = set()
        if "en" in labels and labels["en"].get("value"):
            terms.add(labels["en"]["value"])
        for a in aliases.get("en", []):
            if a.get("value"):
                terms.add(a["value"])
        inv = []
        for stmt in ent.get("claims", {}).get("P1696", []):
            try:
                if stmt.get("mainsnak", {}).get("snaktype") == "value":
                    inv.append(stmt["mainsnak"]["datavalue"]["value"]["id"])
            except (KeyError, TypeError):
                continue
        pid_info[pid] = {"label_en": labels.get("en", {}).get("value"),
                         "n_alias_en": len(aliases.get("en", [])),
                         "inverse_claims": inv}
        for t in terms:
            alias_to_pids.setdefault(norm(t), set()).add(pid)
        fetched += 1
        if (i + 1) % 50 == 0:
            print(f"  fetched {i + 1}/{len(pid2name)} ...")
        time.sleep(GAP_S)
    if failed:
        print(f"NETWORK_BLOCKED: stopped after {fetched} properties; no tables written.")
        return 2
    # Add canonical WebRED names themselves so cross-property collisions denylist.
    for pid, name in pid2name.items():
        alias_to_pids.setdefault(norm(name), set()).add(pid)

    alias_table: dict = {}
    denylist: list = []
    for alias, pids in alias_to_pids.items():
        if len(pids) == 1:
            alias_table[alias] = pid2name[next(iter(pids))]
        else:
            denylist.append(alias)
    denylist.sort()

    inverse_table: dict = {}
    for pid, info in pid_info.items():
        name = pid2name[pid]
        for q in info["inverse_claims"]:
            if q in pid2name:
                inverse_table[name] = {"inverse_name": pid2name[q],
                                       "inverse_relation_id": q}
                break  # first declared inverse that overlaps WebRED
    # Symmetric closure: a declared pair is mutual by meaning (doc 58 s5).
    for name, inv in list(inverse_table.items()):
        back = inv["inverse_name"]
        if back not in inverse_table:
            inverse_table[back] = {"inverse_name": name,
                                   "inverse_relation_id":
                                   next(p for p, n in pid2name.items() if n == name)}

    (OUTDIR / "alias_table.json").write_text(
        json.dumps(alias_table, indent=1, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    (OUTDIR / "inverse_table.json").write_text(
        json.dumps(inverse_table, indent=1, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    (OUTDIR / "denylist.json").write_text(
        json.dumps(denylist, indent=1, ensure_ascii=False), encoding="utf-8")
    (OUTDIR / "missing.json").write_text(
        json.dumps(sorted(missing_props), indent=1, ensure_ascii=False), encoding="utf-8")

    covered = sorted({c for c in alias_table.values() if c in vocab521})
    print(f"properties fetched: {fetched} (+ {len(missing_props)} missing/404)")
    print(f"alias_table entries: {len(alias_table)}; denylist size: {len(denylist)}")
    print(f"inverse_table entries: {len(inverse_table)}")
    print(f"COVERAGE_521: {len(covered)}/{len(vocab521)} WebRED names have >= 1 alias-table key")
    print("inverse pairs:", json.dumps(inverse_table, sort_keys=True, ensure_ascii=False)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
