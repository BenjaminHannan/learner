# Exp 97 RESULTS — independent panel for the exp-63 relation canonicalizer

## Result: PASS (K1, K2, K3 all meet their sealed bars)

One registered run, Mac CPU, offline, `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`.
Panel (300 + 150 + 50) written blind — canon(), testdata, alias/denylist
tables, and exp-63 test JSONs never opened. Only inputs: the 60 canonical
relation names (+PIDs) and plain Wikidata descriptions. PASSMARKS.md and
all three test files sealed (`SEAL.sha256.txt`, verified OK after the run)
before canon() was ever imported. Ledger predictions P97.1–P97.4 appended before the run.

## Marks (integer counts, every case reported)

| mark | n | outcome (integer counts) | bar | verdict |
|---|---|---|---|---|
| K1 paraphrases | 300 | correct 28, abstain 270, **wrong 2** | wrong ≤ 3 | PASS |
| K2 fabricated | 150 | UNKNOWN 150, concrete 0 | ≥ 147 UNKNOWN | PASS |
| K3 near-miss | 50 | correct 1, abstain 49, **wrong 0** | 0 wrong | PASS |

Every case reported, nothing averaged. Abstain is reported, not gated.

## Every wrong answer, verbatim (K1, 2 total)

- `p147 | 'is the author of' | gold='author' | raw='notable work'` — genuinely
  wrong: the phrase states authorship, answered as the author's work.
- `p188 | 'is found at' | gold='location' | raw='location of discovery'` —
  counted wrong per the sealed rule; see Deviation 1 (arguably ambiguous).

## Every near-miss outcome, verbatim (K3, 50 total)

- `n001 | 'is the capital city of' | gold='capital of' | raw=None | abstain`
- `n002 | 'has as its capital city' | gold='capital' | raw=None | abstain`
- `n003 | 'a capital idea' | gold='UNKNOWN' | raw=None | abstain`
- `n004 | 'was born in the town of' | gold='place of birth' | raw=None | abstain`
- `n005 | 'was born on the morning of' | gold='date of birth' | raw=None | abstain`
- `n006 | 'died in the city of' | gold='place of death' | raw=None | abstain`
- `n007 | 'died on the date of' | gold='date of death' | raw=None | abstain`
- `n008 | 'walked down the aisle with' | gold='spouse' | raw=None | abstain`
- `n009 | 'got married in the chapel at' | gold='UNKNOWN' | raw=None | abstain`
- `n010 | 'is engaged to' | gold='UNKNOWN' | raw=None | abstain`
- `n011 | 'is the mother of' | gold='child' | raw='child' | correct`
- `n012 | 'mothers the toddler' | gold='child' | raw=None | abstain`
- `n013 | 'fathers a son' | gold='child' | raw=None | abstain`
- `n014 | 'was followed by the sequel' | gold='followed by' | raw=None | abstain`
- `n015 | 'comes just before the finale' | gold='followed by' | raw=None | abstain`
- `n016 | 'comes just after the opener' | gold='follows' | raw=None | abstain`
- `n017 | 'is next in the list after' | gold='follows' | raw=None | abstain`
- `n018 | 'is next in the list before' | gold='followed by' | raw=None | abstain`
- `n019 | 'owns the corner shop' | gold='owner of' | raw=None | abstain`
- `n020 | 'is owned by the corner shop' | gold='owned by' | raw=None | abstain`
- `n021 | 'belongs to the landlord' | gold='owned by' | raw=None | abstain`
- `n022 | 'includes the appendix as a part' | gold='has part' | raw=None | abstain`
- `n023 | 'is included as a part of' | gold='part of' | raw=None | abstain`
- `n024 | 'is a member of the first team' | gold='member of sports team' | raw=None | abstain`
- `n025 | 'is a member of the local party branch' | gold='member of political party' | raw=None | abstain`
- `n026 | 'is a member of the choir' | gold='member of' | raw=None | abstain`
- `n027 | 'runs the ferry crossing' | gold='operator' | raw=None | abstain`
- `n028 | 'runs the country day to day' | gold='head of government' | raw=None | abstain`
- `n029 | 'school of fish' | gold='UNKNOWN' | raw=None | abstain`
- `n030 | 'wrote the screenplay for' | gold='author' | raw=None | abstain`
- `n031 | 'dreamed up the character for' | gold='creator' | raw=None | abstain`
- `n032 | 'built the game engine for' | gold='developer' | raw=None | abstain`
- `n033 | 'was behind the camera on' | gold='director' | raw=None | abstain`
- `n034 | 'works the tills for' | gold='employer' | raw=None | abstain`
- `n035 | 'set the firm up' | gold='founded by' | raw=None | abstain`
- `n036 | 'got the firm going in the year' | gold='inception' | raw=None | abstain`
- `n037 | 'sits in the county' | gold='located in the administrative territorial entity' | raw=None | abstain`
- `n038 | 'covers the county' | gold='contains administrative territorial entity' | raw=None | abstain`
- `n039 | 'touches the county line' | gold='shares border with' | raw=None | abstain`
- `n040 | 'lies within the nation of' | gold='country' | raw=None | abstain`
- `n041 | 'votes as a citizen of' | gold='country of citizenship' | raw=None | abstain`
- `n042 | 'was first brewed in the land of' | gold='country of origin' | raw=None | abstain`
- `n043 | 'is capped at senior level by' | gold='country for sport' | raw=None | abstain`
- `n044 | 'speaks at home' | gold='languages spoken, written or signed' | raw=None | abstain`
- `n045 | 'is the tongue of administration in' | gold='official language' | raw=None | abstain`
- `n046 | 'studied law at' | gold='educated at' | raw=None | abstain`
- `n047 | 'gave a guest lecture at' | gold='UNKNOWN' | raw=None | abstain`
- `n048 | 'followed the band on tour' | gold='UNKNOWN' | raw=None | abstain`
- `n049 | 'follows online' | gold='UNKNOWN' | raw=None | abstain`
- `n050 | 'is part of the deal' | gold='UNKNOWN' | raw=None | abstain`

K2: all 150 fabricated returned UNKNOWN (raw None); zero concrete outputs.

## What it means

A truly independent panel confirms exp 63's safety shape: on 500 unseen
phrases the canonicalizer gave 2 wrong answers and 0 perspective flips —
it abstains instead of guessing.

## What it does not mean

It does not confirm coverage: only 28/300 paraphrases (9.3%) were answered
at all. Novel everyday phrasing mostly falls outside the alias table, so
the panel passes on caution, not on understanding.

## Deviations

1. p188 (`is found at` → `location of discovery`) is arguably a defensible
   reading (discovery site vs general location); the sealed rule counts any
   non-gold concrete output as wrong, so it stands as wrong #2. Excluding it
   would give 1 wrong; the registered 2 stands.
2. The scorer resolved the entry point by runtime introspection only
   (`canon(relation_string) -> Tuple[Optional[str], Optional[str], bool]`;
   first element scored, predeclared coercion). No exp-63 source was read.
3. Minor process point: two file edits were applied via shell heredoc
   instead of the Edit tool; content verified by assertions + seal.

## Questions for Ben

None. Conservative default applied throughout (ambiguity → counted wrong,
abstain reported not gated).

## Reproduce (exact)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_relcanon97_make.py
shasum -a 256 artifacts/fable-relcanon97-20260921/PASSMARKS.md artifacts/fable-relcanon97-20260921/test_*.json
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_relcanon97_score.py
```

Ledger: P97.1 TRUE (2 ≤ 3) | 0.2025. P97.2 TRUE (150/150) | 0.04.
P97.3 TRUE (0 wrong) | 0.16. P97.4 TRUE (wave ≈ 6 min) | 0.0025.
