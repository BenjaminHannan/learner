"""Exp 86: Simple English Wikipedia reading corpus extractor (Muse).

Raw data only: streams the official simplewiki pages-articles-multistream
bz2, strips wikitext with a plain stdlib stripper, and writes declarative
fact-like sentences. Never touches the notebook or weights.

Only imports: stdlib + numpy.

Outputs (into --out, default data/open/simplewiki86/):
  sentences.jsonl  up to --target kept sentences (JSON per line:
                   id, page, section, text, words)
  heldout.jsonl    --heldout sentences stratified by page (seed 86)
  counts.json      pages seen, kept, drops per filter, vocab size,
                   residue check, timing, source provenance
  verbs_top50.json top-50 relation-ish verbs by sentence count
  vocab.txt        sorted vocabulary (lowercase a-z words)

Run (Mac CPU):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_simplewiki86_extract.py
"""

import argparse
import bz2
import hashlib
import html
import json
import os
import random
import re
import sys
import time
import urllib.request

import numpy as np

DUMP_URL = (
    "https://dumps.wikimedia.org/simplewiki/20260901/"
    "simplewiki-20260901-pages-articles-multistream.xml.bz2"
)
DUMP_DATE = "2026-09-01"
DUMP_SIZE = 385846687  # Content-Length bytes, HEAD 2026-09-22
DUMP_SHA1 = "50152ec5f40669eef3dc7b251d1a025fe3c0bb55"  # published sha1sums.txt

CUE_WORDS = frozenset(
    ["is", "was", "are", "were", "has", "had", "born", "died", "located", "capital"]
)
CUE_PHRASE = "member of"

# Relation-ish verb candidates for the top-50 count (lowercase match).
VERB_LIST = [
    "is", "was", "are", "were", "be", "been", "being", "has", "have", "had",
    "born", "died", "located", "became", "become", "married", "divorced",
    "founded", "elected", "appointed", "named", "called", "built", "opened",
    "established", "joined", "left", "led", "ruled", "served", "worked",
    "wrote", "published", "released", "won", "lost", "defeated", "signed",
    "moved", "lived", "studied", "graduated", "taught", "discovered",
    "invented", "created", "designed", "composed", "directed", "starred",
    "played", "began", "started", "ended", "retired", "resigned", "killed",
    "buried", "crowned", "succeeded", "preceded", "replaced", "merged",
    "split", "renamed", "declared", "announced", "launched", "completed",
    "destroyed", "damaged", "restored", "converted", "sold", "bought",
    "owned", "operated", "managed", "sponsored", "represented", "visits",
    "visited", "awarded", "nominated", "married", "contains", "contain",
    "includes", "include", "covers", "flows", "borders", "lies", "stands",
    "sits", "holds", "makes", "made", "took", "takes", "gave", "gives",
    "became", "known", "considered", "believed", "used", "uses",
]

RE_PAGE = re.compile(r"<page>(.*?)</page>", re.DOTALL)
RE_NS = re.compile(r"<ns>(\d+)</ns>")
RE_TITLE = re.compile(r"<title>(.*?)</title>", re.DOTALL)
RE_TEXT = re.compile(r"<text[^>]*>(.*?)</text>", re.DOTALL)
RE_REDIRECT = re.compile(r"<redirect\s")
RE_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
RE_REF = re.compile(r"<ref[^>/]*>.*?</ref>|<ref[^>]*/>", re.DOTALL | re.IGNORECASE)
RE_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
RE_TABLE = re.compile(r"\{\|.*?\|\}", re.DOTALL)
RE_HTMLTAG = re.compile(r"<[^>]*>")
RE_WIKILINK = re.compile(r"\[\[([^|\]]*\|)?([^\]]*)\]\]")
RE_EXTLINK = re.compile(r"\[https?://[^\s\]]*\s+([^\]]*)\]")
RE_BAREURL = re.compile(r"https?://\S+")
RE_HEADING = re.compile(r"^\s*==+\s*(.*?)\s*==+\s*$")
RE_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")
RE_WORD = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")
RE_VOCAB = re.compile(r"[a-z]+(?:'[a-z]+)?")
NS_PREFIXES_DROP = ("file:", "image:", "category:")


def strip_wikitext(raw):
    """Plain wikitext -> plain text. stdlib only."""
    t = RE_COMMENT.sub(" ", raw)
    t = RE_REF.sub(" ", t)
    for _ in range(20):
        new = RE_TEMPLATE.sub(" ", t)
        if new == t:
            break
        t = new
    for _ in range(5):
        new = RE_TABLE.sub(" ", t)
        if new == t:
            break
        t = new

    def _link(m):
        disp = m.group(2)
        low = (m.group(1) or "").strip().lower()
        if low.startswith(NS_PREFIXES_DROP) or disp.strip().lower().startswith(
            NS_PREFIXES_DROP
        ):
            return " "
        return disp

    t = RE_WIKILINK.sub(_link, t)
    t = RE_EXTLINK.sub(r"\1", t)
    t = RE_BAREURL.sub(" ", t)
    t = RE_HTMLTAG.sub(" ", t)
    t = html.unescape(t)
    t = t.replace("'''", "").replace("''", "")
    lines = []
    for line in t.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith(("{|", "|}", "|-", "|", "!", ";", ":", "*", "#", "----")):
            s = s.lstrip("{|}!|-*#:; ").strip()
            if not s:
                continue
        lines.append(s)
    t = " ".join(lines)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def split_sections(raw_text):
    """Split raw wikitext into (section, raw_chunk) preserving headings."""
    sections = []
    cur_sec = ""
    cur = []
    for line in raw_text.splitlines():
        m = RE_HEADING.match(line)
        if m:
            sections.append((cur_sec, "\n".join(cur)))
            cur_sec = m.group(1).strip()
            cur = []
        else:
            cur.append(line)
    sections.append((cur_sec, "\n".join(cur)))
    return sections


def has_cue(sent_low):
    if CUE_PHRASE in sent_low:
        return True
    for w in RE_WORD.findall(sent_low):
        if w in CUE_WORDS:
            return True
    return False


def sentence_ok(sent):
    """Return (ok, drop_reason)."""
    s = sent.strip().strip("\"'“”‘’").strip()
    if not s:
        return False, "empty"
    if not s.endswith("."):
        return False, "not_declarative_end"
    alpha = re.search(r"[A-Za-z]", s)
    if not alpha or not alpha.group(0).isupper():
        return False, "not_capital_start"
    if any(tok in s for tok in ("{{", "}}", "[[", "]]", "<", ">")):
        return False, "markup_residue"
    if "http" in s.lower() or "=" in s:
        return False, "markup_residue"
    words = RE_WORD.findall(s)
    if len(words) < 4:
        return False, "too_short"
    if len(words) > 30:
        return False, "too_long"
    if not has_cue(s.lower()):
        return False, "no_cue"
    return True, ""


def stable_id(norm):
    return "sw86_" + hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]


def extract(rate_url, target, page_cap, byte_cap, chunk=1 << 20):
    """Stream remote bz2, yield (title, section, sentence) dicts."""
    kept = []
    seen_norm = set()
    drops = {}
    pages_seen = 0
    pages_ns = 0
    pages_redirect = 0
    candidates = 0
    bytes_dl = 0
    hasher = hashlib.sha256()

    def bump(reason):
        drops[reason] = drops.get(reason, 0) + 1

    req = urllib.request.Request(rate_url, headers={"User-Agent": "fable-exp86/1.0"})
    resp = urllib.request.urlopen(req, timeout=60)
    decomp = bz2.BZ2Decompressor()
    pending = b""
    buf = ""
    done = False
    http_eof = False
    try:
        while True:
            if len(kept) >= target or pages_seen >= page_cap or bytes_dl >= byte_cap:
                break
            if not http_eof:
                raw = resp.read(chunk)
                if raw:
                    bytes_dl += len(raw)
                    hasher.update(raw)
                    pending += raw
                else:
                    http_eof = True
            # drain all complete bz2 streams currently in pending
            while pending:
                if decomp.eof:
                    decomp = bz2.BZ2Decompressor()
                try:
                    out = decomp.decompress(pending)
                except EOFError:
                    pending = decomp.unused_data
                    decomp = bz2.BZ2Decompressor()
                    continue
                if decomp.eof:
                    pending = decomp.unused_data
                    decomp = bz2.BZ2Decompressor()
                else:
                    pending = b""
                if out:
                    buf += out.decode("utf-8", errors="ignore")
                if not out and not pending:
                    break  # need more input
            if http_eof and not pending and not buf:
                break
            # process complete pages
            last = 0
            for m in RE_PAGE.finditer(buf):
                block = m.group(1)
                last = m.end()
                pages_seen += 1
                ns = RE_NS.search(block)
                if not ns or ns.group(1) != "0":
                    pages_ns += 1
                    bump("page_ns_skip")
                    continue
                if RE_REDIRECT.search(block):
                    pages_redirect += 1
                    bump("page_redirect")
                    continue
                tm = RE_TITLE.search(block)
                xm = RE_TEXT.search(block)
                if not tm or not xm:
                    bump("page_no_text")
                    continue
                title = html.unescape(tm.group(1)).strip()
                for section, chunk_raw in split_sections(xm.group(1)):
                    plain = strip_wikitext(chunk_raw)
                    if not plain:
                        continue
                    for sent in RE_SENT_SPLIT.split(plain):
                        candidates += 1
                        ok, reason = sentence_ok(sent)
                        if not ok:
                            bump(reason)
                            continue
                        s = sent.strip().strip("\"'“”‘’").strip()
                        s = re.sub(r"\s+", " ", s)
                        norm = s.lower()
                        if norm in seen_norm:
                            bump("exact_dupe")
                            continue
                        seen_norm.add(norm)
                        kept.append(
                            {
                                "id": stable_id(norm),
                                "page": title,
                                "section": section,
                                "text": s,
                                "words": len(RE_WORD.findall(s)),
                            }
                        )
                        if len(kept) >= target:
                            done = True
                            break
                    if done:
                        break
                if done:
                    break
                if pages_seen >= page_cap or len(kept) >= target:
                    break
            buf = buf[last:]
            if len(buf) > (1 << 24):
                # pathologically large single page: drop head to bound memory
                buf = buf[-(1 << 24):]
    finally:
        try:
            resp.close()
        except Exception:
            pass
    stats = {
        "pages_seen": pages_seen,
        "pages_ns_skipped": pages_ns,
        "pages_redirect": pages_redirect,
        "candidates": candidates,
        "drops": drops,
        "kept": len(kept),
        "bytes_downloaded": bytes_dl,
        "bytes_sha256_prefix": hasher.hexdigest(),
    }
    return kept, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/open/simplewiki86")
    ap.add_argument("--url", default=DUMP_URL)
    ap.add_argument("--target", type=int, default=200000)
    ap.add_argument("--heldout", type=int, default=2000)
    ap.add_argument("--check-n", type=int, default=1000)
    ap.add_argument("--page-cap", type=int, default=120000)
    ap.add_argument("--byte-cap", type=int, default=385846687)
    ap.add_argument("--seed", type=int, default=86)
    args = ap.parse_args()

    t0 = time.time()
    kept, stats = extract(args.url, args.target, args.page_cap, args.byte_cap)
    wall_s = time.time() - t0

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "sentences.jsonl"), "w") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Held-out stratified by page (deterministic round-robin, seed 86).
    rng = random.Random(args.seed)
    by_page = {}
    for i, r in enumerate(kept):
        by_page.setdefault(r["page"], []).append(i)
    pages = sorted(by_page)
    rng.shuffle(pages)
    held = []
    round_i = 0
    while len(held) < args.heldout:
        grew = False
        for p in pages:
            idxs = by_page[p]
            if round_i < len(idxs) and len(held) < args.heldout:
                held.append(kept[idxs[round_i]])
                grew = True
        round_i += 1
        if not grew:
            break
    with open(os.path.join(args.out, "heldout.jsonl"), "w") as f:
        for r in held:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Residue check on deterministic 1,000-sample (seed 86), reported per case.
    sample_idx = sorted(rng.sample(range(len(kept)), min(args.check_n, len(kept))))
    residue_hits = [
        kept[i]["id"]
        for i in sample_idx
        if any(t in kept[i]["text"] for t in ("{{", "[[", "<", "]]", "}}"))
    ]

    # Exact-dedup audit.
    norms = [r["text"].lower() for r in kept]

    # Vocabulary + top-50 relation-ish verbs (numpy ranking).
    vocab = set()
    for r in kept:
        vocab.update(RE_VOCAB.findall(r["text"].lower()))
    verb_counts = np.zeros(len(VERB_LIST), dtype=np.int64)
    for n, r in enumerate(kept):
        toks = set(RE_WORD.findall(r["text"].lower()))
        for j, v in enumerate(VERB_LIST):
            if v in toks or (v == "member of" and "member of" in r["text"].lower()):
                verb_counts[j] += 1
    order = np.argsort(-verb_counts, kind="stable")[:50]
    top50 = [
        {"verb": VERB_LIST[j], "sentences": int(verb_counts[j])} for j in order
    ]
    with open(os.path.join(args.out, "verbs_top50.json"), "w") as f:
        json.dump(top50, f, indent=1)
    with open(os.path.join(args.out, "vocab.txt"), "w") as f:
        for w in sorted(vocab):
            f.write(w + "\n")

    counts = {
        "source_url": args.url,
        "source_date": DUMP_DATE,
        "source_size_bytes": DUMP_SIZE,
        "source_sha1_published": DUMP_SHA1,
        "seed": args.seed,
        "wall_seconds": round(wall_s, 1),
        "pages_seen": stats["pages_seen"],
        "pages_ns_skipped": stats["pages_ns_skipped"],
        "pages_redirect": stats["pages_redirect"],
        "candidates": stats["candidates"],
        "dropped_by_filter": stats["drops"],
        "sentences_kept": stats["kept"],
        "heldout": len(held),
        "heldout_pages": len({r["page"] for r in held}),
        "vocabulary_size": len(vocab),
        "residue_check_n": len(sample_idx),
        "residue_check_hits": len(residue_hits),
        "residue_check_hit_ids": residue_hits,
        "exact_dupes_in_file": len(norms) - len(set(norms)),
        "bytes_downloaded": stats["bytes_downloaded"],
        "bytes_sha256_prefix": stats["bytes_sha256_prefix"],
        "marks": {
            "W1_kept_ge_100000": stats["kept"] >= 100000,
            "W2_residue_zero": len(residue_hits) == 0,
            "W3_dedup_exact": (len(norms) - len(set(norms))) == 0,
            "W4_under_25min": wall_s < 25 * 60,
        },
    }
    with open(os.path.join(args.out, "counts.json"), "w") as f:
        json.dump(counts, f, indent=1)

    # 20-sentence random sample (seed 861) for the report.
    rs = random.Random(861)
    for r in rs.sample(kept, min(20, len(kept))):
        print("- [%s | %s] %s" % (r["page"], r["section"] or "lead", r["text"]))
    print(
        "KEPT=%d PAGES=%d HELD=%d VOCAB=%d RESIDUE=%d DUPES=%d WALL_S=%.1f"
        % (
            stats["kept"],
            stats["pages_seen"],
            len(held),
            len(vocab),
            len(residue_hits),
            len(norms) - len(set(norms)),
            wall_s,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
