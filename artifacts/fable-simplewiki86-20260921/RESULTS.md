# Exp 86 RESULTS — Simple English reading corpus (Muse, raw data only)

PASS 4/4. Built a licence-clean reading corpus from the official Simple
English Wikipedia dump. Raw data only: nothing entered the notebook or weights.

## Marks (integer counts, seed 86 throughout, nothing averaged)

| mark | bar | got |
|---|---|---|
| W1 | >= 100,000 kept | 200,000 kept |
| W2 | 0 residue in 1,000-check | 0 hits / 1,000 |
| W3 | 0 exact dupes | 0 dupes in 200,000 |
| W4 | < 25 min Mac CPU | 20.5 s wall |

## Counts

Pages seen 43,925 (ns-skipped 9,688, redirects 9,750). Candidates 570,093.
Drops: no-cue 160,097; not-capital-start 84,522; not-declarative-end 46,499;
markup-residue 42,353; too-long 21,654; too-short 13,879; exact-dupe 1,086;
empty 3. Held-out 2,000 sentences across 2,000 pages (subset of main file,
one per page, round-robin). Vocabulary 86,035. Downloaded 45,088,768 bytes
then stopped early (sha256 of prefix in counts.json).
Top verbs by sentence count: is 87,206; was 47,999; are 38,026; has 14,741;
were 14,092; called 9,926; had 9,886; used 8,173.

## 20-sentence random sample (seed 861)

1. [Tintin/Books] While investigating art forgery ring Tintin is captured; it was Unfinished at the time of Hergé passing leaving one hundred and fifty pages of pencil sketches for the story.
2. [Spyware/lead] Spyware is a category of software for computers.
3. [Orbital period/lead] The year and month are orbital periods.
4. [Drunk driving/lead] The most common blood alcohol content (BAC) limit in the United States is 0.08% for the legal meaning of drunk.
5. [Multiplication/lead] The opposite of multiplication is division.
6. [Sailor Moon/lead] Sailor Moon is a shojo manga by Naoko Takeuchi.
7. [Pope John Paul II/Assassination attempts] He barely survived the assassination attempt, and had to be treated in hospital for 20 days.
8. [Musical notation/modern system] All the parts needed for a piece of music is called a “set of parts”.
9. [Entropy/Energy Dispersal] When an ice cube melts, for example, the molecules move from an orderly, solid structure to a freely moving liquid where energy is more dispersed.
10. [Sagittarius (astrology)/lead] Sagittarius is the astrological Zodiac sign that represents the constellation Sagittarius.
11. [Poland/Geography] Coast lakes are former bays that have been cut off from the sea.
12. [Melbourne/Sister cities] Melbourne has six sister cities.
13. [Dumfries and Galloway/lead] Dumfries is 60 miles south of Edinburgh, the capital of Scotland.
14. [Glay/lead] Since 2007, Teru has been in ads shown on television and in theaters to raise awareness about HIV/AIDS.
15. [Sartène/Climate] The highest temperature ever recorded in Sartène was on 23 July 2009.
16. [Pieve Ligure/lead] The wildlife there is very varied from young catfish to octopus.
17. [Borzoi/lead] It has not changed much since then.
18. [Logic/Logical proof] That kind of statement is called tautology.
19. [Wildebeest/What they eat] In November they move back; there is grass in the plains in summer.
20. [Mafia/In Italy] The mafia is still around here and they make a great deal of money.

## Files

- data/open/simplewiki86/{sentences.jsonl (200,000), heldout.jsonl (2,000), counts.json, verbs_top50.json, vocab.txt, LICENCE.md}
- scripts/fable_simplewiki86_extract.py (stdlib + numpy only)
- Source: https://dumps.wikimedia.org/simplewiki/20260901/simplewiki-20260901-pages-articles-multistream.xml.bz2, 2026-09-01, 385,846,687 bytes, published SHA-1 50152ec5…. CC BY-SA 4.0 + GFDL; credit per sentence via page field.

Reproduce: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_simplewiki86_extract.py --out data/open/simplewiki86`

Deviations: none. Seed-86 smoke test (target 20) before the registered run caught and fixed one bug (fresh bz2 decompressor per multistream chunk); registered run is the 20.5 s run above.

What it means: the reading ladder has 200k clean, labelled-by-source simple sentences ready.
What it does not mean: none of it is verified true — web text stays raw data until taught/inferred properly.
