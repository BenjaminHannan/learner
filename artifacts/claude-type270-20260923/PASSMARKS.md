# Exp 270 PASSMARKS: a text normaliser in front of the ear (builder, 2026-09-23)

Registered arm A: 263 (`scripts/claude_loop263_agent.py` +
`artifacts/claude-comma263-20260923/loop263-config.json`, both reused
read-only, never re-sealed) PLUS the 270 normaliser outermost
(`scripts/claude_type270_agent.py`, THE ONE CHANGE). Arm A263: 263
exactly. Design: the 270 brief (no design file; the brief is the spec).

## Frozen config

- Base: 263 = 260 + comma guard, imported read-only. Sealed 270 config:
  `artifacts/claude-type270-20260923/loop270-config.json` (263 defaults +
  rule270 note; daemon `Loop270Daemon`, turn chain
  turn270(turn263(turn260(...)))).
- Normaliser (`scripts/claude_type270_normalise.py`, fixed before the
  seal): fires only when the turn has no capitals at all (reason
  "lowercase") or has no apostrophes with an "Xs \<relation>" pattern
  (reason "possessive"); everything else passes through byte-identical.
  On firing: (1) possessive fix ("zoranas mother" -> "Zorana's mother";
  s-endings: notebook match wins, else common-stem strips ("dogs" ->
  "dog's", "wills" -> "will's"), else endings ss/us/is/os/mes/les keep
  ("James's", "Tess's"), else strip ("Zorana's"); common/pronoun words
  never fixed; wh-contractions restored: whos -> who's, whats -> what's,
  wheres -> where's, whens, whys, hows); (2) capitalise every non-common
  word (COMMON270: closed-class words, auxiliaries/modals, question
  words, ear verbs live/work/..., relation nouns, openers/fillers,
  pretend-plan markers), with notebook-stored names winning over
  COMMON270 (stored "Will" beats modal "will").
- Verbs stay lowercase because 263's verb shapes need them ("Quillan
  Lives In Drennor." does not save); occupation/animal nouns were
  REMOVED from COMMON270 after the first dev run showed 263's
  description-check refuses lowercase values in name slots ("Corvin's
  boss is baker." does not save, "Corvin's boss is Baker." does).
- Suppression D1: trailing check-tails (", right", bare "right" with
  punctuation, ", isn't it", ", don't you think", ", yeah/yep/yes/no",
  ", ok/okay", ", correct", ", you know") pass through unchanged: the
  fixed text would save junk on 263. Bare "so ..."-heads are NOT
  suppressed (clean "So X." saves by 260's opener design; see dev note).
- Compute: local Mac, same as 263's runs (rule-based, no GPU, no
  llama-server, no BensPC). M6 counts normalise-call ms only.

## Dev (before the seal; own wording, fictional names, no panels)

`scripts/claude_type270_devset.py` -> `dev270.json`: 116 cases
(casual_teach 51, casual_q 16, lower_trap 25, clean 24). Run with
`scripts/claude_type270_devrun.py` (fresh daemon dir per case, both
arms), scored with `scripts/claude_type270_devscore.py` (openpanel260
judgement rules: lowercase normalise, store_ok, reply_ok, junk,
question_write). Rows: `dev270_rowsA.json`, `dev270_rows263.json`;
report: `devreport270.json`.

| Family | A | 263 |
|---|---|---|
| casual_teach (51) | 51 | 13 |
| casual_q (16) | 16 | 12 |
| lower_trap (25) | 24 | 25 |
| clean (24) | 24 | 24 |

42 moves (A right / 263 wrong), 0 both-wrong, 1 new-wrong (d270-079,
"so corvins boss is jesper." -> normalised "so Corvin's boss is
Jesper." saves via 260's "so"-strip; kept as-is by the D1 decision:
writer-validated traps cannot contain bare so-heads under M5 = 0 plus
the brief's rule, while so-led casuals are natural chitchat; see
deviation D1). Clean byte-identical A vs 263: 24/24. Normalise median
0.033 ms (n = 116).

Every rewrite on dev (74; also in `devreport270.json`):
d270-001 Belmara's mother is Marisol. / d270-002 Corvin's boss is
Baker. / d270-003 Tilda's brother is Pellin. / d270-004 Jesper's
friend is Sorrel. / d270-005 Linnea's father is Tamber. / d270-006
Marisol's sister is Wexford. / d270-007 Oswick's mother is Ysolde. /
d270-008 Pellin's boss is Mason. / d270-009 Sorrel's brother is
Corvin. / d270-010 Tamber's friend is Tilda. / d270-019 Corvin lives
in Drennor. / d270-020 Tilda lives in Halloway. / d270-021 Jesper
lives in Fenmere. / d270-022 Linnea lives in Norbury. / d270-023
Marisol lives in Eskdale. / d270-024 Oswick lives in Drennor. /
d270-025 Pellin lives in Halloway. / d270-026 Sorrel lives in
Fenmere. / d270-027 Oswick works at Fenmere. / d270-028 Pellin works
at Norbury. / d270-029 Sorrel works at Eskdale. / d270-030 Tamber
works at Drennor. / d270-031 Wexford works at Halloway. / d270-032
Ysolde works at Fenmere. / d270-034 my boss is Baker. / d270-039 hey
Sorrel's boss is Tilda. / d270-040 yo, Tamber's brother is Jesper. /
d270-041 so Wexford's friend is Linnea. / d270-042 well, Ysolde's
father is Marisol. / d270-043 oh, Belmara's sister is Oswick. /
d270-044 btw, Corvin's mother is Pellin. / d270-045 Listen, Tilda's
boss is Sorrel. / d270-046 Look, Jesper's brother is Tamber. /
d270-047 Morris's mother is Belmara. / d270-048 Tess's boss is
Corvin. / d270-049 Yes, Tilda's brother is Jesper. / d270-050
Marisol's friend is Linnea. / d270-051 Belmara's name is Wren. /
d270-052 who is Belmara's mother? / d270-053 who is Corvin's boss? /
d270-054 who is Linnea's brother? / d270-055 what is Marisol's
friend? / d270-056 Who's Oswick's sister? / d270-057 Who's Pellin's
father? / d270-058 What's Sorrel's mother? / d270-059 who is Tamber's
boss? / d270-060 who is Ysolde's friend? / d270-061 where does Jesper
live? / d270-062 who is Tilda's sister? / d270-063 Who's Wexford's
father? / d270-064 what is Belmara's job? / d270-065 who is Corvin's
mother / d270-066 Where's Linnea's boss? / d270-067 what is Belmara's
name? / d270-068 lets say Belmara's mother is Tilda. / d270-069
suppose Corvin lives in Drennor. / d270-070 imagine Jesper's boss is
Pellin. / d270-071 what if Linnea's brother is Oswick? / d270-072
lets Pretend Marisol lives in Norbury. / d270-073 i want Belmara's
mother to be Tilda. / d270-074 Corvin will live in Drennor. /
d270-075 Tilda's brother will be Jesper. / d270-076 i am Training to
be Baker. / d270-077 Jesper is Going to be Mason. / d270-079 so
Corvin's boss is Jesper. / d270-084 does Tilda live in Drennor. /
d270-085 is Belmara's mother Tilda. / d270-086 do you know Corvin. /
d270-087 Belmara's mother is not Tilda. / d270-088 Corvin does not
live in Drennor. / d270-089 Belmara's mother is Tilda and she lives
in Drennor. / d270-090 Jesper's boss is Pellin and he works at
Fenmere. / d270-091 Tilda's brother Used to be Jesper. / d270-092 my
boss was Corvin.
Suppressed (passthrough, no rewrite, no save on either arm): d270-078
", right", d270-080 ", isn't it", d270-081 ", don't you think",
d270-082 ", yeah", d270-083 ", correct".

## Marks, arm A (predictions P270.1-P270.6, overall P270.7)

| Mark | Bar | Prediction |
|---|---|---|
| M1 | casual exact TEACH >= 30/40 and >= A263+20 | A 33-38, A263 8-14; PASS ~65% (P270.1) |
| M2 | casual_q ASK >= 12/15 | A 13-15; PASS ~80% (P270.2) |
| M3 | lower_trap wrong saves <= 1 | A 0-1; PASS ~70% (P270.3) |
| M4 | clean 30/30 byte-identical to A263 | 30/30 by construction, dev 24/24; PASS ~95% (P270.4) |
| M5 | 0 new wrong saves vs A263 overall | 0 if traps hold no bare-so/,-right shapes; PASS ~60% (P270.5) |
| M6 | median added time <= 20 ms | ~0.03-0.5 ms; PASS ~99% (P270.6) |
| ALL | overall registered PASS | ~30% (P270.7) |

Also reported (no bars): every arm's per-family numbers; A263 beside
every figure; every move and every miss by id (no panel text quoted
beyond counts); per-turn normalise ms distribution (P270.8: median
<= 0.5 ms, max <= 5 ms).

## Registered procedure

1. Poll `artifacts/claude-typepanel270-20260923/SEAL.sha256.txt` every
   2 min up to 120 min; `shasum -c` from the repo root; stop and report
   if unsealed at 120 min.
2. Schema check on load (files, fields, families, labels); mismatch =
   SCHEMA-MISMATCH exit 3, VOID, reported, never hand-scored.
3. Run each arm ONCE (A, A263) with post-seal drivers (new files,
   disclosed; the scorer implements the brief's marks with
   openpanel260-style normalise; writer's README rules beside every
   figure), then RESULTS.md.

## Deviations / notes

- D1 (pre-seal, in the frozen normaliser): check-tail suppression and
  no "so"-head suppression, with the S1 rationale above. If the panel
  holds a bare-so trap, M3/M5 take exactly that hit; reported as-is.
- D2 (pre-seal): whos/whats/wheres/whens/whys/hows -> who's/what's/...
  (contraction, not possessive; needed for casual questions; dev
  d270-057/058/063/066 move on it).
- D3: no panel spec was provided with the brief, so the panel
  runner/scorer are written AFTER the seal from the observed schema
  (new files, diffs disclosed, sealed files untouched).
- D4: the blind panel was never opened before this seal (no listing
  beyond confirming SEAL existence at poll time, no hashes, no counts).
- Known limits: common-word names (will/mark/hope/...) unfixable;
  "as"/"nes"-ending s-names strip (Thomas -> Thoma's, June -> June's
  works, Lucas residual); multi-word names, "X is a Y", our/we owners
  fail on 263 even clean.

## Seal

Sealed files (12):
scripts/claude_type270_normalise.py, scripts/claude_type270_agent.py,
scripts/claude_type270_devset.py, scripts/claude_type270_devrun.py,
scripts/claude_type270_devscore.py,
artifacts/claude-type270-20260923/PASSMARKS.md,
artifacts/claude-type270-20260923/loop270-config.json,
artifacts/claude-type270-20260923/dev270.json,
artifacts/claude-type270-20260923/dev270_rowsA.json,
artifacts/claude-type270-20260923/dev270_rows263.json,
artifacts/claude-type270-20260923/devreport270.json,
artifacts/claude-type270-20260923/predicted_moves270.json
