# 143 — QUESTION-side red team vs loop132 (Muse, 2026-09-22)

For Ben in plain language: I attacked only the *question* half of the
assistant — teaching was already covered by someone else. I taught it 124
tiny made-up worlds, then asked tricky questions. It got 92 right, gave 21
confidently wrong answers, and said "I didn't understand" 10 times where a
person could have answered. I didn't fix anything — this is a bug list with
an exact suggested one-line fix per bug family.

## Target

`scripts/fable_loop132_agent.py` (the loop132 daemon) with
`artifacts/fable-bench132-20260922/loop132-config.json`. Loop132 wraps
loop121 unchanged and only adds `scripts/fable_qrewrite132.py`: when the
base path would say "I didn't understand", the rewriter tries to turn
relative-clause questions into the plain possessive form the old composer
already accepts. The composer under attack is therefore the unchanged
`compose_n_hop` (`scripts/fable_bench92_english_arm.py:198-240`) plus the
113b router (`scripts/fable_loop113b_agent.py:68-103`).

## Method

122 fresh cases + 2 confirms of doc-124 findings, sealed (case file +
PASSMARKS hashed before the run; ledger P143.1 predicted 4 WRONG-ANSWER
classes). Fresh daemon dir per case, teaches through the mailbox first,
then the question, outbox reply judged against sealed expectations
(exact answer or "abstain"). Verdicts: OK / WRONG-ANSWER (confident ≠
expected) / MISSED (abstained though the answer exists) / HARNESS-ERROR.
Every non-OK expectation re-read by hand before claiming a bug: 1 of my 124
expectations was wrong (H5 — the rewriter correctly answered a 2-mention
question I had sealed abstain; reclassified OK).

## Findings

Five WRONG-ANSWER classes (19 fresh cases + 2 confirms), ranked by how
likely a normal user hits them: (1) negation blindness — "not/never" is
invisible (N1–N5); (2) qualifier blindness — years and "as of ..." don't
block (T1/T5/B1); (3) short-chain prefix — asked-but-untaught hops,
including never-taught relations like "employs", are dropped while the
taught prefix is answered (U1–U5/K8/S4/T4/L4/A1); (4) answer-type mismatch
— shared cue stems ("developed"/"created") license a confident wrong-type
answer (K6/K10); (5) substring entity — "Norlandia" matches taught
"Norland" (O3). Two MISSED classes: sub-walk suffix blindness — a 1-hop
question fails whenever the taught chain continues past the asked hop
(P1/P2/Q1/Q2/D2); cue/format gaps — "lives", missing "?", typos (H3/J5/J8/
J9/J10). The unifying defect: the walk always runs to the sink and the
gate checks walked ⊆ mentioned only — never mentioned ⊆ walked, never
residue screening. One alignment rule (stop at the first unmentioned hop;
ask only if every mentioned relation was walked) fixes class 3, class 4,
and the suffix-blindness MISSEDs; negation/qualifier screens are two small
follow-ups. File:line + one-line fix per class in RESULTS.md.

## What held

All intact 1–4-hop phrasings (possessive, of-chains, relative clauses,
passives, polite/case/space variants); abstention on untaught relations,
unknown relations, unknown entities, branches, loops, and two-mention
questions; all three correction prefixes ("Actually,"/"No,"/
"Correction:"); the loop132 rewriter's island wins (F5/H4). Corrections
verified present in triples — post-correction misses are the walk defect,
not the notebook.

## Limits

Single deterministic run per case; in-process mailbox; English only; no
sleep/thinker involvement. Claims stay inside the 124 runs. No code fixed.

## What it means

Question understanding is safe exactly when the asked chain matches the
taught chain — any gap, extra word with meaning ("not", a year), or
continued chain beyond the question flips it into a confident wrong answer
or a confused shrug.

## What it does not mean

It does not mean the assistant invents facts from nothing — every wrong
answer is a taught value served in the wrong slot — and it does not mean
the rewriter regressed anything (both confirms reproduce doc-124 exactly).
