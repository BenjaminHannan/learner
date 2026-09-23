Judging 120 pairs for naturalness — first checking the rules and files.
Stylesheet verified — now reading the judging criteria and pairs.
I've read all 120 pairs — now writing the judgments file.
Verification passed — final check that nothing else was touched.
VERDICT: COMPLETE — all 120 pairs judged, file written at `artifacts/claude-judge241b-20260923/m4-judgments.jsonl` (120/120 lines, valid JSON, verified by script).

Marks table (integer counts):
| mark | count |
|---|---|
| pick X | 54 |
| pick Y | 52 |
| pick tie | 14 |
| meaning_change true | 0 |
| meaning_change false | 120 |
| total pairs judged | 120 |

Every move (every pair, blind to system identity):
- X (54): p002, p005, p006, p012, p013, p017, p019, p023, p024, p025, p027, p028, p029, p031, p032, p036, p037, p038, p040, p045, p046, p047, p048, p051, p055, p058, p060, p061, p064, p065, p071, p072, p074, p076, p079, p080, p083, p085, p086, p089, p094, p095, p097, p098, p104, p105, p107, p108, p110, p112, p114, p117, p118, p120
- Y (52): p001, p003, p007, p008, p010, p015, p016, p018, p020, p022, p026, p030, p034, p035, p039, p041, p042, p043, p044, p049, p050, p052, p053, p054, p056, p062, p066, p067, p068, p069, p070, p073, p075, p077, p081, p084, p087, p088, p091, p093, p099, p100, p101, p102, p103, p106, p109, p111, p113, p115, p116, p119
- tie (14): p004, p009, p011, p014, p021, p033, p057, p059, p063, p078, p082, p090, p092, p096
- meaning_change true ids: none (0 cases).

Every miss: zero. I read all 120 pairs myself plus the stylesheet. No pair skipped, no line missing, no duplicate ids (script-checked: ids_complete=True, dupes=0, bad JSON=0).

Deviations / notes:
1. Stylesheet sha256 matched `16bdf0cf…dad8ef` exactly, so I proceeded.
2. I never opened `pairs-key.jsonl`, `pairs-log.jsonl`, PASSMARKS, RESULTS, or any script contents — only filenames appeared in directory listings.
3. "PUSH" deviation: I did NOT git-add/commit/push. OPUS-RULES forbids commits/pushes, and `artifacts/` is gitignored (`.gitignore:5`), so the file lives on disk at the required path, untracked. No existing file was edited or deleted.
4. Machine load was high (1-min load 30–82) and free disk was 16 GB (above the 3 GB stop line). My work was light reading/writing only, ≤1 process, so I proceeded.
5. Judging bar used throughout: prefer the grammatical/natural reply — words for small numbers, "and"-lists, plural agreement for multi-name lists ("friends are"), articles ("is a welder"), capitalised names, full-sentence confirmations over terse labels, clean chain-stops over "which is not someone I can look up" for places, and explicit "nothing to forget" for not-had cases. Case-only differences (teandsterk vs Teandsterk) were not counted as meaning changes.

What it means (plain English): Across 120 blind A-vs-B comparisons, neither reply ever changed the facts — every pair kept the same names, numbers, and answers, differing only in wording. On wording, the vote split almost evenly (54 vs 52 with 14 ties), with the winner in each pair being the version that sounds like a careful person wrote it.

What it doesn't mean: This says nothing about which system (X or Y) is better overall — I was kept blind to that on purpose, and the near-even split is by construction of the test, not a ranking. It also doesn't mean the replies are perfect, only that none of the 120 altered factual meaning.
