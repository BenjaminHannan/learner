# 167c — Saved confirmations render the answer path's relation surface (Muse)

## The bug (file:line first)

Loop167b teaches "Ada was born in Paris." (verb twin → possessive path,
scripts/fable_fix167_verb.py) and confirms with the raw inventory key:
"Saved: Ada's place_of_birth is Paris." The answer to "Where was Ada
born?" already renders "Ada's place of birth is Paris." Root cause: two
different render functions. The Saved text is built in the notebook
contract (scripts/fable_notebook_contract.py:349,
`f"{subject}'s {relation} is {value}"` with the raw key, wrapped by
TEMPLATES[SAVED] at :77) and echoed verbatim by FakeMouth.say for
`kind == "write"` (scripts/fable_agent_loop.py:160-161). Answers go
through FakeMouth.say's OK branch, which applies `part.replace("_", " ")`
(:166-167) to each relation part. The 167b PASSMARKS left this mismatch
as future work; the 167c brief promotes it to the one change.

## The fix (one change, mouth-side only)

scripts/fable_fix167c_label.py defines `render_saved_label`: a pure
string function matching only `Saved: X's REL is V.` fact confirmations
whose REL contains an underscore, replacing underscores in REL with
spaces — the exact `replace("_", " ")` expression the answer path uses.
`Label167cMouth` wraps the loop's own mouth (delegate first, then
render), so content words still come from the record only.
scripts/fable_loop167c_agent.py stacks it onto loop167b
(`build_agent167c`: same ears/reasoner/sleeper/notebook, mouth wrapped
exactly once; `Loop167cDaemon` keeps `idle_seconds`). No 167b/167/162b,
agent-loop, or contract file is edited.

Scope is deliberately narrow: ONLY Saved fact confirmations move.
CONFLICT, MISSING_FACT, Forgotten, clarifies, and answers are returned
byte-identical (answers already render spaces; the rest are not
confirmations). Non-underscore relations (city, employer, spouse) match
nothing. Stored facts, relation keys, and matching are byte-identical by
construction — the notebook write completes before the mouth runs.

## Inventory (the relations covered)

ALLOWED_KEYS underscore members (scripts/fable_fix162_thename.py:73-79):
country_of_citizenship, country_of_origin, creator_country, educated_at,
founded_by, headquarters_location, language_of_work_or_name,
languages_spoken_written_or_signed, location_of_formation, notable_work,
official_language, place_of_birth, place_of_death,
position_played_on_team_speciality, religion_or_worldview, work_location.
Verb path: place_of_birth (city/employer/spouse have no underscore).
FakeEars general possessive (scripts/fable_agent_loop.py:150-152): any
multi-word surface (e.g. apprentice_of, head_of_state,
chief_executive_officer, composed_by — all evidenced live in the frozen
redteam136 rows). T1 covers all 16 ALLOWED keys + the verb path + 8
general samples (25 turns).

## Evidence (claims never exceed it)

T1 25/25 (exact spaced Saved replies, 0 underscore tokens in any reply,
scrubbed events identical to loop167b); T2 64/64 with exactly the 11
born replies moved; G1 600/600 verdict+reply identical with exactly
1723 Saved teach entries moved; G3 449 turns/cases with 0 verdict/write
moves and exactly 38 redteam136 Saved replies moved; G2 verdicts
identical everywhere with one diagnosed improvement (q4 leaks 7 → 4:
the render erased Saved-sourced leak tokens; MISSING/Forgotten-sourced
tokens remain, verdict FAIL unchanged) → G2 FAIL with diagnosis, all
else PASS. Full counts in
artifacts/fable-label167c-20260922/RESULTS.md.

## Limits

MISSING_FACT, Forgotten, and CONFLICT texts still show raw keys (q4's
0-leak bar still fails); stored keys keep underscores forever (matching
depends on them); multi-word-subject teaches are untouched.

## Reproduce

Sealed config + 25-case probe in
artifacts/fable-label167c-20260922/; scripts/fable_fix167c_probe.py (T1),
scripts/fable_fix167c_t2.py (vs frozen 167b probe),
scripts/fable_fix167c_bench.py, scripts/fable_fix167c_g3.py,
scripts/fable_marks123_all.py --agent scripts/fable_loop167c_agent.py
--config .../loop167c-config.json --workers 2,
scripts/fable_fix167c_marksdiff.py (shared move rule
fable_fix167c_label.saved_render_move).
