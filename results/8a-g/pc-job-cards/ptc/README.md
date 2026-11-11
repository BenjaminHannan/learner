# PTC package: the plain model trained with the calculator (arm PTC)

Spec: `design/8a-g-gemma-growth-2026-10-08.md` addendum AG (section 38, "the calculator fairness rule; arm PTC"). PTC is arm PTS (plain step model, worked steps
on every row, Gemma front, `caps_b3s.json`, seed 400) plus one switch, `calc_train`: in training the characters the calculator writes (the result after each step
`expr =`) are left out of the loss (the model still reads them); at test time the calculator writes them. Intact = calculator on; the lesion is `nocalc` (off).
`calc_full` evaluates the whole integer expression before `=` (+ - * / x, precedence, brackets, negatives; division only when exact). A gold step whose result
differs from the calculator's stays in the loss and is counted (`cap_hits.calc_mismatch`, outside the cap-hit `total`). With `calc_train` off (PT, PTS) every
weight, loss, decode and lesion list is the base code's, bit for bit (tested against 74d6e92c75).

Base code: `src-b3g2` = `custom_io` at commit 74d6e92c75 (reader rules + G2f writer; what g2c3s / g2c10s run; `install_rr.ps1`'s `$SHAG2`). PTC = that code plus six
overlay files. `install_ptc.ps1` copies `src-b3g2` to `src-ptc` (src-b3g2 is never edited).

Rebased on 74d6e92c75 (the first build was on 1acfde9a73, commit e61ec1a88f; `install_ptc.ps1` refused on the PC because `plain_lm.py`, `configs.py` and `job.py` differ
between the two commits). `plain_tf_steps.py`, `capcount.py` and `g8a/caps.py` are byte-identical at both commits, so those two overlays and the caps pin are unchanged.
For the other three the PTC patch (1acfde9a73 file to old overlay) was applied onto the 74d6e92c75 file with a 3-way merge; only `plain_lm.py` and `job.py` conflicted, by
hand: `plain_lm.py` keeps `eg_pre` (no-plug front) and appends `calc_train` after it; `job.py` keeps `--noplug` and the `eg_embed or NOPLUG` front test and adds PTC to the
arm set. Two small additions beyond the old patch so that PTC takes the no-plug front exactly as PTS does (30M / 100M only, not used by the 3M and 10M queues): the
PTC front assert in `job.py` accepts `NOPLUG` like PTS's, and `configs.check_bands`' no-plug branch checks PTC beside PT and PTS. The `diff -u` of each overlay against
its 74d6e92c75 base holds only PTC lines.

## What it changes (full copies of the edited files; sha256 uppercase)

| file here | goes to (under custom_io) | sha256 at 74d6e92c75 | sha256 of this file |
|---|---|---|---|
| `plain_tf_steps.py` | `models/plain_tf_steps.py` | `E3418B45FB339C38F90765CC7929C4B60E97453E28E375102EF15BFF64F76226` | `C39CDF1DC91EDDA7A0F11CF658FAF22148E533759227FC72153DAAFDEAAC4225` |
| `plain_lm.py` | `models/plain_lm.py` | `E90ACCF2E332D08A1E14CD2B5B537A9BE97BC93C44D48ED14DFE26FA8567AD10` | `F0E5FE42662EADC862E300DADE9470EB4AFA2898AF228A5F8061DA86C4CEF90B` |
| `configs.py` | `g8a/configs.py` | `31287A25A6AD9CBF48973520F1174C788A3DB5CE61F607265AA5EC8FA99BD5DA` | `48AA19CCB8B329FE11E45E42A17872D2581298CDBC03C2B11E3E034ADC887ECF` |
| `job.py` | `g8a/job.py` | `A590E3F176159F531571B1E5AE95BD48D2160238CB999ADD5EB6BE7734FE6A1A` | `EB0CF9DB191A75992F8ED24464D996B7EAABC86538843762B23E1A8C5F3C6888` |
| `capcount.py` | `capcount.py` | `92E4CE46013CCC67CBAD583AC9EDB52E76F7504CB004FD236255A2EB89F22C3F` | `E3C43AC13DC76420BBE3DD442456489CB998402F07E4413E39EFE6A8EEA0C97F` |
| `test_ptc.py` | `tests/test_ptc.py` | `(new file)` | `E81321ABB89F34B3AC4D048467ED11EC349EDDFA2E07E0F91C8AA5475EA054DC` |

Other files:

| file | sha256 |
|---|---|
| `ptccheck.py` | `967B62DABC7AE2FAC61EC8D6E77BAB493DD56922A1C03666AC73156DEF44DEB2` |
| `install_ptc.ps1` | `7E48DD0F49A0FA8B48BAE4BD4492FED7CBC4A4110A36A76278B3269571EA29BC` |
| `8aPTC3S-pc.txt` | `EAF2AC3D98F71E2B421C2176C0FEE19A055514D9737A1F3950E75B949F627D52` |
| `8aPTC10S-pc.txt` | `D217ACECD60CDB11FC708B255F03F8BCC8FF79CAF1980DBB0ABF60A97769BD21` |
| `ptc3s.template.md` | `50B8983AC2CA07F03868E3C7C5A862B5C2DF1095462D4D136A0166931807C06D` |
| `ptc10s.template.md` | `3D862398FE57D57D13F8B64DA162BB06374CD71734AD874728E88F7C2EA53404` |

`capcount.py` is the one file outside the brief's list: `calc_mismatch`, `calc_forced` and `calc_rows` must be reported in `RESULT.json` `cap_hits` for mark M1,
and `snapshot()` only reports the names it lists. They appear only when a `calc_train` model has run and are not part of `total` (a mismatch is a quality
count, not a cut), so PT / PTS results are unchanged.

## The edits in one paragraph

`plain_tf_steps.py`: `calc_full`, `calc_mask`, `calc_train` switch (no weights, no RNG draw), a separate loss mask used only in the `tgt` scatter (the length
mask `am` still sets the width `W`, so long targets keep their tail), `generate` with the calculator on for the intact PTC model and off for `nocalc`, the instance
`LESIONS = ['nocalc']` (the class list stays `['calc']`). `plain_lm.py`: passes `calc_train` through `PlainStepsG`, after `eg_pre` (`PlainLM` refuses it). `configs.py`: `PTC_ARM`,
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
`caps.py` and the five replaced files are 74d6e92c75's; then copies `src-b3g2` to `src-ptc.new-<stamp>`, puts the overlays and the two queue files in, runs
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

## Tested here (cloud CPU, no GPU, no Gemma weights)

All on the 74d6e92c75 tree (a worktree of that commit plus the overlay; counts built as the job builds them: eg_embed, caps_b3s.json):

- `python3 -m custom_io.tests.test_ptc` (calc_full cases and fuzz; mask == generate; masked loss and width; count PTC == PTS == PT at 3M 4,023,976 and 10M 9,815,978
  (the same numbers as at 1acfde9a73) and 30M no plug 30,003,659; LESIONS; job caps; calc_train off == 74d6e92c75 by `git archive`) and, from the install folder,
  `ptccheck.py` (the same test with the base tree named by `PTC_ORIG_TREE`, plus both queues through job.py's parser).
- The existing `test_pts`, `test_plain_tf_place`, `test_g8a`, `test_g2_input`, `test_tok_think` and `test_no_plug` pass with the overlay in place. `test_plain_tf_steps` passes
  with a small synthetic data folder (`CUSTOM_IO_DATA`); it and `test_plain_tf_maxans` need the skills data folder, which the cloud box does not have (same failure on the
  untouched 74d6e92c75 tree).
- `install_ptc.ps1` rehearsed with pwsh 7.4.6 (Windows-only cmdlets stubbed) on a fake PC tree built from `git archive 74d6e92c75 custom_io` plus 8aG2C10S-pc.txt as
  `install_rr.ps1` leaves it: full install (ends `INSTALL PTC DONE`), second run ("already installed", `INSTALL PTC DONE`), waiter past the check point, tampered
  `src-b3g2` file, tampered package file, a changed control queue (ptccheck fails, `.failed-` folder), a waiter that is not v3e, a partial insert, a `src-b3g2` still at
  1acfde9a73 (refused), and the old 1acfde9a73 package against the 74d6e92c75 tree (refused at `plain_lm.py`, hash E90ACCF2..., the PC's refusal reproduced).
- Not tested: Windows PowerShell 5.1 itself, the real waiter reading the inserts, a GPU run, real training data (the mismatch rate on the real pool is unmeasured), PTC with
  the no-plug front beyond building and counting it (it needs Gemma).
