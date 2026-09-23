# PASSMARKS — Experiment 134: port loop117 fixes onto loop121 (2026-09-22)

Port, not new science. `scripts/fable_loop134_agent.py` (new, prefix-owned)
defines loop134 = loop121 + the three loop117 fixes re-expressed as small
mixin classes layered on the Loop121 classes (MRO explicit in the module
docstring): (1) F5 please-forget space in `_parse_forget`
(`"forget " + t[m.end(1):]`); (2) M5 shouted-possessive split via the
identical runtime `fable_agent_loop._APOS = r"['\u2019][sS]\b\s*"` override
(no file edited; stored relation keys unchanged); (3) underscore-leak fix
rendering `_` as ` ` in the final English sentence only. Loop121 teach
coverage and the loop113b question side are untouched. No existing file is
edited.

Pre-seal dev evidence (not registered): `--once`/mailbox battery shows
"Please forget Mira city" -> "Forgotten: Mira's city." with the fresh value
answered after (F5), "WHO IS MIRA'S CITY?" answered not clarified (M5),
"Saved:" replies with spaces not underscores, and identical replies to
loop121 on employer/child teaches and the packed-fact refusal.

Registered runs (Mac CPU, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch
--with numpy python -B ...`):
  scripts/fable_marks123_all.py --agent scripts/fable_loop134_agent.py
    --config artifacts/fable-loop134-20260922/loop134-config.json
    --out artifacts/fable-loop134-20260922/marks134 --workers 4
  same runner with --agent scripts/fable_loop121_agent.py
    --config artifacts/fable-bench121-20260922/loop121-config.json
    --out artifacts/fable-loop134-20260922/marks121 --workers 4
  scripts/fable_bench121_run.py by import with daemon class/config swapped
    (loop134 rows + loop121 re-run rows into
    artifacts/fable-loop134-20260922/; sealed 121 rows read-only, never
    overwritten)

| Mark | Pass condition |
|---|---|
| M1 marks123, q1+q4 | q1 PASS (F5+M5 both OK) and q4 PASS (0 underscore leaks), as on loop117 |
| M1 marks123, rest | every other suite verdict identical to loop121 on the same runner (diffed case-by-case; any reply change outside q1/q4 items reported verbatim) |
| M1 marks123, rt81 | gated on wrong writes only: bug == 0 (UNCLEAR wording-drift recorded, not gated, per the exp-123 H1/H2 precedent) |
| M2 bench121 | per-item verdicts identical to loop121: new split 136 correct / 63 abstain / 1 wrong, old split 157 / 43 / 0 |
| M3 Fable-Edit | marks123 bench suite split fable_edit_200: n == 200 and wrong == 0 |
| M4 time | the loop134 marks123 wave < 25 min wall-clock Mac CPU (--workers 4; OMP_NUM_THREADS=1) |

A registered FAIL is recorded as FAIL, never re-run into a pass. Every
seed/case is reported, never averaged. Claims never exceed evidence.
