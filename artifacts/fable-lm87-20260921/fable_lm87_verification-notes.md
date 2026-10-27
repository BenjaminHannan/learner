# fable_lm87 verification notes (2026-09-21)

Read-only scout. No training, no runs, no installs, no commits. No PASSMARKS to seal (no registered run performed).

## arXiv ids — each verified by fetching its abs page

- 2305.07759 TinyStories (Eldan & Li, May 2023) — EXISTS (v2 24 May 2023). https://arxiv.org/abs/2305.07759
- 2308.02019 Baby Llama (Timiryasov & Tastet, Aug 2023, v2 Oct 2023) — EXISTS. https://arxiv.org/abs/2308.02019
- 2412.05149 BabyLM Challenge findings II (Hu et al., Dec 2024) — EXISTS. https://arxiv.org/abs/2412.05149
- 2504.08165 BabyLM Challenge findings I (Apr 2025) — EXISTS (abstract fetched via search). https://arxiv.org/html/2504.08165v1
- 2502.02737 SmolLM2 (Ben Allal et al., Feb 2025) — EXISTS. https://arxiv.org/abs/2502.02737
- 2504.09184 SimpleStories (Finke et al., Apr 2025, v3 May 2025; NeurIPS 2025 D&B) — EXISTS. https://arxiv.org/abs/2504.09184
- 2005.11401 RAG (Lewis et al., 2020, NeurIPS) — EXISTS. https://arxiv.org/abs/2005.11401
- 2007.01282 FiD (Izacard & Grave, Jul 2020, v2 Feb 2021) — EXISTS. https://arxiv.org/abs/2007.01282v2
- 1704.04368 Pointer-Generator (See et al., Apr 2017, v2) — EXISTS. https://arxiv.org/abs/1704.04368
- 2310.11511 Self-RAG (Asai et al., Oct 2023; ICLR 2024) — EXISTS. Note: initially recalled as 2305.14283, corrected during verification.
- 2302.04761 Toolformer (Schick et al., Feb 2023; NeurIPS 2023) — EXISTS. https://arxiv.org/abs/2302.04761
- 2212.08153 FiDO (de Jong et al., 2023) — EXISTS (cited in §3 as efficiency path only).

## Licence checks

- TinyStories HF card: `cdla-sharing-1.0` — VERIFIED on dataset card. https://huggingface.co/datasets/roneneldan/TinyStories
- Simple English Wikipedia (`20220301.simple`): CC BY-SA + GFDL — VERIFIED on legacy dataset card. https://hf.hahadalin.eu.org/datasets/legacy-datasets/wikipedia
- OpenStax: CC BY-NC-SA 4.0 — VERIFIED on OpenStax help. Flagged non-commercial.
- Project Gutenberg: US public domain after stripping PG header — VERIFIED on licence page. https://gutenberg.org/policy/license.html
- Ririro / GlotStoryBook / ChildWiki individual licences — NOT FOUND; marked not-found in report.
- SciClaim/SciTLDR-style traps avoided: no training datasets ingested at all.

## Context docs read

- design/v3/30-modes/48-parallel-build-brief-20260921.md (rules)
- design/v3/30-modes/54-modes-and-demo-opus.md (modes/demo; mouth = templates + 104k-param toy baseline)
- design/v3/30-modes/43-talker-ears-mouth-design-fable.md (own-architecture ears/mouth design; §D pretraining sketch this report builds on)
- design/v3/30-modes/56-scientific-claim-rows-research-muse.md (format reference for research-scout docs)
- No doc 53 exists yet in this worktree (mouth borrowed-decoder doc owned by agent 6); SmolLM2-360M placeholder details taken from user brief + SmolLM2 paper.

## Deviations / open questions for Ben

- None blocking. One question recorded in report §2: confirm OpenStax CC BY-NC-SA counts as acceptable for this project's (non-commercial, personal) use before any ingestion.
