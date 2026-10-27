#!/usr/bin/env python3
"""Exp 235 post-seal DRIVER-ONLY fix (reported in RESULTS.md with this diff).

The sealed loader (claude_smolear235_panel.py) reads a frame's hops from the first
of relation/rel/relations/chain. The blind panel stores chain questions as
  {"relation": "<last hop>", "relation_aliases": [...last hop...], "chain": [hop1, hop2]}
so the sealed loader saw every chain question as a 1-hop question. This wrapper
re-reads such frames: hops = chain; relation_aliases apply to the last hop only
(the panel's "relation" equals chain[-1]). Nothing else changes; the sealed
scorer is reused by patching its loader reference.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235_panel as P  # noqa: E402

_sealed_load = P.load_panel


def load_panel_fixed(path):
    items = _sealed_load(path)
    raw = {}
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines()):
        if line.strip():
            d = json.loads(line)
            raw[str(d.get("id", n))] = d
    for it in items:
        d = raw[it["id"]]
        golds = [g for g in d.get("gold", []) if isinstance(g, dict)
                 and str(g.get("act", "")).upper() not in ("NONE", "")]
        for fr, g in zip(it["gold"], golds):
            ch = g.get("chain")
            if isinstance(ch, list) and len(ch) > 1:
                fr["relation"] = [str(x).strip() for x in ch]
                al = list(g.get("relation_aliases") or [])
                fr["aliases"] = [[] for _ in ch[:-1]] + [al]
    return items


if __name__ == "__main__":
    import claude_smolear235_score as S
    S.P.load_panel = load_panel_fixed
    sys.argv[0] = "claude_smolear235_score.py"
    S.main()
