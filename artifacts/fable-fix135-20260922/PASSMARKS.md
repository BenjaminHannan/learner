# Exp 135 PASSMARKS (sealed BEFORE the registered run)

Base loop: loop129b (scripts/fable_loop129b_agent.py + artifacts/fable-fix129-20260922/loop129b-config.json).
Change: scripts/fable_fix135_office.py mixin (officeholder catch-all guard) + scripts/fable_loop135_agent.py.

- K1 fresh probe artifacts/fable-fix135-20260922/k1-office-probe.jsonl (52 sentences: 30 non-office,
  18 office-table, 4 monarch-informational), sha256 below. Bar: 0 writes on loop135 for the 30
  non-office heads; all 18 office-table sentences byte-identical replies AND identical fact-write
  counts on loop135 vs loop129b. The 4 monarch rows are observe-only (king/queen/monarch/emperor
  are NOT in the bench73/bench92 code tables, so the registered mechanical rule refuses them).
- K2 bench (fable_loop129b_bench run_item/summarize by import, loop135 daemon swapped in, outputs
  in this dir only): Fable-Edit-200 150 answers + 50 expected abstains, 0 wrong; old_s2fresh_4hop
  >= 157 correct, 0 wrong; new_121_4hop >= 136 correct, <= 1 wrong. Per-item identical to loop129b
  expected; any difference explained.
- K3 marks123 all suites (scripts/fable_marks123_all.py --agent scripts/fable_loop135_agent.py
  --config artifacts/fable-fix135-20260922/loop135-config.json --out ... --workers 4, plus the
  same for loop129b into this dir): every suite verdict identical loop135 vs loop129b.
- K4 total registered compute < 25 min Mac CPU wall-clock (OMP_NUM_THREADS=1 MKL_NUM_THREADS=1,
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B).

Ledger: predictions P135.1-P135.7 appended to artifacts/fable-predictions-ledger.md before the run;
outcomes appended as a new line after the run.

case-file sha256:
97859e60b4a9f0e097869045d06cd06a6d8962929d98dda9d8c094c77d3d1f63  k1-office-probe.jsonl
