# Exp 157c RESULTS — filler+Capitalised title guard on loop157b (Muse)

## Result: PASS on all marks (T1, T2, G1, G2, G3, G4)

Loop157c (loop157b + one mixin: a capitalised filler followed directly,
no punctuation, by a Capitalised word never strips; the whole run is
treated as the name via the deep loop157 parse) ends the WRONG-WRITE
class from the director probe with zero measured regressions against
loop157b.

## Marks table (integer counts, every seed/case reported, never averaged)

| mark | bar | got |
|---|---|---|
| T1 probe (scripts/fable_fix157c_probe.py, sealed cases157c.json, 56 cases) | 22/22 titles never shortened; 22/22 fillers identical to loop157b; 12/12 others identical | 56/56 OK (22 title, 22 filler, 12 same) PASS |
| T2 | 0 wrong writes over all 56 | 0 wrong writes PASS |
| G1 bench (scripts/fable_fix157c_bench.py, 600 items) | per-item verdicts AND replies identical to sealed loop157b rows, 0 new wrong | 0 verdict moves, 0 reply moves, 0 new wrong (split correct 136/157/150; wrong 1/0/0 identical to base) PASS |
| G2 marks123 (scripts/fable_marks123_all.py --workers 4) | per-case verdict identical to sealed marks157b; only allowed text diff: sleep SKIP reason filename | identical: p2 64/64, p4 30/30, rt110 62/62, q1 f5/m5 + replies, rt81 74/74, p3 all sub-marks + l5z2 200/200 + l4 3/3, bench 400/400 rows, soak counters, q4 leaks 7/7; sleep reason differs by filename only. ONE cosmetic diff: p3/l6 replied_before_kill counts (verdicts identical, pass true both arms; timing metadata, same class as the sealed 157b note) PASS |
| G3 sessions+redteam (scripts/fable_fix157c_session152.py, scripts/fable_fix157c_redteam.py) | sessions: 0 reply moves, 0 new WRONG/writes; rt136/rt143 two-arm: 0 moves, 0 new WRONG | sessions 0 moves (S4's 2 WRONG are base behaviour, identical); rt136 145 cases 0 moves (126 OK / 14 WRONG-WRITE / 5 MISSED identical both arms); rt143 124 cases 0 moves (91 OK / 21 WRONG-ANSWER / 12 MISSED identical both arms) PASS |
| G4 time | each run < 1500 s Mac CPU, OMP=1 MKL=1, daemon idle_seconds | probe 1.9 s, bench 31.2 s, sessions 2.4 s, redteam 22.4 s, marks123 187.5 s PASS |

Step 1 (pre-seal): the strip is scripts/fable_fix157b_capfiller.py:59
(strip_one_anycase157b, driven by CapFiller157bMixin.hear at :137).
Base bug reproduced pre-seal (dev only): loop157b saved
['Jude','singer','Paul'] and ['Brother','director','Joel']; loop157
refused both. Post-fix the new loop stores nothing on any of the 22
title cases (safe refuse; base still shortens 20/22).

## What it means

Title/name leads that collide with filler words ("Hey Jude", "Oh
Brother", "Well Charlie", across 11 relations) can no longer be
silently shortened into wrong saves, while real phone fillers with a
comma, punctuation, or lowercase follow ("Hey, Kim's...", "Oh. And
also...", "Btw who is...") behave byte-identically to loop157b.

## What it does not mean

It does not mean the assistant understands titles: blocked turns refuse
instead of saving under the full name. It does not change any other
refusal class, and a capitalised filler + capitalised name with no
comma ("Btw Tom's...") now refuses too — the safe direction, comma and
lowercase forms still save.

## Deviations / post-seal notes (reported, per rules)

1. New read-only analysis helper scripts/fable_fix157c_markscompare.py
   (post-seal, mirrors 157b's compare pattern; runs no agent, affects no
   mark) plus its two outputs in my own folder (g2-compare157c.json,
   q4-report.json). No rule changes, no sealed file touched (shasum -c
   clean).
2. G2's single cosmetic diff (p3/l6 replied_before_kill counts) is
   kill-harness timing metadata, identical verdict class to 157b's own
   sealed note; all per-case verdicts identical.
3. No FAILs, no silent re-runs, no rt110/soak flakes (both passed first
   try, no re-run needed).

## Reproduce (from worktree root, after seal verify)

shasum -a 256 -c artifacts/fable-title157c-20260922/SEAL.sha256.txt
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157c_probe.py --out artifacts/fable-title157c-20260922/probe157c-loop157c.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157c_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop157c_agent.py --config artifacts/fable-title157c-20260922/loop157c-config.json --out artifacts/fable-title157c-20260922/marks157c --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157c_session152.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157c_redteam.py
