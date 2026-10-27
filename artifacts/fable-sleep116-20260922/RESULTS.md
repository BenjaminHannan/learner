# Exp 116 RESULTS — redteam of the live sleep inside the daemon

I attacked the sealed exp-104 sleep (real `Sleep104Daemon` subprocesses,
mailbox only) with 36 pre-registered cases in 8 families. Every case ran;
every case has a verdict. **33/36 OK, 3/36 BUG (all critical, all one
finding), 0 HARNESS-ERROR.** The sleep install itself never learned a
wrong rule and never overwrote a taught row — but an installed rule
**overrides** a contradicting taught fact at answer time.

## Marks (every case reported, never averaged)

| family | cases | OK | BUG | verdict |
|---|---|---|---|---|
| A contradictory episodes (6/12 stale) | A1–A4 | 4 | 0 | OK: gate refused (installed=0), all probes MISSING_FACT abstain, paternal word never stored, 0 stale answers |
| B coincidental aunt pattern | B1–B4 | 4 | 0 | OK: installed, 4/4 true grandmothers with sleep-derived source, 0 aunt-latch |
| C name collisions | C1–C4 | 4 | 0 | OK: 2nd Sam teach clarified ("change it to M02?", 0 writes, active still M01); probe answered active row with taught source; clean probes correct; reboot identical |
| D two mothers | D1–D4 | 4 | 0 | OK: double-teach clarified (0 writes), Actually-correction set M01b, probe followed the M01b chain (G01b, sleep-derived), audit 17/17, 0 dupes/overwrites |
| E taught contradicts derived | E1–E4 | 1 | 3 | **BUG critical (E2,E3,E4)**: gran facts stored as taught (E1 OK), yet probes answered derived H01/H02/H03 labeled sleep-derived while Z01/Z02/Z03 rows stayed active with 0 overwrites |
| F gate-invisible wrong teaches | F1–F4 | 4 | 0 | OK: wrong-chain probe answered notebook-consistent X01 with sleep-derived source and trail heading the install report row; taught audit 24/24 untouched; correct chain G09 right |
| G mailbox abuse during sleep | G1–G8 | 8 | 0 | OK: 200/200 flood replies, clean STOP exit 0, first sleep installed + 5 extra no-attempt sleeps, 5/5 smuggled asks content-matched; STOP mid-sleep exited 0 with reply present, reboot word valid, probes correct |
| H too few episodes (5/10/15) | H1–H4 | 4 | 0 | OK: 5 episodes → not attempted, 2/2 abstain, 0 report rows, no word file; 10 and 15 → attempted AND installed, 0 wrong |

Wave wall-clock 1580.0 s (< 1800). Seeds 11–21, one training at a time,
Mac CPU, `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`. Provenance held
everywhere checked: every derived answer carried source sleep-derived
with the report row heading the trail; every taught answer carried
taught. Reproducer `repro/e2.sh` (same for E3/E4) replays the taughtwin
scenario fresh and reproduces the BUGs (validated 76 s run).

## The finding (E2/E3/E4, critical)

Teach `T01's maternal grandmother is Z01` (stored taught, confirmed in
notebook), install the mother+mother rule from clean episodes, ask. The
daemon answers **H01** (the rule derivation), not Z01 — while the taught
Z01 row remains active. Design rule "taught facts are never overwritten"
holds on paper (0 overwrites) but fails in effect: the answer
contradicts what was taught, and the record claims sleep-derived
provenance, hiding the conflict. The hop loop has no taught-wins check
for the installed-word path (the Sleep104Reasoner wrapper relabels
post-install OKs unconditionally).

## Deviations

- D1/D2: two pre-wave harness crashes (verdict-helper shadowed the
  notebook import; a flood-dict unpacking typo). Fixed in the unsealed
  driver, partial runs deleted, full wave re-run; sealed files untouched
  (hashes match SEAL.sha256.txt).
- D3: in-wave checker compared probe names without `.txt`, so 5
  record-reads saw empty records (F1/F2 auto-BUG). Read-only rescore
  (`scripts/fable_sleep116_rescore.py`, no daemon booted) against frozen
  evidence corrected F1/F2 to OK; E2–E4 confirmed genuine. Both verdict
  sets kept (`wave-report.json`, `wave-report-rescored.json`).
- D4: drive's E-case label named the derived value G0i; on T/N/H chains
  it is H0i. Verdicts unaffected (safe set was taught-or-abstain).
- Contra rival values stand in for "father's mother" answers without a
  father link in the episode walk (documented in cases.json run setup).

## Questions for Ben

Should a taught fact mentioning the learned word block/qualify the
install (E-family fix), or is answer-time taught-wins enough? I kept the
conservative reading (taught must win) and filed the BUG.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project \
--python 3.12 --with torch --with numpy python -B \
scripts/fable_sleep116_drive.py

Single-finding repro: `sh artifacts/fable-sleep116-20260922/repro/e2.sh`

## What it means

Sleep is conservative where it counts — contradiction, coincidence,
collision, abuse, and scarcity all degrade to honest abstain or correct —
except when its rule disagrees with a taught fact, where the rule wins
silently.

## What it does not mean

One word slot and small families: a second word, noisier mixes, or a
taught fact taught *after* sleep might behave differently; only the
listed attacks were tried.
