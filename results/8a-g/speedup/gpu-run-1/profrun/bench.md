# Profile: PTC 3M accum 16 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model plain_tf_steps_g, 4,023,976 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3s.json

## bench

arm PTC | rung 3M | accum 16 | batch 256 | device cuda | torch 2.11.0+cu128

| variant | median s/update | speed vs baseline | peak GB | runs |
|---|---|---|---|---|
| baseline | 0.7648 | 1.000 | 2.09 | 0.6188; 0.9109 |
| eg_once | 0.4191 | 1.825 | 2.49 | 0.4137; 0.4245 |
| sortpad,oldw | 0.6015 | 1.271 | 2.09 | 0.5693; 0.6338 |
| sortpad,bigmb,oldw | 0.3830 | 1.997 | 3.56 | 0.3834; 0.3827 |
| eg_once,sortpad,oldw | 0.4268 | 1.792 | 2.49 | 0.4354; 0.4182 |
| eg_once,sortpad,bigmb,oldw,prefetch | 0.3617 | 2.115 | 3.61 | 0.3956; 0.3277 |
| tf32 | 0.6299 | 1.214 | 2.09 | 0.6156; 0.6443 |

