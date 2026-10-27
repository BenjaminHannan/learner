# Exp 150 PASSMARKS — SUBJECT-span guard for teach sentences (sealed BEFORE any registered run)

Registered single-change fix on loop139b (scripts/fable_loop139b_agent.py,
artifacts/fable-fix139b-20260922/loop139b-config.json; RESULTS.md and design
docs 139/139b read first; 139/139b guard only the VALUE span). Director probe
on loop139b: teaches with a polluted SUBJECT store the pollution verbatim
("I think Kip Dune", "Perhaps Kip Dune", "Maybe Kip Dune",
"Someone told me Kip Dune", "Rumor has it Kip Dune", "Honestly Kip Dune",
"So Kip Dune", "My friend Kip Dune").

THE ONE CHANGE (scripts/fable_fix150_subjectguard.py, SubjectGuard150Mixin;
thin loop150 = loop139b + mixin in scripts/fable_loop150_agent.py with
--daemon entry incl. idle_seconds; 139b imported read-only, no file edited):
on the subject span of every teach/correct action AFTER the exp-129 strip,
at ears hear() and again at loop _act() just before the write,
(a) hedge/reporting openers -> no write (hedges: existing value-guard SPLIT
clarify; reporting: existing loop102 HEARSAY reply; reused, none invented);
(b) discourse fillers/introducers -> strip (repeat to fixpoint) and store the
clean subject, remainder re-screened by (a)/(c);
(c) any other multi-token subject whose first token is an all-lowercase word
with a capitalised token later and no " of " -> SPLIT clarify, no write.
Untouched by design: single-token subjects; all-lowercase subjects (legal
common-noun entities per exp-102); "<lowercase words> of <Name>" role phrases
(bench-legit officeholder shape); camelCase product names ("macOS Server",
"iPod Touch", "iOS SDK" -- styled names, not lower-case words); values,
relation keys, forget/ask/clarify paths.

## Sealed lists (exact; case-insensitive leading-phrase match, word/comma boundary; one-line reason each)

HEDGE -> SPLIT clarify, no write:
- "maybe": epistemic hedge, speaker unsure, not a clean assertion.
- "perhaps": same as maybe.
- "probably": probabilistic hedge, not a fact to store.
- "possibly": same as probably.
- "likely": same; no person is named "Likely".
- "presumably": same; no name collision.
- "i think": self-reported uncertainty, not direct telling.
- "i guess": same as i think.
- "i believe": belief, not direct telling.
- "i suppose": same as i think.
REPORTING -> HEARSAY reply, no write:
- "i heard": attribution to another source, second-hand by definition.
- "someone told me": explicit second-hand report (director case).
- "someone said": variant of told-me, same second-hand shape.
- "they say": unattributed report, no direct teller.
- "people say": same as they say.
- "rumor has it": explicit rumor (director case), never a fact.
- "rumour has it": spelling variant of rumor (base ears45 marker).
- "word is": street report ("word is Kip..."), unattributed.
- "i read that": attribution to text, not direct telling.
- "i read online": same, already a base whole-turn marker.
- "according to": attribution by definition, already base whole-turn.
- "apparently": attribution, already base whole-turn; subject-level net.
- "reportedly": same as apparently.
FILLER -> strip, store remainder:
- "by the way": multi-word discourse filler, never part of a name.
- "my friend": introducer, not part of the name (director case).
- "my neighbor": spelling variant of the introducer.
- "my neighbour": spelling variant of the introducer.
- "so": discourse filler; hyphenated "So-Yeon" is one token, unaffected.
- "well": discourse filler, never a name lead.
- "ok": discourse filler, never a name lead in teaches.
- "okay": same as ok, distinct token.
- "honestly": discourse filler (director case), never a name.
- "anyway": discourse filler, never a name lead.
- "also": discourse filler, never a name lead.
- "btw": textspeak filler, never a name.
- "oh": discourse filler, never a name lead in teaches.
- "actually": correction-prefix remnant safety net (base strips at turn
  level); no person is named "Actually".
- "frankly": "Frankly, ..." filler vs name "Frank" are distinct tokens.
CAPITALISED-NAME RULE: a leading token with an initial uppercase letter is a
name token even when the word exists in English (Will, May, Hope, Grace,
Rich, Sunny, Frank, Mark, So-Yeon) -- reason: teaches put names in subject
position capitalised, and the guard matches pollution only from the closed
opener lists plus lowercase-lead shape, so vocabulary membership never
refuses (bare "may"/"will"/"mark"/"frank" are NOT openers, and "maybe" does
not prefix-match "May Lee" by word boundary).

Sealed inputs:
- S1/S2 probe: artifacts/fable-fix150-20260922/cases150.json (57 cases: 12
  hedge + 10 reporting + 16 filler + 16 legit + 3 handled-already; the 8
  director cases flagged "director":true; full-triple expectations).
- loop150-config.json (loop139b config + 2 renamed plug strings).
- S3 reference: sealed loop139b bench rows
  (artifacts/fable-fix139b-20260922/fable_bench139b_loop139b_*_rows.jsonl) +
  marks123 via scripts/fable_marks123_all.py into this exp's marks150 dir.
- S4 reference: sealed loop139b redteam run
  (artifacts/fable-fix139b-20260922/redteam136-loop139b.json: OK 126 /
  WRONG-WRITE 14 / MISSED 5); 136 suite+checker sealed in its own exp.
- 123 suites, bench splits + scorer v2: sealed in their own exps, read-only.

## Marks (integer counts, every seed/case reported, never averaged)

- S1 NEW probe of 57 teach sentences through loop150
  (scripts/fable_fix150_probe.py --agent loop150): 22 hedge/reporting ->
  no write with the right reply kind (12 split + 10 hearsay); 16
  filler-prefixed -> exact clean triple; 16 legit (word-like names Will
  Smith, May Lee, Hope Solo, Frank Ocean, Grace Kelly, Rich Hall, Sunny
  Deol, Mark Twain, So-Yeon Ryu + possessive/The-frames + plain controls)
  -> exact triple; 3 handled-already unchanged (Apparently hearsay-nowrite,
  Actually, clean write, Maybe-capital nowrite); FULL triple judged
  (subject, relation, value); 0 wrong writes over all 57.
- S2 the director's 8 cases (director:true rows of the same probe file) ->
  no polluted subject stored (5 refuse-empty; 3 store ["Kip Dune", ...]).
- S3 bench121 new/old + Fable-Edit per-item verdicts identical to the sealed
  loop139b rows (scripts/fable_fix150_bench.py) with ZERO predicted moves,
  and marks123 suites (scripts/fable_marks123_all.py --agent
  scripts/fable_loop150_agent.py --config
  artifacts/fable-fix150-20260922/loop150-config.json --out <this-dir>/marks150
  --workers 4) with every suite verdict identical to loop139b (sleep SKIP
  reason text names the agent file, verdict identical, as in 139b).
- S4 red team 136 re-run through loop150
  (scripts/fable_fix150_redteam136.py): no case worse than on loop139b
  (no OK->non-OK move); ZERO per-case moves predicted.
- S5 each registered run (probe, bench, marks123, redteam136) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrapper
  takes idle_seconds.

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Pure-function scan of all 3775 bench teach subjects (edit200 + bench103
  s2fresh + bench121, B73/B92 parse): screen_subject_150 fires NOWHERE (0/3775).
- Pure-function scan of 931 sealed suite/redteam non-question strings
  (redteam98 cases, p4-innocent-30, redteam110 cases, redteam81 results,
  cases136): only 2 fires, both already refused on base by whole-turn
  hearsay markers ("I read online that Roberto Merhi ...", "quote CM Punk ...").
- Pure-function scan of 167 redteam81 probe turns: 0 fires.
- Base calibration (scripts/fable_fix150_probe.py --agent loop139b on the
  frozen probe): 36/57 WRONG-WRITE with the exact polluted subjects from the
  director probe (H01-H12, R01-R07+R10, F01-F16); 21/21 other rows OK
  (R08+R09 already hearsay, 16 legit exact incl. all 9 word-like names,
  A01 hearsay-nowrite, A02 clean write, A03 nowrite). L16 was replaced
  pre-seal ("Ann Lee's city ..." is MISSED even on base: FakeEars is
  one-word-names-only) with "The official language of Peru is Spanish.".
- "i feel" deliberately NOT a hedge opener: bench subjects "I Feel Love",
  "I Feel Fine" (songs) would false-fire.
- Redteam139b WW audit: none of the 14 WRONG-WRITE subjects hits the screen
  (role-phrase/exempt shapes or single-token paths); the 5 MISSED are
  clarify/unparseable paths the guard never touches.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix150_probe.py --agent loop150 --out artifacts/fable-fix150-20260922/probe150-loop150.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix150_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop150_agent.py --config artifacts/fable-fix150-20260922/loop150-config.json --out artifacts/fable-fix150-20260922/marks150 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix150_redteam136.py
