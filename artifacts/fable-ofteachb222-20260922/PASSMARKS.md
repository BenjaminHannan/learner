# PASSMARKS — Exp 222 "IS A R OF" ONLY FOR ONE-OF-MANY PERSON RELATIONS (Muse)

One change on loop215: indefinite "X is a/an R of Y." rewrites to "Y's R
is X." only when R (canonical/alias, case-insensitive) is a
value_kind=person + cardinality=multi entry of
artifacts/claude-relationtable-20260922/relation_table_v1.json; every
other R takes the unchanged 138i base path. "The" teaches and the
question rewrite are exactly as in 215.

## B1 — director cases (fresh loop per scenario; replies + FACT triples)

- C013 teach "Kip Dune is a citizen of Peru." ->
  reply "Saved: Kip Dune's country of citizenship is Peru.",
  triple (Kip Dune, country_of_citizenship, Peru); ask
  "What country is Kip Dune a citizen of?" ->
  reply "Kip Dune's country of citizenship is Peru."
  (byte-identical to loop138i; 215 instead saves (Peru, citizen, Kip Dune)
  and fails the question).
- Lima teach "Lima is a city of Peru." -> no FACT stored; reply and the
  "Where does Peru live?" reply byte-identical to loop138i
  (215 instead saves (Peru, city, Lima) and answers "Peru's city is Lima.").
- Friend pair "Nell is a friend of Otto." + "Bram is a friend of Otto."
  -> replies "Saved: Otto's friend is Nell." /
  "Saved: Otto's friend is Bram. (I also have Nell.)"; ask
  "Who is Otto's friend?" -> "Otto's friend is Nell and Bram."
  (byte-identical to 215, incl. triples).
- Daughter pair "Ines is a daughter of Rafe." + "Cora is a daughter of
  Rafe." -> replies "Saved: Rafe's daughter is Ines." /
  "Saved: Rafe's daughter is Cora. (I also have Ines.)"; ask
  "Who is Rafe's daughter?" -> "Rafe's daughter is Ines and Cora."
  (byte-identical to 215, incl. triples).
- "The" forms ("Oslo is the capital of Norway.",
  "Juno is the sister of Pell.") save and answer exactly as on 215.

## B2 — fresh held-out set (cases222-b1b2.json, fictional names only)

- 20 indefinite person/multi sentences (M01-M20: friend, daughter, son,
  sister, brother, cousin, aunt[an], uncle[an], child, sibling, colleague,
  neighbour, rival, apprentice[an], grandchild, parent, grandson,
  granddaughter, grandmother, grandfather): replies + FACT triples
  byte-identical to loop215; each stores (Y, R, X), e.g.
  ('Otto Marlowe', 'friend', 'Wren Hallis').
- 20 indefinite other-noun sentences (O01-O20: citizen, city, town,
  country, region, part, kind, member, resident, native, fan, student +
  single person relations mother, father, spouse, wife, husband, boss,
  teacher, mentor): replies + FACT triples byte-identical to loop138i.
- 0 junk writes (no stored relation ending in `_of`, no `city`/`citizen`
  writes) on 222 across all 40.

## B3 — frozen suites (one suite at a time)

- `python -B scripts/fable_suitediff.py --agent
  scripts/fable_loop222_agent.py --config
  artifacts/fable-ofteachb222-20260922/loop222-config.json --base 138i
  --out <dir> --only <rt136|rt143|sessions152|bench>`
- Moved case set must equal exp 215's registered moved set MINUS C013,
  case by case: rt136 C019-C031 only (C013 no longer moves); rt143 J8 K9
  O3; sessions152 0 moves; bench edit200 exactly the 25 -fwd rows;
  bench other splits 0 moves; marks123 fast subset per-case identical
  except the bench rows.
- Every moved case's detail line read by hand (the tool labels a lost
  correct save "reply-only", so verdicts checked, not just labels).
- 0 new WRONG / WRONG-WRITE / junk writes vs 138i outside that set.

## B4 — sleep smoke

- `python -B scripts/fable_sleepsmoke206.py --agent
  scripts/fable_loop222_agent.py --config
  artifacts/fable-ofteachb222-20260922/loop222-config.json --root <dir>
  --label <label>` passes the same marks as on 138i (sleep fires,
  maternal_grandmother installed, 5/5 new-people probes, broken-chain
  abstains, 0 taught facts overwritten).

## B5 — 0 new wrong writes

- 0 new WRONG / WRONG-WRITE / junk writes on redteam136, redteam143,
  sessions152, scripts/fable_marks123_all.py vs the base agent; bench
  (the base agent's driver) 0 new wrong.

Verdict PASS iff B1-B5 all pass; any miss is FAIL with one diagnosis
note. Each run < 25 min Mac CPU; one suite at a time.
