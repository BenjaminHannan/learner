# DATASET SURVEY — talker reading list (build task 1, design 24 §1.3 / §7)

Surveyed 2026-09-20 from the Hugging Face dataset API (`/api/datasets/{id}/tree/main?recursive=true`
for exact byte sizes, `/api/datasets/{id}` + `README.md` for the licence field). Sizes below are the
**exact byte counts the API reports for the files at the listed repo revision**, not estimates.

Repo revisions pinned at survey time:

| Dataset | HF repo | revision (sha) | lastModified |
|---|---|---|---|
| SimpleStories | `SimpleStories/SimpleStories` | `e63b8adc3b1a1bdc7cac5b500d150b71346b0628` | 2025-12-19 |
| TinyStories (V2 files) | `roneneldan/TinyStories` | `f54c09fd23315a6f9c86f9dc80f725de7d8f9c64` | 2024-08-12 |
| TinyDialogues | `styfeng/TinyDialogues` | `2ee0b671a0780584130337b0138b7adec21836e2` | 2024-11-26 |
| SODA | `allenai/soda` | `fdc848ab0183208ea7808206c91c724414d0a071` | 2023-01-04 |

---

## 1. Full file listings with exact sizes

### SimpleStories — `SimpleStories/SimpleStories` — licence **MIT** (`license: mit` in the card)

| bytes | path | taken? |
|---:|---|---|
| 238,015,938 | `data/train-00000-of-00007.parquet` | yes |
| 238,000,197 | `data/train-00001-of-00007.parquet` | yes |
| 237,741,821 | `data/train-00002-of-00007.parquet` | yes |
| 237,658,974 | `data/train-00003-of-00007.parquet` | yes |
| 238,085,905 | `data/train-00004-of-00007.parquet` | yes |
| 237,848,790 | `data/train-00005-of-00007.parquet` | yes |
| 237,678,067 | `data/train-00006-of-00007.parquet` | yes |
| 16,838,557 | `data/test-00000-of-00001.parquet` | yes (held-out) |
| 431,432,698 | `processed.parquet` | **no** — a derived duplicate of the same stories |
| 4,176 | `README.md` | no |
| 2,419 | `.gitattributes` | no |

Repo total 2,113,307,542. **Taken: 1,681,868,249 bytes** (matches the card's own
`download_size: 1681868249`). Card reports train = 2,115,696 stories, test = 21,371.
Schema: `story` (string) + 20 metadata columns (`topic`, `theme`, `word_count`, readability
scores, `model`, …). Text written by GPT-4o-mini. Paper: arXiv 2504.09184.

### TinyStories V2 (GPT-4 only) — `roneneldan/TinyStories` — licence **CDLA-Sharing-1.0**

| bytes | path | taken? |
|---:|---|---|
| 2,227,753,162 | `TinyStoriesV2-GPT4-train.txt` | yes |
| 22,502,601 | `TinyStoriesV2-GPT4-valid.txt` | yes (held-out) |
| 1,924,281,556 | `TinyStories-train.txt` | **no** — V1, contains the weaker GPT-3.5 text |
| 19,447,282 | `TinyStories-valid.txt` | no (V1) |
| 1,608,001,638 | `TinyStories_all_data.tar.gz` | **no** — superset + prompts, not needed |
| 819,200,980 | `MLP_input_output.npy` | **no** — unrelated activations file |
| 248,731,111 | `data/train-00000-of-00004-2d5a1467fff1081b.parquet` | no (V1 parquet mirror) |
| 248,171,980 | `data/train-00001-of-00004-5852b56a2bd28fd9.parquet` | no |
| 245,894,874 | `data/train-00002-of-00004-a26307300439e943.parquet` | no |
| 247,988,350 | `data/train-00003-of-00004-d243063613e5a057.parquet` | no |
| 9,989,127 | `data/validation-00000-of-00001-869c898b519ad725.parquet` | no |
| 11,759 | `Evaluation prompts.yaml` | no |
| 1,061 | `README.md` | no |

Repo total 7,621,978,240. **Taken: 2,250,255,763 bytes.**
The design's 2.23 GB figure for the train file is confirmed exactly (2,227,753,162 B = 2.23 GB
decimal / 2.07 GiB). Format: plain UTF-8 text, stories separated by a line containing
`<|endoftext|>`. Licence note: CDLA-Sharing-1.0's share-alike obligation attaches to
*republishing the data*; we do not republish it (raw/ is git-ignored) and it does not attach to a
model trained on it.

### TinyDialogues — `styfeng/TinyDialogues` — licence **MIT**

| bytes | path | taken? |
|---:|---|---|
| 141,294,602 | `tinydialogue_train_ordered.txt` | yes |
| 25,376,876 | `tinydialogue_val_ordered.txt` | yes (held-out) |
| 148,892,423 | `individual_age_data.zip` | **conditional** — see note |
| 2,851 | `README.md` | no |
| 2,593 | `.gitattributes` | no |

Repo total 315,569,345. **Taken: 315,563,901 bytes** (the two ordered `.txt` files *and*
the zip).

**This is the one place the plan changed after inspecting the data.** The card says the ordered
files are "ordered ascending by age (2, 5, 10, 15)", and the design (§1.3) says to use ages
2/5/10 and drop 15. Inspecting the downloaded file showed the ordered `.txt` carries **no age
marker at all** — it is only positionally sorted, so age 15 could be dropped only by guessing a
cut point. `individual_age_data.zip` was therefore fetched as well (+148,892,423 B) and the six
per-age `.txt` files for ages 2/5/10 were unpacked from it (125,547,301 B on disk); the three
age-15 files and the four `full-with-metadata.jsonl` files were left inside the zip. Unpacking is
`unzip` on plain text — nothing from the repository is executed.

**The pipeline reads the per-age files; the two ordered files are kept only as provenance and are
not an input** (`RAW_FILES` in `scripts/fable_talker24_data.py` lists exactly what is read).

Format, confirmed on the file: one conversation per line ending in `<|endoftext|>`, turns
separated by a **literal** `\n\n` (backslash-n, not a newline), each turn prefixed by a markdown
speaker tag such as `**Babysitter**:` or `**Child** (struggling to pull the wagon):`. The speaker
tag is stripped — who speaks is a flag in the thought (design §3.2), never text — and the turn
boundary survives as the `<TURN>` token.
Text written by GPT-4; ≈ 130k conversations. Paper: EMNLP 2024, Feng, Goodman & Frank.

### SODA — `allenai/soda` — licence **CC BY 4.0**

| bytes | path | taken? |
|---:|---|---|
| 688,771,672 | `train.parquet` | yes |
| 82,869,716 | `valid.parquet` | yes (held-out) |
| 84,204,550 | `test.parquet` | **no** — not needed; train+valid is already more than the
simplicity filter will keep |
| 4,915 | `README.md` | no |
| 2,265 | `.gitattributes` | no |

Repo total 855,853,118. **Taken: 771,641,388 bytes.**
Card reports train = 1,191,582 dialogues, valid = 146,346, test = 148,968 (1,486,896 total, which
is the 1.49M of the design). Text distilled from InstructGPT seeded by Atomic10x. Fields include
`dialogue` (list of str), `speakers`, `narrative`, `PersonX/Y/Z`. Paper: arXiv 2212.10465.

---

## 2. Download budget

Planned before downloading, then what was actually fetched:

| Source | planned bytes | downloaded bytes | GB (decimal) |
|---|---:|---:|---:|
| SimpleStories (8 parquet) | 1,681,868,249 | 1,681,868,249 | 1.68 |
| TinyStories V2 GPT-4 (2 txt) | 2,250,255,763 | 2,250,255,763 | 2.25 |
| TinyDialogues (2 ordered txt) | 166,671,478 | 166,671,478 | 0.17 |
| TinyDialogues `individual_age_data.zip` | *(not planned)* | 148,892,423 | 0.15 |
| SODA (2 parquet) | 771,641,388 | 771,641,388 | 0.77 |
| **TOTAL DOWNLOADED** | 4,870,436,878 | **5,019,329,301** | **5.02** |
| unpacked from the zip (ages 2/5/10) | — | 125,547,301 | 0.13 |
| **TOTAL ON DISK in `raw/`** | — | **5,144,876,602** | **5.14** |

**5.02 GB downloaded < the 7 GB cap, and inside the "≈ 5–6 GB approved" of decision D3.**
(Free disk at survey time: 81 GiB.) Every file's sha256 and byte size is in
`data/MANIFEST-raw.json` (21 files, 5,144,876,602 bytes), and every downloaded file's size was
checked against the size in this table before the pipeline was allowed to read it.

Nothing here is executed: only `.parquet` and `.txt` data files are fetched, over
`https://huggingface.co/datasets/{repo}/resolve/main/{path}`, i.e. the datasets' official hosting.
No loading script, no `datasets`-library trust-remote-code path, no zip from the repos is executed.

## 3. Not downloaded, and why

- `SimpleStories/processed.parquet` — derived duplicate (431 MB saved).
- TinyStories V1 text + parquet mirrors + `_all_data.tar.gz` + `MLP_input_output.npy` — the design
  asks for the **GPT-4-only V2** files specifically (5.4 GB saved).
- `allenai/soda test.parquet` — surplus to requirements (84 MB saved).
- `styfeng/TinyDialogues` age-15 files and the four `*_full-with-metadata.jsonl` files — left
  inside the zip, never unpacked (≈ 420 MB not written to disk).
- DailyDialog (CC BY-NC-SA), Cosmopedia / UltraChat / MOSS, BabyLM — excluded by the design.
- Project-generated dialogues and the Qwen persona set are produced by build task 2 / BensPC, not
  downloaded here.

## 4. Licence summary (one line each)

| Dataset | Licence | Redistribution obligation | OK for this use? |
|---|---|---|---|
| SimpleStories | MIT | attribution only | yes |
| TinyStories V2 | CDLA-Sharing-1.0 | share-alike **if the data is republished**; we do not republish | yes |
| TinyDialogues | MIT | attribution only | yes |
| SODA | CC BY 4.0 | attribution | yes |

All four are machine-generated text (GPT-4o-mini / GPT-4 / InstructGPT). Per design §1.4 this is
accepted and must be labelled: *"It learned English by reading simple stories and conversations
that were written by large AI models."* No pretrained weights are used anywhere.
