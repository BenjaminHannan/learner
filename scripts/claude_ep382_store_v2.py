#!/usr/bin/env python3
"""ep-382 memory store, version 2 (benchmarks thread, 2026-09-25). New file only; version 1 (claude_ep382_store.py)
stays as it was. The one change: rows are ranked by the text '<speaker> said, "<text>"' instead of
"<speaker>: <text>" (bm-393b: the colon form cost MiniLM about 5 points of evidence recall). Stored text is
unchanged, word for word. Tested as bm-393c.


Interface: design/v3/30-modes/382-memory-store-interface.md (month-end thread). One append-only store per agent
under <state_dir>/memory382/entries.jsonl. "heard" rows are what someone said, word for word, written by the agent's
turn loop; "note" rows are written by the reading thread's note writer. Nothing here writes a note, and sleep, the
creative tool, the teacher and training environments never call remember() (the notebook write rule).

  store = MemoryStore(state_dir)
  hid = store.remember(text, source="heard", speaker="Wren", turn_ids=[12], said_at="1:56 pm on 8 May, 2023",
                       logged_at="2026-09-25T20:00:00+00:00")
  hits = store.recall("Where did Wren move?", k=10)   # [{id, text, source, speaker, turn_ids, said_at, score}]

recall() ranks by meaning with the stack's frozen MiniLM-L6-v2 (fable_self122_train loader, mean-pooled, cosine,
max 128 wordpieces) and, by default, fuses that ranking with BM25 over the same rows (reciprocal rank fusion,
constant 60): bm-393 found the answer's turn in a top 10 for 56.3% of LoCoMo questions with MiniLM, 51.7% with BM25
and 72.7% with either. mode="minilm" or mode="bm25" gives one ranking alone (for tests). It never rewrites text.
before= keeps only rows whose said_at sorts before it when said_at values are ISO dates; other said_at values are
kept as typed and not filtered (the caller decides). A correction is a new row, never an edit.
"""
from __future__ import annotations

import json
import math
import re
import threading
from collections import Counter
from pathlib import Path

RRF_K = 60
MAX_LEN = 128
SOURCES = ("heard", "note")
_ENC = {}
_LOCK = threading.Lock()


def _toks(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def _encoder():
    with _LOCK:
        if "enc" not in _ENC:
            import fable_self122_train as T
            enc, tok, _ = T.load_encoder(T.resolve_snapshot(None))
            _ENC.update(enc=enc, tok=tok)
    return _ENC["enc"], _ENC["tok"]


def embed(texts: list[str]):
    import torch
    import torch.nn.functional as F
    enc, tok = _encoder()
    outs = []
    with torch.no_grad():
        for i in range(0, len(texts), 64):
            ids, mask, _ = tok.batch(texts[i:i + 64], MAX_LEN)
            h = enc(ids, mask)
            m = mask.unsqueeze(-1).float()
            outs.append(F.normalize((h * m).sum(1) / m.sum(1).clamp_min(1e-6), dim=1))
    return torch.cat(outs) if outs else torch.zeros(0, 384)


def _key_text(row: dict) -> str:
    return f'{row["speaker"]} said, "{row["text"]}"' if row.get("speaker") else row["text"]


class MemoryStore:
    def __init__(self, state_dir: str | Path):
        self.dir = Path(state_dir) / "memory382"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "entries.jsonl"
        self.rows: list[dict] = []
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as fh:
                self.rows = [json.loads(x) for x in fh if x.strip()]
        self._emb = None          # embeddings for self.rows[:len(self._emb)]
        self._n = Counter(r["source"] for r in self.rows)

    # ---------------------------------------------------------------- write
    def remember(self, text: str, *, source: str, speaker: str, turn_ids: list[int], said_at: str | None,
                 logged_at: str) -> str:
        if source not in SOURCES:
            raise ValueError(f"source must be one of {SOURCES}")
        self._n[source] += 1
        rid = f"{source[0]}{self._n[source]:07d}"
        row = {"id": rid, "text": text, "source": source, "speaker": speaker, "turn_ids": list(turn_ids),
               "said_at": said_at, "logged_at": logged_at}
        with open(self.path, "a", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.rows.append(row)
        return rid

    # ---------------------------------------------------------------- read
    def _embeddings(self):
        import torch
        have = 0 if self._emb is None else self._emb.shape[0]
        if have < len(self.rows):
            new = embed([_key_text(r) for r in self.rows[have:]])
            self._emb = new if self._emb is None else torch.cat([self._emb, new])
        return self._emb

    def _bm25(self, idx: list[int], query: str) -> list[int]:
        docs = [_toks(_key_text(self.rows[i])) for i in idx]
        n = len(docs)
        avg = sum(len(d) for d in docs) / max(1, n)
        df = Counter(w for d in docs for w in set(d))
        q = _toks(query)
        scored = []
        for j, d in enumerate(docs):
            tf = Counter(d)
            s = 0.0
            for w in q:
                if w in tf:
                    idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
                    s += idf * tf[w] * 2.5 / (tf[w] + 1.5 * (0.25 + 0.75 * len(d) / avg))
            scored.append((s, j))
        return [idx[j] for _, j in sorted(scored, key=lambda z: (-z[0], z[1]))]

    def _minilm(self, idx: list[int], query: str) -> tuple[list[int], dict]:
        emb = self._embeddings()[idx]
        sims = (embed([query]) @ emb.T)[0]
        order = sims.argsort(descending=True).tolist()
        return [idx[j] for j in order], {idx[j]: float(sims[j]) for j in range(len(idx))}

    def recall(self, query: str, *, k: int = 10, sources: set[str] | None = None, before: str | None = None,
               mode: str = "fused") -> list[dict]:
        idx = [i for i, r in enumerate(self.rows) if (sources is None or r["source"] in sources)]
        if before is not None:
            idx = [i for i in idx if not _iso(self.rows[i]["said_at"]) or self.rows[i]["said_at"] < before]
        if not idx:
            return []
        if mode == "bm25":
            order = self._bm25(idx, query)
            score = {i: 1.0 / (RRF_K + r) for r, i in enumerate(order)}
        else:
            m_order, cos = self._minilm(idx, query)
            if mode == "minilm":
                order, score = m_order, cos
            elif mode == "fused":
                b_order = self._bm25(idx, query)
                score = Counter()
                for r, i in enumerate(m_order):
                    score[i] += 1.0 / (RRF_K + r)
                for r, i in enumerate(b_order):
                    score[i] += 1.0 / (RRF_K + r)
                order = sorted(idx, key=lambda i: (-score[i], i))
            else:
                raise ValueError("mode must be fused, minilm or bm25")
        return [dict(self.rows[i], score=round(float(score[i]), 6)) for i in order[:k]]


def _iso(s: str | None) -> bool:
    return bool(s) and re.fullmatch(r"\d{4}-\d{2}-\d{2}([T ].*)?", s) is not None
