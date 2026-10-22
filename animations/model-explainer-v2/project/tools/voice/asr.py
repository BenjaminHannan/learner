"""ASR round trip: transcribe every narration clip and compare with the text the voice was given (after speakify)."""
import json, os, re, subprocess, sys, wave
import numpy as np
from faster_whisper import WhisperModel
A = os.environ["VOICE_AUDIO_DIR"]
idx = json.load(open(A + "/index.json"))
m = WhisperModel(sys.argv[1] if len(sys.argv) > 1 else "base.en", device="cpu", compute_type="int8", cpu_threads=4)
def norm(t):
    t = t.lower().replace("-", " ")
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return t.split()
out = {}
for i, (k, v) in enumerate(sorted(idx.items())):
    pcm = subprocess.run(["ffmpeg","-v","error","-i",f"{A}/{v['hash']}.wav","-f","f32le","-ac","1","-ar","16000","-"],capture_output=True,check=True).stdout
    x = np.frombuffer(pcm, dtype="<f4").copy()
    segs, _ = m.transcribe(x, language="en", beam_size=1, vad_filter=False, condition_on_previous_text=False)
    out[k] = " ".join(s.text.strip() for s in segs)
    if i % 50 == 0: print(i, k, out[k][:80], flush=True)
json.dump(out, open("asr.json", "w"), indent=1)
print("done", len(out))
