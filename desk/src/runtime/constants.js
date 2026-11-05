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
  // Windows (Nov 4): Glim's own brain, Nanbeige4.2-3B (Apache-2.0), as bartowski's public llama.cpp GGUFs (they carry
  // nanbeige.num_loops = 2, so llama.cpp runs the 22 layers twice like the original). Q8_0 when the graphics card has at least
  // WIN_Q8_MIN_VRAM_GB, else Q4_K_M. Exact names, sizes and sha256 are pinned (from the Hugging Face LFS listing, Nov 4).
  WIN_MODEL_REPO: 'bartowski/Nanbeige_Nanbeige4.2-3B-GGUF',
  WIN_Q8_MIN_VRAM_GB: 12,
  WIN_MODELS: {
    q8_0: { file: 'Nanbeige_Nanbeige4.2-3B-Q8_0.gguf', size: 4434787488, sha256: '837ba713ef3a3b5c9aee82e5dcba07600ea7db36ae392419f982b3bfaec04ef2' },
    q4_k_m: { file: 'Nanbeige_Nanbeige4.2-3B-Q4_K_M.gguf', size: 2684023968, sha256: 'b92d2e35c9876b0c4bc671996360204f4149d0546c23d5954d5eb3b106c81f24' }
  },
  // Glim's exact chat template (the GGUF's own copy differs by one rstrip); shipped as resources/nanbeige-chat-template.jinja
  WIN_CHAT_TEMPLATE: 'nanbeige-chat-template.jinja',
  // Glim's eyes for llama-server (SigLIP2 + the vision projector as one mmproj, tools/make_win_mmproj.py), shipped as resources/eyes/
  WIN_MMPROJ: 'glim-eyes-mmproj-f16.gguf',
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
