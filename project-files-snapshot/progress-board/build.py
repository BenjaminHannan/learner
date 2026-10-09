import json,html
d=json.load(open('data.json'));e=html.escape
def li(x):return f"<li>{e(x)}</li>"
out=[]
out.append("<h2>Running now</h2><div class=run>"+"".join(f"<div class=item><b>{e(r['what'])}</b><p>{e(r['detail'])}</p><span class=eta>ETA: {e(r['eta'])}</span><span class=src>{e(r['where'])}</span></div>" for r in d['running'])+"</div>")
lab={'done':'Done','progress':'In progress','todo':'Not started','paused':'Paused'}
nd=sum(1 for r in d['roadmap'] if r['s']=='done')
out.append(f"<h2>Roadmap to the full model ({nd} of {len(d['roadmap'])} done)</h2><ul class=road>"+"".join(f"<li class='{r['s']}'><span class=box aria-hidden=true></span><div><b>{e(r['t'])}</b> <span class=st>{lab[r['s']]}</span><p>{e(r['n'])}</p>"+(f"<span class=eta>ETA: {e(r['eta'])}</span>" if r.get('eta') else "")+"</div></li>" for r in d['roadmap'])+"</ul>")
out.append("<h2>Blockers, ranked</h2><ol class=blk>"+"".join(f"<li><b>{e(b['title'])}</b><p>{e(b['detail'])}</p><p class=next>Next: {e(b['next'])}</p></li>" for b in d['blockers'])+"</ol>")
out.append("<h2>Wins by date</h2>")
for day in d['days']:
    s=f"<section class=day><h3>{e(day['date'])}</h3>"
    if day['wins']:
        s+="<div class=wins>"+"".join(f"<div class='item win'><span class=tag>{e(w.get('tag','PASS'))}</span><b>{e(w['t'])}</b><p>{e(w['d'])}</p><span class=src>{e(w['w'])}</span></div>" for w in day['wins'])+"</div>"
    else: s+="<p class=muted>No passes recorded in this summary.</p>"
    s+="<details open><summary>Misses and nulls ("+str(len(day['misses']))+")</summary><ul>"+"".join(li(m) for m in day['misses'])+"</ul></details></section>"
    out.append(s)
out.append(f"<p class=muted>{e(d['coverage'])} Pass means it met marks written before training. All times are US Eastern (ET). Dates are ET dates.</p>")
page=f"""<title>Premonition Progress Board</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;600&display=swap">
<style>
/* layout: single column board; running strip, ranked blockers, dated wins */
:root{{--bg:#f3f5f7;--fg:#161c24;--mut:#5a6572;--card:#fff;--line:#d5dbe2;--win:#17724a;--winbg:#e4f3ec;--warn:#a5481a;--acc:#1d4f91;
--sans:'IBM Plex Sans',system-ui,sans-serif;--mono:'IBM Plex Mono',ui-monospace,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#10151b;--fg:#e6eaef;--mut:#9aa6b3;--card:#171e26;--line:#2b3541;--win:#5fd39b;--winbg:#14301f;--warn:#f0a070;--acc:#7fb2f0;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#10151b;--fg:#e6eaef;--mut:#9aa6b3;--card:#171e26;--line:#2b3541;--win:#5fd39b;--winbg:#14301f;--warn:#f0a070;--acc:#7fb2f0;color-scheme:dark}}
body{{background:var(--bg);color:var(--fg);font-family:var(--sans);font-size:15px;line-height:1.5;padding-inline:16px;padding-block:24px}}
main{{max-width:860px;margin:0 auto;display:flex;flex-direction:column;gap:16px}}
h1{{font-size:26px;margin:0;text-wrap:balance}}
h2{{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);margin:16px 0 0;font-weight:600}}
h3{{font-family:var(--mono);font-size:18px;margin:0 0 8px;color:var(--acc);font-weight:500}}
.stamp{{font-family:var(--mono);font-size:13px;color:var(--mut)}}
p{{margin:4px 0;min-width:0}} .muted{{color:var(--mut);font-size:13px}}
.run,.wins{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:12px}}
.item{{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:12px;min-width:0;display:flex;flex-direction:column;gap:2px}}
.item p{{font-size:14px;color:var(--mut)}}
.win{{border-left:4px solid var(--win)}}
.tag{{align-self:flex-start;font-family:var(--mono);font-size:11px;background:var(--winbg);color:var(--win);padding:1px 6px;border-radius:3px}}
.eta{{margin-top:auto;font-family:var(--mono);font-size:13px;color:var(--acc);font-weight:500;padding-top:4px}}
.road{{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:6px}}
.road li{{display:flex;gap:12px;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:10px 12px;min-width:0}}
.road li>div{{min-width:0}} .road p{{font-size:14px;color:var(--mut)}}
.box{{flex:none;width:18px;height:18px;margin-top:2px;border:2px solid var(--mut);border-radius:3px;position:relative}}
.done .box{{background:var(--win);border-color:var(--win)}}
.done .box::after{{content:"";position:absolute;left:4px;top:0;width:5px;height:10px;border:solid var(--card);border-width:0 2px 2px 0;transform:rotate(45deg)}}
.progress .box{{border-color:var(--acc);border-style:dashed}} .paused .box{{border-color:var(--warn)}}
.st{{font-family:var(--mono);font-size:11px;color:var(--mut);margin-left:6px}}
.src{{font-family:var(--mono);font-size:12px;color:var(--mut);padding-top:2px}}
.blk{{margin:0;padding:0;list-style:none;counter-reset:b;display:flex;flex-direction:column;gap:10px}}
.blk li{{counter-increment:b;background:var(--card);border:1px solid var(--line);border-left:4px solid var(--warn);border-radius:6px;padding:12px 12px 12px 14px}}
.blk li b::before{{content:counter(b)". ";font-family:var(--mono);color:var(--warn)}}
.blk p{{font-size:14px;color:var(--mut)}} .blk .next{{color:var(--fg)}}
.day{{border-top:1px solid var(--line);padding-top:12px;display:flex;flex-direction:column;gap:8px}}
details{{font-size:14px}} summary{{cursor:pointer;color:var(--warn);font-weight:600}}
details ul{{margin:6px 0 0;padding-left:20px;color:var(--mut)}} details li{{margin:3px 0}}
</style>
<main><header><h1>Premonition Progress Board</h1><div class=stamp>Last updated {e(d['updated'])}</div></header>
{''.join(out)}</main>"""
open('index.html','w').write(page)
