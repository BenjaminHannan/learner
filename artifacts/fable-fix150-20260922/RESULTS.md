# Exp 150 RESULTS — subject-span guard on loop139b (Muse). REGISTERED PASS.

Target: loop150 = loop139b + SubjectGuard150Mixin
(scripts/fable_fix150_subjectguard.py; wrapper
scripts/fable_loop150_agent.py; config
artifacts/fable-fix150-20260922/loop150-config.json). THE ONE CHANGE:
139/139b guard only the VALUE span; teaches with a hedge/reporting/filler
prefix in the SUBJECT span stored the pollution verbatim (director probe:
"I think Kip Dune", "Perhaps Kip Dune", "Maybe Kip Dune",
"Someone told me Kip Dune", "Rumor has it Kip Dune", "Honestly Kip Dune",
"So Kip Dune", "My friend Kip Dune"). Now the subject span, after the 129
strip, (a) hedge/reporting openers -> no write (hedges: existing SPLIT
clarify; reporting: existing HEARSAY reply; reused, none invented);
(b) fillers/introducers -> stripped, clean subject stored, remainder
re-screened; (c) other lowercase-lead multi-token subjects with a
capitalised token and no " of " -> SPLIT clarify, no write. Untouched:
single-token subjects, all-lowercase subjects ("wide receiver"),
role-phrase subjects ("director of X", bench-legit officeholder shape),
camelCase names ("macOS Server"), capitalised word-names (Will/May/Hope/
Grace/Rich/Sunny/Frank/Mark/So-Yeon -- capitalisation shape, never
vocabulary), values, relations, forget/ask/clarify.

## Marks table (integer counts, every case reported, never averaged)

| mark | bar (PASSMARKS.md, sealed) | got | verdict |
|---|---|---|---|
| S1 57-case probe through loop150 | 22 hedge/reporting no-write right-reply; 16 filler exact; 16 legit exact; 3 handled unchanged; 0 wrong writes, full triple | 57/57 OK (12 split + 10 hearsay nowrites; 16/16 clean filler triples; 16/16 legit incl. all 9 word-names; A01 hearsay, A02 clean, A03 nowrite) | PASS |
| S2 director's 8 cases | no polluted subject stored | 8/8 (5 refuse-empty; Honestly/So/My-friend store ["Kip Dune", country_of_citizenship, "Peru"]) | PASS |
| S3 bench per-item + marks123 | identical to loop139b, 0 moves | edit200/old/new 600/600 verdict-identical, reply_moves 0; marks123 10/10 suite verdicts + p2 64/64, p4 30/30, rt110 62/62 per-case, bench rows 400/400 identical (sleep SKIP text differs only by agent filename) | PASS |
| S4 redteam136 re-run | no case worse, 0 moves | 145 cases OK 126 / WW 14 / MISSED 5, moves=[], worse=[] vs loop139b | PASS |
| S5 each run < 1500 s Mac CPU | < 1500 s | probe 1.1 s, bench 27.4 s, marks 133.5 s, redteam 2.5 s | PASS |

Bench detail loop150: edit200 150/50/0; old-s2fresh 157/43/0; new-121
136/63/1 -- each per-item identical to the sealed loop139b rows.

## What it means

Hedged, reported, and filler-prefixed teaches no longer corrupt the
notebook with polluted subjects, while real names -- including names that
are also English words -- and ordinary possessive/The-frames store exactly
as before, with zero moves anywhere else (benches, marks, redteam).

## What it does not mean

It does not judge truth -- a confidently-stated false single fact still
stores; all-lowercase multi-word subjects ("yesterday kip dune") still
store by design (bench common nouns force the exemption); bare "A and B"
values and the other 136 classes are 139/139b's and redteam's business,
not this guard's.

## Deviations

1. L16 replaced pre-seal ("Ann Lee's city ..." is MISSED even on base:
   FakeEars is one-word-names-only) with "The official language of Peru is
   Spanish."; "i feel" deliberately not a hedge (bench songs "I Feel Love",
   "I Feel Fine"); rule (c) needs all-lowercase first token + " of "
   exemption (bench "macOS Server", "director of X"). All pre-seal only.
2. Marks p2/q1/rt81/q4 FAIL labels are byte-identical on loop139b
   (pre-existing harness bars, not regressions); comparison is per-case
   identical, which holds everywhere.
3. probe150-loop139b-calib.json kept in-dir as the sealed pre-seal base
   calibration (36 polluted writes, 21 OK).

Reproduce: PASSMARKS.md command block (sealed SEAL.sha256.txt).
Ledger: P150.1 TRUE, P150.2 TRUE, P150.3 TRUE, P150.4 TRUE, P150.5 TRUE.
