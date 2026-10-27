# 126 — Demo transcript harness (Muse, 2026-09-22)

## Problem

Exp 88 rehearsed the family demo through the structured listening doorway
with a transformer baseline arm. The director needs a different artifact:
a live, plain-English evening with an integrated mailbox agent (loop117
tonight, loop113b as the composer comparison), re-runnable on tonight's
integrated agent with `--agent <loop script> --config <config>`. It must
show the whole arc a viewer cares about — ignorance, teaching, joined-up
questions, forgetting, refusal to overwrite, self-knowledge limits, sleep —
with every turn verbatim and every number read from a file, never typed.

## Design (additive only; no existing file touched)

New: `scripts/fable_demo126_run.py`, this doc, artifact
`artifacts/fable-demo126-20260922/`. Everything else is imported or
spawned read-only.

The harness spawns the agent's own daemon (`--daemon --dir <fresh>`,
`--idle-seconds 3600` so no idle tick interferes) and talks to it only
through mailbox files: each Ben line is atomically written to
`inbox/tNNNN.txt` (tmp + replace; a torn write once produced an empty-turn
reply in dev, hence atomicity), the reply is polled from the matching
`outbox` file, then a STOP file ends the run. One fresh daemon dir per
agent; the notebook inside is the only store.

The conversation (~37 turns) is fixed in `TURNS` with per-turn check kinds:
abstain / saved / exact / forgotten / refuse / clarify / fourhop. Wording
was calibrated in dev probes to templates both agents parse: possessive
teaches ("Mira's mother is Ana."), bench73 templates without trailing
periods ("Mira is married to Theo" — a trailing period leaks into the
entity name and breaks hop 2, found in trial), "Forget Mira's city.",
"Actually"-free contradiction ("Mira's city is Oslo."). Act 3's four-hop
uses a dedicated single-outgoing chain (Ivy/Owen/Petra/Peru/Quechua) in
bench73 phrasings the N-hop composer covers; it is sent only when the
agent stem shows a composer, else the transcript carries the "not
supported by this agent" note and results record SKIP, never a fake.
Act 7 teaches mother-chains then probes "maternal grandmother" on taught
chains and on strangers: both agents carry HardGate46Sleeper with
reasoner=None, so no install is possible — the sealed expectation is
honest abstain, ≥1 audit-only sleep tick in state.json, and zero
sleep-derived facts. Act 8 reads the bench113b/bench66 JSONs and any
bench125 row files present at run time straight into the transcript.

Per-act PASS/FAIL is evaluated in-script against `EXPECT` (frozen before
the run, mirrored in PASSMARKS.md); the transcript is asserted verbatim
(every Ben line and reply present) and the panel asserted equal to a
fresh re-read.

## Evidence (to be filled by the registered runs)

Target: A1–A8 PASS on loop117 (four-hop SKIP) and on loop113b (four-hop
Quechua), each < 900 s Mac CPU.

## Limits

The script speaks only templates the agents parse — not broad English.
Sleep is audit-only ticks, not learning (no episode feed). The panel
re-quotes earlier files; it is not new evidence. Two-hop/three-hop
wording must keep taught entities unambiguous or the composer gate
declines (by design).

## What it means / does not mean

Means: one command replays a full honest evening — teaching, joining,
forgetting, refusing, abstaining, sleeping — verbatim, re-runnable on any
`--agent/--config` pair. Does not mean: the agent understands free-form
English, learns overnight, or answers anything it was not taught.
