"""Make the speech for every narration segment (free Kokoro voice, runs on the CPU; no network use after the model files are downloaded).
    tools/voice/venv/bin/python tools/voice/tts.py [--script narration/script] [--fallback narration/baseline] [--only ch04 ch05]
        [--voice af_heart] [--speed 0.95] [--workers 2] [--model PATH] [--voices PATH]
Text for a segment = the script text if it exists, else the fallback text (the caption itself). It goes through speakify.speakify first.
Writes narration/audio/<hash>.wav (mono 24 kHz, 16-bit) and narration/audio/index.json {segment id: {hash, dur, spoken, source}}.
Cached by hash of (voice, speed, spoken text), so re-running only makes what changed."""
import argparse, hashlib, json, os, sys, time, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from speakify import speakify  # noqa: E402

AUDIO = os.environ.get("VOICE_AUDIO_DIR") or os.path.join(ROOT, "narration", "audio")   # work dir for clips (use a local disk; the shared folder is slow)
_k = None


def _init(model, voices, threads):
    global _k
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    so = ort.SessionOptions()
    so.intra_op_num_threads = threads
    so.inter_op_num_threads = 1
    sess = ort.InferenceSession(model, sess_options=so, providers=["CPUExecutionProvider"])
    _k = Kokoro.from_session(sess, voices)


def _make(job):
    h, spoken, voice, speed = job
    out = os.path.join(AUDIO, h + ".wav")
    if os.path.exists(out):
        return h, None
    s, sr = _k.create(spoken, voice=voice, speed=speed, lang="en-us", trim=True)
    pcm = (np.clip(s, -1, 1) * 32767).astype("<i2")
    tmp = out + ".part"
    with wave.open(tmp, "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr); f.writeframes(pcm.tobytes())
    os.replace(tmp, out)
    return h, len(pcm) / sr


def wav_dur(path):
    with wave.open(path, "rb") as f:
        return f.getnframes() / f.getframerate()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=os.path.join(ROOT, "narration", "script"))
    ap.add_argument("--fallback", default=os.path.join(ROOT, "narration", "baseline"))
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--voice", default="af_heart")
    ap.add_argument("--speed", type=float, default=0.95)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--model", default=os.environ.get("KOKORO_MODEL", "kokoro-v1.0.onnx"))
    ap.add_argument("--voices", default=os.environ.get("KOKORO_VOICES", "voices-v1.0.bin"))
    ap.add_argument("--index", default=os.path.join(AUDIO, "index.json"))
    a = ap.parse_args()
    os.makedirs(AUDIO, exist_ok=True)
    plan = json.load(open(os.path.join(ROOT, "narration", "plan.json")))["segments"]
    script, fallback = {}, {}
    for d, store in ((a.script, script), (a.fallback, fallback)):
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".json"):
                    store.update(json.load(open(os.path.join(d, f))))
    index = json.load(open(a.index)) if os.path.exists(a.index) else {}
    jobs, seen = [], set()
    for s in plan:
        if a.only and s["ch"] not in a.only:
            continue
        text, src = (script[s["id"]], "script") if s["id"] in script else (fallback.get(s["id"], s["text"]), "fallback")
        spoken = speakify(text)
        h = hashlib.sha1(f"{a.voice}|{a.speed}|{spoken}".encode()).hexdigest()[:16]
        index[s["id"]] = {"hash": h, "spoken": spoken, "source": src, "voice": a.voice, "speed": a.speed}
        if not os.path.exists(os.path.join(AUDIO, h + ".wav")) and h not in seen:
            seen.add(h)
            jobs.append((h, spoken, a.voice, a.speed))
    print(f"{len(jobs)} clips to make, {len(index)} segments indexed", flush=True)
    t0 = time.time()
    if jobs:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(a.workers, initializer=_init, initargs=(a.model, a.voices, a.threads)) as pool:
            for n, _ in enumerate(pool.imap_unordered(_make, jobs, chunksize=1), 1):
                if n % 25 == 0 or n == len(jobs):
                    print(f"  {n}/{len(jobs)} clips, {time.time() - t0:.0f} s", flush=True)
    for sid, e in index.items():
        p = os.path.join(AUDIO, e["hash"] + ".wav")
        if os.path.exists(p):
            e["dur"] = round(wav_dur(p), 3)
    json.dump(index, open(a.index, "w"), indent=1, ensure_ascii=False)
    print("index written", a.index)


if __name__ == "__main__":
    main()
