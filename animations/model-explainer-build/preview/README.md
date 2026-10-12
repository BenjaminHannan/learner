# Explainer preview (browser)

Open `watch.html` through a local web server (browsers block file:// scripts in some cases):

    cd animations/model-explainer-build/preview && python3 -m http.server 8791

then go to http://127.0.0.1:8791/watch.html . Space = play/pause, arrow keys = +/-10 s, drop-down = jump to a chapter, `#SECONDS` in the URL starts there.

Built from the delivered chapters (ch01, ch03, ch04, ch05, ch06, ch09; about 43 minutes). Not rendered to MP4 (no arm64 ffmpeg on this Mac; a full render takes much longer than minutes).
Chapters not yet written: ch00, ch02, ch07, ch08, ch10-ch14. Picture review of the delivered chapters is still in progress.
