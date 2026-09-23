# 208 — Natural panel: what Ben experiences (muse)

## Problem

Frozen suites speak stilted agent-English ("The capital of C10 is W10").
Nobody measured what happens when Ben chats normally: "My sister Ada lives
in Leeds", "She works as a nurse", typos, two facts at once, corrections,
small talk, "What's the capital of France?". Exp 208 is that test set —
no agent change, a baseline later bases re-run.

## Design

`panel208.json`: 100 turns, 20 dialogs × 5, fictional names only, fresh
notebook per dialog. Each turn carries its expected behaviour (SAVE /
ANSWER / ABSTAIN / ASK / CHAT), the expected fact or answer substring, and
what counts as a bad write. Categories: teach 28, ask 46, correction 4,
small talk 8, self 5, out-of-scope 5, typo 4. `rubric208.md` grades every
turn OK / wrong / unhelpful / bad write; bad write outranks (a turn that
stores junk is bad write even with a fine reply).

`scripts/fable_naturalpanel208_driver.py` is reusable for any agent +
config: it copies the marks123 pattern (load_agent / load_base_cfg /
make_daemon / process_file), one isolated scratch notebook per dialog,
mailbox files per turn, idle_seconds=3600. It logs reply, statuses,
fact_writes, new triples and full triple state per turn, plus G1
automatic (write counts, answer substrings, abstain bits). G2 is a human
reading of all 100 replies; G1/G2 agreement is reported, G2 rules.

## Result on loop138i

G2 OK 28/100: teach 5/28, ask 1/34, corrections 0/4, typos 0/4, chat
15/23 (all chat turns writeless; 8 greeted with the abstain macro).
Only narrow surface forms save ("X lives in Y", possessive is-statements);
jobs, ages, likes, pronouns, paraphrases miss. Asks on stored facts can
still miss by question form (father vs dad; "remind me?"). Zero junk
writes: the loop never guesses, never stores web/chat text — its failure
mode is silence, not confabulation. Full counts in RESULTS.md.

## Use

Later bases run the same driver on the sealed panel and compare one
number (G2 OK) plus the N3 shape list. Panel, rubric, PASSMARKS and driver
are hash-sealed; any post-seal edit forces FAIL.

## Limits

100 turns cannot cover all phrasing; G2 chat grading needs the documented
bright line; the driver grades writes via notebook_triples (taught-active
only). Questions for Ben: none.
