#!/usr/bin/env python3
"""Exp 232c parity: 232's parity check (35 dialogs, one-word "Orrin" vs each
multi-word name, replies + stored triples byte-identical after substitution)
with particle-heavy multi-word names. Imports the sealed 232 parity script
unchanged and only swaps its MULTI list. Same CLI as 232's.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fullname232_parity as P  # noqa: E402 (sealed, read-only)

P.MULTI = ["Orrin ben Vask", "Orrin do Vask", "Orrin y Vask",
           "Orrin mac Vask", "Orrin de la Vask", "Orrin O'Vask",
           "Orrin bint Vask", "Orrin zu Vask"]

if __name__ == "__main__":
    sys.exit(P.main())
