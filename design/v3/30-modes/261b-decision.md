# 261b: decision notes (director, 2026-09-23 01:45 UTC)

## Ruling 1: a narrower relation counts as right for a broader gold relation (scorer rule, from the relation table)
- Relation table v1 already says `pet` has `narrower: ["dog", "cat"]`, and `dog` and `cat` are their own relations.
- The 261 scorer only accepted `relation_aliases`, so a save whose relation was the species word was counted as a WRONG save against gold `pet`.
- Director review of 261's wrong saves (category level): 6 of 9 were this kind: right owner, right name, species relation.
- Rule from now on: a TEACH frame whose relation is listed in the gold relation's `narrower` list (table v1/v2) counts as a hit, not a wrong save. Panel specs from 261b on also put the species word used in the turn into `relation_aliases` for pet gold.
- 261's registered FAIL stays FAIL. This rule is not applied to 261 retroactively.
- Open check: "What is my pet?" must find facts stored as dog/cat. This is a separate question, not part of 261b.

## Ruling 2: 261's one follow-up is 261b, the mixed-case span guard
- The real meaning errors left in 261 (category level): 2 typo leaks, where a lowercase typo word got glued onto a capitalised name inside a stored subject or value, and 1 "so ..." check with no "?". The checker approved all 3.
- 261b adds one mechanical rule after the checker. A TEACH frame whose subject or value mixes a Capitalised word with a lowercase non-particle word is held back as UNSURE. Particles are de, da, van, von, der, la, le, del, di, bin and al. All-lowercase spans (lowercase chat) and all-capitalised spans pass. Whole relation-word values such as jobs are exempt, by table value_kind.
- Registered on a fresh blind panel, earpanel261b. earpanel261 was read by the director for this diagnosis, so it is spent for 261b.
- Plural-relative recall (R10, the ear) and the "so" check are later work, not this experiment.
