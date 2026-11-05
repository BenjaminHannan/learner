r"""Glim's model server with an optional "keep the brain in memory" mode (track E1, 2026-11-04).

A drop-in for ~/learner-ops/assistant/dory/plain_mlx_lm_big.py (which stays untouched): stock mlx_lm.server, and every request is
answered by the --model given here, whatever name it asks for.

    python glim_mlx_server.py --model DIR [--settings-file ~/Library/Application\ Support/Premonition/settings.json]
                              [--keep-in-memory on|off] [--kv-buffer 2GB] [mlx_lm.server args ...]

Setting OFF (the default; settings.json "keepBrainInMemory" missing or false): byte-for-byte the stock behaviour, which is what the
live server does today. Stock mlx_lm 0.32 already sets MLX's wired limit to max_recommended_working_set_size (30 GB on the M1 Pro)
at start and puts it back after every generation, and frees MLX's buffer pool (mx.clear_cache) during and after generation.

Setting ON:
  - wired limit = model weights (safetensors bytes on disk) + KV buffer + 512 MB margin, capped at max_recommended_working_set_size,
    set at start and kept: mlx_lm's own "set recommended limit" calls (server start, every generate, every BatchGenerator) set this
    same number instead, so it never moves between requests.
  - the KV buffer: MLX's buffer pool is held at exactly --kv-buffer bytes (mx.set_cache_limit), pre-touched once at start, and
    mx.clear_cache() becomes a no-op, so the KV memory is not handed back to macOS after each request and grabbed again on the
    next one. The prompt cache is capped at the same size (--prompt-cache-bytes, unless given).
  - never runs sudo. If the computed limit is above what macOS allows MLX to wire, the limit is capped and the log line says that
    raising it would need `sudo sysctl iogpu.wired_limit_mb=...` (reported, never done).

Cost to the rest of the Mac (ON): up to weights + buffer (+ margin) stays wired: macOS cannot compress or swap it, so other apps have
that much less RAM to move around in. For Nanbeige 8-bit: 4.1 GB + 2 GB = about 6.6 GB. Stock wires the weights plus whatever MLX has
allocated at the moment (up to 30 GB during a long prompt) and lets the pool shrink between requests.
"""
import json
import os
import sys

GB = 1 << 30
MARGIN = 512 << 20


def parse_size(x):
    s = str(x).strip().upper().replace("IB", "B")
    mult = {"K": 1 << 10, "KB": 1 << 10, "M": 1 << 20, "MB": 1 << 20, "G": GB, "GB": GB, "": 1, "B": 1}
    i = len(s)
    while i and not (s[i - 1].isdigit() or s[i - 1] == "."):
        i -= 1
    return int(float(s[:i]) * mult[s[i:].strip()])


def pop_flag(argv, name, default=None):
    """Remove `name value` from argv (our own flags; mlx_lm.server would reject them) and return value."""
    if name in argv:
        i = argv.index(name)
        v = argv[i + 1] if i + 1 < len(argv) else default
        del argv[i:i + 2]
        return v
    return default


def setting_on(settings_file, override):
    """The 'Keep Glim's brain in memory' setting. Explicit --keep-in-memory wins; else settings.json; else OFF."""
    if override is not None:
        return str(override).lower() in ("1", "on", "true", "yes")
    if not settings_file:
        return False
    try:
        with open(os.path.expanduser(settings_file), encoding="utf-8") as f:
            return json.load(f).get("keepBrainInMemory") is True
    except (OSError, ValueError, AttributeError):
        return False  # unreadable settings: the safe default


def weight_bytes(model_dir):
    d = os.path.expanduser(model_dir)
    if os.path.isfile(d):
        return os.path.getsize(d)
    try:
        return sum(os.path.getsize(os.path.join(d, f)) for f in os.listdir(d) if f.endswith(".safetensors"))
    except OSError:
        return 0


def plan(weights, kv_buffer, max_rec):
    """-> (limit, capped). Pure, for the tests."""
    want = weights + kv_buffer + MARGIN
    if max_rec and want > max_rec:
        return int(max_rec), True
    return int(want), False


def install_keep(mx, mlx_modules, weights, kv_buffer, log=print):
    """Make the wired limit + KV pool fixed. Returns a dict describing what was set."""
    info = mx.device_info() if hasattr(mx, "device_info") else mx.metal.device_info()
    max_rec = int(info.get("max_recommended_working_set_size") or 0)
    limit, capped = plan(weights, kv_buffer, max_rec)
    set_wired = mx.set_wired_limit if hasattr(mx, "set_wired_limit") else mx.metal.set_wired_limit
    set_cache = mx.set_cache_limit if hasattr(mx, "set_cache_limit") else mx.metal.set_cache_limit
    prev = set_wired(limit)

    def fixed_limit():  # replaces mlx_lm's maybe_set_recommended_wired_limit: same contract (returns the previous limit)
        return set_wired(limit)

    for m in mlx_modules:
        if hasattr(m, "maybe_set_recommended_wired_limit"):
            m.maybe_set_recommended_wired_limit = fixed_limit
    set_cache(kv_buffer)
    # pre-touch the buffer once so the pool holds it from the start (freed arrays go to the pool, which clear_cache no longer empties)
    try:
        a = mx.zeros((max(1, kv_buffer // 4),), dtype=mx.float32)
        mx.eval(a)
        del a
    except Exception as e:  # noqa: BLE001 - a failed pre-touch only means the pool fills on first use
        log("[glim-brain] pre-touch skipped: %s" % e)
    real_clear = mx.clear_cache
    mx.clear_cache = lambda: None
    out = {"on": True, "wired_limit": limit, "previous_limit": int(prev or 0), "weights": weights, "kv_buffer": kv_buffer,
           "max_recommended": max_rec, "capped": capped, "real_clear_cache": real_clear}
    msg = "[glim-brain] keep in memory ON: wired limit %.2f GB (weights %.2f GB + buffer %.2f GB + margin), pool %.2f GB" % (
        limit / GB, weights / GB, kv_buffer / GB, kv_buffer / GB)
    if capped:
        msg += "; CAPPED at macOS's recommended %.2f GB (raising it needs `sudo sysctl iogpu.wired_limit_mb=...`, not done)" % (max_rec / GB)
    log(msg)
    return out


def page_views(mx, arrays, page_bytes=4096):
    """One element per 4 KB of every array (a strided view): reading these touches every memory page of the weights."""
    out = []
    for w in arrays:
        step = max(1, page_bytes // max(1, w.itemsize))
        out.append(w.reshape(-1)[::step])
    return out


def cpu_page_views(arrays, page_bytes=16384):
    """v3 (E1): byte views, one byte per 16 KB page of every weight, read from the CPU (memoryview, no copy). A CPU read marks the
    page as recently used for the macOS compressor; v2's GPU read did not stop it (it only pulled pages back after a sweep)."""
    out = []
    for w in arrays:
        try:
            out.append(memoryview(w).cast("B")[::page_bytes])
        except (TypeError, ValueError, BufferError):
            pass  # a non-contiguous array: skipped
    return out


def install_touch(S, mx, every_s, clock=None, log=print, mode="gpu"):
    """v2 (E1): macOS compresses idle GPU buffers even under a wired limit (measured: 302 of 633 MB within 45 s idle).
    While the server is idle, read one value per page of every weight every `every_s` seconds, so the pages stay recently used and
    are never compressed. Runs INSIDE mlx_lm's generation thread (its idle wait), so it never races a request. Cost: a few ms."""
    import time as _t
    from mlx.utils import tree_flatten
    clock = clock or _t.monotonic
    RG = S.ResponseGenerator
    orig = RG._next_request
    state = {"last": clock(), "views": None, "count": 0}

    def next_request(self, timeout=None):
        req = orig(self, timeout)
        if req is None and timeout is not None and clock() - state["last"] >= every_s:   # idle (no batch decoding)
            state["last"] = clock()
            try:
                model = self.model_provider.model
                if model is not None:
                    if state["views"] is None or state.get("model") is not model:
                        state["model"] = model
                        leaves = [v for _, v in tree_flatten(model.parameters())]
                        state["views"] = cpu_page_views(leaves) if mode == "cpu" else page_views(mx, leaves)
                    if mode == "cpu":
                        state["bytes"] = sum(len(bytes(v)) for v in state["views"])
                    else:
                        mx.eval([v.sum() for v in state["views"]])
                    state["count"] += 1
            except Exception as e:  # noqa: BLE001 - a failed touch never breaks serving
                log("[glim-brain] touch skipped: %s" % e)
        return req

    RG._next_request = next_request
    log("[glim-brain] idle touch every %ss (%s)" % (every_s, mode))
    return state


# ---- "Glim can see" (track I1, 2026-11-04; OFF by default) ---------------------------------------------------------
# A chat message may carry pooled SigLIP2 features (computed by the Desk's eyes worker, desk/tools/glim_eyes.py) as a content part:
#     {"type": "image_features", "image_features": {"f16": "<base64 float16 LE>", "shape": [64, 768], "eye": "<EYE_ID>"}}
# With the setting ON the server runs the vision projector on them and puts the 64 projected rows into the prompt, where the part was,
# exactly like training (premonition-projectors: the text before and after the media is tokenized separately). Requests without
# such a part take the stock path unchanged (same tokens, batching and prompt cache). Requests with one are served one at a time
# (stock mlx_lm does that for every image request). Ordinary image_url parts are left to stock mlx_lm (it drops them for Nanbeige).
FEATURES_TYPE = "image_features"
MEDIA_MARK = "glim-media"   # private-use characters: never typed, never in a chat template


PUBLISHED_PROJECTOR = os.path.expanduser("~/learner-ops/premonition-projectors/weights/vision_projector.safetensors")

# ---- clips (vid-in, 2026-11-05): an image_features part may carry a short screen clip instead of one picture:
#     {"type": "image_features", "image_features": {"f16": ..., "shape": [n * 64, 768], "eye": ..., "clip": {"frames": n, "times": [0, 3, ...]}}}
# (2 <= n <= MAX_CLIP_FRAMES). It goes through the VIDEO projector (video_projector_v4, trained on BensPC on real MSR-VTT clips) in the
# training layout "Frame 1 (t=0s):\n<64 rows>\nFrame 2 (t=3s):\n<64 rows>..." where the part was. Single pictures keep the image
# projector. The gateway and the brain guard already pass / count image_features parts by their rows, so they need no change.
MAX_CLIP_FRAMES = 8
SHIPPED_VIDEO_PROJECTOR = os.path.expanduser("~/learner-ops/models/glim-video/video_projector_v4.safetensors")


def default_video_projector(settings_file):
    """Sense sleep's copy (userData/sense-sleep/video_projector.safetensors) when it exists, else the shipped v4 file."""
    if settings_file:
        p = os.path.join(os.path.dirname(os.path.expanduser(settings_file)), "sense-sleep", "video_projector.safetensors")
        if os.path.isfile(p):
            return p
    return SHIPPED_VIDEO_PROJECTOR


def clip_of(x):
    """-> (frames, times) for a clip part, None for a single picture. Raises ValueError on a malformed clip."""
    c = x.get("clip") if isinstance(x, dict) else None
    if not c:
        return None
    n = int(c.get("frames") or 0)
    if not 2 <= n <= MAX_CLIP_FRAMES:
        raise ValueError("image_features: a clip has 2..%d frames, not %s" % (MAX_CLIP_FRAMES, n))
    times = c.get("times") or [2 * k for k in range(n)]
    if len(times) != n:
        raise ValueError("image_features: clip times do not match its frames")
    return n, [int(round(float(t))) for t in times]


def clip_label(k, t):
    """The training's frame label (premonition-projectors video.py frame_label), with its leading newline after frame 1."""
    return ("" if k == 0 else "\n") + "Frame %d (t=%ds):\n" % (k + 1, t)


def default_projector(settings_file):
    """The projector sense sleep trains (userData/sense-sleep/vision_projector.safetensors, next to settings.json) when it exists,
    else the published v1 file. Sense sleep never writes the published file."""
    if settings_file:
        p = os.path.join(os.path.dirname(os.path.expanduser(settings_file)), "sense-sleep", "vision_projector.safetensors")
        if os.path.isfile(p):
            return p
    return PUBLISHED_PROJECTOR


def eyes_on(settings_file, override):
    """The 'Glim can see' setting. Explicit --eyes wins; else settings.json "glimCanSee" is True; else OFF."""
    if override is not None:
        return str(override).lower() in ("1", "on", "true", "yes")
    if not settings_file:
        return False
    try:
        with open(os.path.expanduser(settings_file), encoding="utf-8") as f:
            return json.load(f).get("glimCanSee") is True
    except (OSError, ValueError, AttributeError):
        return False


def features_parts(messages):
    for m in messages or []:
        c = m.get("content") if isinstance(m, dict) else None
        if isinstance(c, list):
            for p in c:
                if isinstance(p, dict) and p.get("type") == FEATURES_TYPE:
                    yield p


def make_seeing(model):
    """Give a loaded mlx_lm Nanbeige model an `input_embeddings` argument (stock Nanbeige has none), by swapping in subclasses
    whose __call__ accepts it. Without input_embeddings both calls are the stock ones. The loop body is the stock one
    (mlx_lm 0.32 models/nanbeige.py); test_glim_eyes.py checks ids vs embed(ids) give the same logits on a tiny real Nanbeige."""
    from mlx_lm.models.base import create_attention_mask
    inner = model.model
    if getattr(type(model), "_glim_seeing", False):
        return model
    icls, ocls = type(inner), type(model)

    def inner_call(self, inputs, cache=None, input_embeddings=None):
        if input_embeddings is None:
            return icls.__call__(self, inputs, cache)
        h = input_embeddings
        n_layers = len(self.layers)
        if cache is None:
            cache = [None] * (self.num_loops * n_layers)
        mask = create_attention_mask(h, cache[0])
        for loop_idx in range(self.num_loops):
            loop_cache = cache[loop_idx * n_layers:(loop_idx + 1) * n_layers]
            for layer, c in zip(self.layers, loop_cache):
                h = layer(h, mask, c)
            if not self.skip_loop_final_norm:
                h = self.norm(h)
        if self.skip_loop_final_norm:
            h = self.norm(h)
        return h

    def outer_call(self, inputs, cache=None, input_embeddings=None):
        if input_embeddings is None:
            return ocls.__call__(self, inputs, cache)
        out = self.model(inputs, cache, input_embeddings=input_embeddings)
        return self.model.embed_tokens.as_linear(out) if self.args.tie_word_embeddings else self.lm_head(out)

    inner.__class__ = type(icls.__name__ + "Seeing", (icls,), {"__call__": inner_call})
    model.__class__ = type(ocls.__name__ + "Seeing", (ocls,), {"__call__": outer_call, "_glim_seeing": True})
    return model


def install_eyes(S, mx, projector_path, log=print, placeholder=None, video_projector_path=None):
    """Wire the eyes into mlx_lm.server (module S). Returns the shared state dict (tests read it)."""
    import hashlib
    import numpy as np
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import glim_eyes as E
    proj = E.load_projector(projector_path)
    vproj = None
    if video_projector_path:
        try:
            vproj = E.load_projector(video_projector_path)
        except Exception as e:  # noqa: BLE001 - no video projector: a clip is seen as its last frame
            log("[glim-eyes] no video projector (%s): clips are seen as their last frame" % e)
    state = {"media": [], "placeholder": placeholder, "requests": 0, "projector": projector_path,
             "video_projector": video_projector_path if vproj is not None else None, "clips": 0}
    orig_url = S._image_url

    def image_url(part):   # makes stock mlx_lm serve feature requests one at a time (its rule for image requests)
        if isinstance(part, dict) and part.get("type") == FEATURES_TYPE:
            f = (part.get(FEATURES_TYPE) or {}).get("f16", "")
            return "glimfeat:" + hashlib.sha256(f.encode()).hexdigest()
        return orig_url(part)

    S._image_url = image_url
    RG = S.ResponseGenerator
    orig_tok = RG._tokenize

    def ph_id(tokenizer):
        if state["placeholder"] is None:
            u = getattr(tokenizer, "unk_token_id", None)
            state["placeholder"] = int(u if u is not None else 0)
        return state["placeholder"]

    def tokenize(self, tokenizer, request, args):
        if request.request_type != "chat" or not any(features_parts(request.messages)):
            return orig_tok(self, tokenizer, request, args)
        feats, urls, kinds = [], [], []
        for m in request.messages:
            c = m.get("content")
            if not isinstance(c, list):
                if c is None:
                    m["content"] = ""
                continue
            pieces = []
            for p in c:
                if p.get("type") == "text":
                    pieces.append(p.get("text") or "")
                elif p.get("type") == FEATURES_TYPE:
                    x = p.get(FEATURES_TYPE) or {}
                    shape = [int(v) for v in (x.get("shape") or [E.N_TOKENS, E.ENC_DIM])]
                    clip = clip_of(x)
                    if clip is not None:
                        n, times = clip
                        if shape != [n * E.N_TOKENS, E.ENC_DIM]:
                            raise ValueError("image_features: clip shape %s is not %d frames x %d rows" % (shape, n, E.N_TOKENS))
                        f = E.f16_from_b64(x.get("f16", ""), shape)
                        url = image_url(p)
                        if vproj is None:              # fallback: the clip's last frame as one picture
                            feats.append(f[-E.N_TOKENS:]); kinds.append("image"); urls.append(url); pieces.append(MEDIA_MARK)
                            continue
                        for k in range(n):
                            feats.append(f[k * E.N_TOKENS:(k + 1) * E.N_TOKENS]); kinds.append("video")
                            urls.append(url + ":%d" % k)
                            pieces.append(clip_label(k, times[k]) + MEDIA_MARK)
                        continue
                    if len(shape) != 2 or shape[1] != E.ENC_DIM or not 1 <= shape[0] <= 4 * E.N_TOKENS:
                        raise ValueError("image_features: bad shape %s" % shape)
                    feats.append(E.f16_from_b64(x.get("f16", ""), shape)); kinds.append("image")
                    urls.append(image_url(p))
                    pieces.append(MEDIA_MARK)
            m["content"] = "".join(pieces)
        # every content is a string now; the stock helper then only does its other job, which the chat template needs:
        # tool-call arguments from JSON strings to mappings (without it, a seeing ask in a thread with tool calls fails)
        S.process_message_content(request.messages)
        targs =dict(self.model_provider.cli_args.chat_template_args or {})
        if args.chat_template_kwargs:
            targs.update(args.chat_template_kwargs)
        text = tokenizer.apply_chat_template(request.messages, add_generation_prompt=True, tokenize=False, tools=request.tools, **targs)
        parts = text.split(MEDIA_MARK)
        if len(parts) - 1 != len(feats):
            raise ValueError("image_features: the chat template lost a media slot")
        ph = ph_id(tokenizer)
        prompt = []
        for i, piece in enumerate(parts):
            prompt += tokenizer.encode(piece, add_special_tokens=False) if piece else []
            if i < len(feats):
                prompt += [ph] * feats[i].shape[0]
        media = [(vproj if kind == "video" else proj)(mx.array(f).astype(mx.float16)) for f, kind in zip(feats, kinds)]
        mx.eval(media)
        state["media"] = media
        state["requests"] += 1
        state["clips"] += int("video" in kinds)
        vision = S._make_vision(prompt, urls=urls, pixel_values=media, token_id=ph)
        initial = "normal"
        if tokenizer.has_thinking:
            if tokenizer.rfind_think_start(prompt) > tokenizer.rfind_think_end(prompt):
                initial = "reasoning"
        initial = tokenizer.response_initial_state or initial
        return prompt, [prompt], ["assistant"], initial, vision

    RG._tokenize = tokenize

    def attach(model):
        make_seeing(model)

        def embed_inputs(inputs, pixel_values=None):
            h = model.model.embed_tokens(inputs)
            ids = np.array(inputs).reshape(-1).tolist()
            return E.splice_rows(mx, h, ids, state["placeholder"], state["media"])

        model.embed_inputs = embed_inputs   # stock server: model.embed_inputs(mx.array(rest), pixel_values=...)
        return model

    state["attach"] = attach
    log("[glim-eyes] Glim can see ON: projector %s, %d image rows per frame; clips: %s" % (projector_path, E.N_TOKENS,
        state["video_projector"] or "off (last frame only)"))
    return state


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    settings_file = pop_flag(argv, "--settings-file")
    eyes_override = pop_flag(argv, "--eyes")                       # I1: on|off (default: settings.json "glimCanSee", else off)
    projector = pop_flag(argv, "--eyes-projector") or default_projector(settings_file)
    video_projector = pop_flag(argv, "--eyes-video-projector") or default_video_projector(settings_file)
    override = pop_flag(argv, "--keep-in-memory")
    kv_raw = pop_flag(argv, "--kv-buffer")
    touch_s = float(pop_flag(argv, "--keep-touch-s", "0") or 0)   # E1 v2: idle page touch (0 = off)
    touch_mode = pop_flag(argv, "--keep-touch-mode", "gpu")        # E1 v3: cpu = read one byte per page from the CPU
    model = argv[argv.index("--model") + 1]
    on = setting_on(settings_file, override)
    if on:
        kv = parse_size(kv_raw) if kv_raw else (parse_size(argv[argv.index("--prompt-cache-bytes") + 1]) if "--prompt-cache-bytes" in argv else 2 * GB)
        if "--prompt-cache-bytes" not in argv:
            argv += ["--prompt-cache-bytes", str(kv)]
    sys.argv = argv
    import mlx.core as mx
    import mlx_lm.server as S
    import mlx_lm.generate as G
    import mlx_lm.utils as U
    orig_load = S.load

    eyes = None
    if eyes_on(settings_file, eyes_override):
        try:
            eyes = install_eyes(S, mx, projector, log=lambda s: print(s, file=sys.stderr, flush=True), video_projector_path=video_projector)
        except Exception as e:  # noqa: BLE001 - no eyes is never a reason not to serve text
            print("[glim-eyes] could not start the eyes, serving text only: %s" % e, file=sys.stderr, flush=True)

    def load_fixed(path, *a, **kw):
        out = orig_load(model, *a, **kw)  # ignore the requested name (the gateway sends "lfm3")
        if eyes is not None:
            eyes["attach"](out[0])
        return out

    S.load = load_fixed
    if on:
        install_keep(mx, [S, G, U], weight_bytes(model), kv, log=lambda s: print(s, file=sys.stderr, flush=True))
        if touch_s > 0:
            install_touch(S, mx, touch_s, log=lambda s: print(s, file=sys.stderr, flush=True), mode=touch_mode)
    else:
        print("[glim-brain] keep in memory OFF: stock mlx_lm behaviour", file=sys.stderr, flush=True)
    S.main()


if __name__ == "__main__":
    main()
