# Exp 224: one decline sentence per turn type (results)

**224a (scorer side): PASS.** **224b (agent side): FAIL as sealed.** B2 failed on one intermittent bench row. B1, B3 and B4 pass.

## Marks

| Mark | Bar | Result |
|---|---|---|
| A1 138i rows | 0 verdict changes, 0 sanity mismatches | 0 / 0 (rt136 145, rt143 124, sessions 180, bench 4×200, marks bench 2×200, rt81 74) |
| A1 138h rows | same | 0 / 0 |
| A2 | census 45/45, new 3/3, self-CANNOT rejected 7/7, ≥50 real rejected, 0 accepted | 45/45, 3/3, 7/7, 100/100 rejected, 0 accepted |
| B1 138i pre-run | Q2 and S1 get the glue; Q1 controls don't | Q2 30/30, S1 30/30, Q1 20/20, 0 writes |
| B1 loop224 | Q2 and S1 get their sentence; Q1 byte-identical; 0 writes | Q2 30/30, S1 30/30, Q1 20/20, 0 writes |
| B2 verdict moves | 0 | **1** (bench132-4hop-031, correct→abstain) |
| B2 other (non-glue) leaf moves | 0 | **5** (all on bench132-4hop-031) |
| B2 glue→sentence rows | listed | 102 (Q2 61, S1 41), type mismatches 0 |
| B2 rescore224 on 224 rows | 0 changes / 0 sanity | 0 / 0 |
| B3 sleep smoke | same marks as 138i | same: sleeps 1, installed, probes 5/5, wrong 0, broken=abstain, taught 50/50, ow 0 |
| B4 new wrong writes | 0 | 0 |
| Run time | < 25 min each | max about 88 s |

Seals: `224a/SEAL.sha256.txt` and `224b/SEAL.sha256.txt` both verified OK after the runs. No file was edited after its seal.

## The sentences

They fire only where loop138i served the glue ("I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way?").

- **Q1** (the ears made a lookup and the notebook has no value): "I don't know that yet — you haven't told me."
- **Q2** (a question the ears could not turn into a lookup): "I didn't understand that question — could you say it another way?"
- **S1** (a statement the loop could not save): "I didn't understand that well enough to save it — could you say it another way?"

The type comes from what the pipeline did on that turn:

- If the ears made an ask action, the type is Q1.
- Otherwise the type is Q2 if any of these holds:
  - the ears' question branch ran;
  - the text ends with "?";
  - the exp-151 question check fires.
- Otherwise the type is S1.

All other replies are unchanged, byte for byte.

## The B2 failure

In the registered bench run, row bench132-4hop-031 lost its usual 138b rewrite (ears stage "none" instead of "loop138b-rewrite"). loop138i-equivalent logic then produced the glue, and loop224 served **Q1**.

- The facts for that question had been taught, so "you haven't told me" was false there.
- The glue→Q1 path itself was never seen on 138i in any stored row.
- I ran 11 open reruns of loop224 and 11 of 138i on that split. The row came back correct every time (plus the pilot). So it is intermittent: 1 of 13 loop224 runs and 0 of 11 138i runs.
- The cause is not established. Earlier experiments (218, 220, 226) saw similar one-row flakes with no agent change, but I can't show that is what happened here.
- Two moves fail the sealed bar: the verdict move, and Q1 being served where the facts were taught.

## Moved rows (every row whose 138i reply was the glue, now one sentence)

- **rt136, S1:** C063–C071, C073, C074, C080, C081, C083–C085, C087, C088, C092, C093, C097, C098, C106, C115, C124, C127, C129, C131, C133, C137, C138, C141, C142.
- **rt136, Q2:** C076, C079.
- **rt143, all Q2:** A1, F6, H3, J9, K1–K5, K7, K8, L2, L3, L5, L6, M3–M6, O1–O4, P1, P2, P5, Q1, Q2, Q7, S1, S4, S5, T2, T3, U1, U2, U4.
- **sessions152, Q2:**
  - S1-family10#5, #8, #19
  - S3-teachers-correction#4, #10, #17, #19
  - S6-pronouns-corrections#3, #6, #9, #20
- **sessions152, S1:** S2-casual-friends#8, S3-teachers-correction#6, S6-pronouns-corrections#14.
- **bench, Q2:** bench121-4hop-026, bench121-4hop-066, bench103-s2fresh-4hop-187, bench132-4hop-019, bench132-4hop-112.
- **marks123 rt81, Q2:** D_q_vs_s-04, D_q_vs_s-05, N_yesno-02, Q_quote-02.
- **marks123 rt81, S1:** B_corrections-04, F_pronoun-03, K_json-01, K_json-02, Q_quote-01.
- **marks123 bench, Q2:** bench103-s2fresh-4hop-064, bench103-s2fresh-4hop-187.

## Deviations from the brief

1. **B1-Q1 can't be tested.** On 138i an ask always produces an answer record ("I don't know Mira's father." / "I don't know anyone called Zed."). So the glue is never reached for Q1, and the stored glue rows have no ask. Instead of Q1 test cases I used 20 Q1 controls, which must stay byte-identical. They did (20/20).
2. **Self-router CANNOT answers** ("I have no opinions.", "I cannot predict.", …) are *not* treated as declines. The brief put them in the census, but counting them turned rt143 misroutes J8/K9/O5 from WRONG-ANSWER into non-wrong.
3. **rt81 "must" strings** are content checks and were not swapped.
4. **rt110** is informational only. It sits outside the suitediff marks123 subset, and its list lacks "was that a question", which moves N6.
5. **fable_rescore224.py needs `--exclude diff`** on a suitediff folder. This is a usage-only workaround, not a code change.
6. **Imperative requests** ("Describe Veyla Orne.", "Explain what Tovin does.") get S1, because the pipeline treats them as statements. I did not add a keyword rule. The two cases were replaced before the seal and are listed in `pilot_limitations`.
7. **A1 is not independent evidence.** It was piloted on the same stored rows before the seal, so it is a compatibility check.

**What it means:** on every glue turn in the frozen suites and the 60 fresh cases, one sentence that matches the pipeline's failure (question vs statement) can replace the glue. No write changes, and every scorer still counts it as a decline.

**What it does not mean:** loop224 is not ready to ship. The Q1 branch fired once, intermittently, on a taught question and said "you haven't told me" when that was false. Imperative requests are mislabelled as statements.

## Reproduce

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY="uv run --offline --no-project --python 3.12 --with torch --with numpy python -B"
O=artifacts/fable-decline224-20260922
$PY scripts/fable_rescore224.py --rows-dir artifacts/fable-agent138i-20260922 --exclude g1bench-h --out $O/224a/a1-138i.json
$PY scripts/fable_rescore224.py --rows-dir artifacts/fable-agent138h-20260922 --out $O/224a/a1-138h.json
$PY scripts/fable_decline224_a2.py --out $O/224a/a2.json
$PY scripts/fable_decline224_b1.py --agent 138i --cases $O/224b/cases224b.json --scratch <tmp> --out $O/224b/b1-138i.json
$PY scripts/fable_decline224_b1.py --agent 224 --cases $O/224b/cases224b.json --baseline $O/224b/b1-138i.json --scratch <tmp> --out $O/224b/b1-224.json
for s in rt136 rt143 sessions152 bench marks123; do $PY scripts/fable_suitediff.py --agent scripts/fable_loop224_agent.py --config artifacts/fable-agent138i-20260922/loop138i-config.json --base 138i --out $O/224b/suitediff --only $s; done
$PY scripts/fable_rescore224.py --rows-dir $O/224b/suitediff --exclude diff --out $O/224b/b2-rescore224.json
$PY scripts/fable_decline224_b2.py --new $O/224b/suitediff --rescore $O/224b/b2-rescore224.json --a1 $O/224a/a1-138i.json --out $O/224b/b2.json
$PY scripts/fable_sleepsmoke206.py --agent scripts/fable_loop224_agent.py --config artifacts/fable-agent138i-20260922/loop138i-config.json --root <tmp> --report $O/224b/b3-smoke224.json --label s1-224
python3 -B scripts/fable_decline224_b3.py --report $O/224b/b3-smoke224.json --out $O/224b/b3.json
```
