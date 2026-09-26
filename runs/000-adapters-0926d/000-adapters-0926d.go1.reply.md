Locating those adapters — read-only listings coming up.
SSH to BensPC works. Running the read-only remote listings now.
Remote shell is parsing pipes — quoting fix needed.
Quoting reached PowerShell now — fixing variable escaping.
Quoting cracked. Running full listings.
All three roots listed. Now adapter hashes and folder sizes.
BensPC done. Now the Mac side.
All hashes match. Writing the report.
VERDICT: done — all listings collected read-only, REPORT.md written, nothing else touched.

Marks table (integer counts):
- BensPC files listed, lis319 run root: 14
- BensPC files listed, rd378 nrun root: 14
- BensPC files listed, sleep root: 3
- Total remote files listed: 31
- Unmerged LoRA adapter folders named on BensPC: 2 (lis319 adapter, rd378 adapter, each 94.99 MB with SHA256 recorded)
- Adapter weight SHA256 hashes recorded: 3 (2× adapter_model.safetensors + 1× adapter02c.pt)
- Mac merged-model SHA256 verified matching expected prefixes: 2 of 2 (e688e1b2…, dbcc8db5…)
- *adapter* folders under ~/premonition-models: 0 (only file bm397t-adapter397t.pt, listed with hash)
- Files edited/deleted outside PUSH path: 0; GPU jobs started: 0; TEST-ONLY panels read/tuned/quoted: 0

Every move: ssh benspc PowerShell recursive file listing (depth 3) of the 3 roots; Get-FileHash SHA256 of the 2 adapter safetensors + adapter02c.pt + folder totals; Mac ls -la of both merged dirs; shasum of both model.safetensors + the .pt file; find for *adapter* under premonition-models; created artifacts/claude-adapters-20260926d/REPORT.md (only new file).

Every miss/deviation:
1. OPUS-RULES.txt not found at the given /private/tmp path (scratchpad/briefs/ does not exist in this worktree) — proceeded using the key points restated in the task (additive-only, read-only, no GPU).
2. No *adapter* folder exists under ~/premonition-models, so section 6 reports the one adapter-named .pt file instead — a listing, not extra analysis.
3. Two PowerShell quoting failures before the working recipe (cmd.exe pipe parsing, zsh $ expansion) — remote side effects zero; failing commands never ran.

What it means in plain English: both training runs on BensPC each left a small adapter file (85.54 MB) plus a big merged model file (2,061 MB), and the two adapters are different from each other (different fingerprints). The sleep folder holds a smaller adapter file (15.80 MB). On the Mac, both merged models check out exactly as expected. This report only lists where things are and their fingerprints — it says nothing about which model is better or whether any of them work.
