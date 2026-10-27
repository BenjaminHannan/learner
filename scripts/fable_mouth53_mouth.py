#!/usr/bin/env python3
"""Experiment 53 (MOUTH) -- borrowed decoder + OUR head/format + faithfulness brake.

The mouth turns a RESULT RECORD (status/name/relations/fields, exactly as the
reasoner produces) into one plain English sentence.

Borrowed part: HuggingFaceTB/SmolLM2-360M-Instruct (Apache-2.0) as the decoder.
Ours: the record serialization (-> prompt), the fine-tuned RECORD ADAPTER
(new input-embedding rows for record tokens + last transformer block + an
untied lm_head), and the FAITHFULNESS BRAKE below in plain software.

Ben's rulings enforced here:
  * the decoder must never state a fact not in the record -> the brake sends
    ANY sentence with an out-of-record content string back to TemplateMouth;
  * MISSING_FACT must say it does not know and what is missing -> all
    MISSING targets carry "don't know" + subject + relation, and the brake
    also falls back when an OK answer is absent from the sentence.

Protocol (scripts/fable_agent_loop.py): Mouth.say(record) -> str.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402
from fable_wire51_adapters import TemplateMouth  # noqa: E402  (read-only fallback)

MODEL_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"

# New input-embedding rows for record tokens (the trainable "record adapter"
# input side). Added to the tokenizer; the body stays frozen.
SPEC_TOKENS = ["<REC>", "</REC>", "<ST>", "<NM>", "<RL>", "<AN>", "<SB>",
               "<HP>", "<SC>", "<FD>"]

MAX_NEW_TOKENS = 32

# Fixed function-word list for the brake. Every non-record word the decoder may
# emit must be on this list, else the sentence falls back to TemplateMouth.
# It covers the full template vocabulary of fable_mouth53_data.py plus generic
# function words (frozen literal; coverage is machine-checked in score.py).
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


def untie_lm_head(model):
    """Give the model OUR head: clone lm_head off the tied input embeddings.

    SmolLM2 ties lm_head.weight to the input embeddings. Training a tied head
    would move every input row, so both train and inference untie first: the
    body (including all old input rows) stays frozen while the head is ours.
    Must be called after resize_token_embeddings, before any adapter load.
    """
    import torch
    emb = model.get_input_embeddings().weight
    if model.lm_head.weight is emb:
        model.lm_head.weight = torch.nn.Parameter(emb.detach().clone())
    return model


def serialize(record: dict) -> str:
    """Record -> decoder prompt. Plain tagged text using the record tokens."""
    fields = record.get("fields") or {}
    parts = ["<REC>", "<ST>", str(record.get("status", "")),
             "<NM>", str(record.get("name", "")),
             "<RL>", " ".join(str(r) for r in (record.get("relations") or []))]
    for tag, key in (("<AN>", "answer"), ("<SB>", "subject"), ("<FD>", "relation"),
                     ("<FD>", "value"), ("<FD>", "choices"), ("<FD>", "reason"),
                     ("<HP>", "hop"), ("<SC>", "source")):
        val = fields.get(key)
        if val is not None and val != "":
            parts += [tag, str(val)]
    parts += ["</REC>"]
    return " ".join(p for p in parts if p)


# Rule-based status classifier (shared by score.py for O2). Order matters:
# UNKNOWN ("don't know anyone") before MISSING ("don't know").
def classify(sentence: str) -> str:
    s = sentence.lower()
    if "could not use that" in s:
        return "BAD_REQUEST"
    if "don't know anyone" in s or "do not know anyone" in s:
        return "UNKNOWN_ENTITY"
    if "more than one" in s:
        return "AMBIGUOUS"
    if "not someone i can look up" in s:
        return "BROKEN_CHAIN"
    if "don't know" in s or "do not know" in s:
        return "MISSING_FACT"
    return "OK"


def brake_check(sentence: str, record: dict) -> tuple[bool, str]:
    """Plain-software faithfulness brake. Returns (ok, reason)."""
    if record.get("kind") != "answer":
        return True, "passthrough-kind"
    if not sentence or not sentence.strip():
        return False, "empty decode (silence states nothing)"
    allowed = record_content_words(record) | FUNCTION_WORDS
    for w in _words(sentence):
        b = _base_word(w)
        if b in allowed or b == "":
            continue
        # Digits are content too: only permit them when their exact token is
        # represented by the record (for example E0003 or F00012).
        if w.isdigit() and w in allowed:
            continue
        return False, f"word {w!r} not in record or function list"
    if record.get("status") == "OK":
        ans = str((record.get("fields") or {}).get("answer", ""))
        if ans and ans.lower() not in sentence.lower():
            return False, "OK answer missing from sentence"
    return True, "ok"


class Mouth:
    """Mouth Protocol: say(record) -> one English sentence, brake enforced."""

    def __init__(self, adapter_dir: str | Path | None = None, fast: bool = False) -> None:
        self.adapter_dir = Path(adapter_dir) if adapter_dir else None
        self._fallback = TemplateMouth()
        self._model = None
        self._tok = None
        self.says = 0
        self.fallbacks = 0
        self.reasons: dict[str, int] = {}

    # ------------------------------------------------------------- model
    def _load(self):
        if self._model is not None:
            return self._model, self._tok
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(MODEL_ID, local_files_only=True,
                                            trust_remote_code=False)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID, local_files_only=True, trust_remote_code=False,
            torch_dtype=torch.float32)
        added = tok.add_special_tokens({"additional_special_tokens": SPEC_TOKENS})
        assert added == len(SPEC_TOKENS), added
        model.resize_token_embeddings(len(tok))
        untie_lm_head(model)
        if self.adapter_dir is not None:
            state = torch.load(self.adapter_dir / "adapter.pt", map_location="cpu",
                               weights_only=True)
            if isinstance(state, dict) and "model" in state:
                state = state["model"]  # train.py wraps tensors under "model"
            model.load_state_dict(state, strict=False)
        model.eval()
        for p in model.parameters():
            p.requires_grad_(False)
        self._model, self._tok = model, tok
        return model, tok

    def _decode_raw(self, records: list[dict]) -> list[str]:
        return self._decode_raw_batched(records, batch_size=1)

    def _decode_raw_batched(self, records: list[dict], batch_size: int = 8) -> list[str]:
        import torch
        model, tok = self._load()
        out: list[str] = [""] * len(records)
        with torch.inference_mode():
            for start in range(0, len(records), batch_size):
                chunk = records[start:start + batch_size]
                prompts = [serialize(r) + " " for r in chunk]
                enc = tok(prompts, return_tensors="pt", padding=True, truncation=True,
                          max_length=128)
                generated = model.generate(
                    enc["input_ids"], attention_mask=enc["attention_mask"],
                    max_new_tokens=MAX_NEW_TOKENS, do_sample=False,
                    pad_token_id=tok.eos_token_id, eos_token_id=tok.eos_token_id)
                for i, prompt in enumerate(prompts):
                    plen = enc["attention_mask"][i].sum().item()
                    new = generated[i][plen:]
                    text = tok.decode(new, skip_special_tokens=True).strip()
                    out[start + i] = text.split("\n")[0].strip()
        return out

    # ------------------------------------------------------------- protocol
    def say_raw(self, record: dict) -> str:
        """The borrowed decoder's sentence BEFORE the brake (for scoring)."""
        kind = record.get("kind")
        if kind in ("write", "clarify", "note"):
            return record.get("text", "")
        if kind != "answer":
            return ""
        return self._decode_raw([record])[0]

    def say(self, record: dict) -> str:
        kind = record.get("kind")
        if kind in ("write", "clarify", "note"):
            return record.get("text", "")
        if kind != "answer":
            return ""
        self.says += 1
        try:
            raw = self._decode_raw([record])[0]
        except Exception:
            raw = ""
        ok, reason = brake_check(raw, record) if raw else (False, "empty decode")
        if ok:
            return raw
        self.fallbacks += 1
        self.reasons[reason] = self.reasons.get(reason, 0) + 1
        return self._fallback.say(record)
