# Profile: B3G2 3M accum 4 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model b3g2, 4,023,302 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3g2.json

## profiler

arm B3G2 | rung 3M | accum 4 | batch 256 | device cuda | torch 2.11.0+cu128

CPU op self time per update 4705.0 ms; wall per update 3492.4 ms (profiler overhead included)

| kernel ms/update | kernels/update | mean kernel us | GPU busy / wall | idle gap / wall | launch calls/update | stream syncs/update | DtoH copies/update | CPU op / kernel time | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 4906.6 | 75967 | 64.5 | 0.998 | 0.002 | 70618 | 1305.0 | 745.0 | 0.96 | GPU-bound |

top 25 CUDA kernels by total time:

| kernel | total ms | count | avg us | share |
|---|---|---|---|---|
| ProfilerStep* | 6972.2 | 2 | 3486077.2 | 71.0% |
| fmha_cutlassB_bf16_aligned_64x64_k64_sm80(PyTorchMemEffAttention::AttentionBackwardKernel< | 481.4 | 298 | 1615.5 | 4.9% |
| void at::native::vectorized_elementwise_kernel<4, at::native::CUDAFunctor_add<c10::BFloat1 | 283.4 | 11688 | 24.2 | 2.9% |
| void at::native::(anonymous namespace)::CatArrayBatchedCopy<at::native::(anonymous namespa | 214.1 | 1902 | 112.6 | 2.2% |
| void at::native::elementwise_kernel<128, 2, at::native::gpu_kernel_impl_nocast<at::native: | 170.9 | 6021 | 28.4 | 1.7% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 154.8 | 3439 | 45.0 | 1.6% |
| void at::native::unrolled_elementwise_kernel<at::native::direct_copy_kernel_cuda(at::Tenso | 109.6 | 11121 | 9.9 | 1.1% |
| void at::native::vectorized_elementwise_kernel<4, at::native::bfloat16_copy_kernel_cuda(at | 88.8 | 12442 | 7.1 | 0.9% |
| void at::native::vectorized_elementwise_kernel<4, at::native::(anonymous namespace)::pow_t | 87.4 | 3104 | 28.2 | 0.9% |
| void at::native::vectorized_elementwise_kernel<4, at::native::FillFunctor<c10::BFloat16>,  | 85.2 | 4725 | 18.0 | 0.9% |
| fmha_cutlassF_bf16_aligned_64x64_rf_sm80(PyTorchMemEffAttention::AttentionKernel<cutlass:: | 84.8 | 796 | 106.5 | 0.9% |
| fmha_cutlassF_bf16_aligned_32x128_gmem_sm80(PyTorchMemEffAttention::AttentionKernel<cutlas | 80.8 | 384 | 210.4 | 0.8% |
| ampere_bf16_s16816gemm_bf16_128x64_ldg8_f2f_tn | 64.1 | 239 | 268.3 | 0.7% |
| ampere_bf16_s1688gemm_bf16_64x128_sliced1x2_ldg8_f2f_tn | 63.5 | 441 | 143.9 | 0.6% |
| void (anonymous namespace)::indexing_backward_kernel<float, 4>(long const*, long const*, f | 57.4 | 380 | 151.0 | 0.6% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 50.6 | 2336 | 21.6 | 0.5% |
| ampere_bf16_s1688gemm_bf16_128x64_sliced1x2_ldg8_f2f_tn | 49.6 | 683 | 72.7 | 0.5% |
| void at::native::reduce_kernel<512, 1, at::native::ReduceOp<float, at::native::MeanOps<flo | 39.5 | 3136 | 12.6 | 0.4% |
| ampere_bf16_s1688gemm_bf16_128x128_ldg8_f2f_stages_32x1_tn | 36.1 | 367 | 98.5 | 0.4% |
| void at::native::vectorized_elementwise_kernel<4, at::native::BinaryFunctor<c10::BFloat16, | 35.0 | 384 | 91.0 | 0.4% |
| void at::native::(anonymous namespace)::vectorized_layer_norm_kernel<float, float, false>( | 32.3 | 3389 | 9.5 | 0.3% |
| void cutlass::Kernel2<cutlass_80_tensorop_bf16_s16816gemm_relu_bf16_64x64_32x6_tn_align8>( | 31.8 | 2265 | 14.1 | 0.3% |
| void at::native::reduce_kernel<128, 4, at::native::ReduceOp<c10::BFloat16, at::native::fun | 29.8 | 4188 | 7.1 | 0.3% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 28.4 | 736 | 38.5 | 0.3% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl<at::native::Binary | 27.7 | 403 | 68.8 | 0.3% |

top 25 CPU ops by self time:

| op | self CPU ms (all active) | ms/update | calls | share |
|---|---|---|---|---|
| cudaLaunchKernel | 915.3 | 457.7 | 141237 | 16.5% |
| cudaStreamSynchronize | 481.1 | 240.5 | 2605 | 8.7% |
| aten::mm | 263.7 | 131.9 | 12774 | 4.8% |
| aten::copy_ | 232.4 | 116.2 | 68937 | 4.2% |
| aten::addmm | 212.0 | 106.0 | 5588 | 3.8% |
| aten::empty | 180.7 | 90.3 | 54881 | 3.3% |
| aten::empty_strided | 124.8 | 62.4 | 27624 | 2.2% |
| aten::select | 117.0 | 58.5 | 59856 | 2.1% |
| Command Buffer Full | 114.2 | 57.1 | 1231 | 2.1% |
| AddmmBackward0 | 106.0 | 53.0 | 4164 | 1.9% |
| aten::add | 104.1 | 52.0 | 10006 | 1.9% |
| aten::native_layer_norm | 102.3 | 51.2 | 3389 | 1.8% |
| aten::_to_copy | 97.0 | 48.5 | 26296 | 1.7% |
| aten::sum | 96.9 | 48.4 | 6531 | 1.7% |
| aten::add_ | 96.1 | 48.1 | 17673 | 1.7% |
| aten::mul | 91.9 | 45.9 | 10283 | 1.7% |
| aten::view | 88.0 | 44.0 | 51616 | 1.6% |
| DivBackward0 | 81.4 | 40.7 | 455 | 1.5% |
| cuLaunchKernel | 74.9 | 37.4 | 10637 | 1.3% |
| aten::as_strided | 74.3 | 37.2 | 154038 | 1.3% |
| aten::transpose | 71.7 | 35.8 | 47524 | 1.3% |
| autograd::engine::evaluate_function: AddmmBackward0 | 71.5 | 35.7 | 4164 | 1.3% |
| aten::linear | 63.6 | 31.8 | 13632 | 1.1% |
| aten::pow | 63.3 | 31.6 | 6208 | 1.1% |
| aten::slice | 61.3 | 30.6 | 28550 | 1.1% |

## syncs

arm B3G2 | rung 3M | accum 4 | batch 256 | device cuda | torch 2.11.0+cu128

1319.5 synchronising calls per update

| python line | calls per update |
|---|---|
| writer.py:138 | 302.0 |
| b3g2.py:350 | 214.5 |
| writer.py:121 | 151.0 |
| b3g2.py:551 | 75.5 |
| b3g2.py:553 | 75.5 |
| b3g2.py:554 | 75.5 |
| b3g2.py:355 | 71.5 |
| b3g2.py:361 | 71.5 |
| b3g2.py:374 | 71.5 |
| b3g2.py:375 | 71.5 |
| b3g2.py:376 | 71.5 |
| eg.py:108 | 16.0 |
| masking_utils.py:335 | 16.0 |
| eg.py:128 | 16.0 |
| b3g2.py:224 | 4.0 |
| b3g2.py:535 | 4.0 |
| b3g2.py:536 | 4.0 |
| tool.py:175 | 4.0 |
| tool.py:180 | 4.0 |

