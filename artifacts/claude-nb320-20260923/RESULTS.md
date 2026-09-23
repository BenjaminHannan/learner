# nb-320 RESULTS (report-only baseline of the current notebook store)

Verdict first: the current store (`FixedIndexedLoopNotebook`, as in 292)
is exact at 20k and 100k facts — 0 wrong recalls, 0 lost events, 0 unexpected
write statuses, 20/20 tamper flips caught, 30/30 mid-write SIGKILLs survived
with nothing acknowledged lost. Its scaling cliff is the RETRACT path
(`_triple_remove` re-indexes a Python list: O(store size) per forget and per
replay of each RETRACT event): cold open is 1.8 s at 20k but 59 s at 100k,
and the 1,000,000 size DID NOT FINISH (see §4). Bytes per fact are flat at
~465 bytes per FACT write (~400 bytes per log event). One-hop storage recall
is ~0.005 ms at both sizes. All timings were taken on a very busy Mac (load
averages 50–125 all run long), so treat every timing as noisy; uptime was
logged before each step.

Layout: §1 workload, §2 tables per size, §3 recall detail (every unexpected
status and every non-right probe listed), §4 the 1M run, §5 crash + tamper,
§6 byte layout samples, §7 deviations and what this means / does not mean.
Machine-readable numbers: results.json (same directory).

## 1. Workload

Seed 3200. N total operations per size (85% teach / 10% correction /
5% forget, in that phase order); FACT writes = 95% of N. N/10 people with
unique fictional two-part names; 77 o0b tell/STATE relations (30 functional,
listed in PASSMARKS.md, rest multi-valued); values 50% entity / 50% literal;
raw sentences built from 3,754 o0b templates (tell/STATE/count-1/1-fact/
ASSERT/owner-NAME) with owner/value spans spliced, correction openers on
corrections. Same file replayed into each backend (only the baseline exists
in this run). Probe seeds actually used: 20200 (20k), 101000 (100k) —
see §7 deviation note.

## 2. Per-size tables

### 20,000 ops (17,000 teach + 2,000 correct + 1,000 forget = 19,000 FACT writes; 2,000 people; 22,077 events)

| measure | value |
|---|---|
| write wall | 3.125 s |
| write rate | 6,081 facts/s |
| write statuses | teach 17000 SAVED; correct 2000 SAVED; forget 1000 SAVED; unexpected 0 |
| disk total | 8,827,221 B (events.jsonl 8,827,112 + seal 109) |
| bytes / FACT write | 464.6 |
| bytes / event | 399.9 |
| gzip -9 of log (ref) | 1,750,233 B |
| xz -9 of log (ref) | 1,252,688 B |
| cold open x3 | 1.942 / 1.773 / 1.302 s, median 1.773 s |
| probe-process peak RSS | 146,751,488 B (140 MB) |
| one-hop (2000) | right 2000, wrong 0, missing-but-should-answer 0, answered-but-should-not 0; p50 0.0045 ms, p99 0.0105 ms, max 0.084 ms |
| two-hop (1000) | right 948, hop-1-multi-join artifact 52 (store contract-correct, §3), wrong 0 otherwise; p50 0.0071 ms, p99 0.0110 ms, max 0.048 ms |

### 100,000 ops (85,000 teach + 10,000 correct + 5,000 forget = 95,000 FACT writes; 10,000 people; 110,077 events)

| measure | value |
|---|---|
| write wall | 37.756 s |
| write rate | 2,516 facts/s |
| write statuses | teach 85000 SAVED; correct 10000 SAVED; forget 5000 SAVED; unexpected 0 |
| disk total | 44,372,317 B (events.jsonl 44,372,207 + seal 110) |
| bytes / FACT write | 467.1 |
| bytes / event | 403.1 |
| gzip -9 of log (ref) | 8,915,761 B |
| xz -9 of log (ref) | 6,258,160 B |
| cold open x3 | 59.140 / 63.911 / 51.650 s, median 59.140 s |
| probe-process peak RSS | 592,936,960 B (566 MB) |
| one-hop (2000) | right 2000, wrong 0, missing-but-should-answer 0, answered-but-should-not 0; p50 0.0045 ms, p99 0.0091 ms, max 0.051 ms |
| two-hop (1000) | right 934, hop-1-multi-join artifact 66 (store contract-correct, §3), wrong 0 otherwise; p50 0.0063 ms, p99 0.0100 ms, max 0.023 ms |

### 1,000,000 — DID NOT FINISH (see §4)

## 3. Recall detail: every unexpected status, every non-right probe

Write statuses: none unexpected at any size (every teach/correct/forget
returned SAVED: 19,000/19,000 at 20k; 95,000/95,000 at 100k).

One-hop probes: 4,000/4,000 right (2,000 at 20k + 2,000 at 100k), zero in any
other bucket. Forgotten and never-taught probes all returned MISSING_FACT;
no answered-but-should-not anywhere.

Two-hop probes: 1,882 right (948 + 934); 118 answered with the hop-1
multi-value join instead of the hop-2 value (52 at 20k, 66 at 100k). These
are PROBE-SAMPLER artifacts, not store errors, verified case by case from
the ground truth: each has a multi-valued first hop with 2+ active values,
and the store's answer equals that hop-1 join exactly (52/52 and 66/66) —
which is what the contract's ask() specifies (a multi hop answers at once
and never continues down the chain). The store was contract-correct in all
118; the sampler should have required a single-active first hop. The sealed
runner was left unchanged so all sizes stay comparable. Full list:

### 20k two-hop artifacts (52)

All status OK; each `got` is the hop-1 multi-value join, verified equal to
the ground-truth join for that pair.

```
{"ask": ["Tali Harror", ["neighbour", "boss"]], "expected": "Tala Dallow", "got": "Sulmere, Tali Nerris", "status": "OK", "two_hop": true}
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

Same verification (66/66 equal the ground-truth hop-1 join).

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

## 4. The 1,000,000 run: DID NOT FINISH (stopped by the preregistered rule)

Workload: 850,000 teach + 100,000 correct + 50,000 forget = 950,000 FACT
writes; 100,000 people; 1,100,077 events expected. Write started 15:27:47,
stopped by SIGKILL at 16:58:06 (90.3 min, the 90-minute cap).

| measure | value |
|---|---|
| outcome | DID NOT FINISH (cap stop, not a crash) |
| ops completed | 999,889 / 1,000,000 (teach 850,000/850,000; correct 100,000/100,000; forget 49,889/50,000) |
| FACT writes completed | 950,000 / 950,000 (all of them, in ~6 min ≈ 2,900/s) |
| events on disk | 1,099,966 / 1,100,077; final line parses (no torn tail) |
| write statuses | no write-*.json (process stopped before dump); every completed op returned through the same SAVED-only path observed at 20k/100k — 0 unexpected in 114,000 prior ops |
| disk total | 447,398,382 B (events.jsonl 447,398,277 + seal 105) |
| bytes / FACT write | 471.0 |
| bytes / event | 406.7 |
| gzip -9 of log (ref) | 91,784,021 B |
| xz -9 of log (ref) | 64,099,252 B |
| write-process RSS samples | 1.0–3.2 GB (never near the 8 GB cap; no memory breach) |
| cold open / probes | NOT RUN: a replay open at this size projects to ~2 h (retract replay, §7) — beyond the remaining 180-minute total budget, so there was nothing timely to probe |

What happened: teaches and corrections flew (950k fact writes in ~6 min),
then the forget phase collapsed to ~9 forgets/s flat from 15:33 to the cap.
Each forget pays `_triple_remove`: delete-from + re-index of a ~950k-entry
Python list (~100 ms). 49,889 forgets x ~100 ms ≈ 83 min — that IS the
90-minute write. Same cost sits inside every cold open (each RETRACT event
replays the same O(n) removal: 0.05 s with no retracts vs 59 s at 100k with
5k retracts, both measured), so opens and probes at 1M are out of reach for
this store as built, not just unmeasured.

## 5. Crash and tamper (20k only)

Crash: 30 child processes x 30,000 facts, each event_id appended to an ack
file (flush + fsync) only after assert_fact returned; parent waited for the
first ack (child provably mid-write) then SIGKILLed after a random
0.05–2.0 s. Result: 30 killed mid-write (238–7,585 facts acked, median
5,431), 0 clean finishes, 0 acknowledged-but-lost, 0 duplicates,
0 failed opens, 0 torn tails. (Four earlier attempts were VOID, not
results: attempt 1 crashed the driver on a missing log for startup-kills;
attempts 1–2 and the first two reruns killed only during interpreter startup
(0 acked); attempts 1–4 all used a functional relation in the crash child so
only ~41 events were ever written per child (later teaches CONFLICTed) —
the valid run uses a multi-valued relation, kills verified mid-write by ack
counts. All attempts are reported here; only the valid run counts.)

Tamper: 20 copies of the finished 20k log, one byte flipped at a random
offset in a random line excluding the final line. Opening the store (which
runs fable_fix77_core.verify_full) caught 20/20; missed 0.

## 6. Byte layout: five sample event lines from the 20k log

Line 1 is the first line of the log (a RELATION declaration); the rest are
FACT lines 5000/10000/15000/20000 (truncated to 400 chars here; full lines
average ~400 bytes):

```
{"event_id": "nb320-rel-allergy", "functional": true, "kind": "RELATION", "n": 1, "prev": "0000...0000", "relation": "allergy", "v": 1}
{"actor": "listening", "deps": [], "event_id": "nb320-20000-op0002922", "fact_id": "F02923", "kind": "FACT", "n": 5000, "prev": "28d1fb28...", "raw": "Guess what, The story is Talor Corvoom's favorite food is Tordale. I think.", "relation": "favorite_food", "source": "taught", "subject": "E1960", ...}
{"actor": "listening", "deps": [], "event_id": "nb320-20000-op0007922", "fact_id": "F07923", "kind": "FACT", "n": 10000, "prev": "24c2abcd...", "raw": "Listen, On record: Talvo Karran's teacher is Talor Brenan. really.", "relation": "teacher", "source": "taught", "subject": "E0488", ...}
{"actor": "listening", "deps": [], "event_id": "nb320-20000-op0012922", "fact_id": "F12923", "kind": "FACT", "n": 15000, "prev": "f56b4621...", "raw": "Hey, For the record, Talvo Daller's son is Grenbrook. I think.", "relation": "son", "source": "taught", "subject": "E0049", ...}
{"actor": "listening", "deps": [], "event_id": "nb320-20000-op0017922", "fact_id": "F17923", "kind": "FACT", "n": 20000, "prev": "9ff4f353...", "raw": "I misspoke, Hey, I will state it plainly: Talvo Dallash's school is Salway. I think.", "relation": "school", "source": "taught", "subject": "E0059", ...}
```

Every line carries n (sequence), prev (sha256 of the previous line),
v (format version), actor/source/provenance/supersedes where applicable —
that framing is the ~400 bytes per event.

## 7. Deviations, noise, and what this means / does not mean

- The runner was resealed 3 times before the 1M run (never during it):
  (1) crash driver crashed on a missing log file when a child died during
  startup — added a missing-file guard; (2) kills landed only during
  interpreter startup — wait for the first ack before the random sleep;
  (3) crash child used a functional relation so only ~41 events/child were
  written (CONFLICTs) — switched to a multi-valued relation. The workload
  generator is byte-identical since the first seal; the write/open/probe/
  tamper code paths were never touched (only crash-driver lines changed).
  Final seal: SEAL.sha256.txt.
- Probe seeds used were 20200 (20k) and 101000 (100k) — deterministic and
  recorded, but NOT the preregistered 3200+N formula (a launch-time slip:
  20000+200 / 100000+1000). Sampling is still fully reproducible from
  results.json; only the formula differs.
- Workload interpretation (preregistered in PASSMARKS.md): N = total ops at
  85/10/5, so FACT writes = 95% of N (19,000 / 95,000 / 950,000).
- xz reference sizes were computed with Python's lzma (preset 9) because
  the system xz binary is a broken x86 executable on this Mac; bytes equal
  xz -9 output format.
- Noise: load averages sat between ~50 and ~125 for the whole run (a very
  busy shared Mac). Every wall-time number — especially write rates and the
  minute-scale opens — should be read as "on a busy laptop", not as a clean
  benchmark. Ordering/rank conclusions (retract dominates opens; recall is
  microseconds) are robust to the noise; exact seconds are not.
- What this means: the store never loses, corrupts, or mis-recalls a fact
  at 20k/100k, survives SIGKILL mid-write, and detects every 1-byte log
  edit; recall latency is microseconds. What it does NOT mean: chat answers
  are fixed (F0 showed misses come from the reader, not storage), timings
  transfer to a quiet machine, or the store fits 1M facts on a laptop as
  built (open would take ~hours; the write did not finish in 90 min).
- In plain high-school English: the notebook is a perfect librarian with a
  slow filing system for forgetting things. Asking is instant. Forgetting
  one thing means reshuffling the whole card catalog, so opening a huge
  notebook takes forever. Squeezing the cards smaller (nb-321) is worth it,
  but the reshuffle-on-forget also needs fixing before 1M facts is real.
