"""Tiny OpenAI-compatible embedding server for ShinkaEvolve's code-novelty check.

This container has no OpenAI key, so ShinkaEvolve's default embedding model
(text-embedding-3-small) is unavailable. ShinkaEvolve accepts
`local/<name>@http://host:port/v1` embedding models, so this server answers
POST /v1/embeddings with a deterministic bag-of-code-tokens vector:

  - comments, docstrings and string literals are removed, so two programs
    that differ only in prose are treated as the same code;
  - features are code-token unigrams and bigrams, hashed into DIM buckets,
    with sublinear term frequency, then L2-normalised.

Cosine similarity between two vectors is then a measure of shared code
structure. It is cruder than a neural embedding: it sees renamed variables
as different code. The threshold used with it is calibrated in CARD.md.

Run: python research/shinka/local_embed_server.py --port 8765
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
import tokenize
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DIM = 4096


def code_tokens(src: str) -> list[str]:
    """Return code tokens with comments, strings and docstrings dropped."""
    out: list[str] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING, tokenize.NL,
                            tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT,
                            tokenize.ENDMARKER):
                continue
            if tok.type == tokenize.NUMBER:
                out.append("<num>")
            elif tok.string.strip():
                out.append(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        out = src.split()
    return out


def _bucket(feature: str) -> int:
    return int.from_bytes(hashlib.blake2b(feature.encode(), digest_size=8).digest(), "little") % DIM


def embed(src: str, toks: list[str] | None = None) -> list[float]:
    toks = code_tokens(src) if toks is None else toks
    counts: dict[int, int] = {}
    feats = toks + [a + " " + b for a, b in zip(toks, toks[1:])]
    for f in feats:
        b = _bucket(f)
        counts[b] = counts.get(b, 0) + 1
    vec = [0.0] * DIM
    for b, c in counts.items():
        vec[b] = 1.0 + math.log(c)
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            inputs = body.get("input", [])
            if isinstance(inputs, str):
                inputs = [inputs]
            if not all(isinstance(s, str) for s in inputs):
                raise ValueError("input must be a string or a list of strings")
        except (ValueError, AttributeError) as exc:
            sys.stderr.write(f"bad embedding request: {exc}\n")
            self.send_error(400, str(exc))
            return
        toks = [code_tokens(s) for s in inputs]
        data = [{"object": "embedding", "index": i, "embedding": embed(s, t)}
                for i, (s, t) in enumerate(zip(inputs, toks))]
        n_tok = sum(len(t) for t in toks)
        payload = json.dumps({
            "object": "list", "data": data, "model": body.get("model", "codebag"),
            "usage": {"prompt_tokens": n_tok, "total_tokens": n_tok},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_request(self, code="-", size="-"):
        pass  # successful requests are not logged; errors still go to stderr


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
