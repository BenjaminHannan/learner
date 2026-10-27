Yes. For the next experiment, change only the per-example loss to a fixed-ε contamination likelihood with ε = 0.10. Keep the gate, initialization, temperature, optimizer, and thresholds unchanged.

1. Loss

Let q\_i = p\_model(y\_i | x\_i). With N = 60 possible person labels, use

L = -(1/n) Σ\_i log\[(1 - ε) q\_i + ε/60\].

For ε = 0.10:

p\_obs(y\_i) = 0.9 q\_i + 0.1/60.

I would fix ε = 0.10 for this experiment rather than learn it or CV-select it. Twenty episodes is too little data to estimate ε reliably, and a learned ε can absorb ordinary model errors by increasing the claimed noise rate. Choosing ε by the same CV used for the install decision also adds selection bias unless you nest the CV.

After this experiment, if you need unknown noise rates, a preregistered grid such as {0.05, 0.10, 0.20, 0.30} is reasonable, but that should be a separate experiment.

Why this addresses the failure: plain NLL has

ℓ = -log q,  
dℓ/dq = -1/q.

At q ≈ 10^-12, the loss is about 27.6 and the derivative magnitude is about 10^12 before accounting for the clamp. One contradictory episode can therefore exert enormous pressure on φ.

With the mixture,

ℓ = -log\[(1-ε)q + ε/60\],

so even at q = 0,

ℓ\_max = -log(0.1/60) = log(600) ≈ 6.40,

and

|dℓ/dq| ≤ 60(1-ε)/ε = 540.

That is the important change: impossible-looking labels become bounded outliers instead of dominating the fit.

Because your simulator specifically chooses a uniformly random other person, the mathematically exact corruption model would use ε(1-q)/(N-1) rather than ε/N. The difference at N=60 is tiny; I would use the simpler contamination likelihood first.

2. Keep the gate unchanged

For the one-change experiment, leave both thresholds exactly as they are.

With exactly 5 corrupt labels out of 50, a perfect semantic rule matches 45/50 = 0.90, so the 0.90 requirement is just achievable.

There is one trap: if "10% noise" means independent Bernoulli corruption rather than exactly 5/50, the number corrupted fluctuates. For Binomial(50, 0.10), only about 61.6% of datasets have at most five corruptions. Six corruptions make the maximum possible noisy-label agreement 44/50 = 0.88, so even a perfect learned word must be rejected.

Therefore, for this controlled experiment, inject exactly 2/20 or 5/50 corruptions.

Also, with the unchanged 0.90 gate, 20% and 30% noise cannot normally install even a perfect rule. That is fine for this experiment; treat those as stress tests rather than installation-success conditions.

3. Leave optimization alone

Keep φ = 0, temperature, Adam, and LR unchanged.

The objective is non-convex and there are equivalent optima—for example, identity can occupy different unused stages—but zero initialization is a sensible neutral point because it starts with all 729 chains equally represented.

Changing initialization or temperature now would make a failure impossible to attribute cleanly.

If robust loss fails while exact 729-chain enumeration succeeds, that is strong evidence that optimization, rather than the statistical objective, is the problem.

4. Smallest decisive experiment

Use two paired arms:

A. Current plain NLL.  
B. Robust likelihood, fixed ε = 0.10.

Use exactly the same villages, episodes, corruption locations, and wrong labels in both arms.

Run all three words, 5 seeds, and noise rates 0%, 10%, 20%, 30%, and 100%.

Pre-register these marks:

- 0%: robust arm installs 15/15 and installed words have 1.000 fresh-village semantic accuracy.
- 10%: robust arm correctly installs at least 12/15.
- 20% and 30%: diagnostic only; installation is not required because the unchanged gate makes it structurally difficult/impossible.
- 100%: 0/15 installations.
- Across every condition: zero wrong installations.

Define "installed a wrong word" behaviorally: an installed word that is not semantically equivalent to the intended composition on the preregistered fresh-village evaluation. I would evaluate every start person over multiple fresh villages, not merely inspect the largest φ weights.

One wrong installation = failure of the safety criterion. There is no acceptable percentage.

5. Most likely failure

The robust loss may still prefer a diffuse soft composition that assigns some probability to the contradictory labels.

You would see:

robust training NLL improves substantially,  
but correct-answer probabilities on clean examples cluster around perhaps 0.7–0.89,  
so OOF exact accuracy remains poor because of the hard 0.90 answer threshold.

If hard-chain enumeration simultaneously identifies mother→mother correctly, that would specifically implicate the continuous soft-mixture optimizer.

6. Enumeration is the best scientific control

Yes: enumerate all 729 hard chains.

It is actually a better control than trimmed loss. It removes local optimization, soft-mixture compromise, initialization, and temperature from the experiment. Score every chain with the same corruption likelihood and ask whether the true semantic chain wins by a preregistered likelihood margin or likelihood-ratio criterion.

It will not scale to a large skill bank, so I would not make it the final architecture. But for this toy system it is extremely valuable: if enumeration survives 10% noise and gradient-trained φ does not, you have learned that the problem is optimization/parameterization rather than noisy supervision.

Trimmed loss is a reasonable later ablation, but it hard-codes how many observations to ignore and can make a wrong rule look good by discarding precisely the examples that contradict it. Enumeration is the cleaner scientific control.
