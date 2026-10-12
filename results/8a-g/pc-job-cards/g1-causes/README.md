# G1 follow-ups: D and T-P (12 Oct 2026)

These come from thread "Why G1 didn't scale: Fable and Opus". The ranked causes and sealed marks are in
`/mnt/project-files/whole-model-roadmap/reviews/G1-OTHER-CAUSES-RANKED-2026-10-12.md` (section 3). The Whole-model roadmap thread owns the
PC queue and installs these through the Mac.

Ben's call (through the coordinator, about 10:50 AM ET 10-12): "but i don't want the g1 tests right". The default the roadmap applied:
- **D:** yes.
- **T-P:** yes, after the talker runs.
- **T-C:** dropped. It comes back only if D points to the web rows.
- **No new G1 seeds.**

| piece | what | where it runs | files |
|---|---|---|---|
| **D** | Free, read-only measurements on G1's saved 3M/10M s400 B2 weights: an error ledger, oracle-mode rescoring, a 10M block knockout, per-term teacher-forced loss and gold log-likelihood per family. It applies sealed rules R1 to R3. | On the Mac CPU (preferred, about 3 h, estimated), or on the PC as `cmd:` insert 47-g1diag (GPU, minutes) | `d/` (README has both routes) |
| **T-P** | 3M s400, exactly G1's 3M B2 plus `self_prog: 8`. The model samples its own calculator programs for no-program rows with integer answers and trains on the shortest one the calculator confirms. | PC, insert `46-tp.txt` (queue 8aTP, src-tp), after 40-g2c10s and before B3 group 1 | `tp/` |

Install on the PC: copy one folder's files to a folder on the PC, then run `powershell -ExecutionPolicy Bypass -File install_tp.ps1`
(or `install_d.ps1`). Each script checks src-8ag's pinned hashes (caps.py 3DA2DFBB...5F78 and the others). It runs its CPU check on the CPU
and writes the insert only when everything passes. It deletes nothing and never touches G1's results, pools or checkpoints.

Checked here (cloud CPU, torch 2.14.1, no GPU, no EmbeddingGemma):
- **D:** `g1diag.py --selftest` prints `D SELFTEST OK`, with 0 generate() mismatches. Its pooled-5 equals evalx.eval_all exactly on the fake data.
- **T-P:** `tpcheck.py` prints `TP CPU CHECK OK`. With `self_prog` 0, loss, aux and all 101 grads are bit-identical to G1's ledger.py. The model has 3,544,913 trained params, the same as G1, and the band check is ok. The hit picker passes 12 cases, and the teacher-forced replays of hits reproduce the gold answer.
- **Not checked here:** neither .ps1 has been parse-checked on PowerShell, and nothing has run on the real checkpoints or with EmbeddingGemma.
