# Exp 156c RESULTS — wider small talk on loop138h (Muse)

## Result: PASS (7/7 predictions TRUE)

Loop156c answers the director's held-out small talk ("Hello there.",
"How are you?", "Nice weather today.") with short kind replies that
never claim feelings, writes nothing, and moves zero frozen rows.

## The one change

`scripts/fable_fix156c_smalltalk.py` (Smalltalk156cMixin, outermost
ears layer on loop138h, read-only import) + thin wrapper
`scripts/fable_loop156c_agent.py`. Five closed anchored-phrase
classes, one fixed reply each: greeting / how-are-you / weather /
feelings / bye. Fires only on the exact generic fallthrough + a
whole-message match; possessive and question-word guards keep every
teach/ask shape on the base path. Clarify acts never write.

## Marks table (integer counts)

| mark | bar | got |
|---|---|---|
| S1 new small talk (44 rows, probe) | >= 40/44 exact class reply, 0 writes | 44/44 OK (greeting 8, howareyou 11, weather 10, feelings 8, bye 7), 0 stored triples |
| S2 near-miss (33 rows, probe vs loop138h) | 33/33 byte-identical reply + triples | 33/33 OK, 0 NEAR-DIFF |
| S3 redteam136 (145) | 0 moves, 0 new wrong/write | 0 moves; OK136/WRONG-WRITE6/MISSED3 base-identical |
| S3 redteam143 (124) | 0 moves, 0 new wrong | 0 moves; OK107/MISSED7/WRONG-ANSWER10 base-identical |
| S3 sessions152 (6 sessions) | 0 moves, 0 new writes | 0 moves, 0 new writes |
| S3 bench 4x200 | 0 verdict/reply moves, 0 new wrong | 0 moves all splits (194/2/4, 198/2/0, 150/50/0, 196/3/1 base-identical) |
| S3 marks123 (11 reports vs sealed marks138h) | per-case identical exc. volatile set | 11/11 SAME (sleep SKIP names new agent; total_seconds; rt110 statuses-only); p3-l5z1/p4-1-nonpass/rt81 FAILs inherited byte-identical |
| S4 timing | every run < 1500 s | max 232.9 s (soak); probe 3.1 s, bench 14.9 s, rt110 108.0 s |
| Seal | shasum -c all OK, no post-seal edits | 9/9 OK post-runs |

Director probe (in-process loop156c): "Hello there." -> greeting
reply; "How are you?" -> how-are-you reply; "Nice weather today."
-> weather reply; "Hi!", "Good morning.", "Thanks!", "Bye!" unchanged
(base answers kept byte-identical).

## What it means

Everyday chat no longer gets "I didn't understand that", and the
agent still cannot be tricked into mis-storing a fact by chat-shaped
sentences.

## What it does not mean

It does not remember greetings, learn names from chat, or answer
"who are you" — those belong to other experiments.

## Deviations

None after the seal. Pre-seal D-pilot note (in PASSMARKS.md): the
possessive guard was fixed from quadratic regex to a linear scan
after it timed out the 1 MB rt110-D2 junk case; parity battery 24/24
identical, probe re-piloted 77/77, rt110 re-piloted PASS (herr 0).

## Reproduce (Mac CPU, offline; runs were executed post-seal)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156c_probe.py --out artifacts/fable-smalltalk156c-20260922/probe156c-loop156c.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156c_suites.py --only junk
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156c_suites.py --only rt143
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156c_suites.py --only sessions
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156c_suites.py --only bench
scripts/fable_marks123_all.py --agent scripts/fable_loop156c_agent.py --config artifacts/fable-smalltalk156c-20260922/loop156c-config.json --out artifacts/fable-smalltalk156c-20260922/marks156c --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156c_comparem.py --got artifacts/fable-smalltalk156c-20260922/marks156c
shasum -a 256 -c artifacts/fable-smalltalk156c-20260922/SEAL.sha256.txt
```

## Questions for Ben

None.
