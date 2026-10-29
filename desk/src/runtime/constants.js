'use strict';
// Everything about the built-in local model that may need changing later lives here.
module.exports = {
  // llama.cpp: LFM3 support landed on master on 2026-10-27, so no release published before this moment can run the model.
  // We compare release dates (the exact tag number of the first release after it is not known in advance).
  LLAMA_REPO: 'ggml-org/llama.cpp',
  LLAMA_MIN_PUBLISHED: '2026-10-27T16:06:00Z',
  LLAMA_MIN_TAG_NUMBER: 11938,           // tags up to b11937 point at commits before LFM3 support (19cce69); raise to the first tag that has it
  LLAMA_FALLBACK_TAG: 'b11946',          // downloaded by direct URL (no API, no checksum) when the GitHub release list cannot be read or has nothing usable
  LLAMA_FALLBACK_SHA256: {               // sha256 of the pinned release's assets (checked on the fallback path)
    'llama-b11946-bin-macos-arm64.tar.gz': 'd618da5e7bbb19077f086e6a7e1d77eab55b9bfd481f7531aadada86d13db9ed',
    'llama-b11946-bin-win-vulkan-x64.zip': 'b65b2837c584ca2d37033b8a947513fc02649199077a17455f416921aa6eb8f5',
    'llama-b11946-bin-win-cpu-x64.zip': '8a702bb07c873b133c56eb3acd92a48d7c5c9ad339c6435eddc5185e46e1a043',
  },
  // Until an official release has LFM3, the app ships its own CPU llama-server.exe (resources/llama), cross-built from this
  // master commit with mingw-w64 (AVX2, static). Its tag doubles as the source ref for the sleep adapter converter.
  BUNDLED_LLAMA_COMMIT: 'd05706b4f32a545814856e98ca518292585443b9',
  LLAMA_FLAVORS: ['vulkan', 'cpu'],      // tried in this order; cpu = the avx2 build, used when Vulkan will not start
  // Windows: llama-<tag>-bin-win-<vulkan|cpu>-x64.zip. macOS (Apple silicon only): llama-<tag>-bin-macos-arm64.tar.gz (there is no zip for
  // macOS; Metal is built in, so the one asset serves the single 'metal' flavor). The platform defaults to win32 so older callers are unchanged.
  llamaAssetName: (tag, flavor, platform) => (platform === 'darwin' ? 'llama-' + tag + '-bin-macos-arm64.tar.gz' : 'llama-' + tag + '-bin-win-' + (flavor === 'cpu' ? 'cpu' : flavor) + '-x64.zip'),
  llamaFlavors: (platform) => (platform === 'darwin' ? ['metal'] : ['vulkan', 'cpu']),
  llamaExeName: (platform) => (platform === 'darwin' ? 'llama-server' : 'llama-server.exe'),
  // chat model
  MODEL_REPO: 'LiquidAI/LFM3-1.7B-GGUF',
  MODEL_FILE: 'LFM3-1.7B-QAD-Q4_0.gguf', // preferred exact name; if absent the repo listing is searched for a q4_0 .gguf
  MODEL_SIZE_BYTES: 1050000000,          // only for the up-front "about 1 GB" text
  // llama-server
  SERVER_HOST: '127.0.0.1',
  SERVER_PORT: 18090,
  GATEWAY_PORT: 18091,
  CTX: 8192,
  // sleep runtime (downloaded the first time sleep is turned on)
  PBS_REPO: 'astral-sh/python-build-standalone',
  PYTHON_SERIES: '3.12',
  TORCH_CPU_INDEX: 'https://download.pytorch.org/whl/cpu',
  SLEEP_HF_REPO: 'LiquidAI/LFM3-1.7B',
  SLEEP_PROFILE: 'lfm3_cpu',             // sleepmlx/profiles/*.json: the CPU-sized LoRA recipe
  SLEEP_PIP: ['transformers', 'peft', 'accelerate', 'huggingface_hub', 'safetensors', 'numpy', 'sentencepiece', 'psutil'],
  SLEEP_SIZES: { python: '0.1 GB', libs: '1 GB', weights: '3.4 GB' },
  GATEWAY_URL: 'http://127.0.0.1:18091/v1'
};
