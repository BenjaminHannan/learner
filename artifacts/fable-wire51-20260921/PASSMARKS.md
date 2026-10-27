# PASSMARKS — Agent 4 (WIRING), experiment 51

Written and sealed BEFORE the registered `--replay 3` run. Every mark is an
integer over one cold start of the 40-turn script (so a 3-run vector means
`[3, 3, 3]`).

| mark | threshold | smoke (n=2) | note |
|---|---|---|---|
| turns per run | 40 | 40, 40 | script length |
| taught_rows | 13 | 13, 13 | 12 statements + pick fact (1 correction supersedes) |
| active_taught_rows | 12 | (checked) | 13 − 1 superseded (Paris over Lisbon) |
| superseded_taught_rows | 1 | (checked) | the correction |
| wrong_writes | 0 | 0, 0 | traps, small talk, questions, pre-pick ambiguity |
| missing_writes | 0 | 0, 0 | every expected teaching turn wrote |
| unexpected_entities | 0 | 0, 0 | questions/traps/chat created no entities |
| questions | 15 | (checked) | 6 one-hop + 6 two-hop + 3 unanswerable |
| correct_answers | 12 | 12, 12 | all one- and two-hop |
| wrong_answers | 0 | 0, 0 | |
| abstentions | 3 | 3, 3 | Zed unknown-entity; city-as-subject broken chain; maternal_grandmother reject |
| missed_abstentions | 0 | 0, 0 | |
| two_hop_correct | 6 | 6, 6 | 6/6 two-hop |
| traps_no_write | 5 | 5, 5 | hearsay / hypothetical write nothing |
| smalltalk_no_write | 5 | 5, 5 | |
| sleeps | 2 | 2, 2 | threshold 20: before turn 21 and after turn 40 |
| reasoner_backend | fable_reasoner50 | fable_reasoner50 | agent 3 preferred when present |
| ears turns (english*) | 40 | 40, 40 | no fallbacks required with bridge up |
| bridge_failures | 0 | 0, 0 | |
| router_runs (44 cross-check) | 0 | 0, 0 | N/A when reasoner50 is preferred (cross-check only on the 44 fallback) |
| router_disagree | 0 | 0, 0 | no 44 cross-check runs under preference |
| word_lookups | 0 | 0, 0 | English rejects "maternal grandmother" surface before the reasoner (documented) |
| selftest | 25+ / all | 25 then 27/27 | composition, mapper, mouth, ears, full wire, resume, torn tail, 50-prefer, 44-fallback |

Selftest must be all-PASS immediately before the registered run.

## Seal

    shasum -a 256 PASSMARKS.md > SEAL.sha256.txt
