# One image for Vast and Modal. Pinned (v1/PINS.json). No git inside: code arrives as the tarball + COMMIT file.
FROM pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime
ENV PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 CUBLAS_WORKSPACE_CONFIG=:4096:8
RUN pip install --no-cache-dir numpy==2.1.3
WORKDIR /work
# On the box:  tar xzf v1-code-*.tar.gz -C /work && python -m v1.preflight --pins v1/PINS.json
