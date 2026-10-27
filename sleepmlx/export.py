"""Turn the torch backend's PEFT adapter into a llama.cpp GGUF LoRA (for llama-server --lora).

    python <llama.cpp>/convert_lora_to_gguf.py <adapter dir> --base <HF base model dir> --outfile adapter.gguf

The converter needs the HF base directory (not the GGUF). Failures are returned, never raised, so a night never fails because of the export.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional, Tuple


def export_command(llama_cpp_dir: str, base_dir: str, adapter_dir, out) -> list:
    return [sys.executable, str(Path(os.path.expanduser(llama_cpp_dir)) / "convert_lora_to_gguf.py"), str(adapter_dir),
            "--base", os.path.expanduser(base_dir), "--outfile", str(out)]


def export_gguf(llama_cpp_dir: Optional[str], base_dir: Optional[str], adapter_dir, out, run: Callable = subprocess.run, timeout: float = 900) -> Tuple[bool, str]:
    """-> (ok, message). Skips (False, reason) when llama_cpp_dir is not configured, the converter, the HF base or a PEFT adapter is missing."""
    if not llama_cpp_dir:
        return False, "llama_cpp_dir not configured"
    conv = Path(os.path.expanduser(llama_cpp_dir)) / "convert_lora_to_gguf.py"
    if not conv.exists():
        return False, "converter not found: %s" % conv
    if not base_dir or not Path(os.path.expanduser(base_dir)).is_dir():
        return False, "HF base dir not found: %s" % base_dir
    if not (Path(adapter_dir) / "adapter_model.safetensors").exists():
        return False, "no PEFT adapter in %s (the MLX backend does not write one)" % adapter_dir
    out = Path(out)
    tmp = out.with_name(out.name + ".tmp")
    try:
        r = run(export_command(llama_cpp_dir, base_dir, adapter_dir, tmp), capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return False, "converter exit %s: %s" % (r.returncode, (r.stderr or "")[-300:])
        if not tmp.exists():
            return False, "converter wrote no file"
        os.replace(str(tmp), str(out))
        return True, str(out)
    except Exception as e:   # includes timeouts
        return False, "%s: %s" % (type(e).__name__, e)
