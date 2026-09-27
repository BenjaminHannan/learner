# Exp 237 -- relation table v1.1 on loop221

## Verdict: FAIL (registered). The synonym family (21/30 = 70 % vs 85 % bar) and the trap family (9/10) miss. There is also 1 wrong value, and 221 gives that same reply (see a237-070). Every other mark passes.

Build: loop237 = loop221 + relation_table_v1_1.json (v1 + 68 additions).
- Code: scripts/claude_loop237_agent.py.
- The 228 guard is installed: SrcGuardMixin228 comes first in Loop237Daemon's bases, and install_srcguard228() runs at import.
- Order: pilots were scratch only. The seal (SEAL.sha256.txt) was written at 16:00:50, with 18 files. After that came the registered M2, M3 and M4 runs.
- Then the panel seal was checked from the repo root (both files OK), and the panel was run once per arm.
- All sealed files verify OK after the runs.

## Marks
| mark | bar | result | pass? |
|---|---|---|---|
| M1 synonym | >= 85 % | **21/30 = 70.0 %** | **FAIL** |
| M1 new_relation | >= 80 % | 17/20 = 85.0 % | pass |
| M1 date | >= 80 % | 8/10 = 80.0 % | pass |
| M1 trap (0 values) | 10/10 | **9/10** (a237-070) | **FAIL** |
| M1 control byte-identical to base221.jsonl | 10/10 | 10/10 | pass |
| M1 wrong values, 80 items | 0 | **1** (a237-070; 221 gives the same) | **FAIL** |
| M1 question writes | 0 | 0/80 | pass |
| M2 dev (34) | 34/34, 0 writes | 34/34, 0 writes (loop221 on the same cases: 12/34) | pass |
| M3 new WRONG / WRONG-WRITE / junk / lost OK | 0 | 0 / 0 / 0 / 0; GATE clean | pass |
| M3 moves = predicted | only rt143 L3 | rt143 L3 reply-only OK->OK ("I don't know Tomas Reed's team."); rt136, sessions152, bench 0 moves | pass |
| M4 sleep smoke | same as 221 | sleeps 1, installed, episodes 20, probes 5/5, wrong 0, taught 50/50, overwrote 0, 83.4 s | pass |
| M5 median added ms/question | <= +5 | +0.59 ms (2.77 vs 2.19, panel) | pass |

My own loop221 arm matched base221.jsonl on 80/80 panel replies, so the base is reproduced exactly.

## Every panel move (loop237 reply differs from loop221: 41 of 80)
All are listed in m1panel/rows237.jsonl and rows221.jsonl. Summary:
- **Synonym, now right (17):**
  - physician asked as doctor: 001-003
  - supervisor asked as boss: 004-006
  - attorney asked as lawyer: 007-009
  - roommate asked as flatmate/housemate: 010-012
  - residence asked as "Where does X live?": 021, 022
  - native language asked as mother tongue/first language: 024-026
- **New relation, now right (17):**
  - "the R of X" questions: landlord 031, dentist 033, vet 035, plumber 036, accountant 037, barber 038, tutor 039, babysitter 040, godmother 044, mayor 048-050
  - "Who coaches X?": 041, 042
  - "Who owns X?": 045-047
- **Date, now right (6):**
  - founded: 051, 052
  - opened: 053
  - wedding anniversary: 056
  - graduated: 057, 058
- **Moved but still a miss (1):** a237-054 "When did Copperleaf Garage first open?"
  - 221 gave the plain not-understood reply. 237 now says "I don't know anyone called Copperleaf Garage first."
  - This is still an honest abstain with no value, but the wording is worse. "When did {X} open?" read X as "Copperleaf Garage first".
- No item moved from right to wrong. No control moved.

## Every miss (diagnosis only; nothing changed after the run)
- **Synonym (9): pairs that v1.1 does not list.**
  - pupil/student: 017, 018
  - surname/last name/family name: 019, 020
  - automobile/car: 027, 028
  - phone/telephone number: 029, 030
  - "live these days": 023 (no template)
- **New relation (3): wordings with no template.**
  - "the landlord for X": 032
  - "the dentist for X": 034
  - "piano teacher": 043
- **Date (2):**
  - 054: "first open" is not covered (see above).
  - 060: "When was X born?" when a birthday is stored. By design, birthday and date of birth are not linked (design note), so it abstains.
- **Trap (1), also the 1 wrong value: a237-070.**
  - Setup: "Corwin Nancarrow's employer is Mossbank Library."
  - Question: "Who does Corwin Nancarrow employ?"
  - Reply: "Corwin Nancarrow's employer is Mossbank Library."
  - base221.jsonl and my 221 arm give the SAME reply, so this comes from the 221/138i stack and not from v1.1. It still counts against the registered marks.

All 13 other misses are honest abstains with no value.

## Deviations
1. **Shell slip.** The first registered-run command failed in the shell before any agent started (a zsh variable was not split into words). No runner executed and no rows were written. It was re-issued at once with a shell function; those are the registered runs.
2. **Renamed row copies.** fable_suitediff218 --base-dir could not find 221's rows as saved (rt136-rows.json and rt143-rows.json lack "redteam136"/"redteam143" in the filename).
   - I copied 221's saved rows byte for byte to base221rows/ under recognised names. They are sealed.
   - The pilot with the original folder skipped rt136 and rt143.
3. **Panel field map.** m1panel/fieldmap.json holds field NAMES only. It was written after opening the panel, as PASSMARKS declared. The scoring rules are the sealed ones.
4. **Panel lines printed.** After the seal I printed the panel README and 2 panel lines to learn the field names.

## What it means
- The table approach works where the table has the words. Every synonym group and every new relation that v1.1 lists was answered right on the blind panel: 40 items went from "don't know" to the right answer.
- None of the 40 moved items gave a wrong value, and nothing was written.
- Questions still never write. Controls, frozen suites and sleep are unchanged, and the cost is about half a millisecond.

## What it doesn't mean
- It does not pass. The synonym bar failed because the panel used pairs that v1.1 never lists (pupil/student, surname/last name, automobile/car, phone/telephone). A hand-made list only covers the words someone thought of.
- The one trap failure is an old 221 behaviour ("Who does X employ?" is read as a question about X's employer). This experiment did not fix it.
- The panel has 80 items from one writer, so each family is small (10-30 items). Dev cases were written by me.
