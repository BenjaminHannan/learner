"""Read-only, stdlib only. Summarise a py-spy `--format raw` file (one line per stack: frames joined by ';', then a space and a sample count).
  python spy_agg.py spy.txt [--top 40]
Prints: samples per thread-ish root, then the top self-time frames (the innermost frame) and the top inclusive-time frames (any frame in the stack),
as shares of all samples. Frames are shown as 'function (file:line)'; use --nolines to merge lines of one function."""
import argparse, collections, re, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--top', type=int, default=40)
    ap.add_argument('--nolines', action='store_true')
    a = ap.parse_args()
    selfc, inc, tot = collections.Counter(), collections.Counter(), 0
    for line in open(a.file, encoding='utf-8', errors='replace'):
        line = line.rstrip('\n')
        if not line.strip():
            continue
        stack, _, c = line.rpartition(' ')
        try:
            c = int(c)
        except ValueError:
            continue
        fr = stack.split(';')
        if a.nolines:
            fr = [re.sub(r':\d+\)', ')', f) for f in fr]
        tot += c
        selfc[fr[-1]] += c
        for f in set(fr):
            inc[f] += c
    print(f'total samples {tot}')
    print('\n== top self time (innermost frame)')
    for f, c in selfc.most_common(a.top):
        print(f'{100 * c / tot:5.1f}%  {c:7d}  {f}')
    print('\n== top inclusive time (frame anywhere in the stack)')
    for f, c in inc.most_common(a.top):
        print(f'{100 * c / tot:5.1f}%  {c:7d}  {f}')


if __name__ == '__main__':
    main()
