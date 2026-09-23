# 98 — Red team of the integrated agent (Muse, 2026-09-22)

Earlier red teams attacked one part each (67 core notebook/reasoner, 79 web
quarantine, 81 listening doorway). This one attacks the joined-up exp-90
agent — `scripts/fable_loop90_agent.py` behind the daemon74 mailbox — with
64 new cases that cross component boundaries. Read-only throughout: the only
new files are `scripts/fable_redteam98_cases.py`,
`scripts/fable_redteam98_runner.py`, and `artifacts/fable-redteam98-20260921/`.

## How it drives the agent

One fresh temp dir per case under the artifact folder. Messages enter only
as `inbox/*.txt` files and are processed in sorted name order exactly as
`Loop90Daemon.run()` does; replies are read from `outbox/*.txt`. Restart =
rebuild `Loop90Daemon` on the same root (chain verify + seal on open).
Kill-9 = a real subprocess daemon (`--daemon`), 31-file burst with a
correction inside, SIGKILL, then restart and 30 asks. F5 truncates the last
sealed log line, then restarts. Asks never touch the notebook except to count
new FACT events for the zero-write checks.

## Findings, by seam

**Seam 1 — the ears believe any template-shaped sentence (critical).**
`Bench73Stage.hear` (`fable_loop90_agent.py:129`) tries
`hear_teach_template` (regex fullmatch) before anything else, and
`_teach_action` (`:153`) infers `correct` whenever subject+relation exists
with a different object. There is no provenance check: A2/A6/A8 show
hearsay/web suffixes ("Krakow, Tom said.", "Rome, according to the web.",
"French, I read online.") becoming corrections that overwrite taught facts,
and A3/A5 show prefixed sentences ("I read online that ...", "quote ...")
minting junk entities ("quote CM Punk" is now a person). The `quote` verb
exists in M1 (`fable_listening_m1.py:81`) but ChainEars never emits it, so
quoting protects nothing. H5 is the same seam from the other side: a "?"
routes to `compose_question` first, which returns None on a two-mention
sentence, and then the teach template (with "?" baked into the object)
fires a correction ("AJ Lee" -> "AJ Lee?"). D2/D7 are its mild form:
qualifier/Time junk ("in 2019", "since 1596.") stored and answered verbatim.

**Seam 2 — forget is unreachable end-to-end (medium, C1-C5/C7).** M1
implements `forget` (`fable_listening_m1.py:137`), and `AgentLoop._act`
(`fable_agent_loop.py:348`) even routes forget actions — but no ChainEars
stage ever produces one (bench73 has no forget template; FakeEars has no
forget parse). Every "forget ..." clarifies with 0 writes, so two-hop asks
keep answering stale facts. The notebook is innocent; the verb is lost at
the ears seam. Same root cause as redteam81's "person/alias/forget/quote
unreachable in English", now confirmed through the full agent.

**Seam 3 — correction paths disagree by shape (medium, B5).**
Bench73 re-teaches auto-correct (B1-B4,B6,B8 all pass, including two-hop
re-rooting), but "Actually, " + a template sentence falls through bench73
(fullmatch fails on the prefix) into FakeEars, whose `_STATEMENT` needs a
possessive shape — so the correction is clarified away and the stale fact
stands. Two correction recognisers, disjoint coverage, silent loss.

**Seam 4 — mailbox bytes kill the daemon (high, E7).**
`Loop90Daemon.process_file` (`fable_loop90_agent.py:489`) catches only
`OSError`; `read_text(encoding="utf-8")` raises `UnicodeDecodeError`
(a `ValueError`), which escapes. The base `run()` loop catches only
`LogCorrupt`, so one non-UTF-8 file ends the persistent agent. Everything
else abusive is safe: duplicates idempotent (E1/E2), empty/whitespace/50 KB/
half-then-completed/same-second/non-.txt all handled (E3-E6,E8-E10).

**What held.** Restart/kill-9/tamper discipline (F1-F6: 30/30 post-kill,
0 wrong, sealed-line tear refuses boot), hostile names (G1-G8, including
"Forget", "Ask", unicode, apostrophes), ask stability with zero writes
(H1-H4,H6-H8), and the M1 pending-confirm across restart (F3).

## Score

48 OK / 16 BUG (critical 3, high 4, medium 9) / 0 UNCLEAR across 64 cases;
every BUG has a ≤20-line failing reproducer in `repro/`. No part is
indicted in isolation — the notebook gate, reasoner, thinker quarantine,
and seal all behave; the failures are composition effects at the ears
seam. Fixes are a separate experiment; the two smallest seams to aim at
are (1) a quote/hearsay recogniser before the teach templates (or a
provenance flag that forces quarantine), and (2) a forget/quote path
through ChainEars.

## Limits and deviations

Deviation D1 (documented in RESULTS.md): run 1 exposed harness-side
expectation indexing bugs; run-1 artefacts are preserved and the v1 seal
still verifies. Genuine mid-fsync torn-tail repair was not hit (the F4
burst of 31 processed fully before SIGKILL); only the sealed-line tamper
refusal (F5) was exercised — crash-mid-append remains untested. Sleep and
neural ears/mouth paths were idle by construction (no checkpoint, threshold
unreachable in ≤6-turn cases), so inference-vs-taught beyond the
correction-inference was not stressed.
