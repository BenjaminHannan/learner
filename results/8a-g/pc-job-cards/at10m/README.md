# at10m: the agent model (B3AT, arm AT) at 10M, seed 400, gated on AT-1a/c/d (and AT-1f when its counters are in RESULT.json)

One run, queue 8aAT10M, job 8aAT10M-10M-s400: the agent-turn model at its 10M shape S (7 blocks, width 256, 4 heads, mlp 4.8, small plug; 9,824,546 trained parameters, the plain partner PTS / PTC at 10M has 9,814,442), same pool, caps and readout as AT-1. Code is `src-at` (custom_io at 6e72a5fae5), untouched. Marks A10-1 to A10-4 and the gate lines are sealed in big-run PLAN.md, eighteenth Addendum 10-12 (the AT-1 marks in the sixth Addendum 10-11); spec addendum AG's M3 fixes the size read.

The gate (`15-at10mgate`, runs just before `16-at10m`) reads AT-1's RESULT.json against G2f's and g2c3s's and turns `16-at10m.txt` into a no-op (`cmd: at10m_skipped.cmd`, original kept as `16-at10m.txt.gated-<stamp>`) if any of these is proved wrong or cannot be read:
- AT-1a: pooled-5 more than 6.0 below G2f, or below g2c3s.
- AT-1c: calculator-off within 10 points of the full score (program questions).
- AT-1d: chain-5 more than 5 below G2f, or thinker-off (`loops:0`) above 60% of the full score.
- AT-1f: any cap counter above 0, only if the counters are in RESULT.json (else it prints "AT-1f counters not in RESULT.json: reported later, not gated").
AT-1b (reply swap) and AT-1e (stop and long input) are not gated: reported after the run.

Accum AT=64 is a **memory guess** (it is what the 10M B3G2 queue uses; the agent model runs up to 17 turns per row and may need more; the card doubles it on a spill).

## Files (sha256)
```
09a1b69f6be43f0f3ce1e04bb047ee412cb2ffe1f416b6c2d6826b54e462b6f1  8aAT10M-pc.txt
44c2a9e2401136cfbfa07be447a190cd79fb5dc2714d55d57ed5af6b2733d0b6  at10mcheck.py
392fb1c6378d244e4e21d090844a2576528d1c0113d82bbe7ec81ffd2b0d8d9b  at10m.template.md
c6c3efa7ae18705a521a31d40026ebb5100480bea8951d0fde0d71b5355cd6a1  at10m_gate.py
6fe9d8bb037203bd970d09a993ee3c73e2d773d4f5e41d2f9bc4d853a975e8f9  at10m_gate.ps1
db05da0c21057699f45830e6749f108ef265839c7b0a8cdcb4b62a859a940276  at10m_gate.cmd
6200ad6e45fdca8d8bb81f339d9bcbcd51ba792ff18ec54914c74fbac21dfe11  at10m_skipped.cmd
d982f3bc5cbdc86dec260fd4101a9edbdbb9da712360fa6c3498e5260e3bfb0a  install_at10m.ps1
```

## Install (Mac -> PC), after `INSTALL AGENT DONE` and before G2f ends
The waiter lists WORK\insert once, at its first check point right after G2f, so this has to be on the PC before G2f ends. The installer refuses if the waiter has logged any later `inserted job ` or `8aB3G2s400 ended` line.
```
scp -r results/8a-g/pc-job-cards/at10m benja@<pc>:C:/Users/benja/custom-io/in-at10m
ssh benja@<pc> powershell -ExecutionPolicy Bypass -File C:\Users\benja\custom-io\in-at10m\install_at10m.ps1
```
(Copy the folder as `C:\Users\benja\custom-io\in-at10m`; its README.md can stay.) Expected output: the line `src-at (6e72a5fae5) and its pinned files match; waiter v3e (pid ...) is running and has not reached its first insert check point; 11-at.txt is present`; the at10mcheck lines (`AT 10M trained parameters: 9,824,546 ...`, `PTS 10M trained parameters (g2c10s; PTC equals it): 9,814,442 ...`, `AT10M CPU CHECK OK`); `gate self-test: at10m_gate self-test OK`; the list of WORK\insert files (`15-at10mgate.txt: cmd: at10m_gate.cmd | hours: 1` and `16-at10m.txt: queue: 8aAT10M | src: src-at | caps: 433475...62D3 | card: at10m.template.md`); last line `INSTALL AT10M DONE`. Run again: `already installed ...` and `INSTALL AT10M DONE`. Any problem prints `FAILED: <reason>` and leaves nothing from this run behind.

## Order in the first check-point batch
`05-g1diag`, `10-g2fgate`, `11-at` (AT-1), `12-g2c10s`, `13-ptc3s`, `14-ptc10s`, **`15-at10mgate`, `16-at10m`**, then `30-g2q`, `46-tp`.

## Seconds per update at 10M
`train.py` prints a `train` step line every 500 steps (`elapsed` in seconds, in `AT\stdout.txt`), and RESULT.json holds `steps_per_s`, `train_s`, `steps` and `peak_mem_mib`. Nothing in the training code was changed.
