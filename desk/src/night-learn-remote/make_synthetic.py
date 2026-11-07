#!/usr/bin/env python3
"""Render small made-up window frames with known click points and key presses.

This is development evidence only. It is not a recording and never counts as a
real-data result. Frames are 640x360 PNGs; clicks land on a highlighted button,
key presses land on a highlighted keycap.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

WIDTH, HEIGHT = 640, 360
START_MS = 1_760_000_000_000
KEYCAPS = ((65, 'A'), (83, 'S'), (68, 'D'), (70, 'F'))
CLICK_CENTERS = tuple((130 + 120 * col, 150 + 70 * row)
                      for row in range(3) for col in range(4))


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def base_frame(rng):
    image = Image.new('RGB', (WIDTH, HEIGHT), (232, 234, 239))
    draw = ImageDraw.Draw(image)
    jitter_x = rng.randint(-4, 4)
    jitter_y = rng.randint(-3, 3)
    window = (40 + jitter_x, 28 + jitter_y, 600 + jitter_x, 332 + jitter_y)
    draw.rounded_rectangle(window, radius=10, fill=(250, 250, 252), outline=(120, 124, 132), width=2)
    draw.rounded_rectangle((window[0], window[1], window[2], window[1] + 26), radius=10, fill=(214, 220, 232))
    draw.ellipse((window[0] + 10, window[1] + 8, window[0] + 20, window[1] + 18), fill=(238, 92, 92))
    draw.ellipse((window[0] + 26, window[1] + 8, window[0] + 36, window[1] + 18), fill=(238, 190, 92))
    draw.ellipse((window[0] + 42, window[1] + 8, window[0] + 54, window[1] + 18), fill=(104, 198, 120))
    draw.text((window[0] + 70, window[1] + 7), 'Synthetic window', fill=(60, 64, 72))
    for _ in range(24):
        x = rng.randint(window[0] + 12, window[2] - 18)
        y = rng.randint(window[1] + 40, window[3] - 12)
        shade = rng.randint(210, 238)
        draw.rectangle((x, y, x + rng.randint(2, 5), y + rng.randint(2, 5)), fill=(shade, shade, shade + 4))
    return image, draw, jitter_x, jitter_y


def render_click(rng):
    image, draw, jitter_x, jitter_y = base_frame(rng)
    active = rng.randrange(len(CLICK_CENTERS))
    for index, (cx, cy) in enumerate(CLICK_CENTERS):
        cx += jitter_x
        cy += jitter_y
        box = (cx - 44, cy - 22, cx + 44, cy + 22)
        if index == active:
            draw.rounded_rectangle(box, radius=8, fill=(47, 124, 246), outline=(255, 255, 255), width=3)
            draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=(255, 255, 255))
        else:
            shade = rng.randint(198, 214)
            draw.rounded_rectangle(box, radius=8, fill=(shade, shade, shade + 6), outline=(150, 154, 162), width=2)
    target_x = CLICK_CENTERS[active][0] + jitter_x + rng.randint(-4, 4)
    target_y = CLICK_CENTERS[active][1] + jitter_y + rng.randint(-4, 4)
    action = {'kind': 'click', 'x': int(target_x), 'y': int(target_y)}
    return image, action, 'click the highlighted button'


def render_key(rng):
    image, draw, jitter_x, jitter_y = base_frame(rng)
    active = rng.randrange(len(KEYCAPS))
    for index, (_, label) in enumerate(KEYCAPS):
        cx = 160 + 110 * index + jitter_x
        cy = 210 + jitter_y
        box = (cx - 34, cy - 34, cx + 34, cy + 34)
        if index == active:
            draw.rounded_rectangle(box, radius=9, fill=(246, 158, 47), outline=(90, 58, 12), width=3)
            draw.text((cx - 6, cy - 7), label, fill=(30, 26, 20))
        else:
            draw.rounded_rectangle(box, radius=9, fill=(212, 214, 219), outline=(150, 154, 162), width=2)
            draw.text((cx - 6, cy - 7), label, fill=(120, 124, 132))
    key_code = KEYCAPS[active][0]
    action = {'kind': 'key', 'keyCode': int(key_code)}
    return image, action, 'press the highlighted key'


def build(outdir, count, seed):
    rng = random.Random(seed)
    outdir = Path(outdir)
    frames = outdir / 'frames'
    frames.mkdir(parents=True, exist_ok=True)
    rows = []
    for index in range(count):
        is_key = index % 5 == 4
        image, action, intent = render_key(rng) if is_key else render_click(rng)
        name = f'syn-{index:05d}-{action["kind"]}.png'
        path = frames / name
        image.save(path, format='PNG', optimize=False)
        rows.append({
            'id': f'syn-{index:05d}',
            'timeMs': START_MS + index * 1000,
            'verified': True,
            'verifiedCorrection': False,
            'weight': 1,
            'intent': intent,
            'action': action,
            'frame': str(path.resolve()),
            'frameFileSha256': sha256_file(path),
        })
    dataset = {
        'synthetic': True,
        'note': 'made-up development frames; not a recording and not P2 proof',
        'startMs': START_MS,
        'endMs': START_MS + count * 1000,
        'examples': rows,
    }
    dataset_path = outdir / 'dataset.json'
    dataset_path.write_text(json.dumps(dataset, indent=2) + '\n', encoding='utf8')
    summary = {
        'dataset': str(dataset_path),
        'examples': count,
        'clicks': sum(1 for row in rows if row['action']['kind'] == 'click'),
        'keys': sum(1 for row in rows if row['action']['kind'] == 'key'),
        'heldStartIndex': int(count * 0.8),
        'datasetSha256': sha256_file(dataset_path),
    }
    (outdir / 'synthetic-manifest.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf8')
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('outdir')
    parser.add_argument('--count', type=int, default=300)
    parser.add_argument('--seed', type=int, default=7)
    args = parser.parse_args()
    if not 20 <= args.count <= 5000:
        raise SystemExit('count must be 20..5000')
    print(json.dumps(build(args.outdir, args.count, args.seed)))


if __name__ == '__main__':
    main()
