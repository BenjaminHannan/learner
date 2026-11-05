'use strict';
// The toolbar's Learn button (it replaced the Browser button, Ben Nov 3): "What should I learn about?" -> Start sends Learn-mode
// Motes off with lifetime FOREVER (hours = 0, the same as "until I stop them" in chat); they keep studying until Ben presses Stop.
// Pure Node: startLearn(topic, count, hours) and stopMote(id) are main.js's; the study is kept in userData/learn-button.json.
const fs = require('fs');
const path = require('path');

const COUNT = 3, FOREVER = 0;

class LearnButton {
  // o: { dir, startLearn(topic, count, hours) -> {ok, ids, topic, error}, stopMote(id), onChange(view), now }
  constructor(o) {
    this.o = o; this.file = path.join(o.dir, 'learn-button.json'); this.now = o.now || Date.now;
    this.cur = null;
    try { const j = JSON.parse(fs.readFileSync(this.file, 'utf8')); if (j && typeof j.topic === 'string' && Array.isArray(j.ids)) this.cur = j; } catch (e) { /* none */ }
  }
  save() { try { if (this.cur) fs.writeFileSync(this.file, JSON.stringify(this.cur)); else fs.rmSync(this.file, { force: true }); } catch (e) { /* the Motes still run */ } }
  view() { return this.cur ? { learning: true, topic: this.cur.topic, since: this.cur.since, count: this.cur.ids.length, by: this.cur.by || 'ben' } : { learning: false }; }
  changed() { try { this.o.onChange && this.o.onChange(this.view()); } catch (e) { /* UI only */ } }
  // by: 'ben' (the button / chat) or 'glim' (the study keeper, src/studykeeper.js: Glim's own study while it has nothing to say)
  start(topic, by) {
    topic = String(topic || '').replace(/\s+/g, ' ').trim().slice(0, 200);
    if (!topic) return { error: 'Type what Glim should learn about.' };
    if (this.cur) this.stop();   // one study at a time: a new topic replaces the old one
    const r = this.o.startLearn(topic, COUNT, FOREVER) || {};
    if (!r.ok) return { error: r.error || 'Learn mode could not start.' };
    this.cur = { topic, ids: (r.ids || []).slice(), since: this.now(), by: by === 'glim' ? 'glim' : 'ben' };
    this.save(); this.changed();
    return { ok: true, ...this.view(), partial: r.error || null };
  }
  stop() {
    if (!this.cur) return { ok: true, learning: false };
    for (const id of this.cur.ids) { try { this.o.stopMote(id); } catch (e) { /* already gone */ } }
    const topic = this.cur.topic;
    this.cur = null; this.save(); this.changed();
    return { ok: true, learning: false, stopped: topic };
  }
  // a Learn Mote of this study finished a run (its notes are already saved by memory_save)
  owns(id) { return !!(this.cur && this.cur.ids.includes(id)); }
}

module.exports = { LearnButton, COUNT, FOREVER };
