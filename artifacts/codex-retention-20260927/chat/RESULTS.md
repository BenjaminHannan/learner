# C1: software controls pass; actual 1B evaluation INCONCLUSIVE

**Shown — software only.** Ten core tests passed after PASSMARKS was committed:
default base bypass, adapter-on parity, unchanged state-dict keys and save/load,
base immutability after adapter optimization, poisoned inactive adapter bypass,
nested and failed calls, concurrent request isolation, expired async scope
rejection, unwrapped shared-parameter freeze validation, and paired loss counting.

Four cached-generation checks pass in a small code-generated causal model:
exact base and adapter prefill-logit parity, six cached greedy decode steps,
alternating on/off requests, base preservation after a large adapter update,
rejection of a foreign KV cache at the serving entry point, and the live runner's
explicit route/import path. Individual test methods combine related controls.
This is not a pretrained language model and these are not 1B accuracy scores.

Logs: `../implementation/software-tests.log`, `software-tests.log` (first three
cached tests), and `software-tests-import-fix.log` (four checks after fixing a
stale module import left by the move into the artifact directory).
The same prescribed mechanism and marks were kept; the extra import test caught
an executable packaging issue. Initial run PID/start details are in
`../SOFTWARE-RUN-NOTE.md` and `../software-tests.json`.

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
