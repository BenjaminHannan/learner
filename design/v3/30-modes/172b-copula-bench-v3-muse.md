# 172b — copula-ask agent 172 under bench protocol v3 (design, Muse)

## Problem

Exp 172 fixed the agent (copula/verb-shape re-teach of a non-allow-listed
relation without an explicit correction prefix now asks the possessive
change-prompt) and stopped at its gate: 681/800 bench items move because
bench counterfactual edits ARE copula re-teaches that the old driver
leaves unanswered. The director ruled (08:20): the agent keeps asking;
the bench models a user who states an edit and means it. So bench
protocol v3 = "confirming user": after any bench edit turn whose reply is
the agent's change-prompt naming that edit's new value, the driver sends
exactly one extra turn "yes" and continues. No other extra turns, no
other replies accepted, the question turns are unchanged. The agent code
is 172's, unchanged (the ONE agent change versus loop154c).

## Design

New files only, prefix 172b. Agent: `scripts/fable_loop172_agent.py`
(172's; read-only). Driver: `scripts/fable_fix172b_benchv3.py` reuses
154c's bench121 pattern by import (`fable_bench121_run` scorer/paths,
daemon class swapped): teach sentences verbatim in order; after a taught
turn whose reply contains the CONFLICT template
`Do you want me to change it to <new>?` with `<new>` occurring in the
taught sentence, send one `yes` mailbox turn; count confirms per split.
Row schema extends `run_item` with `confirms`/`yes_replies`, so verdicts
compare directly with frozen rows. Pending is always clean (every earlier
prompt was just confirmed), so any prompt after a teach necessarily names
that edit's value; the substring check enforces the ruling literally
(5 non-prompt rejects took no confirm). Probes:
`scripts/fable_fix172b_probe.py` replays sealed case files through fresh
`build_agent172` loops with exact-reply + notebook-state checks (state
reader reused by import from 154c). G3: `scripts/fable_fix172b_g3.py`
mirrors 154c's G3 with the 172 daemon (idle_seconds=30.0). G2 compare:
`scripts/fable_fix172b_markscmp.py` diffs marks123 reports per-case
against frozen marks154c with the pre-written allowlists.

## Why v3 composes

154c prompts only on possessive re-teaches (bench has ~none: 2 in
bench132); 172 prompts on possessive AND copula re-teaches. A "yes" lands
the identical value 154c writes silently, so both agents converge to the
same notebook state before the (unchanged) question turn — hence the
predicted 800/800 verdict+reply identity, confirmed. Without the "yes"
(old driver) the prompt is dropped by the next turn and the kept chain
answers: stale wrong/abstain on exactly the scan-flagged items.

## Predicted moves and why each is correct behaviour

p2 B1/B2/B3/B7/B8/F2: the copula re-teach prompts, nothing confirms it in
the marks driver, the kept taught value answers (Spanish/English/USA/
Spanish) — a taught-true statement, never a false write (prompt turns
write 0 facts). B6: Krakow unconfirmed, Warsaw re-teach dup-acks, final
Warsaw. rt110 F2/F6: `forget` empties the slot (172 never touches forget
actions), so the re-teach is a first-teach `Saved:` — identical. D5: the
vanished turn never reaches the ears — identical. marks-bench (old
driver): stale-chain verdicts only on scan-flagged ids. G3: zero (scan
found no copula re-teach of an occupied slot in any of the three sets).

## What it is not

No agent change, no notebook/allow-list/scorer change, no rule change
after the seal. The two v3-on-154c diffs (105 reply wording, 162
wrong->abstain) are protocol effects of confirming 154c's own two
possessive prompts, not regressions: abstain-over-guess on a chain broken
by a pre-existing multi-fact reject is the designed behaviour.

## Cost

Slowest registered run 344.8 s (marks123, workers=2); bench arms ~45 s;
G3 8.7 s; probes < 1 s. All Mac CPU, OMP/MKL=1, suites sequential.

## What it means

One driver-side "yes" reconciles ask-first consistency with a
meaning-it user: identical bench, zero new wrongs, zero suite moves
beyond the predicted ones.

## What it does not mean

It does not bless silent replacement anywhere: 721 bench prompts fired,
and every unconfirmed one keeps the old value. Any future bench edit in a
new surface shape that neither prompts nor replaces would need its own
ruling.
