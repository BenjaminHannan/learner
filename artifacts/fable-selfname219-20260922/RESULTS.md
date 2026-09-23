# Exp 219 RESULTS — "YOU NEVER TOLD ME" REPLIES MUST BE TRUE (Muse)

Problem (director-verified on loop138i): after "My name is Juno." the
notebook holds (USER, name, Juno) and "What is my name?" answers "Your name
is Juno.", but "Do you remember my name?" routes to self intent D8 and gets
"You never told me your name, so I do not know it." — a FALSE memory claim,
the only wrong reply in a 31-turn demo dry run. Fix: the D8 denial is checked
against the notebook; when it holds the USER name the reply is "Yes. Your
name is X." (X from the notebook); otherwise byte-identical. Reply-only,
never writes. Verdict: **PASS** (M1-M6 all pass, seal 8/8 OK post-runs).

Census (scripts/fable_fix219_selfname.py census()): D8 my-name — notebook CAN
contradict, grounded HERE. D9 Mira-age — CAN, already grounded by fix168
(passthrough). D6 Tom — handled by fix168 (passthrough). D5 why ("You never
told me why") + C22 "(never taught)" — notebook CANNOT contradict (reasons
never stored; C22 only lists MISSING_FACTs), byte-identical always.

## Marks table (integer counts, every case in m1/m2/m3-rows.json)

| mark | result |
|---|---|
| M1 taught name | 20/20 sessions; 100/100 probe rows pass; 20/20 teach replies identical to base; 0 "never told" claims while held — PASS |
| M2 no name taught | 5 sessions x 5 probes = 25/25 replies byte-identical to base — PASS |
| M3 D9 age | 10 stored (ages 5-14) x 2 probes = 20/20 state the stored value and equal base; 10 empty x 2 = 20/20 byte-identical — PASS |
| M4 frozen | rt136 0 moves; rt143 0 moves; sessions152 0 moves; bench 0 moves (edit200 149 correct/51 abstain/0 wrong; bench132_4hop 191/9/0) — PASS |
| M5 sleep smoke | sleeps=1 installed=1 episodes=20 probes=5/5 wrong=0 taught=50/50 ow=0 broken=abstain, identical to base 138i — PASS |
| M6 wrong writes | 0 new WRONG / WRONG-WRITE / junk on rt136, rt143, sessions152, marks123 (0 moves), bench 0 new wrong — PASS |

Base replies recorded pre-seal (base-replies.json): with name taught, 4 of 5
probes route D8 with the false denial ("Do you know my name?" takes the
notebook path and already answers "Your name is Juno."). Post-fix all four
answer "Yes. Your name is Juno." D5 stays byte-identical with and without a
stored name. All runs Mac CPU, OMP/MKL=1, each < 25 min (slowest: smoke
291 s). Seal verified post-runs: 8/8 OK, zero post-seal edits.

What it means: the assistant no longer denies being told something the
notebook proves it was told; every other behaviour is unchanged.
What it does not mean: it does not learn reasons, guess unknown names, or
change any stored fact — untaught-name replies are byte-identical.

Deviations: none from the plan. The M1/M2/M3 driver
(scratch run_marks219.py, kept out of the repo per the new-files-only rule)
reads the sealed case JSONs and writes m1/m2/m3-rows.json; suitediff and
sleepsmoke206 are the frozen shared drivers.

Reproduce (after seal; one suite at a time):
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_suitediff.py --agent scripts/fable_loop219_agent.py --config artifacts/fable-selfname219-20260922/loop219-config.json --base 138i --out <dir> --only <rt136|rt143|sessions152|bench|marks123>`
`python -B scripts/fable_sleepsmoke206.py --agent scripts/fable_loop219_agent.py --config artifacts/fable-selfname219-20260922/loop219-config.json --root <dir> --report <f> --label s1-219 --seed 1 --idle-seconds 30.0`

Questions for Ben: none.
