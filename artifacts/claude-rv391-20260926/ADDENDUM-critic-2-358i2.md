# rv-391 dev 2, addendum 2: the same probe on the retrained nets (thought-memory thread; written 21:14 UTC by date -u, AFTER seeing the 358i probe numbers, before any 358i2 probe number)

Why: the registered going-back test (rv-391) will run on rsn-358i2's nets, the retrained nets whose loop blocks now
learn (Sleep research, SUSPECT CONFIRMED, c761f8717). The first probe ran on 358i's nets, which were probably
undertrained. A critic reads the net's state, so the verdict that matters for rv-391 is the one on the nets it will
run on. This is the same test on the fixed nets, not a new variant.

What runs: scripts/claude_rv391_critic.py exactly as sealed (SEAL-critic.sha256.txt), with the same training and
practice puzzles, the same settings and the same marks (NOTE-critic-plan.md, "Marks"). The only change is the nets:
rsn-358i2 loop-s1..s4, checked against ../claude-rv390-20260926/NETS-358i2.sha256.txt. No untrained net, since its row
does not depend on the trained nets. Job: handoff/queue/rv391critic2-mac.md (Mac CPU, $0, no GLM). Output:
critic/run-358i2/.

How it is read (fixed now):
- The 358i verdict stands for 358i's nets. The 358i2 verdict is reported beside it, and neither overrides the other.
- rv-391's trigger comes from the 358i2 verdict. GOOD ENOUGH TO USE there means the critic is the trigger. Otherwise
  the time slice (W = 16) stays, and the next plain fix goes to the Thread manager as a proposal: training the
  reasoner on search traces that include its own dead ends and backtracks (Stream of Search, 2404.03683; plan 384b).
- Report only, added after seeing 358i's rows: the critic's AUC within groups of states with the same number of
  written guesses (k). It shows what the critic knows beyond counting. On 358i, p-grids7: 0.535, 0.617, 0.610, 0.703.
