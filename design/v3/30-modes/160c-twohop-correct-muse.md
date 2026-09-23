# 160c — Bare corrections after a multi-hop answer ask which fact is meant (exp 160c, Muse)

## Step 1 — the code responsible (read before sealing)

Same two levels as exps 160/160b (read-only here, reused by import):

- `scripts/fable_agent_loop.py:95` (`_CORRECTION`: only `actually`/`no,`
  plus a full sentence) and `scripts/fable_loop102_agent.py:92`
  (`_CORRECTION_PREFIX_RE`, the rule the real chain uses): a bare
  "no, Milan" matches no prefix, the teach-template parse of the whole turn
  returns None, and the exact old path clarifies with 0 writes.
- `scripts/fable_fix160_barecorrect.py` (exp 160, sealed): the five bare
  shapes plus V validation (`parse_bare_correction`), the sealed clarify
  text (`CLARIFY_MSG`), and the teach-triple readers. Reused by import,
  never copied.
- `scripts/fable_fix160b_laststated.py:141-151`
  (`LastStated160bMixin._act`): on `{"act":"bare_correct"}` it reads
  `self._last_stated160b` — the triple the previous reply saved, or the
  FINAL-hop fact of the answer it just gave (`final_hop_triple`, lines
  73-110) — and synthesizes `{"act":"correct", same name/relation/
  is_person, V}` through `super()._act`. That resolve is the guess: after
  "Kim's boss's city is Rome." (chain: Kim's boss is Lee; Lee's city is
  Rome), "No, Milan." rewrites Lee's city without knowing which hop the
  user meant. Ben's ruling (2026-09-22): after a multi-hop answer, ask
  which fact is meant.

## The one change

`scripts/fable_fix160c_twohp.py` (`TwoHop160cMixin`), stacked in
`scripts/fable_loop160c_agent.py` as loop160c = 160c-mixin + loop160b (loop
`_act` resolve + `_listening_tick` chain bookkeeping; the ears hear tag is
inherited untouched from loop160b, and loop160b plus the 160 module are
imported read-only, nothing edited). A bare correction (160's five sealed
shapes and V validation, reused by import) checks the full stated chain:

- If the IMMEDIATELY previous reply stated a chain of >= 2 facts (one OK
  answer record whose trail covers every hop exactly once with >= 2 hops —
  `chain_triples` resolves every trail fact id in the notebook to a named
  (subject, relation, value), so the listing is never a guess), the turn
  writes NOTHING and replies with the chain's facts as options, e.g.
  "Which one is wrong: Kim's boss is Lee, or Lee's city is Rome? Say e.g.
  "Actually, Lee's city is Milan."" The example names the LAST chain fact
  with the bare value V so the user sees the pattern; the turn counts one
  clarification and performs 0 FACT writes, like 160's sealed clarify.
- Otherwise the turn delegates to `super()._act` — byte-identical loop160b
  behaviour: single-fact answers write the stated fact, fact-free or
  multi-record replies get 160's sealed clarify. An explicit follow-up
  ("Actually, Lee's city is Milan.") travels the loop's EXISTING correction
  machinery, so guards, the "Saved: ..." reply, audit trail and supersede
  rules are identical to loop160b.

Every turn's records REPLACE the chain memory (a non-chain reply clears it
to None), so a bare correction two turns later clarifies; nothing older
than the previous reply is ever addressed. The chain persists in
`state.json` (`chain160c`) across resume. Non-matching turns never re-tag,
so they are byte-identical to loop160b.

## Why this shape

- "Which one did you mean?" is the reading Ben's ruling requires: a bare
  value after a two-hop answer is ambiguous between the hops, and 160b's
  final-hop pick is correct only by luck. Zero wrong writes beats one lucky
  write.
- Listing every chain fact (not just first/last) keeps three-hop answers
  covered with the same rule, and resolving each trail fact against the
  notebook (rather than re-parsing the English reply) keeps the options
  exact.
- The single-fact path is untouched by construction (delegation, not a
  reimplementation), which is what makes the G1/G2 regression bars hold:
  the 160c branch is reachable only when the previous reply stated >= 2
  facts in one answer record.

## Risks / non-goals

Pronouns are still not resolved — the previous reply supplies the subjects,
which is the whole rule. The clarify example names the last chain fact;
if the user meant the first hop they must still type it out (one extra
turn, zero wrong writes — the intended trade). Held-out wording beyond the
five sealed shapes is unchanged. A bare correction can still only rewrite a
triple the existing correction path accepts (same guards as "Actually, ...").
Multi-row answers (several records) keep 160b's sealed clarify, not the
chain listing — only a single answer record with a full trail lists facts.

## Marks

- T1: new 68-dialogue probe (20 chain: 10 two-hop + 10 three-hop, one per
  bare shape per length, follow-ups naming first/middle/last hops incl. the
  director probe verbatim; 24 single-fact -> identical to loop160b; 24 other
  -> identical to loop160b), plus T2 0 wrong writes.
- C2/G3: exp-152 sessions — S3n6 becomes the which-one-is-wrong clarify
  (the one predicted move), other turns identical, 0 new WRONG.
- G1/G2/G3-redteam/G4: bench121, marks123, redteam136/143, budget
  regressions per PASSMARKS.md.
