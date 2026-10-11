# Silent 78.5-minute model explainer, as 11 pieces (each under 25 MB)
Join in this order into one MP4 without re-encoding (needs ffmpeg):

    cd animations/model-explainer-voice/silent-main
    for c in ch00 ch01 ch03 ch04 ch05 ch06 ch07 ch08 ch09 ch14 end; do echo "file '$PWD/$c.mp4'"; done > list.txt
    ffmpeg -y -f concat -safe 0 -i list.txt -c copy model-explainer-main.mp4

Result: 1920x1080, 30 fps, silent, 4708 s, about 208 MB. (Content is "as of Oct 9".)
