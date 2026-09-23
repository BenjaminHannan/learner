## A. Encoder candidates

| Model | Params; license; context; tokenizer | Published extraction evidence |
| --- | --- | --- |
| **ModernBERT-base** | 149M; Apache-2.0; 8,192; 50,368-vocab BPE-family tokenizer. [Hugging Face+1](https://huggingface.co/answerdotai/ModernBERT-base?utm_source=chatgpt.com) | Scientific-text NER+RE: **0.92 F1** with joint entity/relation training at SOMD 2025. [ACL Anthology](https://aclanthology.org/2025.sdp-1.15/?utm_source=chatgpt.com) |
| **DeBERTa-v3-base** | ~184M total (86M backbone+98M embeddings); MIT; 512; 128K SentencePiece. [Hugging Face+1](https://huggingface.co/microsoft/deberta-v3-base/blob/main/config.json?utm_source=chatgpt.com) | SQuAD2 span extraction **88.4 F1**. [Hugging Face](https://huggingface.co/microsoft/deberta-v3-base?utm_source=chatgpt.com) |
| **DeBERTa-v3-small** | ~142M total (44M+98M); MIT; 512; 128K SentencePiece. [Hugging Face](https://huggingface.co/microsoft/deberta-v3-small?utm_source=chatgpt.com) | SQuAD2 **82.8 F1**. [Hugging Face](https://huggingface.co/microsoft/deberta-v3-small?utm_source=chatgpt.com) |
| **SciBERT** | ~110M; Apache-2.0; 512; 31,090 scientific WordPieces. [GitHub+1](https://github.com/allenai/scibert/?utm_source=chatgpt.com) | SciERC NER **67.57**, SciERC RE **79.97**, ChemProt RE **83.64 F1**. [ACL Anthology](https://aclanthology.org/anthology-files/pdf/D/D19/D19-1371.pdf?utm_source=chatgpt.com) |
| **RoBERTa-base** | ~125M; MIT; 512 usable; byte-BPE/50,265 vocab. [Hugging Face](https://huggingface.co/FacebookAI/roberta-base/blob/main/config.json?utm_source=chatgpt.com) | SQuAD2 **83.7 F1**. [Hugging Face](https://huggingface.co/microsoft/deberta-v3-small?utm_source=chatgpt.com) |
| **BERT-base** | ~110M; Apache-2.0; 512; 30,522 WordPiece. [Hugging Face](https://huggingface.co/google-bert/bert-base-uncased/blob/main/config.json?utm_source=chatgpt.com) | SQuAD1.1 **88.4 F1** in Google's reference recipe. [GitHub](https://github.com/google-research/bert/blob/master/README.md?plain=1&utm_source=chatgpt.com) |
| **NeoBERT** | 250M; MIT; 4,096; BERT WordPiece; RoPE/RMSNorm/SwiGLU. [GitHub](https://github.com/chandar-lab/NeoBERT?utm_source=chatgpt.com) | Published NER/RE/span result: **not found**. |
| **EuroBERT-210m** | 210M; Apache-2.0; 8,192; 128,256-vocab Llama-3-style tokenizer; RoPE/RMSNorm. [Hugging Face+1](https://huggingface.co/EuroBERT/EuroBERT-210m/blob/main/config.json?utm_source=chatgpt.com) | Peer-reviewed extraction FT result: **not found**. |
| **GTE-ModernBERT-base** | 149M; Apache-2.0; 8,192; ModernBERT backbone. [Hugging Face](https://huggingface.co/Alibaba-NLP/gte-modernbert-base/blame/main/README.md?utm_source=chatgpt.com) | Published NER/RE/span result: **not found**; its published focus is embeddings/retrieval. |

**Quality/parameter, using actual extraction evidence:** ModernBERT > DeBERTa-v3-base > SciBERT > DeBERTa-v3-small > RoBERTa > BERT. NeoBERT/EuroBERT/GTE cannot honestly be ranked here without extraction results.  
**Scientific vocabulary:** SciBERT is clearly #1: its WordPiece vocabulary was built from 1.14M scientific papers/3.1B tokens. [Hugging Face](https://huggingface.co/allenai/scibert_scivocab_uncased?utm_source=chatgpt.com) No published scientific-tokenizer coverage comparison supports a defensible ordering of the others.  
**Plain-PyTorch implementation ease:** BERT ≈ SciBERT > RoBERTa > DeBERTa-v3 > NeoBERT > ModernBERT/GTE > EuroBERT; the later models add disentangled attention, RoPE/RMSNorm/SwiGLU, or ModernBERT local/global attention. [Hugging Face+2GitHub+2](https://huggingface.co/microsoft/deberta-v3-base/blob/main/README.md?utm_source=chatgpt.com)

## B. Small decoders

Qwen2.5-0.5B, SmolLM2-360M, and Qwen3-0.6B are Apache-2.0 causal decoders. [Hugging Face+2Hugging Face+2](https://huggingface.co/Qwen/Qwen2.5-0.5B/tree/main?utm_source=chatgpt.com) I found **no published apples-to-apples experiment** showing one of these, repurposed with last-token pooling/classification heads, matching or beating a ~100–150M bidirectional encoder on RE/NER. For this extraction-first system, that makes them a substantially less evidenced choice.

## C. Fine-tuning recipe

Use **full fine-tuning**, initially freezing **zero encoder layers**: SciBERT found full FT improved average F1 by **3.25 points** versus frozen representations. [ACL Anthology](https://aclanthology.org/anthology-files/pdf/D/D19/D19-1371.pdf?utm_source=chatgpt.com) Start AdamW at **2–3×10⁻⁵**, effective batch **32** (e.g. physical 16 × accumulation 2), **3 epochs**, max length 256–512, gradient clipping 1.0; BERT's reproducible SQuAD recipe used 3×10⁻⁵, batch 12, two epochs. [GitHub](https://github.com/google-research/bert/blob/master/README.md?plain=1&utm_source=chatgpt.com) Use BF16 autocast; FP16 + GradScaler is the fallback. [PyTorch Documentation+1](https://docs.pytorch.org/docs/stable/accelerator/amp.html?utm_source=chatgpt.com)

LoRA is the fallback if memory becomes limiting, not my default at this scale: LoRA freezes the backbone and can approach full-FT performance while greatly reducing trainable parameters. [arXiv](https://arxiv.org/abs/2106.09685?utm_source=chatgpt.com)

For relation direction, **explicit subject/object role markers are preferable once spans are known**. PL-Marker's subject-oriented markers improved strict RE F1 by 4.1–4.3 points. [ACL Anthology](https://aclanthology.org/2022.acl-long.337/?utm_source=chatgpt.com) Direction-only accuracy comparisons were **not found**. Because deployment starts from raw text, predict both spans first, then feed their representations plus explicit SUBJECT/OBJECT role embeddings into the relation head.

## D. Abstention

Use three stages: temperature-scale logits on held-out calibration data (one scalar T); Guo et al. found this simple method highly effective for calibration. [Proceedings of Machine Learning Research](https://proceedings.mlr.press/v70/guo17a?utm_source=chatgpt.com) Then define overall confidence as something conservative such as the **minimum** of act, subject-span, object-span, and relation confidence. Finally choose the accept threshold with **Learn-then-Test**, which provides finite-sample risk control rather than merely calibrated probabilities. [arXiv](https://arxiv.org/abs/2110.01052?utm_source=chatgpt.com)

Most relevant concrete result: a 2026 extraction study obtained **31.8% coverage at 9.6% accepted error** for a 10% target; stricter Mondrian LTT achieved **17.1% coverage at 6.8% risk**, and a blind audit measured **1.3% accepted error** against the 10% budget. [arXiv](https://arxiv.org/abs/2608.14639?utm_source=chatgpt.com)

## E. Dataset licences

| Dataset | Licence / free today |
| --- | --- |
| WebRED | CC BY 4.0; **yes**, attribution required. [GitHub](https://github.com/google-research-datasets/WebRED?utm_source=chatgpt.com) |
| DocRED | MIT; **yes**. [Hugging Face](https://huggingface.co/datasets/thunlp/docred/blob/main/README.md?utm_source=chatgpt.com) |
| Re-DocRED | MIT; **yes**. [GitHub](https://github.com/tonytan48/re-docred?utm_source=chatgpt.com) |
| TACRED | LDC User Agreement; **not generally free/permissive**. [Linguistic Data Consortium](https://catalog.ldc.upenn.edu/LDC2018T24?utm_source=chatgpt.com) |
| FewRel | Official site says **CC BY-SA 4.0**; free, but **ShareAlike—not permissive**. (HF metadata conflictingly says MIT.) [thunlp.github.io+1](https://thunlp.github.io/1/fewrel1.html?utm_source=chatgpt.com) |
| NYT10 | Underlying NYT Annotated Corpus permits only non-commercial research under an LDC agreement; **not permissive**. [Linguistic Data Consortium](https://catalog.ldc.upenn.edu/license/the-new-york-times-annotated-corpus-ldc2008t19.pdf?utm_source=chatgpt.com) |
| SciERC | Free download exists; licence **not found/unspecified** → do not assume permissive. [Papers with Code+1](https://paperswithcode.com/dataset/scierc?utm_source=chatgpt.com) |
| ChemProt | Public Domain Mark 1.0; **yes**. [Hugging Face](https://huggingface.co/datasets/DFKI-SLT/chemprot/blob/main/chemprot.py?utm_source=chatgpt.com) |
| BioRED | Public download, but licence **unknown/not found** → not confirmed permissive. [Hugging Face+1](https://huggingface.co/datasets/bigbio/biored/blob/main/biored.py?utm_source=chatgpt.com) |

### What I would do

1. Start with **ModernBERT-base**, and benchmark **SciBERT** as the scientific-domain control.
2. Full-fine-tune one encoder with two span pointers + act head + directional relation head.
3. Use role-marked span representations internally; never require gold markers at inference.
4. Calibrate every component, then abstain on the **minimum component confidence**.
5. Hold out a dedicated calibration set and use **LTT thresholds targeting ≤1–2% accepted error**, even if coverage initially becomes low.
