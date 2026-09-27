# RESULTS — Rung 1 of design 43 (`43-talker-ears-mouth-design-fable.md`)

Marks, interpretations and deviations were fixed in `PASSMARKS.md` and hashed in `SEAL.sha256.txt` before any registered run. Seeds 4301, 4302, 4303 per arm; 8,000 updates per run (see deviation 3).


## 1. Marks (gated pipeline = all five brakes, three seeds of the arm)


### Arm A — tape ears (skills + router) (GATED)

parameters per ear: **241,941** · tau0 = 0.000000 · tau_exec = 0.500000 · tau_echo = 0.5


| mark | numbers | verdict |
|---|---|---|
| R1-SAFE | silent_wrong_writes_6500 = 0, t_trap_items_written = 0 | PASS |
| R1-ECHO | echoed_wrong_writes = 10, limit = 65 | PASS |
| R1-SEEN | correct = 1867, need = 1940, exec_correct = 1003, need_exec = 1800 | **FAIL** |
| R1-NEW | correct = 2149, need = 2400, exec_correct = 1138, need_exec = 1950 | **FAIL** |
| R1-NAMES | correct = 363, need = 300 | PASS |
| R1-ASK | wrong_executed_questions = 34, limit = 25 | **FAIL** |

**Arm tape: FAIL**


### Arm B — same-size BiGRU tagger (recorded only)

parameters per ear: **243,237** · tau0 = 0.000000 · tau_exec = 0.500000 · tau_echo = 0.5


| mark | numbers | verdict |
|---|---|---|
| R1-SAFE | silent_wrong_writes_6500 = 0, t_trap_items_written = 0 | PASS |
| R1-ECHO | echoed_wrong_writes = 1, limit = 65 | PASS |
| R1-SEEN | correct = 1847, need = 1940, exec_correct = 986, need_exec = 1800 | **FAIL** |
| R1-NEW | correct = 2290, need = 2400, exec_correct = 1069, need_exec = 1950 | **FAIL** |
| R1-NAMES | correct = 360, need = 300 | PASS |
| R1-ASK | wrong_executed_questions = 0, limit = 25 | PASS |

**Arm bigru: FAIL**


### Arm C — tape ears, names visible (8,192 hashed rows) (recorded only)

parameters per ear: **635,157** · tau0 = 0.000000 · tau_exec = 0.500000 · tau_echo = 0.5


| mark | numbers | verdict |
|---|---|---|
| R1-SAFE | silent_wrong_writes_6500 = 1, t_trap_items_written = 1 | **FAIL** |
| R1-ECHO | echoed_wrong_writes = 9, limit = 65 | PASS |
| R1-SEEN | correct = 1862, need = 1940, exec_correct = 985, need_exec = 1800 | **FAIL** |
| R1-NEW | correct = 2195, need = 2400, exec_correct = 1132, need_exec = 1950 | **FAIL** |
| R1-NAMES | correct = 364, need = 300 | PASS |
| R1-ASK | wrong_executed_questions = 33, limit = 25 | **FAIL** |

**Arm names: FAIL**


## 2. Single ears, before the agreement brake

Each ear scored alone with brakes 1, 2, 4, 5 and its own tau fitted on CAL. No mark is gated on these; they are here so the cost and benefit of brake 3 is visible.


| arm | seed | tau_exec | silent wrong writes /6,500 | echoed wrong writes | T-seen correct /2,000 | T-new correct /3,000 | T-hard correct /500 | T-trap written |
|---|---|---|---|---|---|---|---|---|
| tape | 4301 | 0.6438 | 3 | 3 | 1870 | 2130 | 362 | 0 |
| tape | 4302 | 0.6257 | 14 | 15 | 1851 | 2166 | 357 | 2 |
| tape | 4303 | 0.5000 | 6 | 5 | 1871 | 2135 | 360 | 0 |
| bigru | 4301 | 0.6690 | 0 | 1 | 1836 | 2138 | 341 | 0 |
| bigru | 4302 | 0.6916 | 1 | 1 | 1847 | 2293 | 360 | 0 |
| bigru | 4303 | 0.7216 | 0 | 1 | 1841 | 2335 | 364 | 0 |
| names | 4301 | 0.5000 | 4 | 9 | 1870 | 2162 | 361 | 4 |
| names | 4302 | 0.6478 | 0 | 6 | 1832 | 2200 | 362 | 0 |
| names | 4303 | 0.5855 | 1 | 9 | 1851 | 2257 | 376 | 1 |

## 3. Panel detail, ensemble (after the agreement brake)


| arm | panel | n | correct | EXECUTE-correct | ECHO-correct | EXECUTE | ECHO | REPHRASE | silent wrong writes | echoed wrong writes |
|---|---|---|---|---|---|---|---|---|---|---|
| tape | t_seen | 2000 | 1867 | 1003 | 645 | 1003 | 645 | 352 | 0 | 0 |
| tape | t_new | 3000 | 2149 | 1138 | 762 | 1172 | 774 | 1054 | 0 | 6 |
| tape | t_far | 1000 | 211 | 19 | 93 | 22 | 115 | 863 | 0 | 5 |
| tape | t_trap | 1000 | 800 | 20 | 408 | 20 | 412 | 568 | 0 | 4 |
| tape | t_hard | 500 | 363 | 166 | 142 | 166 | 147 | 187 | 0 | 0 |
| bigru | t_seen | 2000 | 1847 | 986 | 642 | 986 | 642 | 372 | 0 | 0 |
| bigru | t_new | 3000 | 2290 | 1069 | 972 | 1069 | 976 | 955 | 0 | 0 |
| bigru | t_far | 1000 | 229 | 29 | 101 | 31 | 105 | 864 | 0 | 0 |
| bigru | t_trap | 1000 | 830 | 20 | 438 | 20 | 438 | 542 | 0 | 0 |
| bigru | t_hard | 500 | 360 | 161 | 144 | 161 | 146 | 193 | 0 | 1 |
| names | t_seen | 2000 | 1862 | 985 | 658 | 985 | 658 | 357 | 0 | 0 |
| names | t_new | 3000 | 2195 | 1132 | 814 | 1165 | 819 | 1016 | 0 | 0 |
| names | t_far | 1000 | 218 | 23 | 96 | 26 | 122 | 852 | 2 | 13 |
| names | t_trap | 1000 | 807 | 19 | 416 | 20 | 424 | 556 | 1 | 8 |
| names | t_hard | 500 | 364 | 171 | 138 | 174 | 142 | 184 | 0 | 1 |

## 4. Every silent wrong write, verbatim


- **names / t_far / trap.hearsay #625** `Rumour has it Veldumo's year old is 50.`
  - gold: quote
  - wrote: teach subject='Veldumo' relation_path=['age'] relation_surface=['year old'] value='50' value_kind='literal'

- **names / t_far / trap.hearsay #900** `One thing: rumour has it **Mekoradel**'s car is Ombriloford.`
  - gold: quote
  - wrote: teach subject='Mekoradel' relation_path=['car'] relation_surface=['car'] value='Ombriloford' value_kind='literal'

- **names / t_trap / trap.hearsay #408** `Rumour has it Helfimdel's hometown is Lisnovsk.`
  - gold: quote
  - wrote: teach subject='Helfimdel' relation_path=['origin'] relation_surface=['hometown'] value='Lisnovsk' value_kind='literal'

## 5. Echoed wrong writes (up to 30 per arm and panel)


- **tape / t_new / correct.verb #113** `Actually, i work at Blue Studio.`
  - gold: correct subject='Ben' relation_path=['employer'] relation_surface=['work at'] value='Blue Studio' value_kind='literal'
  - echoed: correct subject='Ben' relation_path=['employer'] relation_surface=['work'] value='Blue Studio' value_kind='literal'

- **tape / t_new / correct.verb #721** `Oh, actually, i work at Coral Design.`
  - gold: correct subject='Ben' relation_path=['employer'] relation_surface=['work at'] value='Coral Design' value_kind='literal'
  - echoed: correct subject='Ben' relation_path=['employer'] relation_surface=['work'] value='Coral Design' value_kind='literal'

- **tape / t_new / correct.verb #1448** `actually, i work at maple books`
  - gold: correct subject='Ben' relation_path=['employer'] relation_surface=['work at'] value='maple books' value_kind='literal'
  - echoed: correct subject='Ben' relation_path=['employer'] relation_surface=['work'] value='maple books' value_kind='literal'

- **tape / t_new / correct.verb #1568** `actually, i work at **Cedar Foods**.`
  - gold: correct subject='Ben' relation_path=['employer'] relation_surface=['work at'] value='Cedar Foods' value_kind='literal'
  - echoed: correct subject='Ben' relation_path=['employer'] relation_surface=['work'] value='Cedar Foods' value_kind='literal'

- **tape / t_new / correct.verb #1718** `actually, i work at amber health.`
  - gold: correct subject='Ben' relation_path=['employer'] relation_surface=['work at'] value='amber health' value_kind='literal'
  - echoed: correct subject='Ben' relation_path=['employer'] relation_surface=['work'] value='amber health' value_kind='literal'

- **tape / t_new / correct.verb #2365** `Right, actually, i work at **Lantern Garden**.`
  - gold: correct subject='Ben' relation_path=['employer'] relation_surface=['work at'] value='Lantern Garden' value_kind='literal'
  - echoed: correct subject='Ben' relation_path=['employer'] relation_surface=['work'] value='Lantern Garden' value_kind='literal'

- **tape / t_far / trap.hearsay #517** `quick one: rumour has it `Parsen`'s door is Siumosk.`
  - gold: quote
  - echoed: teach subject='Parsen' relation_path=['door'] relation_surface=['door'] value='Siumosk' value_kind='literal'

- **tape / t_far / trap.hearsay #834** `quick one: rumour has it Sefastaelle's floor is Togos.`
  - gold: quote
  - echoed: teach subject='Sefastaelle' relation_path=['floor'] relation_surface=['floor'] value='Togos' value_kind='literal'

- **tape / t_far / trap.hearsay #882** `Um, rumour has it Dordel's hometown is Remli.`
  - gold: quote
  - echoed: teach subject='Dordel' relation_path=['origin'] relation_surface=['hometown'] value='Remli' value_kind='literal'

- **tape / t_far / trap.hearsay #900** `One thing: rumour has it **Mekoradel**'s car is Ombriloford.`
  - gold: quote
  - echoed: teach subject='Mekoradel' relation_path=['car'] relation_surface=['car'] value='Ombriloford' value_kind='literal'

- **tape / t_far / trap.hearsay #936** `Btw rumour has it Nupur's guitar is Ursreldal.`
  - gold: quote
  - echoed: teach subject='Nupur' relation_path=['guitar'] relation_surface=['guitar'] value='Ursreldal' value_kind='literal'

- **tape / t_trap / trap.hearsay #47** `by the way, rumour has it Nozelle's bed is Fenque.`
  - gold: quote
  - echoed: teach subject='Nozelle' relation_path=['bed'] relation_surface=['bed'] value='Fenque' value_kind='literal'

- **tape / t_trap / trap.hearsay #196** `so, rumour has it vesrolek's letter is torkaholm.`
  - gold: quote
  - echoed: teach subject='vesrolek' relation_path=['letter'] relation_surface=['letter'] value='torkaholm' value_kind='literal'

- **tape / t_trap / trap.hearsay #789** `Um, rumour has it Parsen's train is Beont.`
  - gold: quote
  - echoed: teach subject='Parsen' relation_path=['train'] relation_surface=['train'] value='Beont' value_kind='literal'

- **tape / t_trap / trap.hearsay #958** `by the way, rumour has it melerraenko's plate is nozerraholm.`
  - gold: quote
  - echoed: teach subject='melerraenko' relation_path=['plate'] relation_surface=['plate'] value='nozerraholm' value_kind='literal'

- **bigru / t_hard / forget #230** `Clear Sky's favorite colour.`
  - gold: forget subject='Sky' relation_path=['favorite_color'] relation_surface=['favorite colour']
  - echoed: forget subject="'s" relation_path=['favorite_color'] relation_surface=['favorite colour']

- **names / t_far / trap.hearsay #21** `Rumour has it Nuoradan's job is Copper Systems.`
  - gold: quote
  - echoed: teach subject='Nuoradan' relation_path=['job'] relation_surface=['job'] value='Copper Systems' value_kind='literal'

- **names / t_far / trap.hearsay #35** `rumour has it `ruldan`'s town is gabes.`
  - gold: quote
  - echoed: teach subject='ruldan' relation_path=['city'] relation_surface=['town'] value='gabes' value_kind='literal'

- **names / t_far / trap.hearsay #103** `Rumour has it Storovan's origin is Tibsimholm.`
  - gold: quote
  - echoed: teach subject='Storovan' relation_path=['origin'] relation_surface=['origin'] value='Tibsimholm' value_kind='literal'

- **names / t_far / trap.hearsay #157** `Rumour has it Totam's wall is Veldtamholm.`
  - gold: quote
  - echoed: teach subject='Totam' relation_path=['wall'] relation_surface=['wall'] value='Veldtamholm' value_kind='literal'

- **names / t_far / trap.hearsay #474** `Rumour has it Ostgos's lunch is Tibaineholm.`
  - gold: quote
  - echoed: teach subject='Ostgos' relation_path=['lunch'] relation_surface=['lunch'] value='Tibaineholm' value_kind='literal'

- **names / t_far / trap.hearsay #501** `Rumour has it **Besenald**'s year old is 71.`
  - gold: quote
  - echoed: teach subject='Besenald' relation_path=['age'] relation_surface=['year old'] value='71' value_kind='literal'

- **names / t_far / trap.hearsay #517** `quick one: rumour has it `Parsen`'s door is Siumosk.`
  - gold: quote
  - echoed: teach subject='Parsen' relation_path=['door'] relation_surface=['door'] value='Siumosk' value_kind='literal'

- **names / t_far / trap.hearsay #566** `Rumour has it Zedtamgos's guitar is Remvanford.`
  - gold: quote
  - echoed: teach subject='Zedtamgos' relation_path=['guitar'] relation_surface=['guitar'] value='Remvanford' value_kind='literal'

- **names / t_far / trap.hearsay #768** `Fyi rumour has it Mika's favourite color is red.`
  - gold: quote
  - echoed: teach subject='Mika' relation_path=['favorite_color'] relation_surface=['favourite color'] value='red' value_kind='literal'

- **names / t_far / trap.hearsay #823** `Rumour has it Talro's cup is Parontford.`
  - gold: quote
  - echoed: teach subject='Talro' relation_path=['cup'] relation_surface=['cup'] value='Parontford' value_kind='literal'

- **names / t_far / trap.hearsay #890** `One thing: rumour has it Hellekont's year old is 40.`
  - gold: quote
  - echoed: teach subject='Hellekont' relation_path=['age'] relation_surface=['year old'] value='40' value_kind='literal'

- **names / t_far / trap.hearsay #936** `Btw rumour has it Nupur's guitar is Ursreldal.`
  - gold: quote
  - echoed: teach subject='Nupur' relation_path=['guitar'] relation_surface=['guitar'] value='Ursreldal' value_kind='literal'

- **names / t_far / trap.hearsay #946** `Rumour has it Ostsensen's dinner is Toastadal.`
  - gold: quote
  - echoed: teach subject='Ostsensen' relation_path=['dinner'] relation_surface=['dinner'] value='Toastadal' value_kind='literal'

- **names / t_trap / trap.hearsay #47** `by the way, rumour has it Nozelle's bed is Fenque.`
  - gold: quote
  - echoed: teach subject='Nozelle' relation_path=['bed'] relation_surface=['bed'] value='Fenque' value_kind='literal'

- **names / t_trap / trap.hearsay #252** `One thing: rumour has it `Gorerra`'s plate is Veldverdal.`
  - gold: quote
  - echoed: teach subject='Gorerra' relation_path=['plate'] relation_surface=['plate'] value='Veldverdal' value_kind='literal'

- **names / t_trap / trap.hearsay #343** `rumour has it taltam's street is dovmisholm.`
  - gold: quote
  - echoed: teach subject='taltam' relation_path=['street'] relation_surface=['street'] value='dovmisholm' value_kind='literal'

- **names / t_trap / trap.hearsay #548** `Rumour has it `Petr`'s train is Vaishdal.`
  - gold: quote
  - echoed: teach subject='Petr' relation_path=['train'] relation_surface=['train'] value='Vaishdal' value_kind='literal'

- **names / t_trap / trap.hearsay #604** `rumour has it lodanver's garden is veldtamholm.`
  - gold: quote
  - echoed: teach subject='lodanver' relation_path=['garden'] relation_surface=['garden'] value='veldtamholm' value_kind='literal'

- **names / t_trap / trap.hearsay #612** `Rumour has it Stolek's hill is Fenque.`
  - gold: quote
  - echoed: teach subject='Stolek' relation_path=['hill'] relation_surface=['hill'] value='Fenque' value_kind='literal'

- **names / t_trap / trap.hearsay #679** `Rumour has it `Ombrta`'s hill is Remvanford.`
  - gold: quote
  - echoed: teach subject='Ombrta' relation_path=['hill'] relation_surface=['hill'] value='Remvanford' value_kind='literal'

- **names / t_trap / trap.hearsay #958** `by the way, rumour has it melerraenko's plate is nozerraholm.`
  - gold: quote
  - echoed: teach subject='melerraenko' relation_path=['plate'] relation_surface=['plate'] value='nozerraholm' value_kind='literal'

- **names / t_hard / alias #223** `you can call Mary Jane Sunny.`
  - gold: alias alias='Sunny' canonical='Mary Jane'
  - echoed: alias alias='Jane' canonical='Mary'

## 6. Per-family misses (ensemble)


**tape**


| panel | family: misses |
|---|---|
| t_seen | teach.noun 39, trap.stmtq 28, correct.noun 26, teach.verb 17, correct.link 16, correct.verb 5, alias 2 |
| t_new | trap.hearsay 218, trap.hypo 201, teach.verb 108, correct.verb 91, teach.noun 66, alias 61, ask.vbase 39, ask.noun 37, ask.link 27, forget 2, ask.verb3 1 |
| t_far | teach.verb 113, teach.noun 76, ask.vbase 66, ask.noun 61, correct.verb 59, teach.link 58, alias 57, correct.noun 45, ask.link 41, person 40, ask.verb3 40, forget 39 |
| t_trap | trap.stmtq 105, trap.hearsay 55, trap.hypo 21, trap.negation 19 |
| t_hard | teach.verb 22, alias 16, ask.link 11, teach.link 10, ask.vbase 10, teach.noun 9, correct.noun 9, ask.noun 9, correct.verb 8, trap.stmtq 8, correct.link 6, person 5 |

**bigru**


| panel | family: misses |
|---|---|
| t_seen | teach.noun 51, correct.noun 31, trap.stmtq 28, teach.verb 20, correct.link 16, correct.verb 7 |
| t_new | trap.hearsay 218, teach.verb 112, teach.noun 101, correct.verb 71, alias 60, ask.noun 46, teach.link 45, ask.link 40, ask.verb3 8, forget 5, ask.vbase 4 |
| t_far | teach.verb 113, teach.noun 90, teach.link 87, ask.vbase 66, ask.noun 60, alias 57, correct.verb 55, ask.verb3 43, ask.link 42, person 40, forget 39, trap.hearsay 35 |
| t_trap | trap.stmtq 106, trap.hearsay 55, trap.hypo 9 |
| t_hard | teach.verb 17, alias 16, teach.link 13, ask.link 13, teach.noun 13, ask.noun 13, correct.noun 10, trap.stmtq 8, ask.vbase 7, forget 6, correct.link 6, person 5 |

**names**


| panel | family: misses |
|---|---|
| t_seen | teach.noun 39, trap.stmtq 28, correct.noun 27, teach.verb 17, correct.link 16, correct.verb 5, alias 5, ask.vbase 1 |
| t_new | trap.hearsay 218, trap.hypo 145, teach.verb 104, correct.verb 86, teach.noun 75, alias 46, ask.noun 43, ask.vbase 36, ask.link 32, forget 15, ask.verb3 5 |
| t_far | teach.verb 105, teach.link 93, teach.noun 90, ask.vbase 66, alias 57, correct.verb 56, ask.verb3 51, ask.noun 48, person 40, forget 39, trap.hearsay 35, ask.link 30 |
| t_trap | trap.stmtq 105, trap.hearsay 55, trap.negation 17, trap.hypo 16 |
| t_hard | teach.verb 16, ask.vbase 15, alias 14, teach.noun 13, ask.noun 12, teach.link 10, ask.link 9, trap.stmtq 9, forget 7, correct.noun 7, person 6, correct.verb 6 |

## 7. Recorded only


- **tape** T-far (far constructions, 1,000): correct 211, EXECUTE-correct 19, silent wrong writes 0, echoed wrong writes 5.
- **tape** router gates sigmoid(10 tanh G):
    - stage 0: 0.63 0.25 0.48 0.13 0.11 0.19 0.54 0.34 0.25 0.45 0.16 0.38 0.49 0.19 0.27 0.28 0.11 0.19 0.30 0.42 0.21 0.13 0.13 0.29
    - stage 1: 0.29 0.08 0.13 0.11 0.07 0.22 0.25 0.18 0.11 0.19 0.20 0.12 0.17 0.21 0.21 0.19 0.11 0.16 0.38 0.20 0.21 0.28 0.09 0.07
    - stage 2: 0.28 0.12 0.17 0.32 0.10 0.15 0.17 0.17 0.07 0.15 0.13 0.16 0.20 0.18 0.21 0.21 0.16 0.17 0.38 0.28 0.28 0.24 0.10 0.12
    - stage 3: 0.19 0.26 0.32 0.30 0.16 0.18 0.17 0.19 0.17 0.25 0.18 0.13 0.30 0.28 0.29 0.32 0.30 0.27 0.29 0.15 0.26 0.24 0.13 0.33

- **bigru** T-far (far constructions, 1,000): correct 229, EXECUTE-correct 29, silent wrong writes 0, echoed wrong writes 0.

- **names** T-far (far constructions, 1,000): correct 218, EXECUTE-correct 23, silent wrong writes 2, echoed wrong writes 13.
- **names** router gates sigmoid(10 tanh G):
    - stage 0: 0.70 0.33 0.11 0.24 0.39 0.29 0.29 0.10 0.30 0.40 0.40 0.19 0.32 0.27 0.38 0.36 0.10 0.34 0.26 0.37 0.29 0.21 0.16 0.42
    - stage 1: 0.22 0.24 0.10 0.16 0.13 0.21 0.14 0.10 0.40 0.23 0.51 0.14 0.22 0.15 0.10 0.21 0.07 0.31 0.24 0.14 0.11 0.17 0.09 0.22
    - stage 2: 0.34 0.20 0.11 0.21 0.17 0.30 0.19 0.20 0.32 0.20 0.32 0.15 0.31 0.15 0.17 0.18 0.12 0.27 0.22 0.15 0.15 0.23 0.14 0.21
    - stage 3: 0.29 0.27 0.23 0.18 0.35 0.25 0.31 0.22 0.22 0.23 0.12 0.17 0.17 0.25 0.38 0.27 0.27 0.34 0.29 0.37 0.23 0.27 0.20 0.28

- 4-hop questions: **not measured** — the rung-1 generator makes at most 3 hops (deviation 7).


## 8. Wall-clock and seconds per update


| arm | seed | params | sec/update | train min | dev act acc |
|---|---|---|---|---|---|
| tape | 4301 | 241,941 | 0.130 | 17.3 | 0.975 |
| tape | 4302 | 241,941 | 0.130 | 17.3 | 0.978 |
| tape | 4303 | 241,941 | 0.129 | 17.3 | 0.979 |
| bigru | 4301 | 243,237 | 0.026 | 3.5 | 0.978 |
| bigru | 4302 | 243,237 | 0.027 | 3.5 | 0.979 |
| bigru | 4303 | 243,237 | 0.027 | 3.5 | 0.975 |
| names | 4301 | 635,157 | 0.139 | 18.5 | 0.978 |
| names | 4302 | 635,157 | 0.139 | 18.5 | 0.980 |
| names | 4303 | 635,157 | 0.139 | 18.5 | 0.976 |

- wave **tape**: train 17.5 min, wave incl. scoring 17.6 min (8000 updates × 3 seeds in parallel).

- wave **bigru**: train 3.7 min, wave incl. scoring 3.9 min (8000 updates × 3 seeds in parallel).

- wave **names**: train 18.7 min, wave incl. scoring 19.0 min (8000 updates × 3 seeds in parallel).
