# C1: software controls pass; actual 1B evaluation INCONCLUSIVE

**Shown — software only.** C1 now has **20 passing tests: 10 core and 10 chat**.
The whole retention-isolation software package has **24 passing tests** when the
4 separate reasoner tests are included. The ten core tests passed after PASSMARKS
was committed:
default base bypass, adapter-on parity, unchanged state-dict keys and save/load,
base immutability after adapter optimization, poisoned inactive adapter bypass,
nested and failed calls, concurrent request isolation, expired async scope
rejection, unwrapped shared-parameter freeze validation, and paired loss counting.

Ten chat checks pass with small code-generated CPU fixtures:
exact base and adapter prefill-logit parity, six cached greedy decode steps,
alternating on/off requests, base preservation after a large adapter update,
rejection of a foreign KV cache at the serving entry point, and the live runner's
explicit route/import path. The added checks cover full-tensor prefill-logit
hashing, exact snapshot-file coverage and mutation rejection, committed-manifest
byte parity, loaded runtime-code hashes, strict adapter A/B-only keys, and
exclusive reply-file creation. Individual test methods combine related controls.
This is not a pretrained language model and these are not 1B accuracy scores.

Logs: `../implementation/software-tests.log`, `software-tests.log` (first three
cached tests), and `software-tests-import-fix.log` (four checks after fixing a
stale module import left by the move into the artifact directory).
The same prescribed mechanism and marks were kept; the extra import test caught
an executable packaging issue. Initial run PID/start details are in
`../SOFTWARE-RUN-NOTE.md` and `../software-tests.json`.
The repair run and its UTC/PID/machine record are in `SOFTWARE-REPAIR-RUN-NOTE.md`.
The first repair fixture run had one `/var` versus `/private/var` test setup
error (8/9); the corrected retry passed 9/9, and the final targeted
full-prefill-logits rerun passed **10/10** in
`software-repair-tests-full-prefill.log`. No pretrained-model or GPU run was made.

**Untested / INCONCLUSIVE — MiniCPM5-1B.** The required original base revision was
not found in the checked local model roots. Only altered merged models and the
saved dl-5 adapters were available. No replacement model, download, GPU inference,
seven-night run or newly trained switch was used. No dl-9 result is claimed.
The checked locations and fixture caveats are in `STATUS.md`.

**Suggested.** The request-scoped bypass is a useful serving component for a
successful routing experiment: the base really runs when the adapter is off.
The live `retention_chat.py` CLI is supplied for later review with the actual
base and a frozen evaluation manifest, and is unvalidated on that base. It uses
caller task IDs and does not establish automatic prompt routing or F1–F5.

**Untested.** Broad chat retention, new-skill learning, reworded/blended questions,
any proposed replacement of the project's deployed sleep pipeline, and H-B.
