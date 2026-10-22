# Profile: B3G2 3M accum 4 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model b3g2, 4,023,302 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3g2.json

## profiler

arm B3G2 | rung 3M | accum 4 | batch 256 | device cuda | torch 2.11.0+cu128

CPU op self time per update 5262.8 ms; wall per update 3905.6 ms (profiler overhead included)

| kernel ms/update | kernels/update | mean kernel us | GPU busy / wall | idle gap / wall | launch calls/update | stream syncs/update | DtoH copies/update | CPU op / kernel time | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1391.1 | 75966 | 18.3 | 0.356 | 0.644 | 70618 | 1305.0 | 745.0 | 3.78 | GPU mostly idle: CPU / launch / sync bound |

top 25 CUDA kernels by total time:

| kernel | total ms | count | avg us | share |
|---|---|---|---|---|
| fmha_cutlassB_bf16_aligned_64x64_k64_sm80(PyTorchMemEffAttention::AttentionBackwardKernel< | 461.4 | 298 | 1548.3 | 16.6% |
| void at::native::vectorized_elementwise_kernel<4, at::native::CUDAFunctor_add<c10::BFloat1 | 282.8 | 11688 | 24.2 | 10.2% |
| void at::native::(anonymous namespace)::CatArrayBatchedCopy<at::native::(anonymous namespa | 210.4 | 1902 | 110.6 | 7.6% |
| void at::native::elementwise_kernel<128, 2, at::native::gpu_kernel_impl_nocast<at::native: | 169.8 | 6021 | 28.2 | 6.1% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 153.0 | 3439 | 44.5 | 5.5% |
| void at::native::unrolled_elementwise_kernel<at::native::direct_copy_kernel_cuda(at::Tenso | 107.7 | 11121 | 9.7 | 3.9% |
| void at::native::vectorized_elementwise_kernel<4, at::native::bfloat16_copy_kernel_cuda(at | 87.4 | 12442 | 7.0 | 3.1% |
| void at::native::vectorized_elementwise_kernel<4, at::native::(anonymous namespace)::pow_t | 86.6 | 3104 | 27.9 | 3.1% |
| void at::native::vectorized_elementwise_kernel<4, at::native::FillFunctor<c10::BFloat16>,  | 84.8 | 4725 | 18.0 | 3.0% |
| fmha_cutlassF_bf16_aligned_64x64_rf_sm80(PyTorchMemEffAttention::AttentionKernel<cutlass:: | 84.4 | 796 | 106.1 | 3.0% |
| fmha_cutlassF_bf16_aligned_32x128_gmem_sm80(PyTorchMemEffAttention::AttentionKernel<cutlas | 77.4 | 384 | 201.6 | 2.8% |
| ampere_bf16_s1688gemm_bf16_64x128_sliced1x2_ldg8_f2f_tn | 63.5 | 441 | 144.0 | 2.3% |
| ampere_bf16_s16816gemm_bf16_128x64_ldg8_f2f_tn | 62.6 | 239 | 261.8 | 2.2% |
| void (anonymous namespace)::indexing_backward_kernel<float, 4>(long const*, long const*, f | 55.0 | 380 | 144.8 | 2.0% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 49.8 | 2336 | 21.3 | 1.8% |
| ampere_bf16_s1688gemm_bf16_128x64_sliced1x2_ldg8_f2f_tn | 48.8 | 683 | 71.5 | 1.8% |
| void at::native::reduce_kernel<512, 1, at::native::ReduceOp<float, at::native::MeanOps<flo | 38.4 | 3136 | 12.3 | 1.4% |
| ampere_bf16_s1688gemm_bf16_128x128_ldg8_f2f_stages_32x1_tn | 35.2 | 367 | 96.0 | 1.3% |
| void at::native::vectorized_elementwise_kernel<4, at::native::BinaryFunctor<c10::BFloat16, | 34.9 | 384 | 91.0 | 1.3% |
| void at::native::(anonymous namespace)::vectorized_layer_norm_kernel<float, float, false>( | 31.7 | 3389 | 9.4 | 1.1% |
| void cutlass::Kernel2<cutlass_80_tensorop_bf16_s16816gemm_relu_bf16_64x64_32x6_tn_align8>( | 30.9 | 2265 | 13.6 | 1.1% |
| void at::native::reduce_kernel<128, 4, at::native::ReduceOp<c10::BFloat16, at::native::fun | 28.6 | 4188 | 6.8 | 1.0% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 28.4 | 736 | 38.5 | 1.0% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl<at::native::Binary | 27.7 | 403 | 68.7 | 1.0% |
| void at::native::(anonymous namespace)::layer_norm_grad_input_kernel_vectorized<float, flo | 26.7 | 2424 | 11.0 | 1.0% |

top 25 CPU ops by self time:

| op | self CPU ms (all active) | ms/update | calls | share |
|---|---|---|---|---|
| cudaLaunchKernel | 885.2 | 442.6 | 141237 | 14.5% |
| cudaStreamSynchronize | 459.0 | 229.5 | 2605 | 7.5% |
| aten::mm | 316.6 | 158.3 | 12774 | 5.2% |
| aten::copy_ | 266.2 | 133.1 | 68937 | 4.4% |
| aten::addmm | 257.7 | 128.9 | 5588 | 4.2% |
| aten::empty | 211.0 | 105.5 | 54881 | 3.4% |
| aten::empty_strided | 143.3 | 71.6 | 27624 | 2.3% |
| aten::select | 135.5 | 67.8 | 59856 | 2.2% |
| AddmmBackward0 | 127.6 | 63.8 | 4164 | 2.1% |
| aten::add | 124.0 | 62.0 | 10006 | 2.0% |
| aten::native_layer_norm | 122.2 | 61.1 | 3389 | 2.0% |
| aten::_to_copy | 114.8 | 57.4 | 26296 | 1.9% |
| aten::sum | 114.2 | 57.1 | 6531 | 1.9% |
| aten::add_ | 109.4 | 54.7 | 17673 | 1.8% |
| aten::mul | 105.3 | 52.7 | 10283 | 1.7% |
| DivBackward0 | 101.1 | 50.6 | 455 | 1.7% |
| aten::view | 95.7 | 47.9 | 51616 | 1.6% |
| Command Buffer Full | 88.5 | 44.2 | 973 | 1.4% |
| aten::as_strided | 82.3 | 41.1 | 154038 | 1.3% |
| autograd::engine::evaluate_function: AddmmBackward0 | 79.1 | 39.6 | 4164 | 1.3% |
| aten::transpose | 76.0 | 38.0 | 47524 | 1.2% |
| aten::linear | 72.2 | 36.1 | 13632 | 1.2% |
| aten::pow | 71.5 | 35.7 | 6208 | 1.2% |
| cuLaunchKernel | 69.3 | 34.7 | 10637 | 1.1% |
| aten::slice | 67.4 | 33.7 | 28550 | 1.1% |

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

