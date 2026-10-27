# Canonical-operator variant `hintwarm` — the supporting-line hint as a start-up aid only

Written 2026-09-20 EDT, before any `hintwarm` run. Drafted by the build agent from Ben's
brief. **Review and amend before running `freeze`: `freeze` hashes this file and
`check_manifest` re-verifies the hash before every worker and every wave.**

## The question

`balance`/v3r, which carry the 0.5 x supporting-line attention loss on every update, learn
the lookup reliably. `e0`, which is the same recipe with that term deleted from update 0,
learns perfectly on seed 0 and never starts on seeds 1 and 2 (~8% one-hop after 6,000
updates). That is consistent with two very different stories:

* **Start-up story.** The attention term is only needed to find the right fact among ~45
  lines / ~300 tokens in the first place. Once the model can find it, answer feedback
  alone is enough to keep and sharpen the behaviour.
* **Maintenance story.** The attention term is load-bearing throughout, and removing it at
  any point degrades the lookup.

`hintwarm` separates them. If a hint for the first H updates and nothing afterwards
reaches the same ten cutoffs as `balance`/v3r, the start-up story is right and the
supporting-line supervision is a scaffold, not a crutch.

## The ONE change versus the base recipe

The supporting-line attention term has weight **0.5 for updates < H and exactly 0 from H
on**. `--hint-updates H`, default **H = 1000** of 6,000. Hard switch, no ramp, no decay.

* For step < H the loss is byte-for-byte v3r's: `answer CE + 0.5 * supporting-line
  attention`, canonical/monolithic weighted .75/.25.
* For step >= H it is byte-for-byte `e0`'s: pure answer cross-entropy at the same .75/.25.
  The attention trace is not even computed after H, so no evidence target is read.
* Gold intermediate entities still build the LINK and terminal records throughout, exactly
  as in v3r, `balance` and `e0`.

Train-batch accuracy (canonical overall, one-hop, LINK, monolithic) is logged every 250
updates so the moment of the switch is visible in the seed logs.

## Base recipe

v3r, as `e0` and `marg` are built: the generator's own two one-hop questions per visit, 2
LINK + 2 terminal + 2 monolithic records, `random.Random(1101)` world stream consumed
identically, v3r lr decay (warmup to 1e-3 over 100 steps, flat to update 4,000, linear to
1e-4 at 6,000), 6,000 updates, 16 visits per update, `CanonicalOperator` /
`A.new_model(seed)` / AdamW(1e-3, .9/.99, 1e-8, wd .1) / grad clip 1.0, the semantic
overlap `forbidden` check, final-checkpoint-only scoring on the same ten panels.

`--balance` (relation-balanced fresh one-hop records) is **OFF**: fresh seeds 3-5 showed
the rebalancing is not a net improvement — it degrades 12-person one-hop in seeds that
were perfect without it. The flag and its value are recorded in the launch manifest.

Extra randomness, if `--balance` is set, comes from
`random.Random("fable-startup-hintwarm:<seed>")`. **Deviation worth noting:** that
namespace differs from `balance`'s `fable-variant-balance:<seed>`, so a `--balance`
`hintwarm` run is not record-for-record paired with the `balance` run. With `--balance`
off (the default) there is no extra randomness at all and the records are identical to
`e0`'s, so `hintwarm` vs `e0` IS an exactly paired comparison.

## Label-free? No, and it does not claim to be

`hintwarm` uses the generator's supporting-line annotation (`row.gold`) for the first H
updates and its gold intermediate entities throughout. It is a claim about *when* evidence
supervision is needed, not a claim that the model learns without it.

## Pass marks

Astra's ten R cutoffs, **every seed separately, no averaging**:

| cells | cutoff (of 512) |
| --- | --- |
| c1, c2, p12-1, p12-2 | >= 487 |
| c3, c4, c5, c6, p12-3, s3 | >= 461 |

plus the R gate as the report script computes it: every panel/side native LINK count >=
487, every terminal-oracle count >= 487, and s3 native joint >= 461. Incomplete = failed.
Wave 1 is seeds 0, 1, 2; a later wave is reported the same way and never averaged with
wave 1.

Secondary reading (descriptive, not a pass mark): the 250-update logs at steps H-250 and
H+250. A collapse at the switch falsifies the start-up story even if the cutoffs are met.

## Fable's predictions

## Fable's predictions (2026-09-20 ~11:05 EDT, before any run)
Context (shown): with the hint on throughout (v3r), train-batch canonical accuracy at update 2,000 was 0.76 / 0.95 / 1.00 for seeds 0/1/2, so at the switch point (update 1,000) the slow seeds have probably not finished learning. e0 (no hint ever): seed 0 perfect, seeds 1,2 never start. hintwarm vs e0 is an exactly paired comparison (same records batch for batch).
Predictions: seeds 1 and 2 — the two that never started in e0 — DO start under hintwarm and at least one of them passes all ten R cutoffs; I give ~50% that all three seeds pass. If a seed's accuracy falls after the switch and never recovers, the hint is needed for longer than 1,000 updates, not only to start.
