#!/usr/bin/env python3
"""Experiment 120 (talker mouth PREP) — shared codec, record format, brake, scorer pieces.

The ONE change vs exp 53: the mouth decoder is OUR OWN from-scratch talker
(scripts/fable_talker101_model.py, 28.85M decoder + copy head) instead of the
borrowed SmolLM2. Everything else is the same shape: serialized record words
as prefix, plain-English sentence as target, the copy head copies names/values
from the record, and the plain-software faithfulness brake + TemplateMouth
fallback stay authoritative.

This module is dependency-light on purpose: stdlib + torch only (no
`transformers`, no `tokenizers`), so it runs under the mandated Mac command.
The BPE codec below is a small pure-Python reader of the talker101
tokenizer.json (GPT-2-style ByteLevel). It is validated by round-trip +
the CPU smoke, not claimed to be bit-identical to the Rust encoder; any
segmentation drift is absorbed by fine-tuning since the id space is shared.

Record format (exp-53-compatible keys; statuses are the notebook-answer set):
  {"kind": "answer", "status": OK | UNKNOWN | ABSTAIN | CLARIFY | SAVED | FORGOT,
   "name": entity, "relations": [...],
   "fields": {"answer"|"subject"|"relation"|"value"|"choices"|"reason"|"hop"|"trail"|"ids",
              "source": taught | inferred | sleep-derived | web-verified}}
Status anchors (each sentence carries exactly one; the rule-based `classify`
reads it back, same job as exp 53's anchors):
  OK      -> the answer verbatim (no anchor; default class)
  UNKNOWN -> "don't know"
  ABSTAIN -> "can't answer that"
  CLARIFY -> "do you mean" / "which one"
  SAVED   -> "saved"
  FORGOT  -> "forgotten"
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# --------------------------------------------------------------------------
# Function-word list for the brake: exp 53's frozen list verbatim, plus a small
# documented extension (status words "forgotten"/"forgot" for FORGOT, and 14
# generic non-fact words the new templates need: beyond doubt fear guess
# notebook plain record right see shame time truth simple alas, plus changed
# heard keep last longer passed somehow something two written, plus got wrote
# abstain kept). None names a
# fact; the data script machine-checks brake coverage on all 3,500 pairs.
# --------------------------------------------------------------------------

FUNCTION_WORDS = frozenset("""
a about above afraid after again ago all also am an and another any anyone
anyone are around as ask at away be been before being below between both but
by call called can cannot come could did didn't do does doesn't doing done
down each either else even ever every few for found from further get go going
gone had has have having he her here hers herself him his how however i if
in into is isn't it its itself just know look me mean more most my myself
new no nobody none nor not nothing now of off on once one online only or
other ought our ours out over own read said same say says shall should since
so some someone sorry still such tell than that that's the their theirs them
themselves then there these they this those though through thru to told too
turned under until up use used using very was wasn't we were what when where
which while who whom whose why will with would yet you your yours yourself
yourselves afraid ago ah alright also although am anyway around away because
before besides bye cannot dare despite did each else enough etc ever every
except further goodbye had hardly hello hey hi however indeed instead later
least let's many may maybe might must neither never nor nowhere now oh okay
ok often once only onto oops perhaps please quite rather really shall sure
t then there therefore though thus together too toward towards truly twice
upon whether whose within without won't would yeah yes yesterday yet you've
you're you've yours truly mine ours yours his hers its theirs myself himself
herself itself ourselves yourselves who've what's who's where's when's why's
how's that'll there'll a.m p.m thru couldn't shouldn't wouldn't mustn't
need needs needed needing seem seems seemed seeming become becomes became
become becoming stay stays stayed staying remain remains remained afield
ahead alike apart aside astray backward forwards henceforth hither inside
instead likely meanwhile moreover namely nearby nearly next oft often onward
otherwise outside over pending per plus round since so far somewhere sometime
sometimes somewhat soon then thence thereabout thereby therein thereof
thereon thereto therewith together twice underfoot upward upwardly via whence
whereabout whereby wherein whereof whereon whereto wherewith within without
yonder looked looks looking knows knew known knows say says saying says
found finds finding thinks thought going goes went gone come comes coming
came stop stopped stopping stops stopped cannot can't won't don't doesn't
didn't isn't aren't wasn't weren't haven't hasn't hadn't wouldn't shouldn't
couldn't mustn't needn't oughtn't shan't let's that's there's here's what's
who's where's when's why's how's i'm you're he's she's it's we're they're
i've you've we've they've i'll you'll he'll she'll it'll we'll they'll i'd
you'd he'd she'd we'd they'd mine okay ok hi hey hello bye goodbye sorry
thanks thank please yes no yeah yep nope well oh ah oops huh um hmm
answer taught fact missing person name saved work question
forgotten forgot
beyond doubt fear guess notebook plain record right see shame time truth simple alas
changed heard keep last longer passed somehow something two written
got wrote abstain kept
""".split())

_WORD = re.compile(r"[A-Za-z0-9']+")


def _words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _base_word(w: str) -> str:
    if w.endswith("'s"):
        w = w[:-2]
    return w.strip("'") if len(w) > 2 else w


def record_content_words(record: dict) -> set[str]:
    """Every content string the record allows the sentence to use."""
    out: set[str] = set()
    for key in ("name",):
        val = record.get(key)
        if val:
            out.update(_base_word(w) for w in _words(str(val)))
    for rel in record.get("relations") or []:
        out.update(_base_word(w) for w in _words(str(rel).replace("_", " ")))
    fields = record.get("fields") or {}
    for key in ("answer", "subject", "relation", "value", "name", "choices",
                "reason", "trail", "ids", "source"):
        val = fields.get(key)
        if val is None:
            continue
        if isinstance(val, (list, tuple)):
            for item in val:
                out.update(_base_word(w) for w in _words(str(item).replace("_", " ")))
        else:
            out.update(_base_word(w) for w in _words(str(val).replace("_", " ")))
    out.discard("")
    return out


def serialize(record: dict) -> str:
    """Record -> decoder prefix. Plain-word markers (no new vocabulary: the
    talker101 BPE has no spare special rows, and growing our own embedding
    would break clean resume from any talker101 checkpoint)."""
    fields = record.get("fields") or {}

    def clean(v) -> str:
        return str(v).replace("_", " ")

    parts = ["record", "status", clean(record.get("status", "")),
             "name", clean(record.get("name", "")),
             "relations", " ".join(clean(r) for r in (record.get("relations") or []))]
    for tag, key in (("answer", "answer"), ("subject", "subject"),
                     ("relation", "relation"), ("value", "value"),
                     ("choices", "choices"), ("reason", "reason"),
                     ("hop", "hop"), ("source", "source")):
        val = fields.get(key)
        if val is not None and val != "":
            parts += [tag, clean(val)]
    parts += ["end"]
    return " ".join(p for p in parts if p)


def classify(sentence: str) -> str:
    """Rule-based status read-back. Order matters: specific anchors first."""
    s = sentence.lower()
    if "forgotten" in s or "forgot " in s or s.endswith("forgot"):
        return "FORGOT"
    if "saved" in s:
        return "SAVED"
    if "do you mean" in s or "which one" in s:
        return "CLARIFY"
    if "can't answer that" in s or "cannot answer that" in s:
        return "ABSTAIN"
    if "don't know" in s or "do not know" in s:
        return "UNKNOWN"
    return "OK"


def fallback_say(record: dict) -> str:
    """Deterministic template safety net: one fixed sentence per notebook-answer
    status, built only from record strings + function words. The contract's
    TemplateMouth cannot serve here — it does not know these six statuses
    (it echoes e.g. 'UNKNOWN', which the brake rightly rejects)."""
    kind = record.get("kind")
    if kind in ("write", "clarify", "note"):
        return record.get("text", "")
    if kind != "answer":
        return ""
    fields = dict(record.get("fields") or {})
    status = record.get("status")
    owner = "'s ".join([str(record.get("name", ""))]
                       + [str(p).replace("_", " ") for p in (record.get("relations") or [])])
    if status == "OK":
        s = f"{owner} is {fields.get('answer')}."
        if fields.get("source") == "web-verified":
            s += " (I read that online; you didn't tell me.)"
        return s
    if status == "UNKNOWN":
        rel = str(fields.get("relation", "")).replace("_", " ")
        return f"I don't know {fields.get('subject')}'s {rel}."
    if status == "ABSTAIN":
        return f"I can't answer that: {fields.get('reason')}."
    if status == "CLARIFY":
        return f"Which {fields.get('name')} do you mean: {fields.get('choices')}?"
    if status == "SAVED":
        return f"Saved: {owner} is {fields.get('answer')}."
    if status == "FORGOT":
        rel = str(fields.get("relation", "")).replace("_", " ")
        return f"I've forgotten {fields.get('subject')}'s {rel}."
    return ""


def brake_check(sentence: str, record: dict) -> tuple[bool, str]:
    """Plain-software faithfulness brake (same design as exp 53)."""
    if record.get("kind") != "answer":
        return True, "passthrough-kind"
    if not sentence or not sentence.strip():
        return False, "empty decode (silence states nothing)"
    allowed = record_content_words(record) | FUNCTION_WORDS
    for w in _words(sentence):
        b = _base_word(w)
        if b in allowed or b == "":
            continue
        if w.isdigit() and w in allowed:
            continue
        return False, f"word {w!r} not in record or function list"
    if record.get("status") == "OK":
        ans = str((record.get("fields") or {}).get("answer", ""))
        if ans and ans.lower() not in sentence.lower():
            return False, "OK answer missing from sentence"
    return True, "ok"


# --------------------------------------------------------------------------
# Pure-Python BPE codec for the talker101 tokenizer.json (ByteLevel BPE).
# --------------------------------------------------------------------------

def _bytes_to_unicode() -> dict[int, str]:
    bs = (list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1))
          + list(range(ord("®"), ord("ÿ") + 1)))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {b: chr(c) for b, c in zip(bs, cs)}


_BYTE_ENC = _bytes_to_unicode()
_BYTE_DEC = {c: b for b, c in _BYTE_ENC.items()}
_GPT2_PAT = re.compile(
    r"'s|'t|'re|'ve|'m|'ll|'d| ?[^\W\d_]+| ?\d+| ?[^\s\w]+|\s+(?!\S)|\s+")


class Codec:
    """Minimal encoder/decoder over a talker101 tokenizer.json."""

    def __init__(self, tok_path: str | Path):
        d = json.loads(Path(tok_path).read_text(encoding="utf-8"))
        self.vocab: dict[str, int] = dict(d["model"]["vocab"])
        self.id2tok: dict[int, str] = {i: t for t, i in self.vocab.items()}
        self.rank: dict[tuple[str, str], int] = {
            (a, b): i for i, (a, b) in enumerate(d["model"]["merges"])}
        added = {a["content"]: a["id"] for a in d.get("added_tokens", [])}
        self.eos = added.get("<eos>", 0)
        self.unk = added.get("<unk>", 1)
        self.vocab_size = len(self.vocab)

    def _bpe(self, word: tuple[str, ...]) -> list[str]:
        parts = list(word)
        while len(parts) > 1:
            best, bi = None, -1
            for i in range(len(parts) - 1):
                r = self.rank.get((parts[i], parts[i + 1]))
                if r is not None and (best is None or r < best):
                    best, bi = r, i
            if best is None:
                break
            parts = parts[:bi] + [parts[bi] + parts[bi + 1]] + parts[bi + 2:]
        return parts

    def encode(self, text: str) -> list[int]:
        out: list[int] = []
        for m in _GPT2_PAT.finditer(text):
            tok = m.group(0)
            if not tok:
                continue
            if tok.strip() == "" and tok != " ":
                # whitespace runs other than a single space carry no BPE
                # meaning; fold them to a single space when possible
                tok = " "
            uni = "".join(_BYTE_ENC[b] for b in tok.encode("utf-8"))
            for piece in self._bpe(tuple(uni)):
                vid = self.vocab.get(piece)
                if vid is None:
                    raise KeyError(f"BPE piece {piece!r} not in vocab")
                out.append(vid)
        # coverage assert: the regex must consume every non-space char
        covered = "".join(m.group(0) for m in _GPT2_PAT.finditer(text))
        if covered != text:
            raise ValueError(f"pretokeniser dropped chars in {text!r}")
        return out

    def decode(self, ids: list[int]) -> str:
        chars: list[str] = []
        for i in ids:
            if i == self.eos:
                break
            t = self.id2tok.get(int(i))
            if t is None:
                continue
            chars.append(t)
        text = "".join(chars)
        try:
            raw = bytes(_BYTE_DEC[c] for c in text)
        except KeyError:
            raw = bytes(_BYTE_DEC[c] for c in text if c in _BYTE_DEC)
        return raw.decode("utf-8", errors="replace")


# --------------------------------------------------------------------------
# Mouth protocol: say(record) -> str, brake enforced, template fallback.
# --------------------------------------------------------------------------

class _FallbackMouth:
    """say(record) -> str via fallback_say (same Protocol shape as wire51's
    TemplateMouth, but status-aware for our six notebook-answer statuses)."""

    def say(self, record: dict) -> str:
        return fallback_say(record)


class TalkerMouth:
    """Mouth slot backed by OUR talker + the plain-software brake."""

    def __init__(self, ckpt_path: str | Path | None = None,
                 tok_path: str | Path | None = None) -> None:
        self.ckpt_path = Path(ckpt_path) if ckpt_path else None
        self.tok_path = Path(tok_path) if tok_path else None
        self._fallback = _FallbackMouth()
        self._model = None
        self._codec: Codec | None = None
        self.says = 0
        self.fallbacks = 0
        self.reasons: dict[str, int] = {}

    def _load(self):
        if self._model is not None:
            return self._model, self._codec
        import torch
        from fable_talker101_model import Talker101
        assert self.ckpt_path is not None and self.tok_path is not None
        self._codec = Codec(self.tok_path)
        ck = torch.load(self.ckpt_path, map_location="cpu", weights_only=False)
        model = Talker101()
        model.load_state_dict(ck["model"])
        model.eval()
        for p in model.parameters():
            p.requires_grad_(False)
        self._model = model
        return model, self._codec

    @staticmethod
    def _mixture_next(model, cur: list[int], device: str = "cpu"):
        import torch
        x = torch.tensor(cur, dtype=torch.long).unsqueeze(0)
        with torch.inference_mode():
            out = model(x)
        logits = out["logits"][0, -1]
        pv = torch.softmax(logits, dim=-1)
        pg = float(out["p_gen"][0, -1, 0])
        attn = out["copy_attn"][0, -1, :len(cur)]
        mix = pg * pv
        cw = (1.0 - pg) * attn
        for k, tid in enumerate(cur):
            mix[int(tid)] += float(cw[k])
        return int(torch.argmax(mix).item()), pg

    def _decode_raw(self, record: dict, max_new: int = 32) -> tuple[str, list[float]]:
        import torch
        torch.set_num_threads(1)
        model, codec = self._load()
        cur = codec.encode(serialize(record))
        pgs: list[float] = []
        new: list[int] = []
        for _ in range(max_new):
            nxt, pg = self._mixture_next(model, cur)
            pgs.append(pg)
            if nxt == codec.eos:
                break
            cur.append(nxt)
            new.append(nxt)
            if len(cur) >= 508:
                break
        return codec.decode(new).strip().split("\n")[0].strip(), pgs

    def say_raw(self, record: dict, max_new: int = 32) -> str:
        kind = record.get("kind")
        if kind in ("write", "clarify", "note"):
            return record.get("text", "")
        if kind != "answer":
            return ""
        raw, _ = self._decode_raw(record, max_new)
        return raw

    def say(self, record: dict, max_new: int = 32) -> str:
        kind = record.get("kind")
        if kind in ("write", "clarify", "note"):
            return record.get("text", "")
        if kind != "answer":
            return ""
        self.says += 1
        try:
            raw, _ = self._decode_raw(record, max_new)
        except Exception:
            raw = ""
        ok, reason = brake_check(raw, record) if raw else (False, "empty decode")
        if ok:
            return raw
        self.fallbacks += 1
        self.reasons[reason] = self.reasons.get(reason, 0) + 1
        return self._fallback.say(record)
