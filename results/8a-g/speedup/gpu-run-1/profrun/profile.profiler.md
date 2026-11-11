# Profile: PTC 3M accum 16 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model plain_tf_steps_g, 4,023,976 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3s.json

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

