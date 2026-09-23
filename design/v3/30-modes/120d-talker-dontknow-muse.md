# 120d — Talker don't-know routing (Muse, 2026-09-22)

## Problem

With the mask-fixed talker as wire51's mouth, the 40-turn chat replay loses
two abstentions (1 vs 3). "Where is Zed's city?" gets "I don't know Zed's
city." and "Where is Ana's city's mother?" gets "I don't know Porto's city --
that is beyond what I was taught." The second is unfaithful: it drops
"mother" and invents "city". The older checkpoint said "" on both.

## Cause

`Notebook.ask` returns contract statuses the talker never trained on:
UNKNOWN_ENTITY (`scripts/fable_notebook_contract.py:238`, Zed resolve miss)
and BROKEN_CHAIN (`fable_notebook_contract.py:405`, literal Porto has no
"entity" key). Training records use only six statuses
(`scripts/fable_talker120_data.py:251-252`). The 120 mouth's `fallback_say`
ends in `return ""` (`fable_talker120_mouth.py:208`) for anything else. The
brake passes the unfaithful decode because it is a word allowlist
(porto/city/mother from the record; beyond/taught in FUNCTION_WORDS lines
94-98) — nothing compares the decoded status to the record's.

## Change

`scripts/fable_talker120d_mouth.py` subclasses `TalkerMouth` (base file
unedited): answer records with a non-six status go straight to
`C.Result(status, fields).say()` — no decode, never "". Six-status records
use the inherited talker + brake path unchanged. `contract_say` guards the
empty case so the path is silent-proof even for unknown future statuses.
Drivers `scripts/fable_talker120d_replay.py` / `fable_talker120d_score.py`
are copies pointing at the new mouth; wire51 untouched. Differs from 120c
(which kept decoding and only fixed the fallback): 120d removes the
brake-pass risk on those turns entirely.

## Evidence

Sealed PASSMARKS + ledger P120d.x before any run. Registered runs BLOCKED
(director checkpoint file absent). Open diagnostics with the surviving
100-step mask-fixed smoke checkpoint: replay x3 exactly equals wire51's
counts (12/3/0/6, 5 empties, 40/40 english per run), both turns verbatim
wire51 sentences; 500-record score after-brake 0, OK 250/250 (status 287/500
reflects the weak smoke model; held-out is all six statuses so routing is
untouched there).

## Adapter notes

No interface change: `Talker120dMouth` keeps the `Mouth.say(record)->str`
Protocol. The `contract_routed` counter is additive telemetry.
