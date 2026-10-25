"""Narration for the mechanisms video: Chatterbox TTS, one FLAC per scene + timing.json.
Usage: python gen_tts.py [--device mps|cpu] [--out DIR]"""
import argparse, json, os, time, torch, torchaudio
from chatterbox.tts import ChatterboxTTS
ap = argparse.ArgumentParser()
ap.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "out"))
a = ap.parse_args()
here = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(here, "script.json")))
os.makedirs(a.out, exist_ok=True)
m = ChatterboxTTS.from_pretrained(device=a.device); sr = m.sr
timing = []
for sc in S:
    parts, lines, t = [], [], 0.0
    for i, l in enumerate(sc["lines"]):
        torch.manual_seed(7)
        w = m.generate(l, exaggeration=0.6, cfg_weight=0.45).cpu()
        lines.append({"start": t, "dur": w.shape[-1] / sr, "text": l})
        parts.append(w); t += w.shape[-1] / sr
        gap = 0.45 if i < len(sc["lines"]) - 1 else 0.9
        parts.append(torch.zeros(1, int(gap * sr))); t += gap
    audio = torch.cat(parts, dim=1)
    torchaudio.save(os.path.join(a.out, sc["id"] + ".flac"), audio, sr)
    timing.append({"id": sc["id"], "dur": audio.shape[-1] / sr, "lines": lines})
    json.dump(timing, open(os.path.join(a.out, "timing.json"), "w"), indent=1)
    print(sc["id"], round(audio.shape[-1] / sr, 1), time.strftime("%X"), flush=True)
print("DONE")
