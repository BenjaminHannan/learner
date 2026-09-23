# 160b — Bare corrections target the last stated fact (exp 160b, Muse)

## Step 1 — the code responsible (read before sealing)

Same two levels as exp 160 (which is read-only here, reused by import):

- `scripts/fable_agent_loop.py:95` (`_CORRECTION`: only `actually`/`no,`
  plus a full sentence) and `scripts/fable_loop102_agent.py:92`
  (`_CORRECTION_PREFIX_RE`, the rule the real chain uses): a bare
  "no wait, it's Denver" matches no prefix, the teach-template parse of
  the whole turn returns None, and the exact old path clarifies with 0
  writes.
- `scripts/fable_fix160_barecorrect.py` (exp 160, sealed): the five bare
  shapes plus V validation (`parse_bare_correction`), the sealed clarify
  text (`CLARIFY_MSG`), and the teach-triple readers
  (`triple_from_record`/`triple_from_line`). 160's memory rule (the
  session's most-recent saved teach) is what 160b changes; everything
  else is imported, never copied.

Why 160 is wrong: its memory ignores what the conversation just said.
After "Tom's city is Oslo." / "Ann's city is Rome." / "What is Ann's
city?" / "hi" / "What is Tom's city?" (-> "Tom's city is Oslo.") /
"I meant Paris", the user had just been talking about Tom, but 160
rewrites Ann (most-recent saved teach). After "Tom's city is Oslo." /
"Who is Bob's boss?" (-> don't know) / "no wait, it's Denver", the
previous reply stated no fact at all, but 160 rewrites Tom. The real
exp-152 N6 turn shows the right reading: the agent had just ANSWERED
"Nadia's teacher's city is seattle." and the user replied "no wait, it's
denver" — the correction targets the fact that answer stated.

## The one change

`scripts/fable_fix160b_laststated.py` (`LastStated160bMixin`), stacked in
`scripts/fable_loop160b_agent.py` as loop160b = loop150 + mixin (ears hear
tag, loop `_act` resolve, `_listening_tick` previous-reply bookkeeping;
loop150 and the 160 module imported read-only, nothing edited). A bare
correction (160's five sealed shapes and V validation, reused by import:
`parse_bare_correction`) targets the ONE fact the agent's IMMEDIATELY
previous reply stated:

- the triple it just saved (one wrote-write teach/correct record, read by
  160's `triple_from_record`), or
- the final-hop fact of the answer it just gave (one OK answer record
  whose trail covers every hop exactly once; the last trail fact id is
  looked up in the notebook, e.g. (Rao, city, seattle) for "Nadia's
  teacher's city is seattle.").

If the previous reply stated no fact (refusal/clarify/small talk,
MISSING_FACT/UNKNOWN_ENTITY, 0 writes), or more than one fact (multi-row
answer, several records), or there is no previous reply, the turn gets
the sealed clarify with 0 writes (160's exact text, reused by import).
Nothing older than the previous reply is ever targeted: every turn's
records REPLACE the memory (a fact-free reply clears it to None), so a
bare correction two turns later clarifies. The correction synthesizes
`correct` with the same name/relation/is_person and value V through
`super()._act` — the loop's EXISTING correction machinery, so guards,
the "Saved: ..." reply, audit trail and supersede rules are identical to
the "Actually, ..." form. The memory persists in `state.json`
(`last_stated160b`) across resume. Non-matching turns never re-tag, so
they are byte-identical to loop150.

## Why this shape

- "What did I just say?" is the reading the session evidence supports:
  the N6 user corrects the answer they just heard, and the director's
  Tom/Ann probes resolve to whoever the previous reply talked about.
- The final-hop restriction is load-bearing for 2-hop answers: "Nadia's
  teacher's city is seattle" states (Rao, city, seattle) last; correcting
  the intermediate hop (Nadia's teacher) from a bare value would be a
  guess, so only the final hop is addressable.
- The multi-fact refusal (multi-row answers state several facts at once)
  keeps the rule at zero guesses: one stated fact or clarify.
- Deliberate, inherited from 160: a bare "no, thank you" right after a
  reply that stated a fact rewrites the value to "thank you" — the sealed
  "no, V" shape, no exception carved.

## Risks / non-goals

Pronouns are not resolved — the previous reply supplies the subject,
which is the whole rule. Bare corrections after a save-then-question
("teach, question-about-someone-else, bare") now follow the question,
not the teach; that is the sealed intent (nothing older targeted).
Held-out wording beyond the five sealed shapes is unchanged. A bare
correction can still only rewrite a triple the existing correction path
accepts (same guards as "Actually, ...").

## Marks

- C1: new 56-dialogue probe (16 bare-after-save + 16 bare-after-answer
  with explicit-"Actually" twins; 14 no-fact-previous -> clarify, 0
  writes; 10 unrelated -> byte-identical to loop150), including the
  director's two dialogues verbatim.
- C2: exp-152 sessions — the N6 turn becomes OK, other turns identical,
  0 new WRONG.
- G1/G2/G3: bench121, marks123, budget regressions per PASSMARKS.md.
