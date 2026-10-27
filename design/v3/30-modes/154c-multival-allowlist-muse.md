# 154c — multi-valued relations as an allow-list (design, Muse)

Base: loop154b (`scripts/fable_loop154b_agent.py`), subclassed read-only.
No loop154b / loop138b file is edited. New files:
`scripts/fable_loop154c_agent.py` (agent), `scripts/fable_fix154c_allowlist.py`
(allow-list), `scripts/fable_fix154c_probe.py` + `scripts/fable_fix154c_regress.py`
+ `scripts/fable_fix154c_g3.py` + `scripts/fable_fix154c_scan.py` (drivers),
config + probes in `artifacts/fable-multival154c-20260922/`.

## Step 1: where 154b decides multi-valued

154b's test is `scripts/fable_fix154b_multival.py:39-41` (`is_single154b`):
a relation takes the add-a-second-value path iff its key is NOT in
`SINGLE_VALUED_154` (`scripts/fable_fix154_yesno.py:64-76`). That table has
only 11 entries (mother, father, capital, place_of_birth, date_of_birth,
city, spouse, wife, husband, boss, teacher), so 154b kept a second value
for EVERYTHING else -- including citizenship, language, occupation, team.
Registered result: p2 group-B/F (B1, B2, B3, B5, B8, F2) and p3 l5z2
(mquake-twohop) fell from 100 to 7 correct, because those suites teach a
re-teach of citizenship/language as a CORRECTION (replace), while 154b
kept both values and listed/clarified (FAIL by design, recorded in
`artifacts/fable-multival154b-20260922/RESULTS.md`).

The base parser's relation mapping is trivial
(`scripts/fable_agent_loop.py` `FakeEars._relation`: lowercase, split on
whitespace, join with `_`). So the full list of relation keys the parser
can emit is: every lowercase underscore-joined surface -- unbounded. The
allow-list below therefore works as default-deny: any key not listed takes
the loop138b path byte-identically (change-prompt / replace); listed keys
take the 154b path byte-identically (add, oldest-first `and`-join ask,
mid-chain clarify, correct-not, forget-one-value).

## The allow-list (sealed; one-line reason each)

`sister` (several sisters are normal); `brother` (several brothers are
normal); `sibling` (several siblings are the normal case); `friend` (many
friends are normal); `child` (several children are normal); `son` (several
sons are normal); `daughter` (several daughters are normal); `pet` (several
pets are normal); `dog` (several dogs are normal); `cat` (several cats are
normal); `cousin` (many cousins are normal); `grandchild` (several
grandchildren are normal); `grand_child` (spaced surface "grand child"
parses to a distinct key); `grand_son` (spaced "grand son" is a distinct
key); `grand_daughter` (spaced "grand daughter" is a distinct key);
`aunt` (several aunts are normal); `uncle` (several uncles are normal);
`colleague` (many colleagues are normal); `coworker` (many coworkers are
normal); `co_worker` (spaced "co worker" is a distinct key); `co-worker`
(hyphenated "co-worker" is a distinct key); `notable_work` (creators
normally have several notable works).

Explicitly NOT listed (deny-listed, i.e. loop138b replace-semantics):
citizenship / country_of_citizenship, language / official_language /
languages_spoken_written_or_signed / speaks, country / country_of_origin,
occupation, job, employer, position / position_played_on_team_speciality,
league, team, sport, religion / religion_or_worldview, genre,
headquarters / headquarters_location, capital, city, place_of_birth,
place_of_death, and every SINGLE_VALUED_154 entry (mother, father, spouse,
wife, husband, boss, teacher) plus all place/organisation relations
(author, creator, founder/founded_by, director, manufacturer, developer,
performer, continent, chairperson, head_of_state/government, educated_at,
work_location, ...). Anything unlisted is deny by default.

## How it is built (mixin subclass of loop154b, additive only)

`Loop154cAgentLoop` subclasses `Loop154bAgentLoop`; `turn()` and the three
154b action handlers (`_act_correct_multi154b`, `_act_forget_one154b`,
`_act_multi_teach154b`) are inherited verbatim. Three overrides: (1) at
build, `_wrap_relation154c` declares ONLY allow-listed relations
non-functional (deny-listed multis stay functional, exactly the base
behaviour, so a re-teach replaces); (2) `Loop154cEars.hear` runs the two
154b pre-scans only for allow-listed shapes and otherwise calls
`Loop138bEars.hear` directly (never `super().hear`, whose 154b conditions
would fire on deny-listed keys such as citizenship); (3) `_act` routes
teach/correct on allow-listed keys to the inherited 154b add path and
every other teach/correct straight to `Loop138bAgentLoop._act`, and
post-processes asks only through allow-listed hops (`_post_ask154c`).
Sleep145 retrofit, 148b screens, daemon settle/atomic rules inherited
unchanged. `Loop154cDaemon` swaps only the agent class so the marks123
loader picks it up.

## Registered predictions (summary; full text in PASSMARKS.md)

T1: 154b's sealed probe 81/81 exact (all its multi cases use
sister/friend/brother/child/pet, all allow-listed; all its single cases
are deny). T1b: new 32-case probe -- 16 deny re-teach/edit cases
byte-identical to loop138b (incl. multi-word subjects, copula shapes),
11 allow add-second-value cases in 154b's sealed forms, 5 two-hop
clarifies through a 2-valued allow hop. T2: 0 wrong writes, 0 lost.
G1 bench: moves vs loop138b only on the 16 pre-sealed allow-dup items
(child/notable_work double-teaches), 0 elsewhere, 0 new wrong. G2
marks123: per-case identical to marks138b on every suite (154b's only G2
moves were deny-relation re-teaches; allow relations never trigger there).
G3: 0 moves, 0 new WRONG/WRONG-WRITE. G4: every run < 1500 s.

## What it means

People have several sisters, friends, children, pets, cousins, aunts,
uncles, colleagues and notable works; the assistant keeps every value
taught for exactly those relations, lists them when asked, and asks which
one you mean before reasoning through one.

## What it does not mean

It does not change re-teaches of citizenship, language, occupation,
employer, team, or any other deny-listed relation: those still ask before
replacing, exactly as loop138b. It does not merge or deduplicate values,
and it does not guess which sister you meant in a longer question.
