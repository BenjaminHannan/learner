# Experiments 43G (transport base) and 43H (compositional sleep) — pass marks, fixed before any registered run
(Only a throwaway-seed smoke run exists: seed 9999, 200 updates.)

These are the outside reviewer's (GPT) experiments 2 and 3, built to their spec, run as a CONTROL.
Honest label that must travel with every number: the model is GIVEN the six places it may read and two parity facts;
output length is wired in; it cannot carry. It learns which place to read and what to do to the digit.

43G, seeds 4102/4103/4104, registered base data, 12,000 updates:
- T1 fit: every old skill >= 0.99 exact match at each length 4–8, and mean correct-digit probability >= 0.99, all seeds.
- T2 length: every old skill >= 0.90 exact match at length 12 AND at length 16, all seeds.
- T1 fail = failure to fit; T1 pass + T2 fail = failure to extrapolate. Either way 43H is then not interpreted.

43H, same seeds, CARDFOLD from N = 20 and N = 50 clean raw episodes (exp-42 awake log), plain cross-entropy, no augmentation:
- S1 (per N): installed by the fixed gate AND fresh >= 0.80 in 3/3 seeds.
- S2: old skills unchanged and weights-only reload gives identical answers, every run.
- S3 (recorded, not a gate): CARDFOLD at lengths 9–10, 12, 16.

Reading rule:
- T1+T2+S1(20) pass -> "reusing frozen callable skills + a tiny router learns a new composed skill from 20 episodes"
  is shown FOR A HAND-GIVEN ADDRESS VOCABULARY. It is an upper-bound control, not Ben's architecture and not a claim about
  the transformer. Next step would be to replace the given places with LEARNED relative addressing (43D style) and see how
  much of the result survives.
- It says nothing about arithmetic/carry, language, or skills that are not compositions of known skills.
