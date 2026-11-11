# Profile: B3G2 3M accum 32 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model b3g2, 4,023,302 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3g2.json

## breakdown

arm B3G2 | rung 3M | accum 32 | batch 256 | device cuda | torch 2.11.0+cu128

ms per update (mean / median / p90 over 30 timed updates, every region synced):

| stage | mean | median | p90 | share of wall |
|---|---|---|---|---|
| fetch | 3.5 | 3.3 | 4.4 | 0.0% |
| h2d | 0.3 | 0.2 | 0.6 | 0.0% |
| split_total | 0.2 | 0.2 | 0.2 | 0.0% |
| forward | 4241.3 | 4209.7 | 4818.9 | 55.8% |
| backward | 3292.2 | 3185.2 | 3974.3 | 43.3% |
| clip | 1.4 | 1.4 | 1.8 | 0.0% |
| opt | 0.7 | 0.6 | 0.7 | 0.0% |
| other | 59.9 | 58.5 | 72.2 | 0.8% |
| wall | 7599.5 | 7370.3 | 8729.6 | 100.0% |

forward by group (exclusive, mean ms):

| group | ms | share of forward |
|---|---|---|
| eg_front | 1667.5 | 39.3% |
| writer | 1375.9 | 32.4% |
| thinker_blocks | 715.4 | 16.9% |
| loop_glue | 370.8 | 8.7% |
| reader | 49.7 | 1.2% |
| host_prep | 25.8 | 0.6% |
| other_modules | 22.8 | 0.5% |
| tape_read | 9.7 | 0.2% |
| heads_loss_and_glue | 3.7 | 0.1% |

forward sections (exclusive ms, calls per update, forward-hook calls seen DURING backward = recomputation):

| section | mean ms | median | p90 | calls/update | bwd calls/update |
|---|---|---|---|---|---|
| eg.gemma_forward | 1558.9 | 1526.8 | 1667.8 | 63.4 | 0.0 |
| writer | 936.2 | 923.9 | 1195.9 | 977.9 | 274.0 |
| core.0 | 345.1 | 294.1 | 563.5 | 505.0 | 206.7 |
| core.1 | 296.3 | 275.1 | 374.1 | 505.0 | 206.7 |
| m/loop | 196.8 | 191.7 | 232.5 | 32.0 | 0.0 |
| m/_loss | 174.0 | 169.6 | 207.2 | 32.0 | 0.0 |
| m/ans_pass | 156.6 | 152.3 | 186.1 | 504.9 | 274.0 |
| m/writer.teacher | 143.5 | 142.0 | 165.0 | 505.0 | 0.0 |
| m/call_pass | 118.1 | 113.4 | 142.1 | 473.0 | 0.0 |
| m/think | 73.9 | 60.2 | 82.9 | 505.0 | 0.0 |
| m/eg.align | 66.8 | 67.0 | 71.2 | 400.7 | 0.0 |
| reader | 48.4 | 49.8 | 57.1 | 63.4 | 0.0 |
| m/eg._compute | 26.0 | 25.6 | 27.3 | 63.4 | 0.0 |
| m/answer_teacher | 21.5 | 20.8 | 25.7 | 505.0 | 0.0 |
| m/train_golds | 20.5 | 20.8 | 22.4 | 32.0 | 0.0 |
| ln_z | 20.2 | 19.6 | 24.0 | 505.0 | 0.0 |
| m/read_texts | 7.2 | 7.1 | 7.6 | 32.0 | 0.0 |
| eg_proj | 5.9 | 5.9 | 6.3 | 63.4 | 0.0 |
| m/plan | 4.5 | 4.5 | 4.7 | 32.0 | 0.0 |
| m/eg_term | 4.2 | 4.1 | 4.5 | 63.4 | 0.0 |
| ln_eg | 3.8 | 3.4 | 4.8 | 63.4 | 0.0 |
| stop | 2.6 | 2.6 | 2.7 | 32.0 | 0.0 |
| m/tape_of | 2.5 | 2.4 | 2.7 | 32.0 | 0.0 |
| m/read | 1.3 | 1.2 | 1.3 | 32.0 | 0.0 |
| m/eg.encode | 1.1 | 1.1 | 1.2 | 32.0 | 0.0 |
| m/eg.encode_texts | 0.7 | 0.7 | 0.8 | 31.4 | 0.0 |
| m/num_memory | 0.6 | 0.5 | 0.6 | 32.0 | 0.0 |
| m/slot_kv | 0.2 | 0.2 | 0.2 | 32.0 | 0.0 |

stage times are bracketed by cuda syncs, so wall here is longer than free-running (see throughput); forward sections are EXCLUSIVE of nested sections; bwd_calls = forward-hook calls seen during backward = gradient-checkpoint recomputation
section timing overhead: 8 us per timed section x 6150 sections per update = about 51 ms of the synced wall (methods: all)

synced wall 7600 ms per update vs free-running 7591 ms per update (throughput section): the stage split is shares of the SYNCED time, scale to the free-running number with care.

## throughput

arm B3G2 | rung 3M | accum 32 | batch 256 | device cuda | torch 2.11.0+cu128 | variant baseline

| s/update | updates/s | median chunk | p90 chunk | peak alloc GB | peak reserved GB |
|---|---|---|---|---|---|
| 7.5913 | 0.13 | 7.4717 | 8.0590 | 1.50 | 1.70 |

## padding

arm B3G2 | rung 3M | accum 32 | batch 256 | device cuda | torch 2.11.0+cu128

row prompt length (bytes): mean 176, p50 117, p90 278, p99 698, max 2000, share over 280: 2.2%; padded width W of a 256-row update: mean 1561, p10 963, p50 1300, p90 1998, max 2000 (cap 2000); 300 updates

fraction of padded positions that are real (ratio of sums over the updates):

| accum | quantity | what the code does today | full width W | own widest, random rows | sorted + own widest | linear cost today/sorted | quadratic cost today/sorted |
|---|---|---|---|---|---|---|---|
| 1 | prompt | full | 11.3% | 11.3% | 11.3% | 1.00 | 1.00 |
| 2 | prompt | full | 11.3% | 14.1% | 21.0% | 1.86 | 1.99 |
| 4 | prompt | full | 11.3% | 19.0% | 34.6% | 3.07 | 3.86 |
| 8 | prompt | full | 11.3% | 26.2% | 52.2% | 4.64 | 7.34 |
| 16 | prompt | full | 11.3% | 35.6% | 70.8% | 6.28 | 13.39 |
| 32 | prompt | full | 11.3% | 45.3% | 85.5% | 7.59 | 22.58 |

thinker rounds per row (accum 32, 60 updates): random: mean 15.12 (rows with calls 15.14, without 15.11, share with calls 37%); sorted: mean 15.11 (rows with calls 15.18, without 15.06, share with calls 37%)

prompt = the columns of prompt_ids that split_batch hands every micro-batch: today the full batch width W (this is what the reader / Gemma-front adapter / b3g2 thinker see). For the plain arms the transformer itself already trims to the micro-batch's widest row (plain_tf_steps.py loss: W = max(2 + len + target)), so for "seq" (= prompt + 2 + target) today is "own widest". Cost ratios are rows x width (linear) and rows x width^2 (attention-like) of today over sorted + own widest, not seconds.

## syncs

arm B3G2 | rung 3M | accum 32 | batch 256 | device cuda | torch 2.11.0+cu128

8021.0 synchronising calls per update

| python line | calls per update |
|---|---|
| writer.py:138 | 1822.0 |
| b3g2.py:350 | 1270.5 |
| writer.py:121 | 911.0 |
| b3g2.py:551 | 455.5 |
| b3g2.py:553 | 455.5 |
| b3g2.py:554 | 455.5 |
| b3g2.py:355 | 423.5 |
| b3g2.py:361 | 423.5 |
| b3g2.py:374 | 423.5 |
| b3g2.py:375 | 423.5 |
| b3g2.py:376 | 423.5 |
| eg.py:108 | 125.0 |
| masking_utils.py:335 | 125.0 |
| eg.py:128 | 125.0 |
| b3g2.py:224 | 32.0 |
| b3g2.py:535 | 32.0 |
| b3g2.py:536 | 32.0 |
| tool.py:175 | 32.0 |
| tool.py:180 | 30.5 |

