#!/bin/bash
# rebuild the CPU dry-run venv after a container restart (tmpfs /dev/shm is empty): system site packages (torch CPU etc.), the box script pip-installs the rest
mkdir -p /dev/shm/ptcdry
python3 --version
python3 -m venv --system-site-packages /dev/shm/ptcdry/venv 2>&1 | tail -2
/dev/shm/ptcdry/venv/bin/python -c "import sys, torch, numpy; print(sys.prefix, torch.__version__, numpy.__version__)"
/dev/shm/ptcdry/venv/bin/pip --version
/dev/shm/ptcdry/venv/bin/python -c "import pyarrow; print('pyarrow', pyarrow.__version__)" 2>&1 | tail -1
/dev/shm/ptcdry/venv/bin/python -c "import transformers; print('transformers', transformers.__version__)" 2>&1 | tail -1
nproc; free -m | head -2
