"""MiniWoB-style practice tasks for the HANDS gym.

A task is generated deterministically from ``(kind, seed)``: a small standalone
HTML document, the instruction Glim would give the policy, and task metadata.
The browser reports a JSON state snapshot after every action and :func:`check`
turns the previous/current snapshots into ``(success, step_reward, done)``.

Checks live in Python rather than the page so they are unit-testable without a
browser and behave identically on Windows and macOS. Every task is randomised
(layout, labels, colours, values) but always solvable with real mouse and
keyboard input.
"""
import json
import math
import random

VIEW_WIDTH = 640
VIEW_HEIGHT = 360
MAX_STEPS = 20

KIND_CLICK_BUTTON = 'click_button'
KIND_TYPE_TEXT = 'type_text'
KIND_DROPDOWN = 'dropdown'
KIND_CLOSE_POPUP = 'close_popup'
KIND_DRAG_SLIDER = 'drag_slider'
KIND_CLICK_LINK = 'click_link'
KIND_MENU_SELECT = 'menu_select'
KIND_CHECKBOX = 'checkbox'
KIND_FORM_FILL = 'form_fill'

TASK_TYPES = (
    KIND_CLICK_BUTTON,
    KIND_TYPE_TEXT,
    KIND_DROPDOWN,
    KIND_CLOSE_POPUP,
    KIND_DRAG_SLIDER,
    KIND_CLICK_LINK,
    KIND_MENU_SELECT,
    KIND_CHECKBOX,
    KIND_FORM_FILL,
)

BUTTON_WORDS = ('apple', 'brick', 'cloud', 'daisy', 'ember', 'frost',
                'grape', 'honey', 'ivory', 'jolly', 'kite', 'lemon')
TYPE_WORDS = ('cat', 'dog', 'fox', 'owl', 'bee', 'ant', 'elk', 'ram')
DROPDOWN_WORDS = ('red', 'blue', 'green', 'gold', 'pink', 'teal')
LINK_WORDS = ('docs', 'news', 'shop', 'help', 'maps', 'blog')
MENU_ITEMS = ('New', 'Open', 'Save', 'Export', 'Print', 'Share')
CHECK_LABELS = ('alerts', 'email', 'music', 'sync', 'news', 'backup')
NAME_WORDS = ('ann', 'bob', 'cleo', 'dan', 'eva', 'finn')
CITY_WORDS = ('oslo', 'lima', 'kyiv', 'rome', 'cairo', 'quito')
POPUP_TITLES = ('Update', 'Notice', 'Reminder', 'Confirm')

PALETTE = ('#ffd166', '#a0e7a0', '#9ad0ff', '#ffb3c7', '#d3b4ff', '#ffe08a')

BASE_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:100%;height:100%;overflow:hidden;
  font-family:'Segoe UI',system-ui,-apple-system,Arial,sans-serif;color:#1b1f24}
#stage{position:absolute;left:0;top:0;width:640px;height:360px}
button{font-family:inherit}
.btn{position:absolute;min-width:140px;height:50px;border:none;border-radius:10px;
  font-size:20px;font-weight:600;cursor:pointer;background:#ffd166;
  box-shadow:0 2px 0 rgba(0,0,0,.18)}
.btn:active{transform:translateY(1px)}
.text{position:absolute;height:52px;border:3px solid #3b4a5a;border-radius:8px;
  font-size:22px;padding:0 14px;background:#ffffff}
.select{position:absolute;height:44px;border:3px solid #3b4a5a;border-radius:8px;
  background:#ffffff;font-size:20px;padding:6px 12px;cursor:pointer}
.options{position:absolute;background:#ffffff;border:3px solid #3b4a5a;
  border-radius:8px;overflow:hidden}
.option{height:38px;line-height:32px;font-size:19px;padding:0 12px;cursor:pointer}
.option:hover{background:#e8f0ff}
.linklist{position:absolute;background:#ffffff;border:3px solid #3b4a5a;
  border-radius:10px;padding:8px}
.link{display:block;height:40px;line-height:34px;font-size:20px;padding:0 10px;
  color:#0b3d91;text-decoration:underline;cursor:pointer;border-radius:6px}
.link:hover{background:#e8f0ff}
.menu{position:absolute;background:#ffffff;border:3px solid #3b4a5a;
  border-radius:10px;overflow:hidden}
.item{height:40px;line-height:34px;font-size:19px;padding:0 14px;cursor:pointer}
.item:hover{background:#e8f0ff}
.row{position:absolute;display:flex;align-items:center;gap:14px;height:44px;
  padding:0 12px;background:#ffffff;border:3px solid #3b4a5a;border-radius:8px;
  font-size:20px;cursor:pointer}
.row input{width:24px;height:24px;cursor:pointer}
.backdrop{position:absolute;inset:0;background:rgba(20,30,40,.35)}
.dialog{position:absolute;background:#ffffff;border-radius:14px;
  box-shadow:0 12px 32px rgba(0,0,0,.35)}
.dialog h2{font-size:24px;padding:18px 22px 0}
.dialog p{font-size:17px;padding:10px 22px}
.close{position:absolute;width:40px;height:40px;border:none;border-radius:8px;
  background:#ff6b6b;color:#ffffff;font-size:24px;font-weight:700;cursor:pointer}
.card{position:absolute;background:#ffffff;border:3px solid #3b4a5a;
  border-radius:12px;padding:12px}
.fieldlabel{display:block;font-size:17px;font-weight:600;margin-bottom:4px}
.field{width:100%;height:46px;border:3px solid #3b4a5a;border-radius:8px;
  font-size:20px;padding:0 12px;background:#ffffff}
.range{position:absolute;height:40px;cursor:ew-resize;touch-action:none}
.range-track{position:absolute;left:8px;right:8px;top:16px;height:8px;
  background:#b8c6d6;border-radius:4px;pointer-events:none}
.range-thumb{position:absolute;top:8px;width:16px;height:24px;border-radius:4px;
  background:#1768bd;pointer-events:none}

"""

_RUNTIME = """
window.__gym = {
  clicks: [],
  click: function(el, ev) {
    var r = el.getBoundingClientRect();
    window.__gym.clicks.push({
      label: el.getAttribute('data-label') || (el.textContent || '').trim(),
      x: ev.clientX, y: ev.clientY,
      cx: r.left + r.width / 2, cy: r.top + r.height / 2
    });
  }
};
"""


def _style(cx, cy, w, h):
    return 'left:%.1fpx;top:%.1fpx;width:%dpx;height:%dpx;' % (
        cx - w / 2.0, cy - h / 2.0, w, h)


def _centers(rng, count, top=66, bottom=None, cols=3, rows=3):
    bottom = VIEW_HEIGHT - 20 if bottom is None else bottom
    area_w = VIEW_WIDTH - 48
    area_h = bottom - top
    cw = area_w / float(cols)
    ch = area_h / float(rows)
    cells = [(c, r) for r in range(rows) for c in range(cols)]
    rng.shuffle(cells)
    out = []
    for c, r in cells[:count]:
        x = 24 + cw * (c + 0.5) + rng.uniform(-cw * 0.16, cw * 0.16)
        y = top + ch * (r + 0.5) + rng.uniform(-ch * 0.16, ch * 0.16)
        out.append((x, y))
    return out


def _frame(hue, body, script):
    hue2 = (hue + 40) % 360
    head = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        '<style>' + BASE_CSS +
        'body{background:linear-gradient(135deg,hsl(%d,60%%,94%%),hsl(%d,45%%,86%%))}' % (hue, hue2) +
        '</style></head><body><div id="stage">'
    )
    return head + body + '</div><script>' + _RUNTIME + script + '</script></body></html>'


def _build_click_button(rng, hue):
    n = rng.choice((3, 4, 5))
    labels = rng.sample(BUTTON_WORDS, n)
    target = rng.choice(labels)
    parts = []
    for i, (label, (cx, cy)) in enumerate(zip(labels, _centers(rng, n))):
        color = rng.choice(PALETTE)
        parts.append(
            "<button class='btn' id='b%d' data-label='%s' style='%sbackground:%s' "
            "onclick=\"__gym.click(this,event)\">%s</button>"
            % (i, label, _style(cx, cy, 140, 50), color, label))
    script = ("window.__gym.state=function(){return {clicks:window.__gym.clicks.map("
              "function(c){return c.label;})};};")
    instruction = "Click the button labelled '%s'." % target
    return instruction, _frame(hue, ''.join(parts), script), {'target': target}


def _build_type_text(rng, hue):
    target = rng.choice(TYPE_WORDS)
    cx = rng.uniform(230, 410)
    cy = rng.uniform(120, 180)
    body = (
        "<input class='text' id='text' autocomplete='off' style='%s' "
        "onkeydown=\"if(event.key==='Enter'){window.__gym.submitted=true;}\">"
        "<button class='btn' id='submit' data-label='Submit' style='%sbackground:#9ad0ff' "
        "onclick=\"window.__gym.submitted=true\">Submit</button>"
        % (_style(cx, cy, 240, 52), _style(cx, cy + 92, 180, 50))
    )
    script = ("window.__gym.submitted=false;"
              "window.__gym.state=function(){return {"
              "value:document.getElementById('text').value,"
              "submitted:!!window.__gym.submitted};};")
    instruction = "Type '%s' into the text field, then submit." % target
    return instruction, _frame(hue, body, script), {'target': target}


def _build_dropdown(rng, hue):
    options = rng.sample(DROPDOWN_WORDS, 4)
    target = rng.choice(options)
    cx = rng.uniform(260, 380)
    cy = rng.uniform(80, 110)
    opts = ''.join(
        "<div class='option' data-value='%s' onclick=\"__gym.pick(this,event)\">%s</div>"
        % (word, word) for word in options)
    body = (
        "<div class='select' id='select' style='%s' onclick=\"__gym.toggle(event)\">"
        "<span id='value'>Choose...</span></div>"
        "<div class='options' id='options' style='display:none;%s'>%s</div>"
        % (_style(cx, cy, 200, 44), _style(cx, cy + 76, 200, 38 * len(options)), opts)
    )
    script = ("window.__gym.opened=false;window.__gym.value=null;"
              "window.__gym.toggle=function(ev){if(ev){ev.stopPropagation();}"
              "var o=document.getElementById('options');"
              "o.style.display=(o.style.display==='none')?'block':'none';"
              "window.__gym.opened=true;};"
              "window.__gym.pick=function(el,ev){if(ev){ev.stopPropagation();}"
              "window.__gym.value=el.getAttribute('data-value');"
              "document.getElementById('value').textContent=window.__gym.value;"
              "document.getElementById('options').style.display='none';};"
              "window.__gym.state=function(){var o=document.getElementById('options');"
              "return {open:o.style.display!=='none',value:window.__gym.value,"
              "openedEver:window.__gym.opened};};")
    instruction = "Choose '%s' from the dropdown." % target
    return instruction, _frame(hue, body, script), {'target': target, 'options': options}


def _build_close_popup(rng, hue):
    title = rng.choice(POPUP_TITLES)
    left = rng.uniform(110, 140)
    top = rng.uniform(55, 80)
    w, h = 400, 220
    body = (
        "<div class='backdrop' id='backdrop'></div>"
        "<div class='dialog' id='dialog' style='left:%dpx;top:%dpx;width:%dpx;height:%dpx'>"
        "<h2>%s</h2><p>Please dismiss this message.</p>"
        "<button class='close' id='close' style='right:10px;top:10px' "
        "onclick=\"__gym.closed=true;document.getElementById('backdrop').style.display='none';"
        "document.getElementById('dialog').style.display='none';\">X</button>"
        "<button class='btn' id='ok' data-label='OK' style='left:130px;top:150px;background:#a0e7a0' "
        "onclick=\"__gym.click(this,event)\">OK</button></div>"
        % (left, top, w, h, title)
    )
    script = ("window.__gym.closed=false;"
              "window.__gym.state=function(){return {closed:!!window.__gym.closed,"
              "clicks:window.__gym.clicks.map(function(c){return {x:c.x,y:c.y};}),"
              "dialog:[%d,%d,%d,%d]};};" % (left, top, w, h))
    instruction = 'Close the popup.'
    return instruction, _frame(hue, body, script), {'title': title}


def _build_drag_slider(rng, hue):
    target = rng.choice((20, 30, 40, 50, 60, 70, 80, 90))
    start = rng.choice([v for v in (0, 10, 100) if abs(v - target) >= 30])
    x0 = rng.uniform(120, 150)
    y0 = rng.uniform(150, 200)
    # A DOM pointer slider avoids OS-specific native thumb geometry and input
    # timing. It still requires actual pointer-down/move/up browser events.
    body = ("<div class='range' id='slider' role='slider' aria-valuemin='0' "
            "aria-valuemax='100' aria-valuenow='%d' style='left:%dpx;top:%dpx;width:360px'>"
            "<div class='range-track'></div><div class='range-thumb' id='thumb'></div></div>"
            % (start, x0, y0))
    script = ("window.__gym.sliderValue=%d;window.__gym.dragged=false;" % start +
              "var slider=document.getElementById('slider'),thumb=document.getElementById('thumb');"
              "function paint(){thumb.style.left=((slider.clientWidth-16)*__gym.sliderValue/100)+'px';"
              "slider.setAttribute('aria-valuenow',__gym.sliderValue);}paint();"
              "var active=false,startX=0;"
              "slider.addEventListener('pointerdown',function(e){active=true;startX=e.clientX;"
              "slider.setPointerCapture(e.pointerId);e.preventDefault();});"
              "slider.addEventListener('pointermove',function(e){if(!active)return;"
              "if(Math.abs(e.clientX-startX)>2){__gym.dragged=true;"
              "var r=slider.getBoundingClientRect();"
              "__gym.sliderValue=Math.max(0,Math.min(100,Math.round((e.clientX-r.left-8)/(r.width-16)*20)*5));paint();}});"
              "slider.addEventListener('pointerup',function(e){active=false;});"
              "slider.addEventListener('pointercancel',function(e){active=false;});"
              "window.__gym.state=function(){return {value:__gym.sliderValue,dragged:__gym.dragged};};")
    instruction = 'Drag the slider to %d.' % target
    return instruction, _frame(hue, body, script), {'target': target, 'start': start}


def _build_click_link(rng, hue):
    labels = rng.sample(LINK_WORDS, 4)
    target = rng.choice(labels)
    cx = rng.uniform(240, 380)
    cy = rng.uniform(150, 190)
    w = 220
    links = ''.join(
        "<a class='link' href='#' data-label='%s' "
        "onclick=\"__gym.click(this,event);return false\">%s</a>" % (word, word)
        for word in labels)
    body = ("<div class='linklist' style='left:%.1fpx;top:%.1fpx;width:%dpx'>%s</div>"
            % (cx - w / 2.0, cy - (40 * len(labels) + 16) / 2.0, w, links))
    script = ("window.__gym.state=function(){return {clicks:window.__gym.clicks.map("
              "function(c){return c.label;})};};")
    instruction = "Open the link '%s'." % target
    return instruction, _frame(hue, body, script), {'target': target, 'links': labels}


def _build_menu_select(rng, hue):
    items = rng.sample(MENU_ITEMS, 4)
    target = rng.choice(items)
    cx = rng.uniform(200, 280)
    cy = rng.uniform(80, 110)
    rows = ''.join(
        "<div class='item' data-value='%s' onclick=\"__gym.choose(this,event)\">%s</div>"
        % (item, item) for item in items)
    body = (
        "<button class='btn' id='menubtn' data-label='Menu' style='%sbackground:#d3b4ff' "
        "onclick=\"__gym.toggleMenu(event)\">Menu</button>"
        "<div class='menu' id='menu' style='display:none;%s'>%s</div>"
        % (_style(cx, cy, 140, 46), _style(cx + 10, cy + 84, 200, 40 * len(items)), rows)
    )
    script = ("window.__gym.opened=false;window.__gym.choice=null;"
              "window.__gym.toggleMenu=function(ev){if(ev){ev.stopPropagation();}"
              "var m=document.getElementById('menu');"
              "m.style.display=(m.style.display==='none')?'block':'none';"
              "window.__gym.opened=true;};"
              "window.__gym.choose=function(el,ev){if(ev){ev.stopPropagation();}"
              "window.__gym.choice=el.getAttribute('data-value');"
              "document.getElementById('menu').style.display='none';};"
              "window.__gym.state=function(){var m=document.getElementById('menu');"
              "return {open:m.style.display!=='none',choice:window.__gym.choice,"
              "openedEver:window.__gym.opened};};")
    instruction = "Open the menu, then choose '%s'." % target
    return instruction, _frame(hue, body, script), {'target': target, 'items': items}


def _build_checkbox(rng, hue):
    labels = rng.sample(CHECK_LABELS, 3)
    target = rng.choice(labels)
    rows = []
    for i, (label, (cx, cy)) in enumerate(zip(labels, _centers(rng, len(labels), top=90,
                                                               bottom=300))):
        rows.append(
            "<label class='row' data-label='%s' style='%s'>"
            "<input type='checkbox' id='c%d' data-label='%s' "
            "onchange=\"__gym.checks['%s']=this.checked\">"
            "<span>%s</span></label>"
            % (label, _style(cx, cy, 220, 44), i, label, label, label))
    script = ("window.__gym.checks={};"
              "window.__gym.state=function(){return {checks:window.__gym.checks};};")
    instruction = "Tick the checkbox next to '%s'." % target
    return instruction, _frame(hue, ''.join(rows), script), {'target': target}


def _build_form_fill(rng, hue):
    name = rng.choice(NAME_WORDS)
    city = rng.choice(CITY_WORDS)
    cx = rng.uniform(260, 380)
    cy = rng.uniform(110, 140)
    w = 320
    body = (
        "<div class='card' style='%s'>"
        "<label class='fieldlabel'>Name</label>"
        "<input class='field' id='name' autocomplete='off'>"
        "<label class='fieldlabel' style='margin-top:10px'>City</label>"
        "<input class='field' id='city' autocomplete='off'>"
        "</div>"
        "<button class='btn' id='submit' data-label='Submit' style='%sbackground:#9ad0ff' "
        "onclick=\"window.__gym.submitted=true\">Submit</button>"
        % (_style(cx, cy, w, 190), _style(cx, cy + 130, 180, 50))
    )
    script = ("window.__gym.submitted=false;"
              "window.__gym.state=function(){return {"
              "name:document.getElementById('name').value,"
              "city:document.getElementById('city').value,"
              "submitted:!!window.__gym.submitted};};")
    instruction = ("Fill in the form: name '%s', city '%s', then submit."
                   % (name, city))
    return instruction, _frame(hue, body, script), {'name': name, 'city': city}


_BUILDERS = {
    KIND_CLICK_BUTTON: _build_click_button,
    KIND_TYPE_TEXT: _build_type_text,
    KIND_DROPDOWN: _build_dropdown,
    KIND_CLOSE_POPUP: _build_close_popup,
    KIND_DRAG_SLIDER: _build_drag_slider,
    KIND_CLICK_LINK: _build_click_link,
    KIND_MENU_SELECT: _build_menu_select,
    KIND_CHECKBOX: _build_checkbox,
    KIND_FORM_FILL: _build_form_fill,
}


MULTI_STEP_TYPES = (KIND_FORM_FILL, KIND_MENU_SELECT, KIND_DROPDOWN,
                   KIND_TYPE_TEXT, KIND_DRAG_SLIDER)


def progress_units(kind, spec):
    if kind == KIND_TYPE_TEXT:
        return len(spec['target']) + 2
    if kind == KIND_FORM_FILL:
        return len(spec['name']) + len(spec['city']) + 3
    if kind in (KIND_DROPDOWN, KIND_MENU_SELECT):
        return 2
    if kind == KIND_DRAG_SLIDER:
        return math.ceil(abs(spec['start'] - spec['target']) / 10)
    return 1


def maximum_progress_units(kind):
    if kind == KIND_TYPE_TEXT:
        return max(map(len, TYPE_WORDS)) + 2
    if kind == KIND_FORM_FILL:
        return max(map(len, NAME_WORDS)) + max(map(len, CITY_WORDS)) + 3
    if kind == KIND_DRAG_SLIDER:
        return 9
    return 2 if kind in (KIND_DROPDOWN, KIND_MENU_SELECT) else 1


def _start_script(kind, spec, start_k):
    total = progress_units(kind, spec)
    if start_k >= total:
        return ''
    if kind in (KIND_TYPE_TEXT, KIND_FORM_FILL):
        fields = [('text', spec['target'])] if kind == KIND_TYPE_TEXT else [
            ('name', spec['name']), ('city', spec['city'])]
        steps = []
        for field, value in fields:
            element = 'document.getElementById(%s)' % json.dumps(field)
            steps.append(element + '.focus();')
            for length in range(1, len(value) + 1):
                steps.append(element + '.value=' + json.dumps(value[:length]) + ';')
        return ''.join(steps[:total - start_k])
    if kind == KIND_DROPDOWN:
        return '__gym.toggle();'
    if kind == KIND_MENU_SELECT:
        return '__gym.toggleMenu();'
    if kind == KIND_DRAG_SLIDER:
        direction = 1 if spec['start'] > spec['target'] else -1
        value = spec['target'] + direction * start_k * 10
        return '__gym.sliderValue=%d;paint();' % value
    return ''


def build(kind, seed, start_k=None):
    """Build one deterministic task instance."""
    if kind not in _BUILDERS:
        raise ValueError('unknown task kind: %r' % (kind,))
    if type(seed) is not int:
        raise ValueError('seed must be an int')
    if start_k is not None and (type(start_k) is not int or start_k < 1):
        raise ValueError('start_k must be a positive int or None')
    rng = random.Random('hands-gym:%s:%d' % (kind, seed))
    hue = rng.randrange(360)
    instruction, html, spec = _BUILDERS[kind](rng, hue)
    spec = dict(spec)
    spec['kind'] = kind
    spec['seed'] = seed
    if start_k is not None and kind in MULTI_STEP_TYPES:
        initializer = _start_script(kind, spec, start_k)
        if initializer:
            html = html.replace('</script></body>', initializer + '</script></body>')
    return {
        'kind': kind,
        'seed': seed,
        'instruction': instruction,
        'html': html,
        'spec': spec,
        'max_steps': MAX_STEPS,
    }


def _prefix(value, target):
    n = 0
    for a, b in zip(value, target):
        if a != b:
            break
        n += 1
    return n


def check(kind, spec, state, prev, step, max_steps=MAX_STEPS):
    """Return ``(success, step_reward, done)`` for the latest transition."""
    if step < 0:
        raise ValueError('step must be non-negative')
    success = False
    reward = 0.0

    if kind == KIND_CLICK_BUTTON:
        clicks = state.get('clicks', [])
        prev_clicks = prev.get('clicks', [])
        success = spec['target'] in clicks
        if success:
            reward += 1.0
        if clicks and not prev_clicks:
            reward += 0.1

    elif kind == KIND_TYPE_TEXT:
        value = state.get('value', '')
        prev_value = prev.get('value', '')
        target = spec['target']
        grow = max(0, _prefix(value, target) - _prefix(prev_value, target))
        reward += 0.15 * grow
        success = bool(state.get('submitted')) and value == target
        if success:
            reward += 1.0

    elif kind == KIND_DROPDOWN:
        success = state.get('value') == spec['target']
        if success:
            reward += 1.0
        if state.get('openedEver') and not prev.get('openedEver'):
            reward += 0.2

    elif kind == KIND_CLOSE_POPUP:
        success = bool(state.get('closed'))
        if success:
            reward += 1.0
        prev_n = len(prev.get('clicks', []))
        clicks = state.get('clicks', [])
        if len(clicks) > prev_n:
            x, y, w, h = state.get('dialog', [0, 0, 0, 0])
            px, py = clicks[prev_n].get('x', -1), clicks[prev_n].get('y', -1)
            if x <= px <= x + w and y <= py <= y + h and prev_n == 0:
                reward += 0.1

    elif kind == KIND_DRAG_SLIDER:
        target = spec['target']
        value = float(state.get('value', 0))
        prev_value = float(prev.get('value', value))
        closeness = 1.0 - abs(value - target) / 100.0
        prev_closeness = 1.0 - abs(prev_value - target) / 100.0
        reward += 0.5 * max(0.0, closeness - prev_closeness)
        success = bool(state.get('dragged')) and abs(value - target) <= 5
        if success:
            reward += 1.0

    elif kind == KIND_CLICK_LINK:
        clicks = state.get('clicks', [])
        prev_clicks = prev.get('clicks', [])
        success = spec['target'] in clicks
        if success:
            reward += 1.0
        if clicks and not prev_clicks:
            reward += 0.1

    elif kind == KIND_MENU_SELECT:
        success = state.get('choice') == spec['target']
        if success:
            reward += 1.0
        if state.get('openedEver') and not prev.get('openedEver'):
            reward += 0.2

    elif kind == KIND_CHECKBOX:
        checks = state.get('checks', {})
        prev_checks = prev.get('checks', {})
        success = bool(checks.get(spec['target']))
        if success:
            reward += 1.0
        if checks != prev_checks and not any(prev_checks.values()):
            reward += 0.1

    elif kind == KIND_FORM_FILL:
        target_name, target_city = spec['name'], spec['city']
        for field, target in (('name', target_name), ('city', target_city)):
            value = state.get(field, '')
            prev_value = prev.get(field, '')
            grow = max(0, _prefix(value, target) - _prefix(prev_value, target))
            reward += 0.12 * grow
        success = (bool(state.get('submitted')) and state.get('name') == target_name
                   and state.get('city') == target_city)
        if success:
            reward += 1.0

    else:
        raise ValueError('unknown task kind: %r' % (kind,))

    done = bool(success or step + 1 >= max_steps)
    return bool(success), float(reward), done
