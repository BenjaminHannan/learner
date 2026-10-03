"""Agent 4 (WIRING) -- adapters that fill the glue-loop Protocols with the real parts.

    Ears      fable_listening_english (Qwen bridge, placeholder model) with a
              deterministic FakeEars fallback when the bridge is down; the slot is
              exactly ``hear(turn) -> list[action]`` so a frame-producing model
              (doc 47/ears rung 2) can be dropped in later without touching this file.
    Reasoner  fable_reasoner50 (agent 3) if it appears, else fable_reasoner44 wrapped:
              the hard-coded hop loop over the NOTEBOOK is authoritative; the trained
              64-number router is loaded from the sealed Exp 44 runs and used as a
              logged cross-check on chains it can encode (plus the word-install path).
    Sleeper   the Exp 46 recipe (robust loss + harden-before-gate + unchanged gate),
              called by the loop ONLY when the experience log is full; plus a
              deterministic invariant audit of the log/notebook.
    Thinker   fable_thinking_m2.Thinking (web search, quarantine).
    Mouth     deterministic templates from the notebook's own status strings.

Nothing outside this file is edited; every other module is imported and wrapped.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A                     # noqa: E402  (Protocols + FakeEars)
import fable_listening_english as LE             # noqa: E402  (Qwen-bridge English ears)
import fable_notebook_contract as C              # noqa: E402

PICK_LINE = re.compile(r"^\s*pick\s+(E\d+)\s*$", re.I)
MAX_HOPS = 3


# --------------------------------------------------------------------------- Ears
def _unquote(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text[1:-1]
    return text


def line_to_action(line: str) -> dict:
    """One M1 structured line (what the English module renders) -> one loop action."""
    words = line.split()
    if not words:
        return {"act": "clarify", "text": "I didn't catch anything."}
    act = words[0]
    if act in ("person", "alias", "forget", "quote"):
        return {"act": act, "line": line}
    if act in ("teach", "correct"):
        if "->" in line:
            left, value = line.split("->", 1)
            is_person = True
        elif "=" in line:
            left, value = line.split("=", 1)
            is_person = False
        else:
            return {"act": "clarify", "text": "I couldn't read that statement."}
        head = left.split()
        if len(head) < 3:
            return {"act": "clarify", "text": "I couldn't read that statement."}
        return {"act": act, "name": _unquote(" ".join(head[1:-1])),
                "relation": head[-1], "value": _unquote(value), "is_person": is_person}
    if act == "ask":
        if len(words) < 3:
            return {"act": "clarify", "text": "I couldn't read that question."}
        return {"act": "ask", "name": _unquote(" ".join(words[1:2])),
                "relations": [_unquote(w) for w in words[2:]]}
    if act in ("yes", "no"):
        return {"act": "answer", "value": act}
    if act == "pick" and len(words) >= 2:
        return {"act": "answer", "value": "pick", "id": words[1].upper()}
    if act == "undo":
        return {"act": "clarify", "text": "Undo is not wired into the loop yet."}
    return {"act": "clarify", "text": "I didn't understand that."}


class EnglishEars:
    """Ears slot: English turn -> loop actions.  Qwen bridge first, FakeEars if it is down."""

    def __init__(self, mode: str = "auto", base_url: str | None = None,
                 model: str | None = None, echo_confirm: bool = False) -> None:
        self.mode = mode                       # auto | english | fake
        self.base_url = base_url or LE.DEFAULT_BASE_URL
        self.model = model or LE.DEFAULT_MODEL
        # The English module offers an EXTRA echo-back before writes whose confidence
        # is below 0.98 (confirm_before_write).  The notebook's own CONFLICT /
        # AMBIGUOUS confirmations are authoritative and always on; this second layer
        # is off by default (a two-turn protocol the script and REPL do not assume)
        # and can be switched on with echo_confirm=True / --echo.
        self.echo_confirm = echo_confirm
        self._fake = A.FakeEars()
        self._listening = None
        self._notebook = None
        self._bundle: dict | None = None       # adapter-owned echo confirmation
        self.bridge_failures = 0
        self.fallback_turns = 0
        self.last_source = "english"

    def bind(self, listening, notebook) -> None:
        """Called once after the AgentLoop exists (the loop owns both objects)."""
        self._listening, self._notebook = listening, notebook

    # ------------------------------------------------------------------ hearing
    def hear(self, turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        if not text:
            return [{"act": "clarify", "text": "I didn't catch anything."}]

        if self.mode == "fake":
            self.last_source = "fake"
            return self._fake.hear(text)

        found = PICK_LINE.match(text)
        if found:                       # structured reply: never needs the model
            self.last_source = "english-deterministic"
            return [{"act": "answer", "value": "pick", "id": found.group(1).upper()}]

        if self._bundle is not None:
            handled = self._answer_bundle(text)
            if handled is not None:
                return handled

        if self.mode == "english" or self.mode == "auto":
            try:
                actions = self._hear_english(text)
                if actions is not None:
                    return actions
            except (RuntimeError, OSError, TimeoutError) as exc:
                self.bridge_failures += 1
                if self.mode == "english":
                    raise
                # auto: the bridge is down -- fall back, keep talking
                self.fallback_turns += 1
                self.last_source = "fake-fallback"
                return self._fake.hear(text)
        self.last_source = "fake"
        return self._fake.hear(text)

    def _hear_english(self, text: str) -> list[dict] | None:
        pending = LE._listener_pending(self._listening) if self._listening is not None else None
        known = LE._known_names_from_notebook(self._notebook, []) if self._notebook is not None else []
        try:
            proposal = LE.parse_english_proposal(text, pending, known,
                                                 base_url=self.base_url, model=self.model)
        except LE.ParseRejected as exc:
            self.last_source = "english"
            return [{"act": "clarify",
                     "text": f"I didn't trust that parse, so I saved nothing: {exc}"}]
        doc = proposal["doc"]
        if doc.get("unsure"):
            self.last_source = "english"
            reason = doc.get("unsure_reason") or "I'm not sure what you meant."
            return [{"act": "clarify", "text": reason + " Nothing was saved."}]
        lines = proposal["lines"]
        if self.echo_confirm and proposal.get("confirm_before_write") and lines:
            self.last_source = "english"
            self._bundle = {"raw": text, "lines": lines}
            return [{"act": "clarify", "text": "I heard: " + "; ".join(lines) + ". Save that?"}]
        self.last_source = "english"
        return [line_to_action(line) for line in lines]      # smalltalk renders to nothing

    def _answer_bundle(self, text: str) -> list[dict] | None:
        bundle, self._bundle = self._bundle, None
        if LE.YES_PATTERN.match(text):
            return [line_to_action(line) for line in bundle["lines"]]
        if LE.NO_PATTERN.match(text):
            return [{"act": "clarify", "text": "Cancelled. Nothing was saved."}]
        return None                                         # unrelated: process as fresh


# --------------------------------------------------------------------------- Mouth
class TemplateMouth:
    """Mouth slot: one English sentence from the result record, via the notebook's
    own deterministic status templates.  Content words come from the record only."""

    def say(self, record: dict) -> str:
        kind = record.get("kind")
        if kind in ("write", "clarify", "note"):
            return record.get("text", "")
        if kind != "answer":
            return ""
        status, fields = record.get("status"), dict(record.get("fields") or {})
        if status == C.OK:
            owner = "'s ".join([record["name"]] + [part.replace("_", " ")
                                                   for part in record["relations"]])
            sentence = f"{owner} is {fields.get('answer')}."
            if fields.get("source") == "web-verified":
                sentence += " (I read that online; you didn't tell me.)"
            return sentence
        return C.Result(status, fields).say()


# ------------------------------------------------------------------------ Reasoner
class NotebookReasoner:
    """Reasoner slot over the live NOTEBOOK.

    * Prefers agent 3's ``fable_reasoner50`` when that module appears (duck-typed).
    * Otherwise wraps fable_reasoner44 read-only: ``notebook.ask`` (the hard-coded
      hop loop + discrete statuses) is authoritative; the trained 64-number router
      from the sealed base checkpoint is a logged CROSS-CHECK on chains made only
      of Exp 44's person-to-person relations, and the WORD relations use Exp 44's
      token/install path (an episode is queued for SLEEP when the underlying chain
      of base facts resolves).
    """

    def __init__(self, state_dir, checkpoint: str | None = None, seed: int = 4102,
                 prefer50: bool = True) -> None:
        self.state_dir = Path(state_dir)
        self.seed = seed
        self.router_runs = 0
        self.router_agree = 0
        self.router_disagree = 0
        self.router_skips = 0
        self.word_lookups = 0
        self.episodes: list[dict] = []         # handed to the Sleeper when the log fills
        self.backend = "notebook-hop-loop"
        self.router_ready = False
        self._R44 = None
        self._model = None
        self._impl50 = self._load_reasoner50() if prefer50 else None
        if self._impl50 is not None:
            self.backend = "fable_reasoner50"
        self._checkpoint = Path(checkpoint) if checkpoint else (
            SCRIPTS.parent / "artifacts" / "fable-reasoner44-20260921" / "runs" /
            f"base-seed{seed}.pt")
        if self._impl50 is None:
            self._try_router()                  # torch + Exp 44 checkpoint only on the fallback

    # -- agent 3's module, if/when it lands -------------------------------------------------
    def _load_reasoner50(self):
        try:
            import fable_reasoner50 as R50          # noqa: F401
        except ImportError:
            return None
        for name in ("FableReasoner50", "make_reasoner", "build_reasoner",
                     "Reasoner50", "NotebookReasoner"):
            obj = getattr(R50, name, None)
            if obj is None:
                continue
            try:
                inst = obj() if isinstance(obj, type) else obj
            except TypeError:
                continue
            if hasattr(inst, "answer"):
                return inst
        if hasattr(R50, "answer"):
            return R50
        return None

    def _try_router(self) -> None:
        try:
            import torch
            import fable_reasoner44 as R44
        except Exception:
            return
        if not self._checkpoint.exists():
            return
        try:
            torch.set_num_threads(1)
            state = torch.load(self._checkpoint, map_location="cpu", weights_only=True)
            model = R44.Reasoner()
            model.load_state_dict(state["state"] if isinstance(state, dict) and "state" in state
                                  else state)
            model.eval()
        except Exception:
            return
        self._R44, self._model, self.router_ready = R44, model, True

    # -- the answer ------------------------------------------------------------------------
    def answer(self, question: dict, notebook) -> dict:
        name = question.get("name", "")
        relations = list(question.get("relations") or [])
        entity_id = question.get("entity_id")

        if self._impl50 is not None:                       # agent 3 wins when present
            self._queue_word_episode(notebook, name, relations, entity_id)
            try:
                record = self._impl50.answer(question, notebook)
                if isinstance(record, dict) and "status" in record:
                    return record
            except Exception:
                pass                                       # fall through to our wrap

        if not relations or len(relations) > MAX_HOPS:
            return {"kind": "answer", "status": C.BAD_REQUEST, "name": name,
                    "relations": relations,
                    "fields": {"reason": f"need 1-{MAX_HOPS} hops"}}

        primary = notebook.ask(name, relations, entity_id=entity_id)
        record = {"kind": "answer", "status": primary.status, "name": name,
                  "relations": relations, "fields": dict(primary.detail)}

        start = entity_id
        if start is None and primary.status != C.UNKNOWN_ENTITY:
            resolved = notebook.resolve(name)
            if resolved.status == C.OK:
                start = resolved.detail["entity_id"]

        word_at = next((i for i, r in enumerate(relations)
                        if self._R44 is not None and r in self._R44.WORD_NAMES), None)
        if word_at is not None and self.router_ready and start is not None:
            self._word_path(record, notebook, start, relations, word_at)
        elif self.router_ready and start is not None and primary.status != C.AMBIGUOUS:
            self._cross_check(record, notebook, start, relations)
        return record

    # -- cross-check: chains made only of Exp 44's own relations --------------------------
    def _village(self, notebook):
        R44 = self._R44
        names = tuple(sorted(notebook.entities))
        facts = {}
        for eid in names:
            for rel in R44.RELATIONS:
                rows = notebook.current(eid, rel)
                if len(rows) == 1 and "entity" in rows[0]["value"]:
                    facts[(eid, rel)] = rows[0]["value"]["entity"]
        return R44.Village(names, facts)

    def _walk_live(self, notebook, start: str, relations) -> tuple[str | None, bool]:
        """(answer entity_id or None, encodable) -- encodable = every hop a single
        entity-valued fact of an Exp 44 relation."""
        cur, encodable = start, True
        for rel in relations:
            rows = notebook.current(cur, rel)
            if len(rows) != 1 or "entity" not in rows[0]["value"]:
                encodable = False
                break
            cur = rows[0]["value"]["entity"]
        return (cur if encodable else None), encodable

    def _cross_check(self, record: dict, notebook, start: str, relations) -> None:
        R44 = self._R44
        if any(rel not in R44.RELATIONS for rel in relations):
            self.router_skips += 1
            record["fields"]["router"] = "skip:relation-not-in-exp44-vocab"
            return
        walked, encodable = self._walk_live(notebook, start, relations)
        if not encodable:
            self.router_skips += 1
            record["fields"]["router"] = "skip:hop-not-a-single-entity-fact"
            return
        village = self._village(notebook)
        matrices = R44.notebook_matrices(village)
        tokens = tuple(R44.RELATIONS.index(rel) for rel in relations)
        qs = [R44.Question(start, tokens, walked)]
        with _torch_inference():
            preds = R44.predict(self._model, village, matrices, qs)
        neural = preds[0]
        neural_name = notebook.entities.get(neural, neural) if neural != R44.UNKNOWN else R44.UNKNOWN
        self.router_runs += 1
        if record["status"] == C.OK:
            agree = neural_name == record["fields"].get("answer")
            record["fields"]["router"] = "check:agree" if agree else f"check:disagree({neural_name})"
            if agree:
                self.router_agree += 1
            else:
                self.router_disagree += 1
        else:
            record["fields"]["router"] = f"check:router-says-{neural_name}"

    # -- Exp 44 word tokens over the live notebook -----------------------------------------
    def _word_names(self) -> tuple:
        if self._impl50 is not None and hasattr(self._impl50, "words"):
            try:
                import fable_reasoner50 as R50
                return tuple(R50.WORD_NAMES), tuple(R50.WORD_CHAINS), tuple(R50.CORE8)
            except Exception:
                pass
        if self._R44 is not None:
            return tuple(self._R44.WORD_NAMES), tuple(self._R44.WORD_CHAINS), tuple(self._R44.RELATIONS)
        return (), (), ()

    def _queue_word_episode(self, notebook, name, relations, entity_id) -> None:
        """A bare learned-word question: if its underlying chain of base facts resolves,
        queue one sleep episode (start, word, answer) for the Exp 46 recipe."""
        names, chains, core = self._word_names()
        if len(relations) != 1 or relations[0] not in names:
            return
        start = entity_id
        if start is None:
            found = notebook.resolve(name)
            if found.status != C.OK:
                return
            start = found.detail["entity_id"]
        word = relations[0]
        w = names.index(word)
        self.word_lookups += 1
        cur, ok = start, True
        for rel in chains[w]:
            rows = notebook.current(cur, rel)
            if len(rows) < 1 or "entity" not in rows[0]["value"]:
                ok = False
                break
            cur = rows[0]["value"]["entity"]
        if ok:
            self.episodes.append({"start": start, "word": w, "word_name": word,
                                  "answer": cur})

    def _word_path(self, record: dict, notebook, start: str, relations, word_at: int) -> None:
        """A relation that is one of Exp 44's learned WORDS: queue a sleep episode when
        the underlying chain of taught base facts resolves; if the word is already
        installed (confident router), upgrade a MISSING answer."""
        R44 = self._R44
        word = relations[word_at]
        w = R44.WORD_NAMES.index(word)
        self.word_lookups += 1
        cur = start
        ok = True
        for rel in R44.WORD_CHAINS[w]:
            rows = notebook.current(cur, rel)
            if len(rows) < 1 or "entity" not in rows[0]["value"]:
                ok = False
                break
            cur = rows[0]["value"]["entity"]
        if ok:
            self.episodes.append({"start": start, "word": w, "word_name": word, "answer": cur})
        if record["status"] != C.OK and self.router_ready:
            village = self._village(notebook)
            matrices = R44.notebook_matrices(village)
            qs = [R44.Question(start, (R44.R + w,), cur if ok else None)]
            with _torch_inference():
                preds = R44.predict(self._model, village, matrices, qs)
            neural = preds[0]
            record["fields"]["router"] = f"word:{neural}"
            if neural != R44.UNKNOWN and ok and neural == cur:
                record.update(status=C.OK)
                record["fields"].update(answer=notebook.entities[neural],
                                        source="sleep-installed-word", trail=[])
        else:
            record["fields"]["router"] = "word:pending-install"


class _torch_inference:
    def __enter__(self):
        try:
            import torch
            self._ctx = torch.inference_mode()
            self._ctx.__enter__()
        except Exception:
            self._ctx = None
        return self

    def __exit__(self, *exc):
        if self._ctx is not None:
            return self._ctx.__exit__(*exc)
        return False


# ------------------------------------------------------------------------- Sleeper
class HardGate46Sleeper:
    """Sleeper slot: called by the loop ONLY when the experience log is full.

    1. A deterministic audit (formula over the log + notebook invariants).
    2. If the Reasoner queued Exp 44 word episodes, run the Exp 46 recipe:
       robust loss (-log((1-eps)p+eps/N)), harden phi to the argmax chain (+/-30
       logits) after each fold fit and on the refit, and the UNCHANGED 4-fold gate
       (OOF >= 0.80, refit agreement >= 0.90, old skills unchanged, reload identical).
       fable_hardgate46 is imported read-only; it patches fable_reasoner44.fit_word
       in place, which is exactly the recipe.  Nothing but the word's 27 numbers move.
    """

    MIN_EPISODES = 8

    def __init__(self, state_dir, reasoner: NotebookReasoner | None = None,
                 checkpoint: str | None = None, seed: int = 4102) -> None:
        self.state_dir = Path(state_dir)
        self.reasoner = reasoner
        self.seed = seed
        self.checkpoint = Path(checkpoint) if checkpoint else (
            SCRIPTS.parent / "artifacts" / "fable-reasoner44-20260921" / "runs" /
            f"base-seed{seed}.pt")
        self.sleeps = 0
        self.installs = 0
        self.last_outcome: dict = {}

    # ---------------------------------------------------------------- audit (formula)
    def audit(self, experience: list[dict], notebook) -> dict:
        violations: list[str] = []
        for entry in experience:
            if entry.get("kind") not in ("turn", "work"):
                violations.append(f"unexpected experience kind {entry.get('kind')!r}")
        for fact in notebook.facts.values():
            sup = fact.get("supersedes")
            if sup and fact["source"] != "taught":
                old = notebook.facts.get(sup)
                if old is not None and old["source"] == "taught":
                    violations.append(f"{fact['fact_id']} ({fact['source']}) overwrote a taught row")
            if fact["source"] in ("web-quarantine", "proposed") and notebook.active(fact["fact_id"]):
                for rel_rows in (notebook.current(fact["subject"], fact["relation"]),):
                    if any(r["fact_id"] == fact["fact_id"] for r in rel_rows):
                        violations.append(f"{fact['fact_id']} is answering a question")
        return {"log_size": len(experience), "turns": sum(1 for e in experience
                                                          if e.get("kind") == "turn"),
                "taught_rows": sum(1 for f in notebook.facts.values() if f["source"] == "taught"),
                "active_facts": sum(1 for fid in notebook.facts if notebook.active(fid)),
                "violations": violations}

    # ------------------------------------------------------------------- the recipe
    def _run_exp46(self, notebook) -> dict:
        episodes = list(self.reasoner.episodes) if self.reasoner else []
        if len(episodes) < self.MIN_EPISODES:
            return {"attempted": False, "queued": len(episodes),
                    "reason": f"{len(episodes)} word episodes (< {self.MIN_EPISODES}); "
                              "kept queued, nothing to gate"}
        if self.reasoner is not None:
            self.reasoner.episodes.clear()
        try:
            import torch
            import fable_reasoner44 as R44
            import fable_hardgate46 as G          # read-only import: patches R44.fit_word
        except Exception as exc:
            return {"attempted": False, "reason": f"recipe unavailable: {exc}"}
        torch.set_num_threads(1)
        if not self.checkpoint.exists():
            return {"attempted": False, "reason": f"no base checkpoint at {self.checkpoint}"}

        R44 = G.R44                                # hardgate's patched copy of reasoner44
        village = _village_from_notebook(R44, notebook)
        matrices = R44.notebook_matrices(village)
        base_state = torch.load(self.checkpoint, map_location="cpu", weights_only=True)
        base_state = base_state["state"] if "state" in base_state else base_state
        out = self.state_dir / "sleep-checkpoints"
        out.mkdir(parents=True, exist_ok=True)

        base_model = R44.Reasoner()
        base_model.load_state_dict(base_state)
        probe = R44.base_probe(village, self.seed, 64)
        before = R44.predict(base_model, village, matrices, probe)
        held = R44.sample_set(village, f"wire51/held/{self.seed}", self.seed, 64, (1, 2, 3),
                              "any")
        results = []
        by_word: dict[int, list] = {}
        for ep in episodes:
            by_word.setdefault(ep["word"], []).append(
                R44.Question(ep["start"], (R44.R + ep["word"],), ep["answer"]))
        for w, eps in sorted(by_word.items()):
            rec = R44.sleep_word(base_state, w, eps, village, matrices, self.seed,
                                 "wire51-live", before, probe, village, matrices, held, out)
            results.append({"word": R44.WORD_NAMES[w], "episodes": len(eps),
                            "installed": bool(rec.get("installed")),
                            "oof_best": max((float(v["match"]) for v in
                                             rec.get("cv_table", {}).values()), default=0.0),
                            "refit_agreement": rec.get("refit_agreement"),
                            "reason": rec.get("reason")})
        installed = sum(1 for r in results if r["installed"])
        self.installs += installed
        return {"attempted": True, "installed": installed, "words": results}

    def sleep(self, experience: list[dict], notebook) -> dict:
        self.sleeps += 1
        report = self.audit(experience, notebook)
        recipe = self._run_exp46(notebook) if self.reasoner is not None else {
            "attempted": False, "reason": "no reasoner bound"}
        accepted = not report["violations"]
        outcome = {"accepted": accepted, "audit": report, "recipe": recipe,
                   "reason": "audit passed; log consolidated" if accepted
                   else "audit found violations; log kept for inspection"}
        self.last_outcome = outcome
        return outcome


def _village_from_notebook(R44, notebook):
    names = tuple(sorted(notebook.entities))
    facts = {}
    for eid in names:
        for rel in R44.RELATIONS:
            rows = notebook.current(eid, rel)
            if len(rows) == 1 and "entity" in rows[0]["value"]:
                facts[(eid, rel)] = rows[0]["value"]["entity"]
    return R44.Village(names, facts)


# -------------------------------------------------------------------------- Thinker
class NotebookThinker:
    """Thinker slot: fable_thinking_m2.Thinking.  Returns None when there is no
    assigned topic (THINKING stays the idle default and never searches on its own)."""

    def __init__(self, thinking) -> None:
        self.thinking = thinking

    def think(self, notebook) -> dict | None:
        assigned = [t for t in self.thinking.topics if t["status"] == "assigned"]
        if not assigned:
            return None
        said = self.thinking.think_once()
        return {"said": said, "topic": assigned[0]["topic"]}


# --------------------------------------------------------------------------- build
def build_loop(state_dir, *, ears_mode: str = "auto", sleep_threshold: int = A.SLEEP_THRESHOLD,
               base_url: str | None = None, model: str | None = None,
               checkpoint: str | None = None, seed: int = 4102,
               thinker: bool = True, echo_confirm: bool = False,
               ) -> tuple[A.AgentLoop, dict]:
    """Wire every slot with the real parts and return (loop, parts dict)."""
    parts: dict = {}
    ears = EnglishEars(mode=ears_mode, base_url=base_url, model=model,
                       echo_confirm=echo_confirm)
    mouth = TemplateMouth()
    reasoner = NotebookReasoner(state_dir, checkpoint=checkpoint, seed=seed)
    sleeper = HardGate46Sleeper(state_dir, reasoner=reasoner, checkpoint=checkpoint, seed=seed)
    loop = A.AgentLoop(state_dir, ears=ears, mouth=mouth, reasoner=reasoner,
                       sleeper=sleeper, sleep_threshold=sleep_threshold)
    ears.bind(loop.listening, loop.nb)
    parts["ears"], parts["mouth"] = ears, mouth
    parts["reasoner"], parts["sleeper"] = reasoner, sleeper
    if thinker:
        import fable_thinking_m2 as M
        parts["thinking"] = M.Thinking(loop.nb, M.BridgeSearcher())
        parts["thinker"] = NotebookThinker(parts["thinking"])
        loop.thinker = parts["thinker"]
    return loop, parts
