"""`mlx_lm.server` with MLX's buffer cache capped. Uncapped, two K2 q4 servers grew to 13-16 GB each on the 36 GB M3 and hit
a Metal "Insufficient Memory" error, which kills the server's generation thread (every later request then gets a 404).
Usage: python practice/mlx_server.py <mlx_lm.server args>   (env P1M_MLX_CACHE_GB, default 1)"""
import os

import mlx.core as mx

mx.set_cache_limit(int(float(os.environ.get("P1M_MLX_CACHE_GB", "1")) * 2 ** 30))
mx.set_memory_limit(int(float(os.environ.get("P1M_MLX_MEM_GB", "9")) * 2 ** 30))  # soft: MLX frees cache / waits before going past it

from mlx_lm.server import main  # noqa: E402

if __name__ == "__main__":
    main()
