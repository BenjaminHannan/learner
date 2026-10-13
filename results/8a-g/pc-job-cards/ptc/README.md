# PTC package: the plain model trained with the calculator (arm PTC)

Spec: `design/8a-g-gemma-growth-2026-10-08.md` addendum AG (section 38, "the calculator fairness rule; arm PTC"). PTC is arm PTS (plain step model, worked steps
on every row, Gemma front, `caps_b3s.json`, seed 400) plus one switch, `calc_train`: in training the characters the calculator writes (the result after each step
`expr =`) are left out of the loss (the model still reads them); at test time the calculator writes them. Intact = calculator on; the lesion is `nocalc` (off).
`calc_full` evaluates the whole integer expression before `=` (+ - * / x, precedence, brackets, negatives; division only when exact). A gold step whose result
differs from the calculator's stays in the loss and is counted (`cap_hits.calc_mismatch`, outside the cap-hit `total`). With `calc_train` off (PT, PTS) every
weight, loss, decode and lesion list is the base code's, bit for bit (tested against 1acfde9a73).

Base code: `src-b3g2` = `custom_io` at commit 1acfde9a73 (what g2c3s / g2c10s run). PTC = that code plus six overlay files. `install_ptc.ps1` copies
`src-b3g2` to `src-ptc` (src-b3g2 is never edited).

## What it changes (full copies of the edited files; sha256 uppercase)

| file here | goes to (under custom_io) | sha256 at 1acfde9a73 | sha256 of this file |
|---|---|---|---|
| `plain_tf_steps.py` | `models/plain_tf_steps.py` | `E3418B45FB339C38F90765CC7929C4B60E97453E28E375102EF15BFF64F76226` | `C39CDF1DC91EDDA7A0F11CF658FAF22148E533759227FC72153DAAFDEAAC4225` |
| `plain_lm.py` | `models/plain_lm.py` | `CDC9DE0BCA66A6FF58AA2FC50865B24D4A72F6CB6E1BA06AB9E596B01437CDF6` | `582B463F871F1FB1857C82E070C948550A744CC2C96258ECE6F1DC1ADBCAC697` |
| `configs.py` | `g8a/configs.py` | `550AC52D25F83177620A1C7C47042BE7FD966C888A383DAC664E95E879A573BD` | `862D2ADF252CA454DF815F2BA97EF265D072ED18098AE761C12455C149716E2C` |
| `job.py` | `g8a/job.py` | `28E09E53F0CA7FDFC45ABE3174E7189F21F166AFBDC20D2B0C591D47CFD54242` | `5F432C282C263FD37ED2306CC3DC5024EEA2DE6BDC94BDEE843D5D92003567FF` |
| `capcount.py` | `capcount.py` | `92E4CE46013CCC67CBAD583AC9EDB52E76F7504CB004FD236255A2EB89F22C3F` | `E3C43AC13DC76420BBE3DD442456489CB998402F07E4413E39EFE6A8EEA0C97F` |
| `test_ptc.py` | `tests/test_ptc.py` | `(new file)` | `BBB44E5ED38C77D28F776DD32B51A540A89220F3121D928DA7CBF0D971F06FD0` |

Other files:

| file | sha256 |
|---|---|
| `ptccheck.py` | `B29C561A7D0A295518B780B6FDBBBA97F63B2716EA704789D78385956DF5948E` |
| `install_ptc.ps1` | `A3B59633B7C223E707FAA98E3C3D89AD95CECB47719325A0FA7B2E1C689D3B6D` |
| `8aPTC3S-pc.txt` | `57C7BD32A7A3282677B7C35A9EB3F032AEAC30819B9E030810FFFB943BC5C6C2` |
| `8aPTC10S-pc.txt` | `40F579784638991C4E843A5244ECAB6DE77182D5F07C3AB7ACB0EEFE3927D440` |
| `ptc3s.template.md` | `30B061F349233ACE19C389052F303ADF72DFD23EDE4E1F4971D05755AB83ED66` |
| `ptc10s.template.md` | `1980C4926D0E9A051BCE53E7A3DD2B0BC231611EAA890A993C03837E6D98A8AF` |

`capcount.py` is the one file outside the brief's list: `calc_mismatch`, `calc_forced` and `calc_rows` must be reported in `RESULT.json` `cap_hits` for mark M1,
and `snapshot()` only reports the names it lists. They appear only when a `calc_train` model has run and are not part of `total` (a mismatch is a quality
count, not a cut), so PT / PTS results are unchanged.

## The edits in one paragraph

`plain_tf_steps.py`: `calc_full`, `calc_mask`, `calc_train` switch (no weights, no RNG draw), a separate loss mask used only in the `tgt` scatter (the length
mask `am` still sets the width `W`, so long targets keep their tail), `generate` with the calculator on for the intact PTC model and off for `nocalc`, the instance
`LESIONS = ['nocalc']` (the class list stays `['calc']`). `plain_lm.py`: passes `calc_train` through `PlainStepsG` (`PlainLM` refuses it). `configs.py`: `PTC_ARM`,
`ptc_cfg` = `pts_cfg` + `calc_train` (same count as PTS), `add_ptc`, `train_args` for PTC. `job.py`: PTC takes everywhere PTS does (caps pin `caps_b3s.json`, the
same sibling caps dir `<pool>.caps-PTS`, `eg_embed` required, arm lists). The training mask replays `generate`: walk the gold text; after each character that was
not forced, ask `calc_full(prefix)`; if the gold continues with the answer, mask those characters and skip them.

## Queue and cards

- `8aPTC3S-pc.txt` (queue 8aPTC3S, run `8aPTC3S-3M-s400`, `--arms PTC`, `--accum PTC=16` = PTS's in 8aG2C3S) and `8aPTC10S-pc.txt` (queue 8aPTC10S, run
  `8aPTC10S-10M-s400`, `--accum PTC=32` = PTS's in 8aG2C10S). Same pool, caps file, seed, `eg_embed`, MEM lines as the g2c3s / g2c10s files.
- `ptc3s.template.md`, `ptc10s.template.md`: the job cards (`@STARTED@` filled by the waiter; marks M1 to M3 from addendum AG copied in; never-edit rules kept).
  They are copied to `C:\Users\benja\custom-io\` where v3e's `card:` line looks for them.

## Slot

Two inserted jobs for the post-G1 waiter v3e: `WORK\insert\13-ptc3s.txt` and `WORK\insert\14-ptc10s.txt`. The waiter runs inserts alone, in name order, at its
first check point (right after group 2 at 3M): `11-at`, `12-g2c10s`, **`13-ptc3s`, `14-ptc10s`**, then `30-g2q` and `46-tp` (and every 10M agent-model job, 50+).
Each insert has `queue:`, `src: src-ptc`, `caps:` (the SHA-256 of `src-ptc\custom_io\g8a\caps.py`, which v3e needs for any src but src-b3g2 / src-b3; it is
32862AE2D4E6E401FCAD5BB6C5E54B0B8845019202DEA73E2CB4C7EFE5EEA03E, src-b3g2's, unchanged) and `card:`. The waiter lists `WORK\insert` once per check point, so both
files must exist before G2f ends; `install_ptc.ps1` refuses once the waiter has logged an `inserted job ... (after group 2` line or `8aB3G2s400 ended`
after its v3e start line.

## Install (from the Mac)

```
scp -r <this folder> benja@<pc>:C:/Users/benja/custom-io/in-ptc        # copy the folder to C:\Users\benja\custom-io\in-ptc
ssh benja@<pc> powershell -ExecutionPolicy Bypass -File C:\Users\benja\custom-io\in-ptc\install_ptc.ps1
```

`install_ptc.ps1` checks: all package files and their sha256; the waiter is v3e, runs exactly once and is not past its first insert check point; `src-b3g2`'s
`caps.py` and the five replaced files are 1acfde9a73's; then copies `src-b3g2` to `src-ptc.new-<stamp>`, puts the overlays and the two queue files in, runs
`ptccheck.py` on the CPU (needs about 2 GB free to commit plus 2 GB to spare; no GPU, no Gemma weights; about 30 s on a laptop CPU), renames the folder to
`src-ptc`, copies the two card templates into `custom-io` (an older copy is kept as `.before-<stamp>`) and writes the two insert files. On any failure it prints
`FAILED: <reason>`, renames the new folder `src-ptc.failed-<stamp>` and changes nothing else. It deletes nothing. A second run prints "already installed" and
`INSTALL PTC DONE`.

Expected output (last lines):

```
  ptccheck: (ii) test_ptc: all checks passed
  ptccheck: (iii) 8aPTC3S-pc.txt: 2 entries, 8aPTC3S-3M-s400 --arms PTC --accum PTC=16, job.py parses it, ...
  ptccheck: (iii) 8aPTC10S-pc.txt: 2 entries, 8aPTC10S-10M-s400 --arms PTC --accum PTC=32, job.py parses it, ...
  ptccheck: PTC CPU CHECK OK
src-ptc: in place; card templates ptc3s.template.md and ptc10s.template.md in custom-io; WORK\insert:
  13-ptc3s.txt: queue: 8aPTC3S | src: src-ptc | caps: 32862AE2... | card: ptc3s.template.md
  14-ptc10s.txt: queue: 8aPTC10S | src: src-ptc | caps: 32862AE2... | card: ptc10s.template.md
INSTALL PTC DONE
```

## Tested here (cloud CPU, no GPU)

- `python3 -m custom_io.tests.test_ptc` (calc_full cases and fuzz; mask == generate; masked loss and width; count PTC == PTS at 3M 4,023,976 and 10M 9,815,978;
  LESIONS; job caps; calc_train off == 1acfde9a73) and the existing `test_pts` and `test_plain_tf_steps` in a worktree with the overlay.
- `install_ptc.ps1` rehearsed with pwsh on a fake PC tree built from `git archive 1acfde9a73 custom_io`: full install, second run, waiter past the check point,
  tampered `src-b3g2` file, tampered package file, a changed control queue (ptccheck fails, `.failed-` folder), a waiter that is not v3e, a partial insert.
- Not tested: Windows PowerShell 5.1 itself, the real waiter reading the inserts, a GPU run, real training data (the mismatch rate on the real pool is unmeasured).
