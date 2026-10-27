# 61 — Wiring end-to-end: sleep installs a word, new people are asked (muse)

## Problem

Wire51 wired the real parts (EnglishEars via Qwen bridge, NotebookReasoner,
HardGate46Sleeper, TemplateMouth, NotebookThinker) and its 40-turn replay
scored 12/15 with 0 wrong writes — but two paths never fired. (A) The sleep
install recipe (Exp 46 hard gate) needs ≥ 8 queued word episodes; the script
queued 0 because the Qwen parser rejects "maternal grandmother" before the
reasoner sees it. (B) Teaching a new English word then asking about it was
never shown. This doc designs the session that exercises both.

## Session design (80 turns)

- Turns 1–50: teach mother chains as plain statements ("K01's mother is
  M01."). 20 train triples (kid/mom/gran) + 5 held-out test triples. Test
  chains are taught but never asked about before sleep, so the probes test
  generalisation, not memory.
- Turns 51–70: one "Who is Kxx's maternal grandmother?" per train kid. Each
  resolves its mother→mother chain over taught facts, so the reasoner queues
  one sleep episode per question: 20 episodes of word 0.
- Turns 71–75: small-talk fillers that write nothing (padding so the fixed
  sleep threshold lands after the episodes, before the probes).
- Sleep fires automatically at experience-log size 75 (a number, never a
  judgement). The audit runs; the Exp-46 recipe gates the 20 episodes.
- Turns 76–80: one grandmother question per held-out kid.

FakeEars is a declared stand-in: it emits exactly the action dicts
(`ask` with relations `["maternal_grandmother"]`) EnglishEars would emit on a
correct parse, so sleep and reasoning are exercised with no Qwen dependency.
The same 80 turns are offered to the real EnglishEars iff the bridge answers
within 5 s; otherwise "bridge down" is recorded and the run skipped.

## Three adaptations (all in my file, nothing else edited)

1. **Phased execution.** The loop processes turns 1–75 (sleep fires inside
   `run_until_idle`), the script bridges the installed word, then turns
   76–80 run. One 80-turn session; phasing only orders install-before-probe.
2. **Word bridge.** `HardGate46Sleeper` trains Exp-44 logits and saves a
   checkpoint but never calls `FableReasoner50.load_word`, so the live
   reasoner would abstain forever after an accepted install. The script
   copies the hardened `words.0` ([3][9], keep + 8 skills; R44.RELATIONS and
   R50.CORE8 share the order) into the loop's own reasoner50. Read-only copy
   of audited numbers.
3. **Village-sized probe.** The recipe's fixed 3×64 probe assumes a dense
   Exp-44 village; a live notebook of mother facts has no hop-3 chains. The
   subclass builds best-effort 64 per hop length over (1,2,3), skipping
   lengths with < 4 resolvable (here: 128 = 64 + 64). The install gate —
   robust loss, harden-to-argmax, OOF ≥ 0.80, agreement ≥ 0.90, unchanged,
   reload-identical — is untouched, and "unchanged" stays exact equality.

Seeds 5701–5703 drive the sleeper's gate RNG; the base net is fixed to sealed
base-seed4102.pt (no 5701+ bases exist). Pass marks W1–W6 were sealed before
the wave; outcome: 3/3 attempts, 3/3 accepted (OOF 1.00, agreement 1.00),
5/5 new-people probes every seed, 0 wrong writes, chains verify, ≈ 4 min.

## What it means

Sleep is no longer a path that is "wired but unexercised": a live log of
taught facts produced 20 episodes, the unchanged gate accepted a word, and
the word answered new people correctly the same session. The recipe for
future words is: teach chains, ask the word ≥ 20 times, let sleep fire,
bridge the hardened logits, probe new people.

## What it does not mean

It does not show the assistant learning from raw English: parsing was
bypassed by the stand-in and the bridge was down at run time. It does not
show the gate rejecting a bad word (all three installs were clean accepts;
the reject branch is covered by Exps 45/46). It does not test hop-3
regression (no hop-3 chains existed to probe).
