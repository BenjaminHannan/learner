# 150 — Subject-span guard (Muse)

One-change fix for the director's loop139b probe: eight teach sentences each
stored a polluted subject ("I think Kip Dune", "Perhaps Kip Dune", "Maybe
Kip Dune", "Someone told me Kip Dune", "Rumor has it Kip Dune", "Honestly
Kip Dune", "So Kip Dune", "My friend Kip Dune"). Exps 139/139b guard only
the VALUE span, so the subject span -- captured by the same greedy
`(.+?)` template match -- entered the notebook raw. The fix is a
subject-span guard applied to every teach/correct path just before the
write, at the same two levels as the value guard.

## The rule

On the subject span AFTER the exp-129 strip, the turn:

(a) does NOT write when the subject starts with a hedge opener (maybe,
perhaps, probably, possibly, likely, presumably, i think, i guess,
i believe, i suppose) -- existing value-guard SPLIT clarify -- or a
reporting opener (i heard, someone told me/said, they say, people say,
rumor/rumour has it, word is, i read that/online, according to,
apparently, reportedly) -- existing loop102 HEARSAY reply. Both replies
reused; nothing invented. Matching is case-insensitive, word/comma
boundary ("Maybe, Kip Dune" refuses; "May Lee" does not match "maybe").
(b) stores the CLEAN subject when it starts with a discourse filler or
introducer (by the way, my friend/neighbor/neighbour, so, well, ok, okay,
honestly, anyway, also, btw, oh, actually, frankly) -- stripped to a
fixpoint, remainder re-screened by (a)/(c), so "so maybe Kip Dune" still
refuses. "So, Kip Dune" strips the comma too; hyphenated "So-Yeon" is one
token and never matches "so".
(c) gets the SPLIT clarify with no write for any other multi-token subject
whose first token is an all-lowercase word with a capitalised token later
and no " of " ("yesterday Kip Dune"). Deliberately NOT covered:
single-token subjects (untouched, base-identical); all-lowercase subjects
("wide receiver", "association football" -- legal common-noun entities per
exp-102); "<lowercase words> of <Name>" role phrases ("director of
American Broadcasting Company" -- the bench-legit officeholder shape);
camelCase products ("macOS Server", "iPod Touch", "iOS SDK" -- styled
names, found by scanning all 3775 bench subjects); and the "i feel" hedge
is excluded (bench songs "I Feel Love", "I Feel Fine").

## The capitalised-name rule

A leading token with an initial uppercase letter is a name token even when
the word exists in English -- Will, May, Hope, Grace, Rich, Sunny, Frank,
Mark, So-Yeon all store exactly ("Will Smith is married to Jada Pinkett",
"May Lee is a citizen of Peru"). Rationale: teaches put names in subject
position capitalised, and the guard matches pollution only from the closed
opener lists plus lowercase-lead shape, so dictionary membership never
refuses; bare "may"/"will"/"mark"/"frank" are not openers and "maybe" does
not word-boundary-match "May Lee".

## Where it sits

`SubjectGuard150Mixin` (scripts/fable_fix150_subjectguard.py) is
cooperative, stacking with sibling mixins: `hear()` runs the base hear
first (129 strip + 139b value screen already applied) then screens/rewrites
the `name` of teach/correct actions; `_act()` re-checks strip-then-screen
just before the write, covering the inner-chain delegate path. loop150 =
loop139b + mixin at both levels (scripts/fable_loop150_agent.py, --daemon
entry with idle_seconds). Values, relation keys, forget/ask/clarify paths
untouched; no existing file edited.

## Results (registered PASS, 5/5)

S1: sealed 57-case probe 57/57 (22 hedge/reporting no-writes with the right
reply kind, 16 filler exact clean triples, 16 legit exact incl. all 9
word-like names, 3 handled-already unchanged; full triple judged, 0 wrong
writes; base wrote all 36 polluted subjects). S2: director's 8 store no
polluted subject. S3: bench 600/600 per-item identical to loop139b, marks123
10/10 suites + all per-case rows identical. S4: redteam136 0 per-case moves
(OK 126 / WW 14 / MISSED 5). S5: slowest run 133.5 s. See
artifacts/fable-fix150-20260922/RESULTS.md.

## What it means

Polluted subjects never enter the notebook while real names -- even
dictionary-word names -- store exactly; the change is invisible everywhere
except its target (zero bench/marks/redteam moves).

## What it does not mean

No truth judgement -- confident false single facts still store;
all-lowercase multi-word pollution ("yesterday kip dune") still stores by
design (bench common nouns force the exemption); value-side and remaining
136 classes are out of scope.
