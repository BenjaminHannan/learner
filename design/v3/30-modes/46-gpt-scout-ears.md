# GPT xhigh scout B — tiny from-scratch parsers and wrong-write prevention (2026-09-21). Citations NOT yet verified by me.

A. Tiny from-scratch parsers / pointers / unseen entities

1. Using Deep Time Delay Neural Network for Slot Filling in Spoken Language Understanding — 2020, Symmetry 12(6):993. The paper’s plain BiGRU reaches 95.34 slot-F1 on ATIS and 91.80 on SNIPS with E=50, H=100. It does not report parameter counts, but from its published vocabulary/hyperparameters the BiGRU is roughly 0.2M parameters on ATIS and 0.7M on SNIPS, so this is the cleanest sub-1M baseline I found. Try: reproduce this architecture at ~0.3M as the yardstick, but score exact frames and trap subsets rather than slot-F1 alone. [MDPI+1](https://www.mdpi.com/2073-8994/12/6/993?utm_source=chatgpt.com)
2. Span Pointer Networks for Non-Autoregressive Task-Oriented Semantic Parsing — 2021, Findings of EMNLP, arXiv:2104.07275. It predicts source-span endpoints instead of regenerating entity text, reaching 87% exact match on TOPv2 while reducing output vocabulary and decoding cost. It uses a much larger pretrained encoder, so it is not evidence for sub-1M performance. Try: make subject/object pure `(start,end)` pointer heads and never let the network spell names. [ACL Anthology](https://aclanthology.org/2021.findings-emnlp.161/?utm_source=chatgpt.com)
3. Slot Filling with Delexicalized Sentence Generation — 2018, Interspeech. Replacing concrete slot values with abstract labels made learning less dependent on particular words. More recent robustness evidence likewise finds large relation-extraction drops when entity names are merely changed; Entity Variation Robust Training counters this using renamed examples plus consistency training. Try: randomly replace every person/company with OPQ1…OPQ8 during training while retaining pointers to the original spans, and require predictions to remain unchanged after renaming. [ISCA Archive+1](https://www.isca-archive.org/interspeech_2018/shin18_interspeech.html?utm_source=chatgpt.com)

A complete under-1M pointer/copy semantic parser with published results on unseen-template and unseen-name splits: not found.

B. Compositional generalization / unseen templates

4. Good-Enough Compositional Data Augmentation (GECA) — 2020, ACL, arXiv:1904.09545. GECA recombines fragments that occurred in compatible contexts; it reduced errors by as much as 87% on SCAN diagnostics and 16% on semantic parsing. Try: automatically recombine relation phrases, act forms, names, question wrappers, negation, and possessive constructions while preserving semantic roles. [ACL Anthology](https://aclanthology.org/2020.acl-main.676/?utm_source=chatgpt.com)
5. Span-based Semantic Parsing for Compositional Generalization — 2021, ACL-IJCNLP. Representing meaning as compositions over input spans raised average compositional-split accuracy from 61.0 to 88.9 versus sequence models across their tests. Try: factor your frame directly into act/relation/span decisions rather than generating a serialized frame token-by-token. [ACL Anthology](https://aclanthology.org/2021.acl-long.74/?utm_source=chatgpt.com)
6. The Devil is in the Detail: Simple Tricks Improve Systematic Generalization of Transformers — 2021, EMNLP. Relative positional representations plus otherwise small training changes produced major SCAN/COGS gains, including reported COGS improvement from about 35% to 81%. Try: feed each pointer scorer relative distance/direction to relation-cue tokens instead of relying only on absolute positions. [ACL Anthology](https://aclanthology.org/2021.emnlp-main.49/?utm_source=chatgpt.com)

C. Abstention / preventing silent wrong writes

7. Calibrated Interpretation: Confidence Estimation in Semantic Parsing — 2023, TACL 11, arXiv:2211.07443. Sequence confidence based on the minimum token confidence was substantially better calibrated than averaging confidence, because one dangerous low-confidence decision is otherwise hidden by several easy ones. Try: define frame confidence as the minimum calibrated confidence across act, relation, both span endpoints, and direction. [ACL Anthology+1](https://aclanthology.org/2023.tacl-1.69/?utm_source=chatgpt.com)
8. Learn then Test: Calibrating Predictive Algorithms to Achieve Risk Control — 2025, Annals of Applied Statistics; arXiv:2110.01052. LTT chooses decision thresholds on held-out calibration data to give finite-sample risk control without retraining the predictor. Try: calibrate a WRITE/ASK threshold to an explicit maximum wrong-write rate; below it, always clarify. This is simpler than ensembles and more directly aligned with your objective than ordinary conformal coverage. Very-low error targets require correspondingly large calibration sets, so “near zero at reasonable coverage” cannot be promised beforehand. [Stanford Graduate School of Business+1](https://www.gsb.stanford.edu/faculty-research/publications/learn-then-test-calibrating-predictive-algorithms-achieve-risk?utm_source=chatgpt.com)

Parser-specific evidence demonstrating near-zero accepted error at high coverage: not found.

D. Reversed subject/object errors

9. Joint extraction of entities and relations by entity role recognition — 2022, Cognitive Robotics 2, DOI:10.1016/j.cogr.2022.11.001. It explicitly predicts semantic entity roles, distinguishing normal versus reversed subject/object orientation instead of expecting the relation classifier to encode direction implicitly. Try: add a tiny `FORWARD / REVERSE / NONE` role head and require agreement between it and the subject/object pointers. [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2667241322000210?utm_source=chatgpt.com)

For possessive canonicalization specifically in tiny semantic parsers: not found. The strongest transferable intervention I found is explicit role supervision plus contrastive minimal pairs such as “X is Y’s mother” / “Y’s mother is X” / “Y is X’s mother.”

E. Open evaluation data

10. WebRED — 2021, arXiv:2102.09681, CC BY 4.0. Over 100k web sentences with marked subject/object entities, hundreds of relations, and negative examples. Use only a held-out mapped subset of person/organization relations as natural-language evaluation. [GitHub](https://github.com/google-research-datasets/WebRED?utm_source=chatgpt.com)
11. WikiFact — 2019, KDD dataset accompanying Assessing the Factual Accuracy of Generated Text, CC BY 4.0. Sentences explicitly mark `SUBJ{...}` and `OBJ{...}` and associate them with Wikidata relations, making it unusually well matched to direction testing. [GitHub](https://github.com/google-research-datasets/wikifact?utm_source=chatgpt.com)
12. bAbI — 2015, arXiv:1502.05698, CC BY 3.0. Synthetic rather than natural, but its fact, two-argument relation, negation, and coreference tasks are useful as adversarial tests. CLUTRR would also fit family-relation generalization well, but its CC-BY-NC license is not permissive, so avoid it if permissive licensing is a hard requirement. [Hugging Face+1](https://huggingface.co/datasets/facebook/babi_qa/blob/ab3777b46c6c0d9a4513cd3b82ea6562293837a8/dataset_infos.json?utm_source=chatgpt.com)

Ranked changes most likely to cut silent wrong writes:

1. Calibrated abstention: use minimum-component confidence plus an LTT-calibrated WRITE threshold; everything else becomes ASK.
2. Explicit role/direction prediction: independently predict FORWARD/REVERSE/NONE and reject any frame where role and pointer heads disagree.
3. Counterfactual training: aggressively rename entities and generate GECA-style paired paraphrases, especially swapped-role, possessive, negated, and question/statement traps.
