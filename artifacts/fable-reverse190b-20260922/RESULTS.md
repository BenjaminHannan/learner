# RESULTS — Experiment 190b: reverse no-match rewording (loop190b)

Base: loop190 (`scripts/fable_loop190_agent.py`,
`artifacts/fable-reverse190-20260922/`). One change, reply text only:
any closed-shape (E1–E4) reverse question with zero stored matches now
replies `I don't know anyone whose <R> is <V>.` with the relation
display name — even when the value was never taught. Plain who-is
questions about unknown names keep `I don't know anyone called <V>.`
Notebook events are byte-identical to 190 on every suite (clarify-only
wrapper, never writes). Registered verdict: **PASS**.

## Marks table (integer counts, every seed/case reported, none averaged)

| Mark | Bar | Result |
|---|---|---|
| R1 (V1b new case, 46 turns) | 15/15 r1 exact + full parity | 15/15 r1 exact (R1–R12 unknown values across boss/city/birthplace/mother/teacher/school/coach/friend/country in shapes E1–E4; R13–R14 correction-removed Zep; R15 153-frame already whose-form, identical); S12 match exact; 31/31 r2+trap+teach/correct rows byte-identical reply AND triples; 0 writes on all 32 asks; 0 FAILs |
| R2 (who-is unknown) | 8/8 unchanged | 8/8 byte-identical (W1–W6 forward possessive unknown-subject `called`; W7–W8 plain `Who is <Name>?` decline) |
| R3 (190 V1 suite, 70 turns) | only E1–E5 move | exactly E1,E2,E3,E4,E5 move `called` → `whose` (same value); other 65 rows identical; events identical all 70 turns |
| R4 redteam136 (145) | 0 moves | 0 moves, 0 new WRONG/WRONG-WRITE (OK 136, WRONG-WRITE 6, MISSED 3 — inherited counts, per-case identical) |
| R4 redteam143 (124) | 0 moves | 0 moves, 0 new wrong (OK 107, MISSED 7, WRONG-ANSWER 10 — inherited, per-case identical) |
| R4 sessions152 (180 turns) | 0 moves | 0 moves, 0 new wrong, 0 new writes (OK 165 / UNHELPFUL 15 both sides) |
| R4 marks123 (10 reports) | per-case identical | 10/10 compared, 0 diffs after scrub (p3 l5z1 FAIL, p4 P4-09 nonpass, rt81 15 unclear all inherited byte-identical; sleep SKIP; rest PASS) |
| R4 bench121 (4×200) | 0 moves, 0 new wrong | 0 moves, 0 new wrong all splits (new_121_4hop 194/2/4, old_s2fresh 198/2/0, edit200 150/50/0, bench132 196/3/1); 0 reversal rows matched closed shapes |
| Time | each run < 1500 s | max single run 250.9 s (soak); frozen+bench 81.9 s; rt110 213.6 s |

## What it means

Reverse questions with no stored match always name the relation now
(`Who lives in Lima?` → `I don't know anyone whose city is Lima.`),
never mislabel the value as a person — with zero changes anywhere else.

## What it does not mean

It does not mean new relations are learned, inferences are stored,
who-is wording changed, or any ask path writes.

## Deviations

None. All pilots ran on the final sealed code before the seal; no
post-seal edits (seal 8/8 OK after all runs). One note: suite-level
FAILs in marks p3/p4/rt81 are inherited from loop190 byte-identical,
not regressions (comparer exit 0, 0 diffs).

## Questions for Ben

None.

## Reproduce (Mac CPU, offline, one suite at a time)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix190b_v1.py --only all
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix190b_suites.py --only all
for s in p2 p3 p4 rt110 q1 bench rt81 sleep soak q4; do
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop190b_agent.py --config artifacts/fable-reverse190b-20260922/loop190b-config.json --out artifacts/fable-reverse190b-20260922/marks190b --suites $s; done
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix190b_marks.py
shasum -a 256 -c artifacts/fable-reverse190b-20260922/SEAL.sha256.txt
```
