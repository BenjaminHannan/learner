Labeling the 1B’s drafts — running the sealed teacher check.
Sealed files verified — now splitting DEV and labeling candidates.
Split confirmed — now labeling half A with both candidate methods.
Half A favors one method — now checking it once on half B.
Check complete — now copying results into the worktree.
Files staged — final verification before reporting.
FAIL — 63 of 79 agree on half B (needs 85%), kappa 0.603

k1e-teacher-c: one labeller change chosen on half A, checked once on half B. Script `scripts/claude_k1e_teacher_c.py` read from origin/main, never edited. Run from temp dir via `uv run --offline --no-project --python 3.12 python -B` (stdlib only). Key only in `~/.config/openrouter/key`, read by script; no output contains `sk-or`. Additive only; nothing written to repo-root `notebook/`.

Sealed inputs (origin/main):
- `sha256sum -c artifacts/claude-k1e-20260926/SEAL-teacher-c.sha256.txt` -> 7 lines OK
- `selftest` -> `k1e teacher-c selftest 3/3 ok`
- `split --packet D/packet_dev.jsonl --key D/key_dev.json --out O` -> `{"chats": 40, "chats_A": 20, "lines_A": 78, "lines_B": 79}`, `cmp O/packet_A.jsonl teacher-c-split/packet_A.jsonl` silent, same for B
- D = `artifacts/claude-k1e-20260926/dev`, O = `artifacts/claude-k1e-20260926/teacher-c` (in tmp)

Printed JSON lines (real run, from console log):
- `{"how": "high", "lines": 78, "labelled": 78, "unparsed": 0, "calls": 8, "useful_yes": 38, "cost_usd": 0.0066}`
- `{"how": "vote3", "lines": 78, "labelled": 78, "unparsed": 0, "calls": 25, "useful_yes": 37, "cost_usd": 0.0115}`
- `{"compared": 78, "teacher_useful": 38, "opus_useful": 25, "both_useful": 23, "agree": 61, "kappa": 0.56, "passes_label_rule": false}`
- `{"compared": 78, "teacher_useful": 37, "opus_useful": 25, "both_useful": 22, "agree": 60, "kappa": 0.53, "passes_label_rule": false}`
- `{"chosen": "high", "A_high": {"compared": 78, "teacher_useful": 38, "opus_useful": 25, "both_useful": 23, "agree": 61, "kappa": 0.56, "passes_label_rule": false}, "A_vote3": {"compared": 78, "teacher_useful": 37, "opus_useful": 25, "both_useful": 22, "agree": 60, "kappa": 0.53, "passes_label_rule": false}}`
- C = `high`, only that one labelled on B:
- `{"how": "high", "lines": 79, "labelled": 79, "unparsed": 0, "calls": 8, "useful_yes": 43, "cost_usd": 0.0071}`
- `{"compared": 79, "teacher_useful": 43, "opus_useful": 31, "both_useful": 29, "agree": 63, "kappa": 0.603, "passes_label_rule": false}`
- `{"chosen": "high", "lines_B": 79, "compared": 79, "teacher_useful": 43, "opus_useful": 31, "both_useful": 29, "agree": 63, "kappa": 0.603, "passes_label_rule": false, "verdict": "FAIL"}`

Counts:
- DEV total 157 = 78 A + 79 B, 40 chats = 20 A + 20 B
- Phase 1 reference: 121 of 157 (77%, needs 85%)
- A_high: 61 of 78 agree, A_vote3: 60 of 78 agree -> chosen high
- B_high: 63 of 79 agree (79%), 29 both_useful, teacher 43 useful vs judges 31
- Labels: 78 + 78 + 79 = 235 lines; calls 8 + 25 + 8 = 41; cost 0.0066 + 0.0115 + 0.0071 = 0.0252 USD
- GPU: 0

Copied to worktree:
- `artifacts/claude-k1e-20260926/teacher-c/` (6 files: packet_A.jsonl 78, packet_B.jsonl 79, chosen.txt `high`, A_high/labels.jsonl 78, A_vote3/labels.jsonl 78, B_high/labels.jsonl 79; cmp OK vs tmp)
- `artifacts/claude-k1e-20260926/teacher-c-log.txt` (107 lines, console log, no key)
