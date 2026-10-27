# 119g director deviations

## Seal scope (11:01)
SEAL.sha256.txt covers PASSMARKS.md only. The agent printed the code hashes right after sealing; the director re-hashed at 11:01 and they match (model 38ba94b9, train 062eab5a, score 0feefe2e, smoke 9067d69e, wave bat f5e1cd82, scp119g.txt 06e63112).

## Note on gate numbers (11:01)
Pointer temperatures are fitted on CAL with the UNCONDITIONED queries (the 47 rule, unchanged), which training never uses alone. Spans are decoded by argmax (S47._span), so the registered ungated marks M1-M3 are unaffected; only confidence-gated numbers (W2 writes, gate47, M4) depend on these temperatures and should be read as descriptive for 119g.

## Staging (11:01)
The PC folder was mirrored from C:\Users\benja\ears119f\repo (scripts, panels, data, artifacts the 119f wave needed), then the scp119g.txt files were copied on top. Checked on the PC: panel94b 9ca7035c, wave bat f5e1cd82, scorer 0feefe2e, imports OK, 119f checkpoints present, GPU idle.

## D1 scorer-only fix (11:04), no rule change
First launch 11:02:35 crashed at step 0 (re-scoring the OLD 119f checkpoints), before any 119g training or score: `TypeError: string indices must be integers` in triples_of_row (log kept: wave119g-crash1.log). Cause: score_panel_multi passes decode_all_k1's flat list (one parse dict per row) to score_k, which iterates each row as a list of frames. score47g needs the flat form, so the fix applies inside score_panel_multi only.
Fix = new file scripts/fable_ears119g_score_d1.py (sha 60660e39), which imports the sealed scorer unchanged and, during score_panel_multi only, wraps each K=1 parse as a one-frame list:
```
def _k1_rows(*a, **k):
    return [[p] for p in _orig_k1(*a, **k)]
```
Wave = artifacts/fable-ears119g-20260922/wave119g_d1.bat (sha 241eea4b): the sealed bat with `fable_ears119g_score.py` → `fable_ears119g_score_d1.py` on the six scorer lines; nothing else changed (diff shown in the board entry). Relaunched 11:04:02. The agent's sealed files are untouched.
