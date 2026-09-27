# Cached-gradient projection: untested alternative

2026-09-27. Read-only design review while AR1 finishes. This is not a registered experiment and no projection model was constructed, trained or scored.

The idea is to keep the existing four-context dense model and full-replay schedule, and project its actual AdamW weight displacement away from a span of old gradients. Those gradients would come only from already-scheduled practice; there would be no extra examples, old model copies, task label at inference or additional trainable parameters. A temporary optimizer buffer is still a real memory cost and must be reported.

The initially considered 64 loss-gradient vectors per old kind would hold up to 128 vectors of 1,646,750 float32 values: about 804 MiB before temporary buffers. With vectors as rows of G, the proposed displacement is d minus G.T @ pinv(G @ G.T) @ G @ d. It would constrain new-kind updates and cross-kind replay. Neither that size nor its numerical cutoff has been registered.

**Suggested, not shown:** this may reduce local interference. **Untested:** whether it preserves exact own-stop grid accuracy, lets mazes learn, or beats AR1. There are substantive reasons not to launch twelve trajectories of this formulation yet:

- Cached batch-loss gradients can become stale. Near mastery, small or highly correlated gradients may be uninformative; normalizing them can amplify noise.
- A nullspace constraint blocks both harmful and helpful movement along those directions. It may interfere with replay's repair of an old skill.
- Exact orthogonality only addresses a local approximation at the parameters where the gradients were measured. Nonlinear drift can still erase old behavior.
- Matrix products, rank thresholds, optimizer moments and decoupled weight decay all matter. Scaling raw gradients is insufficient to control actual AdamW movement.

Published work motivates this family, but not this particular construction. [Orthogonal Gradient Descent](https://proceedings.mlr.press/v108/farajtabar20a.html) protects earlier network outputs through gradient projection. [Gradient Projection Memory](https://arxiv.org/abs/2103.09762) derives subspaces from network activations using SVD. A span of recent batch-loss gradients is not a replication of either method.

A reviewer suggested eight gradients per kind (about 100.5 MiB total) as a bounded software design if the idea is revisited. That reduces cost and coverage; it is not an accuracy prediction or a selected next experiment. The [learned controller draft](NEXT-CONTROLLER-DRAFT.md) remains a different, untested approach. Any future run needs its own immutable, pushed PASSMARKS before software tests or training.
