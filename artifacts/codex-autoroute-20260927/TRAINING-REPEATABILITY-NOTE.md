# Training repeatability observation

Recorded during the first paired seed, before its candidate B/C scores. The two
seed-41 runs have identical software commit, source hashes, panel hash, Torch
version, MPS device, float32 precision and CPU-thread setting. Both follow the
same seeded data and update path throughout A; the candidate replay change only
begins in B. Nonetheless their logged A losses diverge:

| A update | baseline | late_replay |
| ---: | ---: | ---: |
| 100 | 1.7374922037124634 | 1.737492322921753 |
| 200 | 1.3365507125854492 | 1.336580753326416 |
| 300 | 1.4807687997817993 | 1.4791768789291382 |
| 600 | 1.029774785041809 | 0.8804333806037903 |

**Shown:** identical registered seeds do not produce bitwise-identical training
trajectories in this execution. **Suggested:** small numerical differences in
MPS training grow through subsequent updates. The specific kernel/cause was not
isolated, so that explanation remains an inference. No repeat training or
optimizer/device change was introduced to diagnose or remove it mid-experiment.

The registered comparison is still six paired seeds under the same software and
device; it did not require bitwise-equal A training. Report A scores for each arm
separately and do not attribute any pre-intervention difference to replay timing.
The exact save/reload and request-invariance requirements for inference remain
binding. The final recount must still reproduce every saved C prediction and
stop probability from the final checkpoint; training variability does not waive
that check or change any pass mark.
