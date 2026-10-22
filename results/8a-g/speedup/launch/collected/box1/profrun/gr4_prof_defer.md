# Profile: B3G2 3M accum 4 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model b3g2, 4,023,302 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3g2.json

## profiler

arm B3G2 | rung 3M | accum 4 | batch 256 | device cuda | torch 2.11.0+cu128 | variant defer

CPU op self time per update 2868.0 ms; wall per update 2178.9 ms (profiler overhead included)

| kernel ms/update | kernels/update | mean kernel us | GPU busy / wall | idle gap / wall | launch calls/update | stream syncs/update | DtoH copies/update | CPU op / kernel time | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1336.0 | 44830 | 29.7 | 0.613 | 0.387 | 42239 | 62.5 | 20.0 | 2.15 | GPU busy >= 60% of wall |

top 25 CUDA kernels by total time:

| kernel | total ms | count | avg us | share |
|---|---|---|---|---|
| fmha_cutlassB_bf16_aligned_64x64_k64_sm80(PyTorchMemEffAttention::AttentionBackwardKernel< | 460.3 | 298 | 1544.5 | 17.2% |
| void at::native::vectorized_elementwise_kernel<4, at::native::CUDAFunctor_add<c10::BFloat1 | 277.4 | 6346 | 43.7 | 10.4% |
| void at::native::(anonymous namespace)::CatArrayBatchedCopy<at::native::(anonymous namespa | 210.0 | 1902 | 110.4 | 7.9% |
| void at::native::elementwise_kernel<128, 2, at::native::gpu_kernel_impl_nocast<at::native: | 169.0 | 5880 | 28.7 | 6.3% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 152.6 | 3104 | 49.2 | 5.7% |
| void at::native::unrolled_elementwise_kernel<at::native::direct_copy_kernel_cuda(at::Tenso | 103.0 | 7726 | 13.3 | 3.9% |
| void at::native::vectorized_elementwise_kernel<4, at::native::(anonymous namespace)::pow_t | 87.5 | 3104 | 28.2 | 3.3% |
| void at::native::vectorized_elementwise_kernel<4, at::native::bfloat16_copy_kernel_cuda(at | 84.1 | 7811 | 10.8 | 3.1% |
| void at::native::vectorized_elementwise_kernel<4, at::native::FillFunctor<c10::BFloat16>,  | 83.8 | 3710 | 22.6 | 3.1% |
| fmha_cutlassF_bf16_aligned_64x64_rf_sm80(PyTorchMemEffAttention::AttentionKernel<cutlass:: | 83.4 | 456 | 182.9 | 3.1% |
| fmha_cutlassF_bf16_aligned_32x128_gmem_sm80(PyTorchMemEffAttention::AttentionKernel<cutlas | 77.2 | 384 | 201.0 | 2.9% |
| ampere_bf16_s1688gemm_bf16_64x128_sliced1x2_ldg8_f2f_tn | 63.2 | 441 | 143.3 | 2.4% |
| ampere_bf16_s16816gemm_bf16_128x64_ldg8_f2f_tn | 62.2 | 239 | 260.3 | 2.3% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 49.7 | 2336 | 21.3 | 1.9% |
| ampere_bf16_s1688gemm_bf16_128x64_sliced1x2_ldg8_f2f_tn | 48.5 | 683 | 71.0 | 1.8% |
| void (anonymous namespace)::indexing_backward_kernel<float, 4>(long const*, long const*, f | 42.2 | 31 | 1362.2 | 1.6% |
| void at::native::reduce_kernel<512, 1, at::native::ReduceOp<float, at::native::MeanOps<flo | 38.5 | 3136 | 12.3 | 1.4% |
| ampere_bf16_s1688gemm_bf16_128x128_ldg8_f2f_stages_32x1_tn | 35.1 | 367 | 95.5 | 1.3% |
| void at::native::vectorized_elementwise_kernel<4, at::native::BinaryFunctor<c10::BFloat16, | 34.8 | 384 | 90.5 | 1.3% |
| void at::native::(anonymous namespace)::vectorized_layer_norm_kernel<float, float, false>( | 28.3 | 1548 | 18.3 | 1.1% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 28.2 | 736 | 38.3 | 1.1% |
| void cutlass::Kernel2<cutlass_80_tensorop_bf16_s16816gemm_relu_bf16_64x64_32x6_tn_align8>( | 28.1 | 1520 | 18.5 | 1.1% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl<at::native::Binary | 27.1 | 231 | 117.4 | 1.0% |
| void at::native::(anonymous namespace)::layer_norm_grad_input_kernel_vectorized<float, flo | 25.2 | 1129 | 22.3 | 0.9% |
| void at::native::vectorized_elementwise_kernel<4, at::native::GeluCUDAKernelImpl(at::Tenso | 25.1 | 768 | 32.6 | 0.9% |

top 25 CPU ops by self time:

| op | self CPU ms (all active) | ms/update | calls | share |
|---|---|---|---|---|
| cudaLaunchKernel | 508.5 | 254.3 | 84478 | 14.5% |
| cudaStreamSynchronize | 422.7 | 211.3 | 120 | 12.1% |
| aten::mm | 196.1 | 98.0 | 7772 | 5.6% |
| aten::copy_ | 137.4 | 68.7 | 19734 | 3.9% |
| aten::addmm | 131.8 | 65.9 | 2868 | 3.8% |
| aten::empty | 109.1 | 54.6 | 23640 | 3.1% |
| AddmmBackward0 | 100.0 | 50.0 | 2092 | 2.9% |
| aten::empty_strided | 93.1 | 46.5 | 17110 | 2.7% |
| aten::add | 88.1 | 44.0 | 7558 | 2.5% |
| aten::mul | 87.6 | 43.8 | 8676 | 2.5% |
| Command Buffer Full | 85.9 | 43.0 | 928 | 2.5% |
| aten::pow | 73.1 | 36.5 | 6208 | 2.1% |
| aten::_to_copy | 67.6 | 33.8 | 15782 | 1.9% |
| aten::native_layer_norm | 58.3 | 29.1 | 1548 | 1.7% |
| aten::sum | 56.4 | 28.2 | 2829 | 1.6% |
| aten::add_ | 54.2 | 27.1 | 8851 | 1.6% |
| aten::view | 53.4 | 26.7 | 24481 | 1.5% |
| aten::mean | 46.2 | 23.1 | 3136 | 1.3% |
| aten::transpose | 44.6 | 22.3 | 29022 | 1.3% |
| aten::linear | 40.4 | 20.2 | 8370 | 1.2% |
| autograd::engine::evaluate_function: AddmmBackward0 | 40.3 | 20.1 | 2092 | 1.2% |
| aten::convolution_backward | 39.3 | 19.6 | 32 | 1.1% |
| aten::t | 37.3 | 18.6 | 14886 | 1.1% |
| aten::as_strided | 33.2 | 16.6 | 48562 | 0.9% |
| cuLaunchKernel | 33.1 | 16.6 | 5124 | 0.9% |

## syncs

arm B3G2 | rung 3M | accum 4 | batch 256 | device cuda | torch 2.11.0+cu128 | variant defer

60.0 synchronising calls per update

| python line | calls per update |
|---|---|
| eg.py:108 | 16.0 |
| masking_utils.py:335 | 16.0 |
| eg.py:128 | 16.0 |
| tool.py:175 | 4.0 |
| tool.py:180 | 4.0 |
| defer.py:324 | 4.0 |

