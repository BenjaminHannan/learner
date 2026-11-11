# CPU equivalence runs on Ben's M1 Pro Mac (E2 / E3, real EmbeddingGemma 2, fp32)

Byte-identical copies of the small outputs in `~/speedup/out/` on the Mac. All runs: `prof_train.py --arm PTS --rung 3M --accum 16 --data ~/speedup/pool-sample --pkg-root ~/speedup/pkg --device cpu --eg real --sections equiv --equiv-check --curve-updates 0`, under `caffeinate -i nice -n 10`, OMP_NUM_THREADS=8, a perl alarm cap, the ~/fable-test venv (Python 3.12.14, torch 2.14.1, transformers 5.19.0), CUSTOM_IO_EG2 = the EmbeddingGemma-2 folder used for g1diag, package = `git archive 74d6e92c75 custom_io` (src-b3g2), caps = package default `custom_io/g8a/caps_b3s.json`. Pool sample = every 67th line (from line 0) of the PC's `p10-rung30-s400-a64-L/train.jsonl` (20,049 of 1,343,273 rows, all CRLF; sample sha256 9c8993731b72dfb5921681e866e2f5b80a785e0745d8b3f32250f3992f749876) plus that pool's charvocab.json; neither is copied here.

| file | bytes | sha256 | harness prof_train.py sha256 | run (ET, 2026-10-13) | equiv list / seed |
|---|---|---|---|---|---|
| test_prof.log | 7135 | 43a64347a6eb120e6c801fba59ee986312062a0d6f36654f0113816ce61df2dc | 912045830f968526e9d92f5a48fe46e47a78b4c08a69b301b05f4f3e3728dbe1 (test_prof.py bb69c8ce082830aae753bfe7bf17687c7608ec97e9cd9c70d714770fa8577ad9) | 11:09 PM | 24 of 24 passed |
| equiv_cpu.json | 11912 | dc67a4ddbe045d5280dd9aab54c9440ea09f082fb3a3d2210648ed75b7558bf5 | 912045830f968526e9d92f5a48fe46e47a78b4c08a69b301b05f4f3e3728dbe1 | 11:18:13-11:21:40 PM | eg_once;eg_sorted;sortpad;sortpad,oldw;bigmb,oldw;prefetch / 400 |
| equiv_cpu.md | 2627 | c01e865c684661e077a790767d0158872627c520744693a51d19720f35318364 | same | same | same |
| equiv_cpu_v2.json | 5745 | e91a401e01bfa3cb9254973952d02260aae3179e06ba0637cfefd0947d85d14c | c8acb7df50b2b7857b8671c26e24188f5ac5a5b8cae6df251b426cf7e9bc54c4 | 11:34:22-11:36:21 PM | eg_once / 400 |
| equiv_cpu_v2.md | 2106 | 8ca570854c7ce50b096e3fa6065fb13e4903d7ecb0798ac4da1701b69e4fbdac | same | same | same |
| equiv_cpu_s401.json | 5894 | 5a66014c0e1e3a7f62c5c1e26f33bbdd114b56d8cbf458c91a03bb90d206a82c | 91041f40ee157f1d01fee745a6c77eb494242f91593c8b6c67991a3b477f9bbc | 11:41:24-11:42:54 PM | eg_once / 401 |
| equiv_cpu_s401.md | 2334 | 03db2a122f8ecb14ec8ae7cb277bdc9f32ee2377e276a1b4a2102bf285c12f74 | same | same | same |
| equiv_cpu_s402.json | 5955 | 2d62b30b78390d696cbbcfa79fb16add89bbaeacc8e81c0f4c502634a9d636da | 91041f40ee157f1d01fee745a6c77eb494242f91593c8b6c67991a3b477f9bbc | 11:42:54-11:44:49 PM | eg_once / 402 |
| equiv_cpu_s402.md | 2336 | 5ed86262b66396cd55a155e8cb901e75a99f76fa899d56ff5f71d9af8fb3a646 | same | same | same |

Harness commits: 912045… = 6a870a767c, c8acb7… = daee2fd9e9, 91041f… = bbaa4a9a16 (results/8a-g/speedup/prof/prof_train.py).
