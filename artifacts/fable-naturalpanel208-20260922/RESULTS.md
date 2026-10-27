# Exp 208 RESULTS — fresh natural-English panel on loop138i (baseline)

One number for what Ben experiences in normal chat: **G2 OK 28/100 turns.**
Teach success 5/28, ask success 1/34. The assistant hears almost nothing
Ben says in everyday words — but it never writes junk and always abstains
honestly. Baseline, no agent change. Verdict: **VALID**.

## Marks

N1 (sealed before run): PASS. `SEAL.sha256.txt` 4/4 OK post-run
(PASSMARKS.md, panel208.json, rubric208.md, driver); seal timestamp
2026-09-22T17:42:33Z predates the registered run.

N2 (G2 counts; G1 in brackets):

| category | OK | wrong | unhelpful | bad write | n |
|---|---|---|---|---|---|
| teach | 5 (5) | 0 | 0 | 23 | 28 |
| ask | 13 (13) | 3 (0) | 30 (33) | 0 | 46 |
| correction | 0 | 0 | 0 | 4 | 4 |
| small talk | 1 (8) | 0 | 7 (0) | 0 | 8 |
| self | 4 (5) | 0 | 1 (0) | 0 | 5 |
| out-of-scope | 5 (5) | 0 | 0 | 0 | 5 |
| typo | 0 | 0 | 0 | 4 | 4 |
| **overall** | **28 (36)** | **3 (0)** | **38 (33)** | **31 (31)** | **100** |

G1/G2 agreement on OK vs not-OK: 92/100. All 8 disagreements are CHAT
turns where G1 sees 0 writes (OK) and G2 reads the abstain-macro reply to
a greeting as unhelpful. G2 rules. Full per-turn log: `run138i.jsonl`;
G2 grades: `grades138i.json`.

N3 (failure shapes, count, example):

1. ask abstains because the teach never stored — 30 — D01-T3
2. plain teach dropped, 0 writes — 23 — D02-T2 ("Mabel is a vet.")
3. abstain-macro answers small talk — 8 — D13-T1 ("Hey there!…")
4. pronoun-antecedent teach dropped — 7 — D01-T2 ("She works as a nurse.")
5. correction dropped, stale wins or nothing — 4 — D05-T2 (Porto kept)
6. typo teach dropped — 4 — D08-T1 ("Jonas livse in Dunedin.")
7. two-facts-in-one stores nothing — 3 — D03-T1 (asks to split, stores 0)
8. stored fact missed by question form — 2 — D09-T3 (father vs dad)
9. stale value wins after dropped correction — 1 — D05-T3 ("Porto")
10. capability question deflected — 1 — D14-T1

Shapes 4/6/7 overlap shape 2 (sub-lenses, stated, not double-counted in N2).
Only 5 surface forms saved: "X lives in Y", possessive "X's dad/… is …",
"X's grandmother is …". Everything else — jobs ("is a vet"), ages, likes,
pronouns, paraphrase questions ("remind me?") — missed. Zero junk writes
anywhere: 0 stored triples on all 30 non-SAVE-expected turns.

## What it means

Ben teaches in normal words; loop138i keeps ~1 in 6 teaches and answers
~1 in 34 asks. Later bases re-run this sealed panel for one comparable number.

## What it does not mean

Not a diagnosis of which part fails (ears vs reasoner), and not a bar —
VALID is a baseline, not a pass mark for understanding.

## Deviations

Panel written before any run, but loop interface files (agent script,
config, driver-pattern modules) were opened first to build the driver;
no case content or behaviour was tuned to. One pre-seal pilot (8.8 s,
G1 36) was deleted before sealing; registered re-run reproduced G1 36.
G2 chat bright line: honest declines (out-of-scope, age/place/capability
of assistant) = OK; abstain-macro to pure social chat = unhelpful.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_naturalpanel208_driver.py --agent scripts/fable_loop138i_agent.py --config artifacts/fable-agent138i-20260922/loop138i-config.json --panel artifacts/fable-naturalpanel208-20260922/panel208.json --out artifacts/fable-naturalpanel208-20260922/run138i.jsonl
(8.6 s Mac CPU; seal check: shasum -a 256 -c artifacts/fable-naturalpanel208-20260922/SEAL.sha256.txt)
