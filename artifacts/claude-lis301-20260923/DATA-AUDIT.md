# lis-301 data audit (2026-09-23)

- **New rows:** three Opus writers each wrote 500 rows (opus_w4, opus_w5, opus_w6), with families weighted to the lis-300 dev errors (PASSMARKS). Three separate blind Opus labellers relabelled the rows without seeing the frames (relabel_w4..w6). `claude_lis300_agree.py` compares each pair.
- **Agreed rows:** w4 454/500, w5 483/500, w6 440/500, so 1,377 rows in total (agreed_ids.txt).
- **Main disputes:**
  - "Y, not X" contrast turns: act STATE plus a NEGATED fact, or act CORRECT.
  - "lives in": city or home.
  - Some pronoun calls.

  Disputed rows are dropped, not adjudicated.
- **Agreed rows by family:** direction 180, reported 135, pronoun_ambiguous 131, verb_rel 120, pronoun_clear 118, check 117, mixed_tell_ask 96, suppose 73, typo 69, correct 68, other_rel 60, plan 60, short_answer 56, plain_tell 55, contrast_owner 39.
- **Dev key fix:** a blind relabel of the 439 opus_dev and o0a2 dev turns. 394 were kept (dev_agreed_ids.txt), and 45 were dropped because the scored fields disagree.
- **CPU smoke run of `claude_lis301_data.py`:**
  - train 36,972 rows: o0b 27,000, opus 5,012, opus301 4,960;
  - dev 959 rows: o0b_l2 428, opus_dev 131, o0a2 263, opus301_dev 137.

  The lis-300 part rebuilt to the same counts as before (27,000 + 5,012 train, 867 dev).
- **Longest row:** prompt plus target is 701 characters, which is under the 256-token max length.
- **Blind panel 301:** only 1 panel turn is also a training turn, a 2-word chat line.
