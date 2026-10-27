# 77 — Core fixes for the redteam67 findings (additive wrappers, 2026-09-22)

Three confirmed bugs, three wrappers, zero edits to existing files. The
unfixed modules (`fable_thought49_notebook`, `fable_qual56_reasoner`,
`fable_notebook_contract`) are imported read-only; all new behaviour lives
in `scripts/fable_fix77_core.py`.

## Fix 1 (critical): one shared rule-2 gate

Doc-56 rule 2: an unqualified taught row always wins over qualified rows for
the same subject+relation, even when the question carries a matching
qualifier. `QualifierAwareReasoner` already enforced this in its filtered
view; `ThoughtNotebook._gate` did not, so a qualified question over
Tom/friend returned multi "Mira, Ana" (conditioned claim served as fact)
while qual56 answered "Ana". `GatedThoughtNotebook(ThoughtNotebook)`
overrides only `_gate`: if any active row for the hop is an unqualified
taught row (foreign events count as unqualified with their stored source),
all qualified rows are dropped; otherwise the parent gate runs unchanged.
Both readers now compute the same kept-set, verified 24/24 agreement on the
qual56 battery plus the contract lifecycle 32/32 through the subclass.

## Fix 2 (medium): bool qualifier equality

`value_equals` stringified the question value (`str(True)` = `"True"`) and
compared against the stored `"true"` literal, so bool qualifiers could never
match through qual56. `QualifierAwareReasoner77` reuses the parent's hop
loop verbatim with views from `filtered_view77`, which uses
`qualifiers_match77`/`value_equals77`: for boolean row values a real bool
compares by identity and any other spelling compares case-insensitively
against "true"/"false" — the exact branch `ThoughtNotebook._value_matches`
already had. All non-boolean comparisons are the parent's exact equality;
verified that `"true"`/`"TRUE"`/`" True "` match, `False` does not, and the
24-case battery is unchanged.

## Fix 3 (medium): tail-evident loading

A last-line value rewrite keeps valid JSON and a valid prev link, making it
byte-identical to a legitimate append — undetectable by any pure function
of `events.jsonl`. So `verify_full` pairs the full prev-link re-hash (names
the line; torn tail raises with a repair pointer) with a sidecar seal
(`events.fix77.seal.json`: line count + tail sha). The seal must first be
written on a trusted state (same trust model as the chain's genesis); every
later verify detects prefix edits, truncation, and tail edits, then advances
the seal. `open_verified(dir, factory)` verifies then loads with any
notebook factory. `VerifiedNotebook(C.Notebook)` keeps read/write semantics
identical (same torn-tail flag and repair flow) while maintaining the seal
on every append and verifying on every clean open — this is what flips
RT49b-as-coded from silent `HACKED` to `LogCorrupt`. New appends after a
seal are link-verified and resealed; only tail writes through
non-maintaining handles between verified opens are outside the guarantee,
and the module docstring says so.

## Swap guidance for the director

Agent loop (`fable_agent_loop.py:218`): swap to `open_verified`/`VerifiedNotebook`
for tail-evidence; `LookupReasoner` (:175) is qualifier-blind but safe while
turns teach unqualified rows only. Bench arm (`fable_bench65_notebook_arm.py:63,87`):
swap demonstrated at 200/200 with zero contract disagreements. Wire57
(`fable_wire57_e2e.py:66`): no direct construction; covered by the loop swap.
`VerifiedNotebook`'s extra cost is one small sidecar write per append
(RT51 10k-fact case still passes).

## What it means / does not mean

Means: the two qualifier readers agree everywhere measured and the log is
tail-evident on verified loads, with qual56/baby-bench behaviour unchanged.
Does not mean: safety of English ears, mouth wording, or sleep mining, which
were never in scope.
