# PASSMARKS — own-M0: conversational-mouth training pairs (builder, CPU only)

Sealed BEFORE the registered run. Scripts:
scripts/claude_own_m0_build.py, scripts/claude_own_m0_check.py.
No TEST-ONLY panel is opened anywhere in this experiment. No model is
trained; no downloads; CPU only.

## What gets built
- artifacts/claude-own-m0-20260923/train.jsonl: 20,000 rows
  (OK 7000, SAVED 3000, UNKNOWN 3000, ABSTAIN 2000, CLARIFY-tag 1500,
  WHOSE-tag 1000 with status CLARIFY, FORGOT 2500).
- artifacts/claude-own-m0-20260923/dev.jsonl: 1,000 rows
  (OK 350, SAVED 150, UNKNOWN 150, ABSTAIN 100, CLARIFY-tag 100,
  WHOSE-tag 50, FORGOT 100).
- Row: {"record" (talker120-style + tag-aware fields), "user_turn",
  "tag", "reply"}. Reply holds slot tokens <S1>/<V1>/<R1> only, no
  literal names. Tags: ANSWER, ACK_SAVE, ABSTAIN, CLARIFY, FORGOT_ACK,
  WHOSE (our/we turns ask whose; status CLARIFY).
- Name pools: 64 train owners + 40 dev owners + 64/40 person values +
  24/16 places, all fictional, all asserted disjoint from each other and
  from the 96 talker120 names (train + heldout, names only). Dev combos
  are disjoint from train combos by construction (disjoint pools).
- 5 replies per record combo; templates assigned round-robin per
  template list (uniform shares). UNKNOWN/ABSTAIN/FORGOT draw
  person/place/thing kinds in strict rotation.
- Filter (check.py, code only): R1 required slots; R2 no extra slots;
  R3 no literal pool-name leak + capitalised-word allowlist; R4 status
  wording (UNKNOWN/ABSTAIN hedge + no value slot; FORGOT forget-lemma +
  never restates value; SAVED save-phrase + never infer-words; CLARIFY /
  WHOSE question-mark + clarify/whose wording). Failing rows are dropped
  and counted per rule.

## Marks (integers; all must hold on the registered output)
| Mark | Bar | Predicted |
|---|---|---|
| Pm0.1: rows failing a fresh re-run of the check on every row | 0 train, 0 dev | 0 / 0 |
| Pm0.2: max share of any single reply string within a status | <= 3% every status, train and dev | train <= 2.5%, dev <= 3.00% |
| Pm0.3: distinct reply templates per status, slots kept | >= 40 every status, train and dev | train 48..92, dev 48..92 |
| Pm0.4: dev name pool ∩ train name pool | 0 | 0 |
| Pm0.5: crashes | 0 (exit 0) | 0 |

Predicted drops by filter: 0 per rule (every template passes the
selftest on fitting rows; pilot confirms).
Also reported (no bar): rows per status, rows per tag, drops per rule,
dev∩train combo overlap (predicted 0), 10 random train rows quoted.

## Proved wrong / FAIL conditions
Any mark missed = registered FAIL with one diagnosis note. Any change
to a sealed file after the seal = registered FAIL (never re-seal).
