# Profile: B3G2 3M accum 4 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model b3g2, 4,023,302 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3g2.json

## profiler

arm B3G2 | rung 3M | accum 4 | batch 256 | device cuda | torch 2.11.0+cu128

CPU op self time per update 4700.9 ms; wall per update 3491.6 ms (profiler overhead included)

| kernel ms/update | kernels/update | mean kernel us | GPU busy / wall | idle gap / wall | launch calls/update | stream syncs/update | DtoH copies/update | CPU op / kernel time | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 4900.1 | 75967 | 64.5 | 0.998 | 0.002 | 70618 | 1305.0 | 745.0 | 0.96 | GPU-bound |

top 25 CUDA kernels by total time:

| kernel | total ms | count | avg us | share |
|---|---|---|---|---|
| ProfilerStep* | 6970.7 | 2 | 3485369.9 | 71.1% |
| fmha_cutlassB_bf16_aligned_64x64_k64_sm80(PyTorchMemEffAttention::AttentionBackwardKernel< | 479.2 | 298 | 1607.9 | 4.9% |
| void at::native::vectorized_elementwise_kernel<4, at::native::CUDAFunctor_add<c10::BFloat1 | 283.2 | 11688 | 24.2 | 2.9% |
| void at::native::(anonymous namespace)::CatArrayBatchedCopy<at::native::(anonymous namespa | 213.4 | 1902 | 112.2 | 2.2% |
| void at::native::elementwise_kernel<128, 2, at::native::gpu_kernel_impl_nocast<at::native: | 171.1 | 6021 | 28.4 | 1.7% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 154.4 | 3439 | 44.9 | 1.6% |
| void at::native::unrolled_elementwise_kernel<at::native::direct_copy_kernel_cuda(at::Tenso | 109.2 | 11121 | 9.8 | 1.1% |
| void at::native::vectorized_elementwise_kernel<4, at::native::bfloat16_copy_kernel_cuda(at | 88.2 | 12442 | 7.1 | 0.9% |
| void at::native::vectorized_elementwise_kernel<4, at::native::(anonymous namespace)::pow_t | 87.1 | 3104 | 28.1 | 0.9% |
| void at::native::vectorized_elementwise_kernel<4, at::native::FillFunctor<c10::BFloat16>,  | 85.0 | 4725 | 18.0 | 0.9% |
| fmha_cutlassF_bf16_aligned_64x64_rf_sm80(PyTorchMemEffAttention::AttentionKernel<cutlass:: | 84.7 | 796 | 106.4 | 0.9% |
| fmha_cutlassF_bf16_aligned_32x128_gmem_sm80(PyTorchMemEffAttention::AttentionKernel<cutlas | 79.7 | 384 | 207.6 | 0.8% |
| ampere_bf16_s16816gemm_bf16_128x64_ldg8_f2f_tn | 63.7 | 239 | 266.6 | 0.7% |
| ampere_bf16_s1688gemm_bf16_64x128_sliced1x2_ldg8_f2f_tn | 62.8 | 441 | 142.4 | 0.6% |
| void (anonymous namespace)::indexing_backward_kernel<float, 4>(long const*, long const*, f | 57.2 | 380 | 150.5 | 0.6% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 50.3 | 2336 | 21.6 | 0.5% |
| ampere_bf16_s1688gemm_bf16_128x64_sliced1x2_ldg8_f2f_tn | 49.4 | 683 | 72.4 | 0.5% |
| void at::native::reduce_kernel<512, 1, at::native::ReduceOp<float, at::native::MeanOps<flo | 39.1 | 3136 | 12.5 | 0.4% |
| ampere_bf16_s1688gemm_bf16_128x128_ldg8_f2f_stages_32x1_tn | 35.9 | 367 | 97.8 | 0.4% |
| void at::native::vectorized_elementwise_kernel<4, at::native::BinaryFunctor<c10::BFloat16, | 35.0 | 384 | 91.2 | 0.4% |
| void at::native::(anonymous namespace)::vectorized_layer_norm_kernel<float, float, false>( | 32.2 | 3389 | 9.5 | 0.3% |
| void cutlass::Kernel2<cutlass_80_tensorop_bf16_s16816gemm_relu_bf16_64x64_32x6_tn_align8>( | 31.7 | 2265 | 14.0 | 0.3% |
| void at::native::reduce_kernel<128, 4, at::native::ReduceOp<c10::BFloat16, at::native::fun | 29.6 | 4188 | 7.1 | 0.3% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 28.5 | 736 | 38.7 | 0.3% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl<at::native::Binary | 27.7 | 403 | 68.8 | 0.3% |

top 25 CPU ops by self time:

| op | self CPU ms (all active) | ms/update | calls | share |
|---|---|---|---|---|
| cudaLaunchKernel | 942.5 | 471.2 | 141237 | 16.9% |
| cudaStreamSynchronize | 480.1 | 240.0 | 2605 | 8.6% |
| aten::mm | 267.7 | 133.9 | 12774 | 4.8% |
| aten::copy_ | 225.3 | 112.6 | 68937 | 4.1% |
| aten::addmm | 211.4 | 105.7 | 5588 | 3.8% |
| aten::empty | 181.8 | 90.9 | 54881 | 3.3% |
| aten::empty_strided | 127.2 | 63.6 | 27624 | 2.3% |
| aten::select | 114.3 | 57.1 | 59856 | 2.1% |
| Command Buffer Full | 111.3 | 55.6 | 1209 | 2.0% |
| aten::add | 103.4 | 51.7 | 10006 | 1.9% |
| AddmmBackward0 | 102.9 | 51.5 | 4164 | 1.9% |
| aten::sum | 99.8 | 49.9 | 6531 | 1.8% |
| aten::native_layer_norm | 99.8 | 49.9 | 3389 | 1.8% |
| aten::_to_copy | 98.9 | 49.5 | 26296 | 1.8% |
| aten::add_ | 96.0 | 48.0 | 17673 | 1.7% |
| aten::mul | 92.2 | 46.1 | 10283 | 1.7% |
| aten::view | 84.6 | 42.3 | 51616 | 1.5% |
| DivBackward0 | 76.6 | 38.3 | 455 | 1.4% |
| cuLaunchKernel | 75.6 | 37.8 | 10637 | 1.4% |
| aten::as_strided | 73.5 | 36.8 | 154038 | 1.3% |
| aten::transpose | 73.1 | 36.6 | 47524 | 1.3% |
| autograd::engine::evaluate_function: AddmmBackward0 | 70.6 | 35.3 | 4164 | 1.3% |
| aten::linear | 63.4 | 31.7 | 13632 | 1.1% |
| aten::pow | 63.3 | 31.6 | 6208 | 1.1% |
| aten::slice | 62.5 | 31.2 | 28550 | 1.1% |

