# PASSMARKS — Exp 138i: MERGE LAYER B PART 2 onto loop138h (Muse)

Agent: `scripts/fable_loop138i_agent.py` (+ `scripts/fable_fix138i_*.py`
drivers). Config: `artifacts/fable-agent138i-20260922/loop138i-config.json`.
Base: loop138h (no 154c/172/171/167d/154d/174/173b/170 — verified in its MRO).
Port order (outside-in, per `design/v3/30-modes/138h-portplan-layer-b-muse.md`
collision order): 174 of-chain > 167d verbs (+167) > 173b word-names (over
173) > 172b copula (over 154e multi incl. language) > 171b word-names (over
171); 167e label mouth; 154d yes/no; 170 index installed last. Loop155 stays
OUT (MRO + module scan in every M1 run). G3h-4a "My name is Juno." is a
predicted move: it must now save (173b replaces 173).

## M1 — each piece's own sealed case file on loop138i
Bar: verdict + reply identical to that piece's own agent, except the
cross-piece classes below (all piloted pre-seal; pilot outputs in
scratch138i-pilot/, final code).
- 154e (case154e.jsonl): 76/76 identical. 172b-t1 81/81, 172b-t1c 92/92,
  154d 38/38 identical.
- 172b-t1b: n=9,10,11 move (language re-teach multi-adds French next to
  Spanish under 154e instead of 172's change-prompt; "no." then answers
  both); n=12,16,20,24,28 replies identical to 172-own, stored state carries
  the extra French value from n=9. One class (154e x 172b), 8 rows.
- 171b (+171 T1): 120/122. T1-D12 clarifies with 138-lineage wording
  ("Did you mean ...") — byte-identical to loop138h (lineage). T1-C02
  ("No, Kim's dog is Chen.") multi-adds "(I also have Bruno.)" and answers
  both — 154e dog is allow-listed (predicted 154e x 171b).
- 173b: t1 (vs 173-own) moves F12/F20 (154e sister/brother multi-add),
  F14 (171b MILO clarify, no write), A01-A10/O08-O16 (138-lineage decline /
  name-decline / smalltalk reply forms, byte-identical to loop138h, stored
  [] both); t1c (vs 173b-own) moves C01-C14/O01/O05 reply-FORM only
  (138-lineage mouth; stored [] both sides; byte-identical to loop138h).
  W01-W16/I01-I06 all identical to 173b-own (word-names save).
- 167d: W/S groups 22/22 identical; X01-X10 decline-prefix reply form
  (byte-identical to loop138h, lineage).
- 167e: 33/34; n32 ('blarg nonsense xyz') decline-prefix form
  (byte-identical to loop138h, lineage).
- 174: 39/40; n35 ('The city of Lumen is Brack.') short smalltalk
  "I have no opinions." (byte-identical to loop138h, lineage).
- MRO check every M1 run: no 155 class, no fable_loop155 module.

## M2 — 138h's M1/M2/G3 cases on loop138i
Bar: identical to loop138h except the predicted moves below (piloted).
Part A (vs 138h sealed rows + live): 162b/165/167b all diffs reply-identical
to 138h (lineage). Moves vs 138h, 13 case ids: 154e multi-add — 166c
F12/F20, 166c-B C11, 173-t1 F12/F20 ("(I also have …)" where 138h replaced);
171b lowercase screen (clarify, no write) — 166c F14, 166c-B C06/C08,
166c-C S02/S03/E07/E08/T07/T08, 173-t1b S13 ("You can call me lena."
no longer saves; 173b-own also stores nothing).
Part B: 139e/146d/150b/153/157/158/159 PASS. 137e/158c/168/156b fail-sets
(ids + got) identical to 138h sealed m2-138h. 142: 50 diffs, all pet/song —
25 ask->multi-add (n=52,58,64,70,76,82,88,94,100,106,112,118,124,130,136,142,
148,154,160,166,172,178,184,190,196 + odd mates 53..197 ask-prefix knock-on
from the changed prior state): 154e allow-lists pet+song (widened vs 138h
which has no multi at all).

## G1 — bench under protocol v3 (confirming user), both arms
Bar: 138i-v3 0 new wrong vs loop138h; 138h-v3 == 138h-old (799/800: 1 move
bench132-4hop-162 wrong->abstain, 0 new wrong — mirrors 172b's sealed
P172b.5 deviation on the same item: the confirmed chain breaks on a
pre-existing multi-fact reject). 138i-v3 predicted moves (17, all
correct->abstain except 162 wrong->abstain shared with 138h-v3, 0 new
wrong): multi-valued re-teach keeps both values and asks
("… and …. Which one do you mean?") instead of silently resolving —
new_121_4hop 026/069/079/110/137/162/195; bench132_4hop
022/045/113/142/162/179; edit200 bench65-mquake-033; s2fresh_4hop
031/125/200. Every move reply states only taught values.

## G2 — frozen suites
Bar per-case identical to loop138h except predicted; 0 new WRONG /
WRONG-WRITE / junk writes. redteam136 (145) / redteam143 (124): 0 moves.
sessions152: 1 move, S4-pets-identity n1 ("my dog is biscuit" — 171b
lowercase screen clarifies, no write; 138h saved "biscuit"). marks123
(stock CLI, no confirming user) per-case vs marks138h: p2 B1/B2/B3/B7/B8/F2
OK->BUG with kept-chain finals byte-identical to 172b's sealed marks172b
rows (Spanish/Spanish/English/Spanish/USA/Spanish; B6 keeps Warsaw);
p3-l5z2 99 WRONG + 1 MISS id-set identical to 172b's sealed l5z2 rows;
marks-bench (edit200 100 moves + s2fresh 198 moves) verdict+reply
byte-identical to 172b's sealed marks172b bench rows (400/400); p4 P4-08
("Mira's mother is actually Ana." clarifies — byte-identical to 171b-own);
p3 l2/l5z1 fail per-case identically to 138h (pre-existing); rt110/rt81/q1/
q4/soak/sleep per-case identical; 0 new WRONG/WRONG-WRITE/junk writes.

## G3 — director pairs, fresh loop each (frozen pre-seal, cases138i-g3.json)
Bar: exact replies as below (a,b,c,d,f byte-identical to owning piece's
agent live pre-seal; e composed 167d+154e):
(a) "Sabine works at Acme." => "Saved: Sabine's employer is Acme.";
"Where does Sabine work?" => "Sabine's employer is Acme."
(b) "Bela's sister is Zuri." => "Saved: Bela's sister is Zuri.";
"Is Zuri Bela's sister?" => "Yes, Bela's sister is Zuri."
(c) "Kim's boss is Lee." => "Saved: Kim's boss is Lee.";
"Lee's city is Oslo." => "Saved: Lee's city is Oslo.";
"What is the city of Kim's boss?" => "Kim's boss's city is Oslo."
(d) "My name is Juno." => "Saved: your name is Juno.";
"What is my name?" => "Your name is Juno." (saves: 173b replaces 173)
(e) "Omar speaks Urdu." => "Saved: Omar's language is Urdu.";
"Omar speaks Hindi." => "Saved: Omar's language is Hindi. (I also have Urdu.)";
"What is Omar's language?" => "Omar's language is Urdu and Hindi."
(f) "Kim's boss is Lee." => "Saved: Kim's boss is Lee.";
"No, Kim's boss is Sam, not Lee." => "I can take one fact at a time — could
you split that?" (keeps Lee; byte-identical to 154e-own)

## G4 — 170 index identity on loop138i itself
Bar: S2-fresh 1000 turns, every reply + notebook facts-sha + event count
identical with index on vs off (off arm: FABLE138I_INDEX=off subprocess).

## Common rules
Seal: shasum -a 256 PASSMARKS.md + cases138i-g3.json + agent code + config
> SEAL.sha256.txt BEFORE any registered run. Ledger P138i.n appended before
the run. Fictional names only. Bench = base agent's driver (v3 protocol for
G1; marks123's own bench suite stays stock). Each run < 25 min Mac CPU
(OMP_NUM_THREADS=1 MKL_NUM_THREADS=1, uv offline py3.12); daemon wrappers
use idle_seconds=3600. Heavy suites one at a time. Never write to the
repo-root notebook/. Post-seal code/config/case change => registered FAIL;
driver-only fix reported with diff, affected marks re-run in the open.
