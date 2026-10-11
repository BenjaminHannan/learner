"""Put every clip at its time on one soundtrack, level it, and (optionally) add it to a video without re-encoding the picture.
    VOICE_AUDIO_DIR=<clips dir> python3 tools/voice/compose.py --out narration.m4a [--mux video.mp4 narrated.mp4] [--only ch04] [--tempo-max 1.0]
Rules: a clip that is longer than its slot is sped up with ffmpeg atempo (at most --tempo-max); anything still longer is an error (rewrite it shorter).
Clips never overlap (checked). Level: two-pass loudnorm to -16 LUFS, true peak -1.5. Audio: mono AAC 80 kbps, 48 kHz. Video is copied as is."""
import argparse, json, os, subprocess, sys, tempfile, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from fit import classify, AUDIO  # noqa: E402

SR = 24000


def read_wav(path):
    with wave.open(path, "rb") as f:
        assert f.getframerate() == SR and f.getnchannels() == 1 and f.getsampwidth() == 2
        return np.frombuffer(f.readframes(f.getnframes()), dtype="<i2").astype(np.float32) / 32768.0


def tempo(x, factor):
    """speed up by factor (pitch kept) with ffmpeg atempo"""
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-", "-filter:a", f"atempo={factor:.4f}",
                        "-f", "s16le", "-ar", str(SR), "-ac", "1", "-"], input=pcm, capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype="<i2").astype(np.float32) / 32768.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--tempo-max", type=float, default=1.0)
    ap.add_argument("--mux", nargs=2, metavar=("VIDEO_IN", "VIDEO_OUT"), action="append", default=[])
    ap.add_argument("--allow-missing", action="store_true")
    a = ap.parse_args()
    plan_all = json.load(open(os.path.join(ROOT, "narration", "plan.json")))
    plan = [s for s in plan_all["segments"] if not a.only or s["ch"] in a.only]
    index = json.load(open(os.path.join(AUDIO, "index.json")))
    rows = {r["id"]: r for r in classify(plan, index, a.tempo_max)}
    bad = [r for r in rows.values() if r["cls"] == "shorten" or (r["cls"] == "missing" and not a.allow_missing)]
    if bad:
        for r in bad:
            print("  PROBLEM", r["cls"], r["id"], r.get("dur"), r["slot"])
        sys.exit(f"{len(bad)} clips do not fit; fix them first (tools/voice/fit.py)")
    total = plan_all["total"]
    n = int(round(total * SR))
    mix = np.zeros(n, dtype=np.float32)
    prev_end, prev_id, sped, overlap = 0.0, None, 0, 0
    for s in plan:
        r = rows[s["id"]]
        if r["cls"] == "missing":
            continue
        x = read_wav(os.path.join(AUDIO, index[s["id"]]["hash"] + ".wav"))
        if r["cls"] == "tempo":
            x = tempo(x, max(1.0, r["need"] + 0.005))
            sped += 1
        fade = min(len(x) // 2, int(0.012 * SR))
        if fade:
            x[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)
            x[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
        i0 = int(round(s["start"] * SR))
        i1 = min(n, i0 + len(x))
        if s["start"] < prev_end - 1e-3:
            overlap += 1
            print(f"  overlap: {s['id']} starts {s['start']:.2f} but {prev_id} runs to {prev_end:.2f}")
        mix[i0:i1] += x[: i1 - i0]
        prev_end, prev_id = s["start"] + len(x) / SR, s["id"]
    if overlap:
        sys.exit(f"{overlap} overlaps")
    peak = float(np.abs(mix).max())
    print(f"{len(plan)} segments placed, {sped} sped up, peak {peak:.3f}")
    if peak > 0.89:
        mix *= 0.89 / peak          # headroom before the 16-bit file, so nothing is clipped (loudnorm sets the real level later)
        print(f"scaled by {0.89 / peak:.3f} for headroom")
    work = tempfile.mkdtemp(prefix="compose-", dir=os.environ.get("VOICE_WORK") or None)
    raw = os.path.join(work, "mix.wav")
    with wave.open(raw, "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
    LN = "I=-16:TP=-1.5:LRA=11"
    p1 = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", raw, "-af", f"loudnorm={LN}:print_format=json", "-f", "null", "-"], capture_output=True, text=True, check=True)
    js = json.loads(p1.stderr[p1.stderr.rindex("{"): p1.stderr.rindex("}") + 1])
    print("measured", {k: js[k] for k in ("input_i", "input_tp", "input_lra", "input_thresh")})
    flt = (f"loudnorm={LN}:measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}"
           f":offset={js['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af", flt, "-ar", "48000", "-ac", "1", "-c:a", "aac", "-b:a", "80k", "-movflags", "+faststart", a.out], check=True)
    print("audio written", a.out)
    for vin, vout in a.mux:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", vin, "-i", a.out, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy",
                        "-t", str(total), "-movflags", "+faststart", vout], check=True)
        print("muxed", vout)
    os.remove(raw); os.rmdir(work)


if __name__ == "__main__":
    main()
