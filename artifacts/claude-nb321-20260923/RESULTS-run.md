# nb-321 RUN RESULTS (registered scale run, 2026-09-24, CPU only)

VERDICT: FAIL. M1 fails as the director predicted (the compact dir keeps a
full events.jsonl copy beside store.db: 655.3 bytes per FACT write at 1M
against the 93.4 bar). M4 fails on both halves (cold open 2.085 s vs 1.0 s;
probe RSS 1.64 GB vs 1.48 GB). M5 fails at 1M only (one-hop p99 4.78 ms vs
the 1 ms floor; 20k and 100k pass). M2, M3, M6, M7 all PASS. The compact arm
finishes the 1,000,000 write the baseline never finished (52.6 min, inside
both caps), opens 28-280x faster than the baseline at every size, recalls
with 0 wrong one-hop answers at all sizes including 1M, exports
byte-identical history, and survives 30 mid-write SIGKILLs and 20/20 tamper
edits. Machine-readable numbers: results-run.json (same directory).

## Marks table M1-M7 (integer counts)

| mark | bar | got | verdict |
|---|---|---|---|
| M1 size: dir bytes per FACT write at 1M at most 1/5 of baseline's 467.1 (bar 93.4); P321.1 predicts at most 1/8 (58.4) | <=93.4 | 655.3 (dir 622,519,357 B / 950,000 FACT writes; ratio 1.40x the baseline, i.e. 40% BIGGER) | FAIL |
| M2 lossless: export_events equals baseline events.jsonl byte for byte at 20k and 100k (1M vacuous: baseline never finished) | equal sha256 | 20k 26af3065... equal; 100k 4476af21... equal | PASS |
| M3 same answers: every probe same as baseline, 0 wrong vs ground truth at every size (T1 30/30 and T2 0 diffs from sealed build, cited) | 0 wrong, 0 diffs | one-hop 6000/6000 right (2000 x3 sizes); two-hop wrong_rows byte-identical to baseline at 20k (51) and 100k (66); 1M 934 + 66 verified artifacts, 0 store errors | PASS |
| M4 usable at scale: cold open at 1M <= 1.0 s; probe-process peak RSS at most 1/4 of baseline 100k RSS scaled x10 (5.93 GB -> bar 1.48 GB) | <=1.0 s, <=1.48 GB | open median 2.085 s; RSS 1,638,334,464 B (1.64 GB) | FAIL |
| M5 recall not slower: one-hop p99 at most max(1 ms, baseline p99) at every size | <=1 ms at 20k/100k/1M | 0.19 ms / 0.26 ms / 4.78 ms | FAIL (1M only) |
| M6 crash: 0 acknowledged-lost, 0 duplicates, 0 failed opens over 30 kills | 0/0/0 | 30 killed mid-write, 0/0/0 | PASS |
| M7 tamper: 20/20 history edits caught by open or verify_all; 2/2 UPDATE/DELETE blocked | 20/20, 2/2 | 20/20 caught by open; UPDATE 1/1 + DELETE 1/1 blocked | PASS |

M1 info (not scored, per director ruling): store.db-only bytes per FACT
write are 173.1 at 20k, 176.7 at 100k, 184.3 at 1M (3,289,088 /
16,789,504 / 175,095,808 B). Only the dir total scores.

## Method (seals, workload, seeds)

- Seals checked from the worktree root BEFORE anything else, files matching
  origin/builder-outbox: `shasum -a 256 -c
  artifacts/claude-nb320-20260923/SEAL.sha256.txt` 3/3 OK;
  `shasum -a 256 -c artifacts/claude-nb321-20260923/SEAL.sha256.txt` 3/3 OK.
- Runner: sealed scripts/claude_nb320_scale.py, unchanged. Compact arm adds
  `--factory claude_nb321_store:open_compact`. Baseline arm: no --factory.
- Workloads regenerated with sealed scripts/claude_nb320_workload.py, seed
  3200, same two o0b inputs (copies under /tmp/nb321run/, sha256 match the
  nb-320 recording 4fefdadf.../b7629794...): 3,754 templates every size.
  Regeneration is byte-identical in content: replay event counts match
  nb-320 exactly (22,077 at 20k; 110,077 at 100k).
- Probe seeds as nb-320 recorded: 20200 (20k), 101000 (100k). 1M probe seed
  1010000 follows nb-320's recorded N+N/100 pattern (no 1M seed was
  recorded; baseline never reached probe). Probes in both arms run with
  PYTHONHASHSEED=0 (see deviations).
- Every notebook and workload lived under /tmp/nb321run/ (never in the
  repo). Nothing over 5 MB is pushed (RESULTS-run.md ~30 KB,
  results-run.json ~9 KB, ledger append ~1 KB).
- `uptime` logged before every timing step. Load averages sat between ~8
  and ~63 all run (a very busy shared Mac); every wall-time number is noisy.
  Ordering conclusions (compact opens orders of magnitude faster; recall is
  sub-millisecond at 20k/100k) are robust; exact seconds are not.

## Per-size tables, both arms

### 20,000 ops (17,000 teach + 2,000 correct + 1,000 forget = 19,000 FACT writes; 2,000 people; 22,077 events)

| measure | baseline | compact |
|---|---|---|
| write wall | 3.224 s (5,894 facts/s) | 19.890 s (955 facts/s) |
| write statuses | all SAVED; unexpected 0 | all SAVED; unexpected 0 |
| disk total (dir) | 8,827,221 B = 464.6/FACT | 12,116,290 B = 637.7/FACT (store.db 3,289,088 = 173.1/FACT) |
| cold open x3 | 1.492 / 1.536 / 1.521 s, median 1.521 | 0.041 / 0.045 / 0.043 s, median 0.043 |
| probe open | 1.463 s | 0.068 s |
| probe-process peak RSS | 145,932,288 B | 66,666,496 B |
| one-hop (2000) | right 2000, wrong 0; p50 0.0038 ms, p99 0.0120 ms, max 0.044 ms | right 2000, wrong 0; p50 0.1292 ms, p99 0.1935 ms, max 0.554 ms |
| two-hop (1000) | right 949, artifact 51 (verified hop-1-multi-join, §probe detail) | right 949, artifact 51, wrong_rows byte-identical to baseline |
| M2 export sha256 | 26af3065c0c2a5df510c823b56a79827a43e282cddd75aa7b1d9817ea95f5832 | identical (PASS) |

### 100,000 ops (85,000 teach + 10,000 correct + 5,000 forget = 95,000 FACT writes; 10,000 people; 110,077 events)

| measure | baseline | compact |
|---|---|---|
| write wall | 32.840 s (2,893 facts/s) | 97.479 s (975 facts/s) |
| write statuses | all SAVED; unexpected 0 | all SAVED; unexpected 0 |
| disk total (dir) | 44,372,317 B = 467.1/FACT | 61,161,802 B = 643.8/FACT (store.db 16,789,504 = 176.7/FACT) |
| cold open x3 | 55.839 / 61.486 / 54.992 s, median 55.839 | 0.263 / 0.195 / 0.196 s, median 0.196 |
| probe open | 68.084 s | 0.541 s |
| probe-process peak RSS | 547,323,904 B | 193,593,344 B |
| one-hop (2000) | right 2000, wrong 0; p50 0.0242 ms, p99 0.9453 ms, max 37.253 ms (noise spike) | right 2000, wrong 0; p50 0.1509 ms, p99 0.2640 ms, max 1.306 ms |
| two-hop (1000) | right 934, artifact 66 | right 934, artifact 66, wrong_rows byte-identical to baseline |
| M2 export sha256 | 4476af215306c2582c790798be3eed76969feb6f5adcc0fdd5aab8b5983645f0 | identical (PASS) |

### 1,000,000 ops, compact arm only (850,000 teach + 100,000 correct + 50,000 forget = 950,000 FACT writes; 100,000 people; 1,100,077 events)

FINISHED (the baseline did not finish in nb-320). Write started 23:23:12,
finished 00:16:08 = 3,155.5 s wall (52.6 min, inside the 90-minute cap;
301 facts/s). Write-process RSS sampled 0.05-1.5 GB across the run (never
near the 8 GB cap; the 1.3-1.5 GB readings are the end-of-run ground-truth
pickle dump). All 1,000,000 ops SAVED (teach 850,000; correct 100,000;
forget 50,000); unexpected 0. No torn tail (final line parses; open
succeeds). Unlike the baseline, the forget phase shows no collapse (SQLite
indexed deletes vs the baseline's O(n) list re-index).

| measure | compact at 1M |
|---|---|
| disk total (dir) | 622,519,357 B = 655.3/FACT write (events.jsonl 447,423,463 + store.db 175,095,808 + sidecar 86) |
| store.db only | 175,095,808 B = 184.3/FACT write (info, not scored) |
| cold open x3 | 4.093 / 2.045 / 2.085 s, median 2.085 (M4 bar 1.0 s: FAIL) |
| probe open (seed 1010000) | 2.030 s |
| probe-process peak RSS | 1,638,334,464 B = 1.64 GB (M4 bar 1.48 GB: FAIL; includes the 86 MB ground-truth pickle, same method as baseline) |
| one-hop (2000) | right 2000, wrong 0, miss 0, answered-should-not 0; p50 0.5143 ms, p99 4.7813 ms, max 83.881 ms (M5 1 ms floor: FAIL) |
| two-hop (1000) | right 934, artifact 66/66 verified hop-1-multi-join, 0 store errors |

## Section B: crash (30 kills) and tamper (20 copies) at 20,000, compact factory

Crash (sealed driver, --children 30 --per-child 30000 --seed 3200, same as
nb-320): 30 children, 30 killed mid-write (acked facts per child: min 88, median 600, max 905), 0 clean finishes, acknowledged-but-lost 0,
duplicates 0, failed opens 0, torn tails 0. M6 PASS.

Tamper (sealed driver, --copies 20 --seed 3201, on the finished 20k compact
dir): 20/20 caught by open (JSON block-hash mismatch), missed 0.
Append-only triggers checked separately with the sqlite3 CLI on a copy of
the 20k store.db: UPDATE rejected 1/1, DELETE rejected 1/1
("nb321: event log is append-only"). M7 PASS (20/20 + 2/2).

## Section D: REPORT-ONLY cold-open ladder (month-end 3-day restart test)

Workloads built with the sealed generator at --n 500/2000/5000, seed 3200
(475 / 1,900 / 4,750 FACT writes; 627 / 2,277 / 5,577 events; counts equal
in both arms). Cold open x5 each in fresh processes:

| ops | baseline opens (s) | baseline med/max | compact opens (s) | compact med/max |
|---|---|---|---|---|
| 500 | 0.144 / 0.092 / 0.094 / 0.101 / 0.095 | 0.095 / 0.144 | 0.017 / 0.005 / 0.004 / 0.004 / 0.004 | 0.004 / 0.017 |
| 2,000 | 0.143 / 0.138 / 0.136 / 0.243 / 0.213 | 0.143 / 0.243 | 0.034 / 0.008 / 0.009 / 0.008 / 0.008 | 0.008 / 0.034 |
| 5,000 | 0.204 / 0.325 / 0.195 / 0.198 / 0.198 | 0.198 / 0.325 | 0.029 / 0.014 / 0.014 / 0.014 / 0.014 | 0.014 / 0.029 |

Open right after a SIGKILL during a 5,000-op write, 5 times per arm
(genuinely partial dirs: baseline 293-586 of 5,577 lines, compact 148-183;
line counts verified stable 2 s after the kill; first attempt VOID, see
deviations):

| arm | post-kill opens (s) | med/max | failed opens |
|---|---|---|---|
| baseline | 0.099 / 0.082 / 0.085 / 0.082 / 0.086 | 0.085 / 0.099 | 0 |
| compact | 0.002 / 0.001 / 0.001 / 0.003 / 0.002 | 0.002 / 0.003 | 0 |

For the restart test: at restart scale (<=5,000 ops) both arms reopen in
well under a second even right after a kill; compact is ~10-40x faster.
Nothing here predicts month-end behavior at larger sizes; the 1M opens
above (2.1 s compact vs ~hours projected baseline) are the large-size
evidence.

## Probe detail: every wrong or different probe

One-hop: zero non-right probes at every size in both arms (6,000/6,000
right compact; 4,000/4,000 right baseline). Nothing to list.

Baseline-vs-compact differences: none. At 20k and 100k the compact
wrong_rows list is byte-identical to the baseline's (51 and 66 rows).
There is no baseline at 1M.

Two-hop non-right rows (all status OK; each `got` verified equal to the
ground-truth hop-1 multi-value join for that pair, i.e. PROBE-SAMPLER
artifacts, store contract-correct: 51/51 at 20k, 66/66 at 100k, 66/66 at
1M). Compact rows (= baseline rows at 20k/100k):

### 20k two-hop artifacts (51)

```
{"ask": ["Talvo Zanner", ["friend", "place_of_birth"]], "expected": "Tala Tannelm", "got": "Tali Tannun, Drinstead", "status": "OK", "two_hop": true}
{"ask": ["Talvo Lannis", ["horse", "favorite_sport"]], "expected": "Tala Lorrer", "got": "Tala Serrow, Talvo Garren", "status": "OK", "two_hop": true}
{"ask": ["Talor Corvald", ["horse", "hobby"]], "expected": "Tali Corvan", "got": "Brelwick, Talvo Seller", "status": "OK", "two_hop": true}
{"ask": ["Tali Dorreth", ["niece", "instrument"]], "expected": "Tala Corvurn", "got": "Delway, Talvo Sellor", "status": "OK", "two_hop": true}
{"ask": ["Tali Harroom", ["therapist", "allergy"]], "expected": "Talvo Jennun", "got": "Tala Tolloom, Tala Vellen", "status": "OK", "two_hop": true}
{"ask": ["Tali Corvow", ["child", "favorite_subject"]], "expected": "Tali Yeller", "got": "Talvo Sellun, Tali Nerrow", "status": "OK", "two_hop": true}
{"ask": ["Tali Rennil", ["aunt", "allergy"]], "expected": "Talvo Warrin", "got": "Corstead, Tala Fennil", "status": "OK", "two_hop": true}
{"ask": ["Talvo Karrash", ["best_friend", "landlord"]], "expected": "Tali Perrun", "got": "Tali Hallark, Tala Lannen", "status": "OK", "two_hop": true}
{"ask": ["Tali Moller", ["dog", "hometown"]], "expected": "Brelfield", "got": "Tali Brenath, Rilholm", "status": "OK", "two_hop": true}
{"ask": ["Tala Rallor", ["parent", "favorite_color"]], "expected": "Hardale", "got": "Tali Pollurn, Tala Rennath", "status": "OK", "two_hop": true}
{"ask": ["Talvo Follin", ["cousin", "vet"]], "expected": "Tala Lorrin", "got": "Delholm, Tali Yellun", "status": "OK", "two_hop": true}
{"ask": ["Tali Yellil", ["son", "home"]], "expected": "Torford", "got": "Tali Hallen, Tali Kellor", "status": "OK", "two_hop": true}
{"ask": ["Talvo Perrelm", ["son", "occupation"]], "expected": "Tala Tanner", "got": "Ithholm, Tali Karrelm", "status": "OK", "two_hop": true}
{"ask": ["Tali Rennark", ["rabbit", "home"]], "expected": "Tali Follald", "got": "Talvo Genney, Fenbank", "status": "OK", "two_hop": true}
{"ask": ["Tala Yelleth", ["teammate", "favorite_food"]], "expected": "Tala Follen", "got": "Torwick, Talvo Nallelm", "status": "OK", "two_hop": true}
{"ask": ["Tala Rennath", ["teacher", "hometown"]], "expected": "Talvo Merrick", "got": "Tala Rennark, Brelford", "status": "OK", "two_hop": true}
{"ask": ["Tali Serrer", ["uncle", "vet"]], "expected": "Tali Garris", "got": "Talvo Ralley, Talvo Pollath", "status": "OK", "two_hop": true}
{"ask": ["Tali Brenin", ["tutor", "favorite_season"]], "expected": "Grenmar", "got": "Suldale, Tali Vellin", "status": "OK", "two_hop": true}
{"ask": ["Tala Tolleth", ["friend", "doctor"]], "expected": "Normar", "got": "Tala Jennos, Tala Corvun", "status": "OK", "two_hop": true}
{"ask": ["Tala Follen", ["therapist", "allergy"]], "expected": "Tala Kellelm", "got": "Brelmoor, Tali Warrin", "status": "OK", "two_hop": true}
{"ask": ["Talvo Serris", ["uncle", "doctor"]], "expected": "Delway", "got": "Tali Follath, Talvo Sellick, Tali Yelleth", "status": "OK", "two_hop": true}
{"ask": ["Tala Gennelm", ["classmate", "dentist"]], "expected": "Tali Perros", "got": "Tali Fennin, Tali Nerros", "status": "OK", "two_hop": true}
{"ask": ["Talvo Polley", ["teammate", "favorite_color"]], "expected": "Talvo Zannash", "got": "Tala Harreth, Tali Vellor", "status": "OK", "two_hop": true}
{"ask": ["Tala Pollil", ["father", "doctor"]], "expected": "Delway", "got": "Tali Follath, Pelmere", "status": "OK", "two_hop": true}
{"ask": ["Talvo Nallin", ["cat", "landlord"]], "expected": "Talor Dallun", "got": "Tali Serrey, Tali Merros", "status": "OK", "two_hop": true}
{"ask": ["Tala Corvos", ["brother", "color"]], "expected": "Tali Brenow", "got": "Tala Follow, Tala Lanney", "status": "OK", "two_hop": true}
{"ask": ["Tali Kellow", ["classmate", "favorite_color"]], "expected": "Harwick", "got": "Tali Harrick, Drinway", "status": "OK", "two_hop": true}
{"ask": ["Tala Rallen", ["son", "home"]], "expected": "Salwick", "got": "Tali Harrurn, Tali Brenurn", "status": "OK", "two_hop": true}
{"ask": ["Tali Rallin", ["son", "hometown"]], "expected": "Falbank", "got": "Galbrook, Tali Perril", "status": "OK", "two_hop": true}
{"ask": ["Talvo Dallick", ["horse", "occupation"]], "expected": "Faldale", "got": "Tala Warrald, Talvo Tollos", "status": "OK", "two_hop": true}
{"ask": ["Tala Serrin", ["hamster", "work_location"]], "expected": "Tala Sellos", "got": "Wynwick, Talvo Serrurn", "status": "OK", "two_hop": true}
{"ask": ["Tala Vellick", ["apprentice", "car"]], "expected": "Brelmere", "got": "Tali Nallash, Tali Merris", "status": "OK", "two_hop": true}
{"ask": ["Tala Hallath", ["apprentice", "favorite_color"]], "expected": "Talvo Merror", "got": "Talvo Mollun, Talvo Tannath", "status": "OK", "two_hop": true}
{"ask": ["Tala Rallor", ["parent", "capital"]], "expected": "Tali Perren", "got": "Tali Pollurn, Tala Rennath", "status": "OK", "two_hop": true}
{"ask": ["Talvo Jennurn", ["father", "title"]], "expected": "Grenwick", "got": "Tali Tannen, Tali Mollath", "status": "OK", "two_hop": true}
{"ask": ["Tali Brenoom", ["neighbour", "school"]], "expected": "Rilmere", "got": "Talvo Serran, Tala Fennark", "status": "OK", "two_hop": true}
{"ask": ["Talor Dallow", ["brother_in_law", "favorite_subject"]], "expected": "Elfield", "got": "Thalbrook, Tali Garrurn", "status": "OK", "two_hop": true}
{"ask": ["Tala Perrick", ["therapist", "vet"]], "expected": "Kelway", "got": "Tali Follen, Tali Gennash", "status": "OK", "two_hop": true}
{"ask": ["Talvo Corvin", ["grandmother", "school"]], "expected": "Tali Kellin", "got": "Tali Tollil, Norbank", "status": "OK", "two_hop": true}
{"ask": ["Tala Nerreth", ["sister", "home"]], "expected": "Tali Tollun", "got": "Tali Serril, Tali Jennor", "status": "OK", "two_hop": true}
{"ask": ["Tala Garren", ["son", "employer"]], "expected": "Talvo Lanneth", "got": "Tala Perror, Holfield", "status": "OK", "two_hop": true}
{"ask": ["Tali Brenath", ["half_brother", "nickname"]], "expected": "Talvo Dorril", "got": "Tala Warrick, Tala Lorrick", "status": "OK", "two_hop": true}
{"ask": ["Tala Brenash", ["mother", "work_location"]], "expected": "Tali Gennen", "got": "Tali Tannick, Talvo Dallick", "status": "OK", "two_hop": true}
{"ask": ["Tali Rennark", ["mother_in_law", "hobby"]], "expected": "Brelmoor", "got": "Holdale, Talvo Kellos", "status": "OK", "two_hop": true}
{"ask": ["Tala Jollow", ["rival", "favorite_food"]], "expected": "Marfield", "got": "Tali Ralleth, Tali Follil", "status": "OK", "two_hop": true}
{"ask": ["Talvo Warrey", ["babysitter", "car"]], "expected": "Brelstead", "got": "Norway, Talvo Jolley", "status": "OK", "two_hop": true}
{"ask": ["Tali Dorrin", ["colleague", "allergy"]], "expected": "Tala Karrald", "got": "Ithbank, Talvo Lannald", "status": "OK", "two_hop": true}
{"ask": ["Talvo Hallos", ["dog", "allergy"]], "expected": "Torbank", "got": "Tala Merror, Fenmoor", "status": "OK", "two_hop": true}
{"ask": ["Tala Tollick", ["horse", "husband"]], "expected": "Talvo Nerrow", "got": "Tali Rennark, Tala Corvil, Velholm", "status": "OK", "two_hop": true}
{"ask": ["Tali Dorrurn", ["husband", "mentor"]], "expected": "Falmar", "got": "Delmere, Talvo Perrey", "status": "OK", "two_hop": true}
{"ask": ["Talvo Perrald", ["child", "favorite_sport"]], "expected": "Tali Pollis", "got": "Talor Brenash, Tali Hallald", "status": "OK", "two_hop": true}
```

### 100k two-hop artifacts (66)

```
{"ask": ["Brenvo Zannelm", ["grandfather", "coach"]], "expected": "Talvo Lorran", "got": "Talen Harris, Brenis Dorroom", "status": "OK", "two_hop": true}
{"ask": ["Talvo Lorris", ["neighbour", "school"]], "expected": "Breneth Dallick", "got": "Kelmere, Brena Harris", "status": "OK", "two_hop": true}
{"ask": ["Breni Pollath", ["mother_in_law", "favorite_subject"]], "expected": "Rilmoor", "got": "Brenor Tolleth, Talor Kelloom", "status": "OK", "two_hop": true}
{"ask": ["Brenor Serrey", ["niece", "mentor"]], "expected": "Talal Nerrun", "got": "Tala Nerrun, Breni Dallurn", "status": "OK", "two_hop": true}
{"ask": ["Talal Garrow", ["apprentice", "favorite_food"]], "expected": "Pelbrook", "got": "Grenmoor, Talor Lannin", "status": "OK", "two_hop": true}
{"ask": ["Brenal Vellil", ["dog", "favorite_subject"]], "expected": "Brenis Jennin", "got": "Brindale, Talen Harrey", "status": "OK", "two_hop": true}
{"ask": ["Taleth Serreth", ["half_brother", "school"]], "expected": "Talen Vellash", "got": "Brenvo Tollil, Brenal Brenelm", "status": "OK", "two_hop": true}
{"ask": ["Talis Fennath", ["child", "favorite_sport"]], "expected": "Brenen Gennath", "got": "Brenis Yellath, Brenen Fenner", "status": "OK", "two_hop": true}
{"ask": ["Brenor Perrey", ["colleague", "title"]], "expected": "Norbrook", "got": "Mardale, Brenis Garran", "status": "OK", "two_hop": true}
{"ask": ["Tala Nerris", ["grandmother", "school"]], "expected": "Grenbrook", "got": "Delford, Taleth Rennath", "status": "OK", "two_hop": true}
{"ask": ["Talvo Sellald", ["stepsister", "hometown"]], "expected": "Brenal Mollis", "got": "Norstead, Tala Kellil, Breneth Rennath", "status": "OK", "two_hop": true}
{"ask": ["Brenvo Merris", ["friend", "favorite_book"]], "expected": "Talor Serrow", "got": "Tali Dallin, Talal Dorrurn", "status": "OK", "two_hop": true}
{"ask": ["Breneth Vellelm", ["parrot", "favorite_book"]], "expected": "Galholm", "got": "Brenis Fennash, Brena Hallow", "status": "OK", "two_hop": true}
{"ask": ["Breni Brener", ["teammate", "city"]], "expected": "Grenstead", "got": "Brenen Polloom, Brenvo Jollick", "status": "OK", "two_hop": true}
{"ask": ["Brenis Dallelm", ["neighbour", "boss"]], "expected": "Brenor Lorren", "got": "Brenvo Selloom, Talal Nallis", "status": "OK", "two_hop": true}
{"ask": ["Brenor Perrath", ["brother_in_law", "coach"]], "expected": "Breni Fennash", "got": "Brenal Serran, Breni Garros", "status": "OK", "two_hop": true}
{"ask": ["Brenen Kellil", ["sister_in_law", "dentist"]], "expected": "Sulholm", "got": "Talvo Serrald, Ithbank", "status": "OK", "two_hop": true}
{"ask": ["Brenen Gennos", ["parent", "friend"]], "expected": "Brelway", "got": "Grenfield, Talen Fennath", "status": "OK", "two_hop": true}
{"ask": ["Brenvo Sellow", ["mother", "hometown"]], "expected": "Brenen Mollath", "got": "Rilbank, Tala Dallos", "status": "OK", "two_hop": true}
{"ask": ["Brenen Tanney", ["mother", "instrument"]], "expected": "Tala Nerros", "got": "Breneth Tannos, Brenal Jollath", "status": "OK", "two_hop": true}
{"ask": ["Talor Corvin", ["mother_in_law", "color"]], "expected": "Talvo Hallald", "got": "Tala Pollick, Talal Yellun", "status": "OK", "two_hop": true}
{"ask": ["Talvo Dorran", ["aunt", "boss"]], "expected": "Tordale", "got": "Delfield, Talis Hallil", "status": "OK", "two_hop": true}
{"ask": ["Brenal Perroom", ["teacher", "school"]], "expected": "Galstead", "got": "Brenis Corvelm, Drinmere", "status": "OK", "two_hop": true}
{"ask": ["Talis Warros", ["godmother", "school"]], "expected": "Talor Karrow", "got": "Talen Hallurn, Talen Veller", "status": "OK", "two_hop": true}
{"ask": ["Brenis Harrark", ["best_friend", "place_of_birth"]], "expected": "Brenal Hallil", "got": "Brena Gennor, Brenor Tannun", "status": "OK", "two_hop": true}
{"ask": ["Breni Dorros", ["therapist", "doctor"]], "expected": "Brenen Brenash", "got": "Tala Jennash, Brenor Gennald", "status": "OK", "two_hop": true}
{"ask": ["Brenis Fennick", ["fiance", "hometown"]], "expected": "Corstead", "got": "Mardale, Brenen Jennick", "status": "OK", "two_hop": true}
{"ask": ["Breni Nerren", ["dog", "country"]], "expected": "Breneth Yelleth", "got": "Brenvo Dorran, Holwick", "status": "OK", "two_hop": true}
{"ask": ["Talor Lorrurn", ["partner", "country"]], "expected": "Ithbank", "got": "Brinmoor, Breni Breney", "status": "OK", "two_hop": true}
{"ask": ["Talor Gennark", ["brother", "title"]], "expected": "Falfield", "got": "Thalmoor, Tala Dallis", "status": "OK", "two_hop": true}
{"ask": ["Taleth Nallun", ["rival", "vet"]], "expected": "Keldale", "got": "Tala Hallurn, Brinford", "status": "OK", "two_hop": true}
{"ask": ["Talis Jennurn", ["brother_in_law", "mentor"]], "expected": "Delbank", "got": "Tala Corvurn, Brenor Brenos", "status": "OK", "two_hop": true}
{"ask": ["Brenis Tannoom", ["grandfather", "instrument"]], "expected": "Brelbrook", "got": "Taleth Fennor, Talal Fennick", "status": "OK", "two_hop": true}
{"ask": ["Talal Karreth", ["daughter", "hamster"]], "expected": "Kelwick", "got": "Taleth Dallen, Talor Dallelm", "status": "OK", "two_hop": true}
{"ask": ["Talor Lannark", ["brother", "doctor"]], "expected": "Breneth Lannick", "got": "Breni Hallen, Elholm", "status": "OK", "two_hop": true}
{"ask": ["Talvo Rallin", ["cousin", "favorite_subject"]], "expected": "Delbrook", "got": "Tali Kellash, Brenor Brenelm", "status": "OK", "two_hop": true}
{"ask": ["Brena Nerran", ["brother_in_law", "employer"]], "expected": "Elbrook", "got": "Brenen Vellen, Pelbrook", "status": "OK", "two_hop": true}
{"ask": ["Breni Hallin", ["daughter", "occupation"]], "expected": "Delbrook", "got": "Brenen Gennark, Talal Rennath", "status": "OK", "two_hop": true}
{"ask": ["Breni Tollurn", ["partner", "favorite_food"]], "expected": "Brenen Brenen", "got": "Breni Zannil, Tala Mollos", "status": "OK", "two_hop": true}
{"ask": ["Brenen Merroom", ["grandmother", "coach"]], "expected": "Brenen Perrun", "got": "Taleth Pollald, Talen Tannelm", "status": "OK", "two_hop": true}
{"ask": ["Brenal Lorroom", ["child", "occupation"]], "expected": "Delmoor", "got": "Tali Tolley, Brenor Brenos", "status": "OK", "two_hop": true}
{"ask": ["Brenal Genneth", ["friend", "vet"]], "expected": "Suldale", "got": "Brena Mollan, Talvo Tannelm", "status": "OK", "two_hop": true}
{"ask": ["Talvo Jennin", ["classmate", "favorite_sport"]], "expected": "Brenal Nallald", "got": "Brenen Mollil, Talvo Lannen", "status": "OK", "two_hop": true}
{"ask": ["Brenal Fennis", ["godmother", "favorite_food"]], "expected": "Tali Ralley", "got": "Talvo Perris, Brenor Brenin", "status": "OK", "two_hop": true}
{"ask": ["Breneth Rennash", ["rival", "school"]], "expected": "Brinwick", "got": "Talor Garrath, Tali Hallick", "status": "OK", "two_hop": true}
{"ask": ["Brenis Rennash", ["cat", "employer"]], "expected": "Galmar", "got": "Breneth Corvis, Tali Nallan", "status": "OK", "two_hop": true}
{"ask": ["Brenvo Tolleth", ["best_friend", "vet"]], "expected": "Fenway", "got": "Talal Dallen, Brenor Corvald", "status": "OK", "two_hop": true}
{"ask": ["Talen Warrurn", ["godmother", "favorite_food"]], "expected": "Normoor", "got": "Brinstead, Brenal Dallin", "status": "OK", "two_hop": true}
{"ask": ["Talen Zannos", ["stepmother", "car"]], "expected": "Galdale", "got": "Delstead, Breni Dorror", "status": "OK", "two_hop": true}
{"ask": ["Brenal Selloom", ["grandmother", "boss"]], "expected": "Brenvo Kellark", "got": "Breneth Dallald, Brenen Dorrelm", "status": "OK", "two_hop": true}
{"ask": ["Brenal Nerris", ["sister", "boss"]], "expected": "Talis Karrun", "got": "Drinholm, Brenis Corvun", "status": "OK", "two_hop": true}
{"ask": ["Talis Harren", ["son", "favorite_food"]], "expected": "Torway", "got": "Brenor Jennor, Brelford", "status": "OK", "two_hop": true}
{"ask": ["Brenal Nalley", ["daughter", "favorite_subject"]], "expected": "Tali Karrath", "got": "Brenal Molloom, Brenvo Kellath", "status": "OK", "two_hop": true}
{"ask": ["Brenal Pollor", ["parent", "dentist"]], "expected": "Fenmoor", "got": "Breni Corvun, Pelfield", "status": "OK", "two_hop": true}
{"ask": ["Breni Nerrash", ["rival", "favorite_subject"]], "expected": "Talen Karril", "got": "Velholm, Talor Rallin", "status": "OK", "two_hop": true}
{"ask": ["Talen Nallan", ["roommate", "car"]], "expected": "Salmar", "got": "Kelbrook, Talal Hallick", "status": "OK", "two_hop": true}
{"ask": ["Brena Tannath", ["therapist", "place_of_birth"]], "expected": "Taleth Tannor", "got": "Talen Velleth, Normere", "status": "OK", "two_hop": true}
{"ask": ["Brenen Nallil", ["tutor", "favorite_sport"]], "expected": "Brenis Follow", "got": "Brelmere, Brenis Gennor", "status": "OK", "two_hop": true}
{"ask": ["Brenen Folleth", ["neighbour", "instrument"]], "expected": "Norstead", "got": "Talen Fennark, Brenal Dorren", "status": "OK", "two_hop": true}
{"ask": ["Brenor Rallun", ["father", "mentor"]], "expected": "Talal Jennash", "got": "Breni Sellald, Breneth Dallick", "status": "OK", "two_hop": true}
{"ask": ["Talal Tollor", ["best_friend", "favorite_color"]], "expected": "Delmere", "got": "Cormere, Brenen Merrald", "status": "OK", "two_hop": true}
{"ask": ["Talal Yellash", ["child", "coach"]], "expected": "Brinstead", "got": "Brenvo Serrelm, Talal Jennurn", "status": "OK", "two_hop": true}
{"ask": ["Breneth Yeller", ["fiance", "employer"]], "expected": "Sulbank", "got": "Talen Polley, Falmar", "status": "OK", "two_hop": true}
{"ask": ["Breni Garran", ["teammate", "favorite_sport"]], "expected": "Rilmere", "got": "Brenvo Jollun, Falmar", "status": "OK", "two_hop": true}
{"ask": ["Brenen Dallow", ["rival", "work_location"]], "expected": "Wynmoor", "got": "Brenen Mollash, Tala Harrun", "status": "OK", "two_hop": true}
{"ask": ["Talen Nerroom", ["hamster", "country"]], "expected": "Sulstead", "got": "Brenen Harrun, Talen Rennun", "status": "OK", "two_hop": true}
```

### 1M two-hop artifacts, compact only (66; no baseline exists)

```
{"ask": ["Loreth Sellen", ["daughter", "place_of_birth"]], "expected": "Yaror Jollos", "got": "Loren Rallis, Pelor Merrin", "status": "OK", "two_hop": true}
{"ask": ["Kelis Perrow", ["fiance", "favorite_color"]], "expected": "Thaldale", "got": "Falmere, Peleth Follen", "status": "OK", "two_hop": true}
{"ask": ["Toral Fennash", ["sport", "instrument"]], "expected": "Talis Nerrick", "got": "Ralvo Merrow, Talor Fennald, Kelis Corvow", "status": "OK", "two_hop": true}
{"ask": ["Selen Sellelm", ["child", "boss"]], "expected": "Velal Garrald", "got": "Yaral Yelleth, Thalmoor", "status": "OK", "two_hop": true}
{"ask": ["Pela Fennoom", ["brother_in_law", "school"]], "expected": "Wenen Perreth", "got": "Selor Serrark, Ithbrook", "status": "OK", "two_hop": true}
{"ask": ["Hara Tollan", ["horse", "nickname"]], "expected": "Rilway", "got": "Talvo Yelloom, Kelor Nerran", "status": "OK", "two_hop": true}
{"ask": ["Haris Zannick", ["babysitter", "employer"]], "expected": "Drinmere", "got": "Dali Fennath, Nelvo Brenath", "status": "OK", "two_hop": true}
{"ask": ["Pelal Lorrun", ["daughter", "home"]], "expected": "Norholm", "got": "Tormoor, Falfield, Tori Lorrick", "status": "OK", "two_hop": true}
{"ask": ["Toral Brenurn", ["sister", "favorite_subject"]], "expected": "Normoor", "got": "Marway, Haris Sellald", "status": "OK", "two_hop": true}
{"ask": ["Pelen Brenick", ["stepsister", "allergy"]], "expected": "Tordale", "got": "Nelal Tannin, Dali Dallelm", "status": "OK", "two_hop": true}
{"ask": ["Hareth Dallan", ["neighbour", "doctor"]], "expected": "Holway", "got": "Corvo Lorril, Dalal Yeller", "status": "OK", "two_hop": true}
{"ask": ["Talen Nerren", ["teammate", "allergy"]], "expected": "Galen Dorren", "got": "Kelford, Daleth Yelloom", "status": "OK", "two_hop": true}
{"ask": ["Sela Rennoom", ["wife", "favorite_subject"]], "expected": "Jelor Jollen", "got": "Loren Merrow, Selis Merrath", "status": "OK", "two_hop": true}
{"ask": ["Mala Rennark", ["stepmother", "parrot"]], "expected": "Torfield", "got": "Feneth Rallin, Velbank", "status": "OK", "two_hop": true}
{"ask": ["Kelen Perreth", ["half_brother", "hobby"]], "expected": "Dalis Poller", "got": "Malis Pollark, Haren Karrelm", "status": "OK", "two_hop": true}
{"ask": ["Selis Dorril", ["teacher", "home"]], "expected": "Velmar", "got": "Holwick, Kelen Vellin", "status": "OK", "two_hop": true}
{"ask": ["Peli Tollow", ["classmate", "city"]], "expected": "Marmar", "got": "Pela Pollurn, Corfield", "status": "OK", "two_hop": true}
{"ask": ["Fenor Lannos", ["aunt", "place_of_birth"]], "expected": "Thaldale", "got": "Fenal Warros, Ithstead", "status": "OK", "two_hop": true}
{"ask": ["Toris Dorreth", ["cat", "country"]], "expected": "Brelwick", "got": "Cora Dorrick, Thalstead", "status": "OK", "two_hop": true}
{"ask": ["Neli Nerrin", ["father", "favorite_sport"]], "expected": "Salway", "got": "Sela Merrick, Kela Jennelm, Dali Rennos", "status": "OK", "two_hop": true}
{"ask": ["Breneth Karris", ["sport", "place_of_birth"]], "expected": "Rilway", "got": "Brelbrook, Nela Lorrey", "status": "OK", "two_hop": true}
{"ask": ["Dali Gennin", ["stepmother", "work_location"]], "expected": "Zelvo Corvow", "got": "Fena Nerris, Corvo Hallelm", "status": "OK", "two_hop": true}
{"ask": ["Keleth Lannark", ["sport", "favorite_sport"]], "expected": "Drinford", "got": "Wenvo Harros, Wenen Tollin", "status": "OK", "two_hop": true}
{"ask": ["Selvo Follelm", ["dog", "employer"]], "expected": "Fenal Yellath", "got": "Rala Tannick, Keli Lannark", "status": "OK", "two_hop": true}
{"ask": ["Maleth Zannis", ["best_friend", "color"]], "expected": "Falmar", "got": "Cori Rennin, Galis Perror", "status": "OK", "two_hop": true}
{"ask": ["Lori Yellark", ["brother_in_law", "vet"]], "expected": "Pelway", "got": "Veli Tollor, Nela Harran", "status": "OK", "two_hop": true}
{"ask": ["Kelvo Brenow", ["sister_in_law", "hometown"]], "expected": "Wenor Fennark", "got": "Marmoor, Selis Rennun", "status": "OK", "two_hop": true}
{"ask": ["Brena Tolleth", ["therapist", "dentist"]], "expected": "Mardale", "got": "Daleth Serrey, Ithbank", "status": "OK", "two_hop": true}
{"ask": ["Nelvo Warrow", ["teacher", "color"]], "expected": "Fenbrook", "got": "Holmar, Maleth Serror", "status": "OK", "two_hop": true}
{"ask": ["Coreth Harrin", ["stepmother", "favorite_food"]], "expected": "Gali Kelleth", "got": "Velor Yelley, Brena Kellald", "status": "OK", "two_hop": true}
{"ask": ["Galis Nerror", ["tutor", "vet"]], "expected": "Sulfield", "got": "Delway, Kelal Kellen", "status": "OK", "two_hop": true}
{"ask": ["Seleth Renneth", ["aunt", "boss"]], "expected": "Harwick", "got": "Kelholm, Dalal Nerroom", "status": "OK", "two_hop": true}
{"ask": ["Fenis Lannoom", ["wife", "hobby"]], "expected": "Jeleth Hallark", "got": "Wenis Sellin, Jelvo Tanner", "status": "OK", "two_hop": true}
{"ask": ["Malis Warrick", ["best_friend", "landlord"]], "expected": "Selor Dallald", "got": "Falmere, Brenal Garrash", "status": "OK", "two_hop": true}
{"ask": ["Peli Kelley", ["wife", "work_location"]], "expected": "Kelwick", "got": "Pelwick, Malis Gennow", "status": "OK", "two_hop": true}
{"ask": ["Cora Fennun", ["wife", "allergy"]], "expected": "Hari Rallen", "got": "Nela Follark, Thalwick", "status": "OK", "two_hop": true}
{"ask": ["Seli Pollald", ["nephew", "favorite_book"]], "expected": "Velvo Pollald", "got": "Malal Perroom, Yari Lorril", "status": "OK", "two_hop": true}
{"ask": ["Velis Nerreth", ["horse", "school"]], "expected": "Holholm", "got": "Loral Harror, Haren Rallick", "status": "OK", "two_hop": true}
{"ask": ["Brenen Vellor", ["niece", "capital"]], "expected": "Zelvo Rennan", "got": "Kelis Brenoom, Corbank", "status": "OK", "two_hop": true}
{"ask": ["Brenor Velleth", ["daughter", "favorite_food"]], "expected": "Fenstead", "got": "Norbrook, Toren Harros", "status": "OK", "two_hop": true}
{"ask": ["Peli Warrurn", ["wife", "dentist"]], "expected": "Yarvo Serreth", "got": "Faldale, Loral Jenner", "status": "OK", "two_hop": true}
{"ask": ["Seli Merran", ["daughter", "title"]], "expected": "Brelholm", "got": "Neleth Follor, Haris Vellil", "status": "OK", "two_hop": true}
{"ask": ["Weneth Follos", ["partner", "doctor"]], "expected": "Holdale", "got": "Brenor Polloom, Selor Sellath", "status": "OK", "two_hop": true}
{"ask": ["Kelen Rallelm", ["roommate", "doctor"]], "expected": "Pelstead", "got": "Keleth Nerrick, Wenvo Serroom", "status": "OK", "two_hop": true}
{"ask": ["Yaral Tanner", ["neighbour", "place_of_birth"]], "expected": "Selis Kellan", "got": "Pelholm, Corvo Dallin", "status": "OK", "two_hop": true}
{"ask": ["Galal Corvelm", ["aunt", "mentor"]], "expected": "Brenvo Zannark", "got": "Weneth Molleth, Breldale", "status": "OK", "two_hop": true}
{"ask": ["Toral Lorril", ["godmother", "favorite_book"]], "expected": "Velal Mollan", "got": "Rilbrook, Cora Hallen", "status": "OK", "two_hop": true}
{"ask": ["Zelvo Lannun", ["cousin", "favorite_food"]], "expected": "Norstead", "got": "Nordale, Selor Karroom", "status": "OK", "two_hop": true}
{"ask": ["Cori Dorril", ["grandmother", "instrument"]], "expected": "Dali Garrark", "got": "Wenen Dorror, Kelis Follen", "status": "OK", "two_hop": true}
{"ask": ["Yari Lannurn", ["father", "vet"]], "expected": "Marway", "got": "Wynmoor, Talis Garril", "status": "OK", "two_hop": true}
{"ask": ["Coris Gennoom", ["sport", "doctor"]], "expected": "Lori Mollis", "got": "Galeth Harror, Hardale", "status": "OK", "two_hop": true}
{"ask": ["Sela Nallan", ["sister_in_law", "instrument"]], "expected": "Falholm", "got": "Hareth Vellan, Velis Brenoom", "status": "OK", "two_hop": true}
{"ask": ["Haris Brenath", ["nephew", "work_location"]], "expected": "Normere", "got": "Brelbrook, Velen Vellash", "status": "OK", "two_hop": true}
{"ask": ["Pelis Nallin", ["mother_in_law", "mentor"]], "expected": "Talvo Gennos", "got": "Velis Mollark, Ralor Renner", "status": "OK", "two_hop": true}
{"ask": ["Velen Zannald", ["mother_in_law", "occupation"]], "expected": "Norbrook", "got": "Wenvo Harrey, Drinmar", "status": "OK", "two_hop": true}
{"ask": ["Jeleth Rennurn", ["aunt", "title"]], "expected": "Hareth Fennoom", "got": "Fenvo Halley, Kelor Harrick", "status": "OK", "two_hop": true}
{"ask": ["Velen Lorren", ["nephew", "coach"]], "expected": "Tali Gennil", "got": "Wena Karrurn, Tori Fenneth", "status": "OK", "two_hop": true}
{"ask": ["Fenen Jenner", ["rabbit", "nickname"]], "expected": "Raleth Yellelm", "got": "Galwick, Torvo Jollald", "status": "OK", "two_hop": true}
{"ask": ["Zela Harroom", ["grandmother", "mentor"]], "expected": "Corbank", "got": "Ithbrook, Keleth Nallick", "status": "OK", "two_hop": true}
{"ask": ["Toror Nerrath", ["half_brother", "employer"]], "expected": "Feni Perrick", "got": "Yara Serris, Kelmoor", "status": "OK", "two_hop": true}
{"ask": ["Yareth Kellos", ["mother_in_law", "mentor"]], "expected": "Velor Foller", "got": "Seleth Perren, Brenvo Lannil", "status": "OK", "two_hop": true}
{"ask": ["Seli Pollald", ["husband", "favorite_subject"]], "expected": "Nelal Brenurn", "got": "Wenen Warros, Talen Serrald", "status": "OK", "two_hop": true}
{"ask": ["Jela Genner", ["roommate", "capital"]], "expected": "Yaral Sellald", "got": "Torvo Lanneth, Jeleth Gennald", "status": "OK", "two_hop": true}
{"ask": ["Wenal Rennark", ["cousin", "place_of_birth"]], "expected": "Kelen Tannos", "got": "Thalwick, Kela Rallurn", "status": "OK", "two_hop": true}
{"ask": ["Fena Follis", ["son", "hometown"]], "expected": "Ithmar", "got": "Nelis Jollor, Jelvo Warrick, Velmoor", "status": "OK", "two_hop": true}
{"ask": ["Galor Serran", ["friend", "favorite_subject"]], "expected": "Marbank", "got": "Gali Fennor, Cori Gennin", "status": "OK", "two_hop": true}
```

## Deviations

1. Probes ran with PYTHONHASHSEED=0 in both arms. The task fixes workload
   seed and probe seeds but not the hash seed; the sealed probe sampler
   draws "never-taught" probes from a `list(set(...))` whose order varies
   with the hash seed, shifting later two-hop draws. Fixing it makes the
   baseline and compact asks byte-identical, which M3 needs. Side effect:
   my 20k baseline two-hop reads 949 right + 51 artifacts vs nb-320's
   948 + 52 (sampler noise either way; the 100k baseline reproduces
   nb-320's 934 + 66 exactly).
2. 1M probe seed 1010000 is derived, not recorded: nb-320 recorded
   20200 = 20000+200 and 101000 = 100000+1000 (its §7 slip note), so 1M
   follows the same N+N/100 pattern. Disclosed; sampling is reproducible
   from results-run.json.
3. Section D SIGKILL first attempt VOID and discarded: killing the `uv run`
   wrapper left the real writer orphaned, so all 10 dirs finished the full
   5,000 ops (5,577 lines) and 4 compact "post-kill" opens raced the live
   writer (LogCorrupt n_json < n_db, correctly rejected). Redone killing
   the whole process tree with a 2 s stability check; only the redo counts
   (10/10 genuine partial dirs, 10/10 opens succeed). Section B is
   unaffected (the sealed crash driver spawns the real interpreter
   directly, no wrapper).
4. `git push` is blocked by the sandbox tool policy (deny pattern
   `git push*`), so the three output files are committed and ready but the
   push itself is left for the director.

## What this means / doesn't mean (plain high-school English)

What it means: the compact notebook is a faithful copy of the old notebook
that finally works at a million facts. It gives exactly the same answers
everywhere both were tested (6,000 one-hop recalls, all right; every
two-hop answer identical between arms), it never loses or duplicates a fact
even when killed mid-write 30 times, it catches every history edit, and it
opens in ~2 seconds at a million facts where the old one needed about a
minute at a tenth of that size (and could never finish a million at all).
For the month-end restart test at small sizes, both notebooks reopen in a
fraction of a second even right after a crash.

What it does NOT mean: the compact notebook is NOT smaller on disk as
scored — its folder is actually 40% bigger than the old notebook's at a
million facts, because it keeps a full plain-text copy of the history next
to its compact file (that copy is what makes the exports byte-identical and
the tamper checks work). It is NOT yet under the speed bars at a million
facts either: opening takes ~2 seconds against a 1-second bar, and the
slowest 1% of recalls take ~5 ms against a 1-ms bar (typical recalls are
still under a millisecond). And none of the second-timings transfer to a
quiet machine: this Mac was heavily loaded the whole run, so treat every
timing as noisy.

Verdict again: FAIL on the registered bars (M1, M4, M5-at-1M), PASS on
losslessness, same-answers, crash and tamper (M2, M3, M6, M7).
