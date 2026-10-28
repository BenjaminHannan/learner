llama-server.exe: llama.cpp master d05706b4f32a545814856e98ca518292585443b9 (has LFM3, PR #31252), cross-built on Linux:
mingw-w64 13 (posix threads), static, CPU only, GGML_NATIVE=OFF + AVX/AVX2/FMA/F16C, OpenMP off, OpenSSL off.
One local patch: ggml-cpu.c gets a THREAD_POWER_THROTTLING_STATE fallback typedef for older mingw headers.
Drop it once an official llama.cpp release can load LFM3 (raise LLAMA_MIN_TAG_NUMBER in src/runtime/constants.js).
