# Exp 124 RESULTS — red team round 3 (N-hop composer + fallback)

62 NEW multi-turn cases, 12 families, each in a fresh daemon dir through the
mailbox, vs loop113b (primary) and loop102 (before column). 124 runs,
0 HARNESS-ERROR, 6.2 s wall-clock (Mac CPU, OMP=1, offline).
Seal `cdef0361…` (cases) / `06819c73…` (PASSMARKS) preceded all runs.
No existing file edited; new files only (`fable_redteam124_*`).

## Marks (strict per sealed definitions; genuine subset after triage)
| mark | strict | genuine (agent behaviour) | bar | verdict |
|---|---|---|---|---|
| M1 wrong writes | 10 events (R1,R2,R3,V6,V7 x2 arms) | 10 (same) | 0 | FAIL sealed-critical |
| M2 confidently wrong answers | 46 reason lines | 40 answer events (17 x113b, 23 x102) | 0 | FAIL sealed-critical |
| M3 invented names | 128 capitalized-absent hits | 11 (U3-113b AJ Lee + 10 period-junk) | 0 | FAIL sealed-critical |
| M4 per-family BUG counts | see table | 18 x113b / 25 x102 genuine | report | reported |
| M5 harness errors | 0 | 0 | 0 | PASS |

Strict counts are inflated by 48 expectation errors of mine (absent-decoys
echoed in `Saved:` acks and `UNKNOWN_ENTITY` template echoes, e.g. C03–C06,
S1–S4, L2/L4; plus S3/T2/V10 where loop102 correctly answers full 2-hop
chains I wrongly sealed to clarify). Verdicts stand per seal; triage below
is explicit. Strict: 113b 22 OK/40 BUG; 102 11 OK/51 BUG.

## Genuine bugs (each with minimal reproducer, all fresh-dir mailbox runs)
1. Prefix answers on broken chains (113b: B2,B3,B4,B5,B6,G1,R2,V4,W2).
   Min: B6 — teach `Roberto Merhi is a citizen of Spain`, ask the language
   → answers `Spain`. Cause: `compose_n_hop` returns the walked prefix at
   the break (`fable_bench92_english_arm.py:224-235`), and `Loop113bEars`
   asks any non-None frame (`fable_loop113b_agent.py:78-85`), so the
   fallback never fires — the 113b-outcome M1 mechanism, still present.
2. Same truncation already in loop102 (C01,C02,C03,C07,Q1,Q3,Q4,E2,E5,W1,
   T1,T4,U1,V4,B3,B5,G4,C08,Q2): `compose_question` walks 2 hops and
   `Bench73Stage` asks ANY frame with no explicitness gate
   (`fable_loop90_agent.py`), the gate existing only in 113/113b routing.
   Min: C01 on 102 → 2-hop `Spain` for a 3-hop question.
3. Wrong-question answers (113b: C08 whose→Spanish, U1 occupation→Spanish,
   U3 employs→AJ Lee, Q2/V11 as-of-year→Spanish). Min: U3 (2 turns).
   Cause: coverage gate is one-directional — walked ⊆ mentioned required,
   extra/unknown relations and interrogatives never block
   (`fable_bench92_english_arm.py:237-240`).
4. Trailing-period junk writes (R1,R2,R3,V6,V7, BOTH arms — shared teach
   path): `Actually, AJ Lee is a citizen of Portugal.` writes
   `(AJ Lee, country_of_citizenship, 'Portugal.')`. Cause: F3 correction
   feeds the raw sentence incl. `.` to `hear_teach_template`, whose
   patterns capture it into the object (`fable_bench73_english_arm.py:194-205`),
   and `Bench73Stage._teach_action` treats it as a new object
   (`fable_loop90_agent.py`). Cascades: R1/V6/V7 then answer junk or break.
5. V4 branch-mid: second outgoing edge stops the walk → 1-hop prefix asked.

## What held
3/4/5/6-hop novel phrasings answer (C01–C05,C07,V1, incl. 211-char W1 and
shouted V10/T2); loops refuse safely (L1/L3 answer, L2/L4 clarify); same-name
ambiguity clarifies (S2/S4); forget/reteach/qualifier-drop paths work
(G2,G3,G4,Q1,Q3,Q4); hearsay/self/long-teach all clarify with 0 writes
(V8,V9,E1,E3,E4,W4); 7-hop and no-entity clarify (V2,V3,V5); qualifier-on-tail
answers (Q4); typo-value chains walk (T4 Spian).

## What it means
The composer adds real capability (5/6-hop, long, shouted questions) but
answers prefixes of broken chains and answers wrong questions confidently;
plus a shared teach-path period bug writes junk triples.

## What it does not mean
It does not mean the fallback is broken — fallback paths (possessives,
hearsay, loops) were 100% safe; failures are all composer-frame shape errors
plus one teach-path punctuation bug.

## Deviations
None from the brief (62 ≥ 60 cases, 12 ≥ 8 families, no repeats of 98/110
case shapes, new names, <25 min). Harness note: my sealed absent-lists also
fire on teach acks — triaged as expectation errors, verdicts unchanged.

## Questions for Ben
None.

## Reproduce
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project \
--python 3.12 --with torch --with numpy python -B \
scripts/fable_redteam124_runner.py  # reads sealed cases, writes \
artifacts/fable-redteam124-20260922/fable_redteam124_results.json
