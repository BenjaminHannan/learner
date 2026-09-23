# Exp 160b PASSMARKS — bare corrections target the last stated fact (sealed BEFORE any registered run)

Registered single-change fix on loop150 (scripts/fable_loop160b_agent.py,
artifacts/fable-correct160b-20260922/loop160b-config.json; loop150 = loop129b
+ 139b value guard + 150 subject guard, read-only, no file edited). Exp 160's
sealed rule (most-recent saved teach) makes WRONG writes on the director's
probes: "Tom's city is Oslo." / "Ann's city is Rome." / "What is Ann's
city?" / "hi" / "What is Tom's city?" (-> "Tom's city is Oslo.") /
"I meant Paris" rewrites ANN (the user had just been talking about TOM);
and "Tom's city is Oslo." / "Who is Bob's boss?" (-> don't know) /
"no wait, it's Denver" rewrites TOM although the previous reply stated no
fact.

Responsible code (Step 1): scripts/fable_agent_loop.py:95 (`_CORRECTION`
prefix set) and scripts/fable_loop102_agent.py:92 (`_CORRECTION_PREFIX_RE`);
on 160's chain, scripts/fable_fix160_barecorrect.py (sealed shapes, V
validation, clarify text, teach-triple readers — reused by import).

THE ONE CHANGE (scripts/fable_fix160b_laststated.py, LastStated160bMixin;
thin loop160b in scripts/fable_loop160b_agent.py with --daemon entry incl.
idle_seconds): a bare correction matching a sealed 160 shape with a valid V
applies to the ONE fact the agent's IMMEDIATELY previous reply stated —
either the triple it just saved (one wrote-write teach/correct record), or
the final-hop fact of the answer it just gave (one OK answer record whose
trail covers every hop exactly once; the last trail fact, e.g. (Rao, city,
seattle) for "Nadia's teacher's city is seattle."). It synthesizes
{"act":"correct", same name/relation/is_person, value V} through
super()._act — the loop's EXISTING correction machinery (same guards, same
"Saved: ..." reply, same audit trail and supersede rules as "Actually, X's
R is V."). If the previous reply stated no fact (refusal/clarify/small
talk, MISSING_FACT/UNKNOWN_ENTITY, 0 writes), or more than one fact
(multi-row answer, several records), or there is no previous reply, it
answers the sealed clarify with 0 writes. Every turn's records REPLACE the
memory (a fact-free reply clears it); nothing older than the previous reply
is ever targeted. Previous stated fact persists in state.json
("last_stated160b"). Non-matching turns never re-tag: byte-identical to
loop150.

## Sealed bare-correction shapes (identical to 160, reused by import)

- "no wait, [it's|its|it is] V" (e.g. "no wait, it's Denver")
- "wait, [it's|its|it is] V" (e.g. "wait, it's Denver")
- "sorry, [it's|its|it is] V" (e.g. "sorry, it's Denver")
- "I meant[,] V" (e.g. "I meant Denver"; no it's-form)
- "no, [it's|its|it is] V" (e.g. "no, Denver")
V valid iff ALL hold: non-empty; no "?" or "!" in the turn; no "'s"/"'s"
and no " is "/" are " in V; no ","/";"/":" in V; <= 8 words; not a bare
question word (what/who/where/when/why/how/which/whom/whose); does not
start with "to ". Else the base path runs untouched.
No-fact clarify (exact, 0 writes): Which fact should I change? You can say
e.g. "Actually, Tom's city is Denver."
Deliberate, inherited: bare "no, thank you" right after a reply that
stated a fact rewrites the value to "thank you" (the sealed "no, V" shape,
no exception carved).

Sealed inputs:
- C1 probe: artifacts/fable-correct160b-20260922/cases160b.json (56
  dialogues: 16 bare-after-save with explicit-"Actually" twins, 16
  bare-after-answer (8 one-hop incl. the director's Tom/Paris dialogue
  verbatim, 8 two-hop) with explicit twins on the stated fact, 14
  bare-with-no-fact-in-previous-reply incl. the director's
  don't-know dialogue verbatim, 10 unrelated no/wait/sorry).
- loop160b-config.json (loop150 config + 2 renamed plug strings).
- G1 reference: sealed loop150 bench rows
  (artifacts/fable-fix150-20260922/fable_bench150_loop150_*_rows.jsonl) via
  scripts/fable_loop129b_bench.py run_item by import.
- G2 reference: sealed loop150 marks
  (artifacts/fable-fix150-20260922/marks150) via scripts/fable_marks123_all.py.
- G3/C2 reference: sealed T-T session rows
  (artifacts/fable-session152-20260922/turns152-T-T-*.json) via
  scripts/fable_session152_run.py run_session/judge by import.

## Marks (integer counts, every seed/case reported, never averaged)

- C1 NEW probe of 56 dialogues (scripts/fable_fix160b_probe.py): A 16/16
  bare-after-save -> triples AND turn-2 reply equal to the explicit
  "Actually, ..." twin run on a fresh loop; B 16/16 bare-after-answer ->
  triples AND last reply equal to the explicit twin on the stated fact
  (older teaches untouched); C 14/14 bare with no fact in the previous
  reply -> exactly the sealed clarify with 0 FACT writes on the bare
  turn; D 10/10 unrelated no/wait/sorry -> every reply byte-equal to
  loop150 with equal FACT counts. 56/56 OK.
- C2/G3 sessions152 re-run through loop160b
  (scripts/fable_fix160b_session152.py): exactly ONE predicted move,
  S3-teachers-correction turn 6 "no wait, it's denver" UNHELPFUL->OK with
  +1 write and reply "Saved: Rao's city is denver." (turn 5 answered
  "Nadia's teacher's city is seattle.", final-hop fact (Rao, city,
  seattle)); the other 179 T-T turns byte-identical (reply, statuses,
  writes); 0 new WRONG, 0 other new writes.
- G1 bench121 new + old fresh split + Fable-Edit per-item verdicts AND
  replies identical to the sealed loop150 rows
  (scripts/fable_fix160b_bench.py): ZERO predicted moves, 0 new wrong.
- G2 scripts/fable_marks123_all.py suites per-case verdicts identical to
  loop150's marks150 run (same --workers 4 invocation, --out into this
  exp's marks160b dir): ZERO predicted moves except the sleep SKIP reason
  naming the new agent file (verdict identical, same precedent as
  139b->150 and 150->160).
- G3 each registered run (probe, bench, marks123, sessions) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds.

## Pre-seal evidence (dev only, NOT registered runs)

- Pure-function scan, parse_bare_correction (the imported 160 function)
  over 26647 bench strings (all string values, edit200 + old_s2fresh +
  new_121): 0 hits.
- Same scan over 180 sealed session152 turns: exactly 1 hit (S3 turn 6).
- Same scan over 1068 suite/case strings (redteam110 cases + cases150):
  0 hits (plus 160's sealed evidence: 0 hits over redteam136/110/81).
- Dev smoke (fresh in-process loop160b, temp dirs, no artifact writes):
  director-1 -> Tom Paris / Ann Rome; director-2 -> sealed clarify, Tom
  stays Oslo; save-then-bare and 1-hop/2-hop-answer-then-bare equal
  explicit twins incl. person-relation (teacher Rao->Finn) and chained
  bares (denver->austin); two-turns-later and post-small-talk bares ->
  clarify; unrelated after an answer byte-identical to loop150.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. No code edit after sealing except as reported with
affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160b_probe.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160b_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop160b_agent.py --config artifacts/fable-correct160b-20260922/loop160b-config.json --out artifacts/fable-correct160b-20260922/marks160b --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160b_session152.py
