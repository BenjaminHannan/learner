# RESULTS — redteam98: whole integrated agent under mailbox attack (2026-09-22)

Result first: 64 new cross-component cases through the exp-90 Loop90Daemon
mailbox (fresh temp dir per case, Mac CPU, offline, 3.6 s): 48 OK, 16 BUG
(3 critical, 4 high, 9 medium), 0 UNCLEAR, 0 crashes of the harness. The
joined-up agent keeps every promise of its parts and breaks at their seams:
template ears plant web/hearsay text as taught facts, the M1 forget/quote
verbs never survive the ears chain, one stray "?" rewrites a fact, and one
bad byte kills the daemon. Nothing was fixed (red-team rules).

## Counts (every case reported, never averaged)

| group | cases | OK | BUG |
|---|---|---|---|
| A teach->web contradicts->ask | 8 | 3 | 5 (A2,A6,A8 critical; A3,A5 high) |
| B teach->correct->two-hop | 8 | 7 | 1 (B5 medium) |
| C forget->two-hop must abstain | 8 | 2 | 6 (C1-C5,C7 medium) |
| D qualifier English->unqualified ask | 8 | 6 | 2 (D2,D7 medium) |
| E mailbox abuse | 10 | 9 | 1 (E7 high) |
| F restart / kill-9 | 6 | 6 | 0 |
| G hostile names | 8 | 8 | 0 |
| H inference never overwrites taught | 8 | 7 | 1 (H5 high) |

Ledger P98.1 TRUE (64/64, 3.6 s) | P98.2 TRUE (>=1 critical web-overwrite)
| P98.3 TRUE (8/8 forgets clarify + stale answers) | P98.4 TRUE (E7 raises)
| P98.5 TRUE (F1/F2/F6 + F4 30/30, 0 wrong) | P98.6 TRUE (B5 stale Spanish).
6/6 TRUE; marks R1-R5 PASS (R4 scale fixed pre-run; R5 this file + doc 98).

## The 16 BUGs (each with a failing reproducer in repro/)

Critical — taught fact overwritten by non-teach text: A2 ("Krakow, Tom
said." becomes the capital via correction-inference), A6 ("Rome, according
to the web."), A8 (same shape on a two-hop mid fact, answered "French, I
read online."). The bench73 stage treats any template-shaped sentence as a
teach/correct, including hearsay suffixes.
High — junk entities planted: A3 ("I read online that Roberto Merhi" becomes
a person, citizen of France), A5 ("quote CM Punk" becomes a person). H5 (a
"?" on a teach-shaped sentence corrects "AJ Lee" to "AJ Lee?"). E7
(non-UTF-8 inbox bytes raise UnicodeDecodeError out of process_file; the
production run() loop catches only LogCorrupt, so one bad file kills the
persistent agent).
Medium — C1-C5,C7 (every "forget ..." clarifies with 0 writes; the chain
still answers the stale fact; the M1 forget verb is unreachable through
ChainEars, which emits only teach/correct/ask/clarify). B5 ("Actually, " +
template sentence clarifies; the correction is silently dropped). D2/D7
("Lisbon in 2019" / "Warsaw since 1596." stored and answered verbatim).

## Held under attack

Restarts keep everything (F1/F2/F6), SIGKILL mid-burst restarts chain_ok
with 30/30 correct and 0 wrong (F4; kill landed idle, see deviations),
sealed-tail tampering refuses boot with "log truncated" (F5), duplicate ids
are idempotent (E1/E2), empty/whitespace/50 KB/half/completed/same-second/
non-.txt mail is handled safely (E3-E6,E8-E10), two-hop corrections land
(B1-B4,B6,B8), hostile names round-trip (G1-G8), asks never write (H1,H7).

## What it means

The loop is durable (mailbox, seal, restart) but its English front door
cannot tell teaching from quoting: anything shaped like a template sentence
is believed, and the verbs that would retract or quarantine it don't exist
in the chain.

## What it does not mean

No notebook, reasoner, thinker, or seal primitive is broken in isolation;
every critical here is a seam effect (ears template + correction-inference +
no quote/forget path), fixable without touching the parts.

## Deviations

D1 (post-first-run, pre-registration-close): the first wave exposed three
harness-side expectation bugs, not agent behaviour — reply indices counted
RESTART log lines as turns (F1/F2/F3/F6/E10), and absent_everywhere scanned
legitimate teach echoes (B7/C1-C5/C7/D8/A3). Run-1 evidence is preserved
(fable_redteam98_results_run1.json + fable_redteam98_cases_sealed_v1.json,
the latter still matching SEAL.sha256.txt); v2 expectations scope absence to
the post-intervention turn. No agent verdict changed direction except the
eight named expectation bugs (all now OK) — every other BUG reproduces
identically in run 1 and run 2. Genuine mid-fsync torn-tail repair was not
hit (F4 processed 31/31 before SIGKILL); only the sealed-line tamper path
(F5) was exercised.

## Questions for Ben

None. Suggested next experiment (not this one): route quote/hearsay-shaped
mail to quarantine and expose forget through ChainEars.

## Reproduce

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B
scripts/fable_redteam98_runner.py --run` (reads the sealed v1 expectations;
v2 file documents D1). Any single BUG: run its
`artifacts/fable-redteam98-20260921/repro/fable_redteam98_repro_<ID>.py`
with the same invocation — it fails today.
