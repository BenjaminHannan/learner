# 142 — Perf port onto loop134 (Muse)

## Problem
Exp 128 made per-turn CPU flat in notebook size (15k/1k p50 0.67–0.76), but
it is built on loop102. Tonight's base is loop134 (loop121 teach phrasings +
loop113b N-hop router + loop117 fixes), whose ears add paths 128 never
indexed. Without a port, the integrated agent's cost still grows ~9–10x.

## Profile (unregistered, `diag134.json`, 128's method on loop134)
Every O(n)-per-turn scan, file:line: contract `current()`
(notebook_contract.py:244); listening `_relation()` (listening_m1.py:61);
`notebook_triples()` (loop90_agent.py:109, via :133 and :76/:182 on "?");
`Bench73Stage._teach_action()` (:160, reached twice: chain :146 and loop121
:150); `filtered_view77()`/:`known()` (fix77_core.py:157/:244);
`_save()` dump 2x/turn (agent_loop.py:262); daemon set-copies
(loop102_agent.py:405); `compose_n_hop()` (bench92_english_arm.py:198);
`_walk_nodes()`/`compound_subject_hit()` (loop113_agent.py:109/:123);
`compose_question()` MQuAKE section (bench73_english_arm.py:246).
Kept as-is: `_resolve_forget_name()` prefix scan (loop102_agent.py:204,
forget turns only). O(1): teach regexes, hearsay/qualifier strips, 121/guard
screens, Fake templates, `resolve()`, thinker.

## Design (additive only, no existing file edited)
Reuse 128 by import (indexed notebook, FastReasoner77, relation patch,
chain-stage patch, tail-200 persist, sliced daemon bookkeeping: same log,
same decisions). New mixins in `fable_perf142_index.py`: `FastQuestionMixin142`
("?" router mirroring loop113b: hearsay → index N-hop walk → compound guard
→ 2-hop explicit/non-explicit → verbatim loop102 fallback; doubtful
never-taught/Who shapes delegate to original code); `_fast_compose_n_hop`,
`_fast_compound_hit`, `_mentions92` (same frames over the incremental
`(subject,relation)`/relation/mention indexes); `_fast_teach_action142`
(same act, loop121 stage tag kept). `FastReasoner142` (128's reasoner + the
empty-subject guard: None where the original view has no entry, fixing a
latent 128 crash on drop-cache HITs with no surviving rows).
`fable_loop142_agent.py`: `Loop142Ears`
(mixin first), indexed loop, `Loop142Daemon`, `--daemon` entry.

## Correctness argument
Fast paths read the same logical data and return the same frames; only
None-ness of the compound guard is consumed. Verified by S2 (5000/5000
replies), S3 (all-suite verdict identity), S4 (400/400 bench rows).

## What it means / does not mean
Per-turn CPU stays flat while keeping loop134's teach coverage, N-hop
questions, and fixes. It changes no answers, storage format, or sleep/think.
Wall-clock under load can still rise (mailbox + fsync, as in 128).
