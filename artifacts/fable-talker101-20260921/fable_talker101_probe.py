import sys
print("python:", sys.version.replace("\n", " "))
try:
    import torch
    print("torch:", torch.__version__, "cuda:", torch.cuda.is_available(),
          torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")
except Exception as e:
    print("torch FAIL:", e)
try:
    import numpy
    print("numpy:", numpy.__version__)
except Exception as e:
    print("numpy FAIL:", e)
try:
    import tokenizers
    print("tokenizers:", tokenizers.__version__)
except Exception as e:
    print("tokenizers MISSING:", e)
