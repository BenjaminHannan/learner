# Profile: PTC 3M accum 16 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model plain_tf_steps_g, 4,023,976 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3s.json

## breakdown

arm PTC | rung 3M | accum 16 | batch 256 | device cuda | torch 2.11.0+cu128

ms per update (mean / median / p90 over 30 timed updates, every region synced):

| stage | mean | median | p90 | share of wall |
|---|---|---|---|---|
| fetch | 6.7 | 5.1 | 11.1 | 0.8% |
| h2d | 0.4 | 0.3 | 0.6 | 0.0% |
| split_total | 0.2 | 0.1 | 0.3 | 0.0% |
| forward | 749.2 | 589.3 | 1135.9 | 86.1% |
| backward | 108.9 | 108.2 | 120.8 | 12.5% |
| clip | 0.7 | 0.5 | 1.0 | 0.1% |
| opt | 0.6 | 0.5 | 0.9 | 0.1% |
| other | 3.7 | 2.6 | 5.6 | 0.4% |
| wall | 870.3 | 713.7 | 1265.6 | 100.0% |

forward by group (exclusive, mean ms):

| group | ms | share of forward |
|---|---|---|
| eg_front | 685.8 | 91.5% |
| thinker_blocks | 34.4 | 4.6% |
| heads_loss_and_glue | 16.7 | 2.2% |
| host_prep | 9.7 | 1.3% |
| embed_norm | 2.5 | 0.3% |

forward sections (exclusive ms, calls per update, forward-hook calls seen DURING backward = recomputation):

| section | mean ms | median | p90 | calls/update | bwd calls/update |
|---|---|---|---|---|---|
| eg.gemma_forward | 597.4 | 467.5 | 905.5 | 16.0 | 0.0 |
| m/eg.align | 65.3 | 48.0 | 103.3 | 256.0 | 0.0 |
| m/eg._compute | 12.1 | 9.9 | 18.3 | 16.0 | 0.0 |
| blocks.0 | 9.5 | 8.0 | 13.7 | 16.0 | 0.0 |
| blocks.1 | 8.6 | 7.3 | 12.2 | 16.0 | 0.0 |
| blocks.2 | 8.2 | 7.2 | 11.8 | 16.0 | 0.0 |
| blocks.3 | 8.1 | 7.1 | 11.7 | 16.0 | 0.0 |
| m/_targets | 6.2 | 4.5 | 9.6 | 16.0 | 0.0 |
| m/_set_front | 3.9 | 4.1 | 5.7 | 16.0 | 0.0 |
| m/_calc_loss_mask | 3.5 | 2.4 | 5.9 | 16.0 | 0.0 |
| eg_proj | 3.3 | 3.1 | 4.7 | 16.0 | 0.0 |
| ln_eg | 3.0 | 3.1 | 4.4 | 16.0 | 0.0 |
| tok | 1.3 | 0.9 | 2.1 | 16.0 | 0.0 |
| m/eg.encode | 0.7 | 0.5 | 1.1 | 16.0 | 0.0 |
| ln_f | 0.7 | 0.5 | 1.0 | 16.0 | 0.0 |
| pos | 0.6 | 0.4 | 0.9 | 16.0 | 0.0 |

stage times are bracketed by cuda syncs, so wall here is longer than free-running (see throughput); forward sections are EXCLUSIVE of nested sections; bwd_calls = forward-hook calls seen during backward = gradient-checkpoint recomputation
section timing overhead: 13 us per timed section x 496 sections per update = about 6 ms of the synced wall (methods: all)

synced wall 870 ms per update vs free-running 739 ms per update (throughput section): the stage split is shares of the SYNCED time, scale to the free-running number with care.

## throughput

arm PTC | rung 3M | accum 16 | batch 256 | device cuda | torch 2.11.0+cu128 | variant baseline

| s/update | updates/s | median chunk | p90 chunk | peak alloc GB | peak reserved GB |
|---|---|---|---|---|---|
| 0.7386 | 1.35 | 0.6247 | 0.9838 | 2.09 | 2.43 |

## profiler

arm PTC | rung 3M | accum 16 | batch 256 | device cuda | torch 2.11.0+cu128

CPU op self time per update 1247.2 ms; wall per update 1090.5 ms (profiler overhead included)

| kernel ms/update | kernels/update | mean kernel us | GPU busy / wall | idle gap / wall | launch calls/update | stream syncs/update | DtoH copies/update | CPU op / kernel time | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1380.0 | 47878 | 28.8 | 0.995 | 0.005 | 44875 | 178.3 | 48.0 | 0.90 | GPU-bound |

top 25 CUDA kernels by total time:

| kernel | total ms | count | avg us | share |
|---|---|---|---|---|
| ProfilerStep* | 3255.2 | 3 | 1085074.8 | 78.6% |
| void cutlass::Kernel2<cutlass_80_tensorop_bf16_s16816gemm_relu_bf16_64x64_32x6_tn_align8>( | 144.3 | 7108 | 20.3 | 3.5% |
| void at::native::elementwise_kernel<128, 2, at::native::gpu_kernel_impl_nocast<at::native: | 85.2 | 17616 | 4.8 | 2.1% |
| void at::native::unrolled_elementwise_kernel<at::native::direct_copy_kernel_cuda(at::Tenso | 78.8 | 19920 | 4.0 | 1.9% |
| fmha_cutlassF_bf16_aligned_32x128_gmem_sm80(PyTorchMemEffAttention::AttentionKernel<cutlas | 41.5 | 1152 | 36.0 | 1.0% |
| void at::native::vectorized_elementwise_kernel<4, at::native::bfloat16_copy_kernel_cuda(at | 39.5 | 12144 | 3.3 | 1.0% |
| void at::native::vectorized_elementwise_kernel<4, at::native::(anonymous namespace)::pow_t | 39.0 | 9312 | 4.2 | 0.9% |
| void at::native::reduce_kernel<512, 1, at::native::ReduceOp<float, at::native::MeanOps<flo | 33.2 | 9312 | 3.6 | 0.8% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 32.2 | 7008 | 4.6 | 0.8% |
| ampere_bf16_s16816gemm_bf16_128x64_ldg8_f2f_stages_32x6_tn | 24.0 | 2522 | 9.5 | 0.6% |
| ampere_bf16_s1688gemm_bf16_64x128_sliced1x2_ldg8_f2f_tn | 23.6 | 391 | 60.4 | 0.6% |
| void at::native::(anonymous namespace)::CatArrayBatchedCopy<at::native::(anonymous namespa | 21.0 | 2496 | 8.4 | 0.5% |
| void at::native::(anonymous namespace)::GammaBetaBackwardCUDAKernelTemplate<float, float,  | 20.9 | 480 | 43.6 | 0.5% |
| void pytorch_flash::flash_bwd_dq_dk_dv_loop_seqk_parallel_kernel<Flash_bwd_kernel_traits<6 | 18.6 | 192 | 97.1 | 0.5% |
| ampere_bf16_s1688gemm_bf16_128x64_sliced1x2_ldg8_f2f_tn | 17.6 | 418 | 42.0 | 0.4% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 16.7 | 3312 | 5.0 | 0.4% |
| void at::native::(anonymous namespace)::vectorized_layer_norm_kernel<float, float, false>( | 12.2 | 480 | 25.4 | 0.3% |
| void cutlass::Kernel2<cutlass_80_tensorop_bf16_s16816gemm_bf16_128x64_64x3_nt_align2>(cutl | 11.0 | 371 | 29.7 | 0.3% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 10.7 | 2112 | 5.1 | 0.3% |
| void at::native::vectorized_elementwise_kernel<4, at::native::rsqrt_kernel_cuda(at::Tensor | 10.2 | 9312 | 1.1 | 0.2% |
| void at::native::vectorized_elementwise_kernel<4, at::native::CUDAFunctorOnSelf_add<float> | 9.5 | 9318 | 1.0 | 0.2% |
| void at::native::vectorized_elementwise_kernel<4, at::native::CUDAFunctor_add<float>, std: | 9.3 | 3045 | 3.1 | 0.2% |
| void pytorch_flash::flash_fwd_kernel<Flash_fwd_kernel_traits<64, 128, 128, 4, false, false | 9.3 | 192 | 48.4 | 0.2% |
| void at::native::vectorized_elementwise_kernel<4, at::native::CUDAFunctor_add<c10::BFloat1 | 8.9 | 3648 | 2.4 | 0.2% |
| void at::native::vectorized_elementwise_kernel<4, at::native::BinaryFunctor<c10::BFloat16, | 8.7 | 1152 | 7.5 | 0.2% |

top 25 CPU ops by self time:

| op | self CPU ms (all active) | ms/update | calls | share |
|---|---|---|---|---|
| cudaLaunchKernel | 560.0 | 186.7 | 134625 | 23.5% |
| aten::mm | 210.8 | 70.3 | 12240 | 8.8% |
| aten::copy_ | 136.6 | 45.5 | 37560 | 5.7% |
| aten::mul | 126.6 | 42.2 | 24963 | 5.3% |
| aten::pow | 113.1 | 37.7 | 18624 | 4.7% |
| aten::empty_strided | 98.0 | 32.7 | 33708 | 4.1% |
| aten::add | 89.7 | 29.9 | 16131 | 3.8% |
| aten::_to_copy | 77.6 | 25.9 | 32748 | 3.3% |
| aten::mean | 72.8 | 24.3 | 9312 | 3.1% |
| cudaStreamSynchronize | 55.5 | 18.5 | 528 | 2.3% |
| aten::empty | 51.1 | 17.0 | 19299 | 2.1% |
| cuLaunchKernel | 43.2 | 14.4 | 9004 | 1.8% |
| aten::transpose | 32.8 | 10.9 | 26688 | 1.4% |
| Activity Buffer Request | 30.9 | 10.3 | 15 | 1.3% |
| aten::matmul | 28.7 | 9.6 | 10512 | 1.2% |
| cudaMemsetAsync | 28.0 | 9.3 | 4912 | 1.2% |
| aten::to | 27.5 | 9.2 | 53946 | 1.2% |
| aten::as_strided | 25.7 | 8.6 | 49727 | 1.1% |
| aten::t | 25.4 | 8.5 | 14784 | 1.1% |
| aten::view | 25.4 | 8.5 | 21696 | 1.1% |
| aten::sum | 23.3 | 7.8 | 1056 | 1.0% |
| aten::cat | 21.2 | 7.1 | 2595 | 0.9% |
| aten::add_ | 19.8 | 6.6 | 2952 | 0.8% |
| aten::linear | 19.6 | 6.5 | 12192 | 0.8% |
| aten::addmm | 18.3 | 6.1 | 816 | 0.8% |

## padding

arm PTC | rung 3M | accum 16 | batch 256 | device cuda | torch 2.11.0+cu128

row prompt length (chars): mean 176, p50 117, p90 278, p99 698, max 2000, share over 280: 2.2%; padded width W of a 256-row update: mean 1561, p10 963, p50 1300, p90 1998, max 2000 (cap 2000); 300 updates

fraction of padded positions that are real (ratio of sums over the updates):

| accum | quantity | what the code does today | full width W | own widest, random rows | sorted + own widest | linear cost today/sorted | quadratic cost today/sorted |
|---|---|---|---|---|---|---|---|
| 1 | prompt | full | 11.3% | 11.3% | 11.3% | 1.00 | 1.00 |
| 1 | seq | own | 12.2% | 12.2% | 12.2% | 1.00 | 1.00 |
| 2 | prompt | full | 11.3% | 14.1% | 21.0% | 1.86 | 1.99 |
| 2 | seq | own | 12.2% | 15.3% | 22.4% | 1.46 | 1.40 |
| 4 | prompt | full | 11.3% | 19.0% | 34.6% | 3.07 | 3.86 |
| 4 | seq | own | 12.2% | 20.5% | 36.6% | 1.79 | 1.74 |
| 8 | prompt | full | 11.3% | 26.2% | 52.2% | 4.64 | 7.34 |
| 8 | seq | own | 12.2% | 28.3% | 54.5% | 1.93 | 1.98 |
| 16 | prompt | full | 11.3% | 35.6% | 70.8% | 6.28 | 13.39 |
| 16 | seq | own | 12.2% | 38.2% | 72.6% | 1.90 | 2.11 |
| 32 | prompt | full | 11.3% | 45.3% | 85.5% | 7.59 | 22.58 |
| 32 | seq | own | 12.2% | 48.3% | 86.6% | 1.79 | 2.14 |

prompt = the columns of prompt_ids that split_batch hands every micro-batch: today the full batch width W (this is what the reader / Gemma-front adapter / b3g2 thinker see). For the plain arms the transformer itself already trims to the micro-batch's widest row (plain_tf_steps.py loss: W = max(2 + len + target)), so for "seq" (= prompt + 2 + target) today is "own widest". Cost ratios are rows x width (linear) and rows x width^2 (attention-like) of today over sorted + own widest, not seconds.

## sweep

arm PTC | rung 3M | accum 16 | batch 256 | device cuda | torch 2.11.0+cu128

| accum | rows/micro-batch | s/update | peak alloc GB | peak reserved GB | note |
|---|---|---|---|---|---|
| 1 | 256 | - | 22.77 | 22.85 | OOM |
| 2 | 128 | 0.9832 | 12.15 | 12.28 |  |
| 4 | 64 | 0.6689 | 6.43 | 6.57 |  |
| 8 | 32 | 0.5208 | 3.56 | 3.64 |  |
| 16 | 16 | 0.7368 | 2.09 | 2.17 |  |
| 32 | 8 | 1.3559 | 1.34 | 1.38 |  |

## syncs

arm PTC | rung 3M | accum 16 | batch 256 | device cuda | torch 2.11.0+cu128

176.0 synchronising calls per update

| python line | calls per update |
|---|---|
| plain_tf_steps.py:207 | 32.0 |
| eg.py:108 | 32.0 |
| masking_utils.py:335 | 32.0 |
| eg.py:128 | 32.0 |
| plain_tf_steps.py:227 | 16.0 |
| plain_tf_steps.py:238 | 16.0 |
| plain_tf_steps.py:243 | 16.0 |

