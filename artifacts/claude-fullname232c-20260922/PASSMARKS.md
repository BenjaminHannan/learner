# 232c PASSMARKS (sealed before I opened the 232c panel)

**The one change on top of 232: complete name-particle handling.**
- Code: `scripts/claude_loop232c_agent.py`. It imports sealed 232 and rebinds 232's `PARTICLES232` and `subject_ok232` at import.
- 228 guard: `install_srcguard228()` runs at import and in the builder, and `SrcGuardMixin228` is first in `Loop232cDaemon`'s bases.
- Config: 232's `artifacts/claude-fullname232-20260922/loop232-config.json`, unchanged.

The new subject rule:
- **Particles:** de da di do dos das del della delle degli van von der den ter ten te le la les du des ben bin ibn bat bint al el abu ap mac y zu.
  - Only between name words.
  - At most 2 in a row ("de la", "van der", "von der", "van den").
- **Name words:** 137 name tokens, which covers O'X, D'X, X-Y and initials. At least 2 name words.
- **Length:** 2–4 tokens in all. The 137 possessive parser refuses longer names, so a longer subject could never be saved.
- **Conjunctions:** and / or / & / with / plus / nor, plus 232's closed non-name words, anywhere in the subject → the turn is not claimed.
- **Guards:** the subject must pass 150 (as in 232) and also 150b (`screen_subject_150b` → "store"). The stack applies 150b to every teach anyway. It rejects only "do" among the particles (it reads "do" as a verb). So "X do Y" names are **not claimed**: they get 138i's reply, and no guard is changed.

Everything else is 232's code: the five verbs, question shapes, guards, value screen, surrogate, refusal mirror, doubt record and pending drop.

**Known limits, predicted misses:**
- names with "do";
- names of 5+ tokens ("Tomas de la Vega Ruiz");
- typed possessive teaches with particle names (out of scope, as in 232).

## Scorer: `scripts/claude_fullname232c_score.py`
**Schema check first** (OPUS-RULES "Panel schema contract"). Any mismatch → `SCHEMA-MISMATCH`, exit 3, VOID. It checks:
- panel fields: exactly id, family, pair, name_words, setup, question, gold, expect, stated_facts, note;
- family ∈ {multi, one, trap, stated_extra} and expect ∈ {ANSWER, ABSTAIN, NO_WRITE};
- pair is "pNN" on multi/one items, with exactly one multi and one one per pair, and null otherwise;
- types; ANSWER items need a gold and a question; trap items have stated_facts == [];
- family counts via `--expect-counts multi=36,one=36,trap=8,stated_extra=4`;
- base138i.jsonl fields: exactly id, base_reply, base_setup_replies, stored, with the same id set as the panel;
- run rows: the same id set as the panel.

**Wrong write** (non-trap items): a stored triple, active or superseded, that matches no `stated_facts` entry.
- Subject and value: equal case-insensitively, with spaces collapsed and trailing periods dropped.
- Relation: equal after this mapping (232's sealed alias map plus extras); anything else is compared as itself (lowercased, spaces → "_").

| Relation word as written | Canonical relation |
|---|---|
| lives in, live in, living in, lives, city, residence, home, home city | city |
| works at, work at, works for, work for, works, work, employer, employed by, workplace | employer |
| speaks, speak, language, languages | language |
| was born in, born in, born, birthplace, place of birth | place_of_birth |
| anything else (sister, dog, boss, …) | itself |

**Trap write** (family trap): any stored triple.

**Right** (items with a question): 232's sealed rule. Gold = the gold for ANSWER items and abstain ("") otherwise. The gold must be in the reply and no other value (stated values, or capitalised setup words not in the question). Items with no question: right = n/a; they are scored on writes only.

**stated_extra:**
- value answer = the reply contains a stated value or another setup name word not in the question. This is the abstain rule.
- saved = the stated fact is stored (reported, not scored).

## Marks
- **M1 (panel, primary A runs):**
  - M1a: 232c wrong writes = 0.
  - M1b: trap-family writes = 0.
  - M1c: 232c multi right ≥ 232c one right − 2.
  - M1d: 232c multi right ≥ 138i multi right + 20.
  - M1e: 0 items right on 138i but not on 232c.
  - M1f: every one-family item's replies byte-identical to 138i.
  - M1g: stated_extra value answers = 0.
- **M2 (dev, dev232c.jsonl, 103 items):**
  - it covers all 34 particles, 4 particle runs, O'/D'/hyphen/initial names, 12 traps (7 conjunction) and 3 stated_extra items;
  - 232c pass ≥ 95% (≥ 98/103);
  - 0 wrong writes and 0 trap writes;
  - predicted misses exactly d232c-007 ("do") and d232c-085 (5 tokens).
  - Extra M2p (particle parity, `claude_fullname232c_parity.py`): 238/280, where the misses are exactly:
    - all 35 "Orrin do Vask" dialogs (not claimed);
    - t27 for ben, y, mac, de la, bint and zu (typed particle possessive);
    - t31 for "Orrin ben Vask" (138i's reply to a declined ";" turn).
- **M3 (frozen suites):**
  - (a) `--base 138i` on rt136, rt143, sessions152 and bench: GATE clean, and the move set identical to 232's registered one (only rt143 K5, reply-only). Any move beyond that is a move against 232.
  - (b) `--base-dir artifacts/claude-fullname232-20260922/registered/suitediff`: sessions152 and bench, 0 moves. (rt136 and rt143 are SKIPPED by the tool's filename search there, so they are covered by (a).)
- **M4:** sleep smoke passes (sleeps ≥ 1, installed ≥ 1, wrong 0, taught 50/50, ow 0).
- **M5:** pooled per-turn median over the panel A+B runs: 232c − 138i ≤ +5 ms.
- **Reruns identical:** A vs B identical on both arms. Otherwise the flake rule applies: run the item alone 5 times and report.

## Registered run (one attempt)
1. Check `uptime`. Verify this seal and the panel seal from the repo root.
2. Panel runs, each in a fresh workdir: 138i A, 232c A, 138i B, 232c B.
3. Score with `--expect-counts multi=36,one=36,trap=8,stated_extra=4 --base-panel artifacts/claude-namepanel232c-20260922/base138i.jsonl`.
4. Dev, parity, M3 (a)+(b), sleep smoke.
5. My own 138i arm is the base for M1d, M1e and M1f. The writer's base138i.jsonl is schema-checked, and its base_reply values are compared with my 138i A run; that comparison is reported only.

## Predictions
- **Panel:** 232c multi right = 36 minus names with "do" and names over 4 tokens (the writer's contract allows 2–4 word names, so 0–2 are expected). 138i multi right = 0.
- 0 wrong writes, 0 trap writes, 0 stated_extra value answers, 0 lost items, one-word replies identical.
- 232c saves the stated fact on stated_extra items when its name is claimable.
