# Profile: B3G2 3M accum 4 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model b3g2, 4,023,302 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3g2.json

## profiler

arm B3G2 | rung 3M | accum 4 | batch 256 | device cuda | torch 2.11.0+cu128

CPU op self time per update 4772.1 ms; wall per update 3541.6 ms (profiler overhead included)

| kernel ms/update | kernels/update | mean kernel us | GPU busy / wall | idle gap / wall | launch calls/update | stream syncs/update | DtoH copies/update | CPU op / kernel time | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 4927.4 | 75967 | 64.8 | 0.998 | 0.002 | 70618 | 1305.0 | 745.0 | 0.97 | GPU-bound |

top 25 CUDA kernels by total time:

| kernel | total ms | count | avg us | share |
|---|---|---|---|---|
| ProfilerStep* | 7070.7 | 2 | 3535359.2 | 71.7% |
| fmha_cutlassB_bf16_aligned_64x64_k64_sm80(PyTorchMemEffAttention::AttentionBackwardKernel< | 464.2 | 298 | 1557.7 | 4.7% |
| void at::native::vectorized_elementwise_kernel<4, at::native::CUDAFunctor_add<c10::BFloat1 | 283.0 | 11688 | 24.2 | 2.9% |
| void at::native::(anonymous namespace)::CatArrayBatchedCopy<at::native::(anonymous namespa | 210.5 | 1902 | 110.7 | 2.1% |
| void at::native::elementwise_kernel<128, 2, at::native::gpu_kernel_impl_nocast<at::native: | 169.9 | 6021 | 28.2 | 1.7% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 153.1 | 3439 | 44.5 | 1.6% |
| void at::native::unrolled_elementwise_kernel<at::native::direct_copy_kernel_cuda(at::Tenso | 108.0 | 11121 | 9.7 | 1.1% |
| void at::native::vectorized_elementwise_kernel<4, at::native::bfloat16_copy_kernel_cuda(at | 87.5 | 12442 | 7.0 | 0.9% |
| void at::native::vectorized_elementwise_kernel<4, at::native::(anonymous namespace)::pow_t | 86.9 | 3104 | 28.0 | 0.9% |
| void at::native::vectorized_elementwise_kernel<4, at::native::FillFunctor<c10::BFloat16>,  | 84.9 | 4725 | 18.0 | 0.9% |
| fmha_cutlassF_bf16_aligned_64x64_rf_sm80(PyTorchMemEffAttention::AttentionKernel<cutlass:: | 84.4 | 796 | 106.0 | 0.9% |
| fmha_cutlassF_bf16_aligned_32x128_gmem_sm80(PyTorchMemEffAttention::AttentionKernel<cutlas | 77.8 | 384 | 202.6 | 0.8% |
| ampere_bf16_s16816gemm_bf16_128x64_ldg8_f2f_tn | 61.9 | 239 | 259.1 | 0.6% |
| ampere_bf16_s1688gemm_bf16_64x128_sliced1x2_ldg8_f2f_tn | 60.9 | 441 | 138.0 | 0.6% |
| void (anonymous namespace)::indexing_backward_kernel<float, 4>(long const*, long const*, f | 55.3 | 380 | 145.5 | 0.6% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 49.8 | 2336 | 21.3 | 0.5% |
| ampere_bf16_s1688gemm_bf16_128x64_sliced1x2_ldg8_f2f_tn | 47.9 | 683 | 70.1 | 0.5% |
| void at::native::reduce_kernel<512, 1, at::native::ReduceOp<float, at::native::MeanOps<flo | 38.6 | 3136 | 12.3 | 0.4% |
| void at::native::vectorized_elementwise_kernel<4, at::native::BinaryFunctor<c10::BFloat16, | 35.0 | 384 | 91.1 | 0.4% |
| ampere_bf16_s1688gemm_bf16_128x128_ldg8_f2f_stages_32x1_tn | 34.8 | 367 | 94.9 | 0.4% |
| void at::native::(anonymous namespace)::vectorized_layer_norm_kernel<float, float, false>( | 31.8 | 3389 | 9.4 | 0.3% |
| void cutlass::Kernel2<cutlass_80_tensorop_bf16_s16816gemm_relu_bf16_64x64_32x6_tn_align8>( | 30.5 | 2265 | 13.5 | 0.3% |
| void at::native::reduce_kernel<128, 4, at::native::ReduceOp<c10::BFloat16, at::native::fun | 28.9 | 4188 | 6.9 | 0.3% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl_nocast<at::native: | 28.5 | 736 | 38.7 | 0.3% |
| void at::native::elementwise_kernel<128, 4, at::native::gpu_kernel_impl<at::native::Binary | 27.7 | 403 | 68.7 | 0.3% |

top 25 CPU ops by self time:

| op | self CPU ms (all active) | ms/update | calls | share |
|---|---|---|---|---|
| cudaLaunchKernel | 939.8 | 469.9 | 141237 | 16.7% |
| cudaStreamSynchronize | 474.8 | 237.4 | 2605 | 8.4% |
| aten::mm | 270.5 | 135.3 | 12774 | 4.8% |
| aten::copy_ | 225.4 | 112.7 | 68937 | 4.0% |
| aten::addmm | 218.6 | 109.3 | 5588 | 3.9% |
| aten::empty | 187.3 | 93.6 | 54881 | 3.3% |
| aten::empty_strided | 130.4 | 65.2 | 27624 | 2.3% |
| aten::select | 118.5 | 59.2 | 59856 | 2.1% |
| AddmmBackward0 | 106.1 | 53.0 | 4164 | 1.9% |
| aten::add | 105.6 | 52.8 | 10006 | 1.9% |
| Command Buffer Full | 102.7 | 51.3 | 1122 | 1.8% |
| aten::native_layer_norm | 102.7 | 51.3 | 3389 | 1.8% |
| aten::sum | 100.0 | 50.0 | 6531 | 1.8% |
| aten::_to_copy | 99.9 | 50.0 | 26296 | 1.8% |
| aten::add_ | 98.3 | 49.1 | 17673 | 1.7% |
| aten::mul | 94.4 | 47.2 | 10283 | 1.7% |
| aten::view | 86.0 | 43.0 | 51616 | 1.5% |
| DivBackward0 | 76.9 | 38.5 | 455 | 1.4% |
| cuLaunchKernel | 76.6 | 38.3 | 10637 | 1.4% |
| aten::as_strided | 76.1 | 38.1 | 154038 | 1.4% |
| aten::transpose | 73.4 | 36.7 | 47524 | 1.3% |
| autograd::engine::evaluate_function: AddmmBackward0 | 73.0 | 36.5 | 4164 | 1.3% |
| aten::linear | 64.9 | 32.5 | 13632 | 1.2% |
| aten::pow | 63.8 | 31.9 | 6208 | 1.1% |
| aten::slice | 63.4 | 31.7 | 28550 | 1.1% |

