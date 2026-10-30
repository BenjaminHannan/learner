'use strict';
// A single dated item, chosen from local saved notes and the active tracking list.
const fs = require('fs');
const path = require('path');
const { dayKey } = require('./followup');
function pick({ notes = [], tracked = [], now = new Date() }) {
  const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  const dates = [dayKey(now), dayKey(tomorrow)];
  const candidates = [];
  const relevant = (text) => /\b(assignment|homework|essay|project|exam|test|quiz|class|meeting|event|deadline|due|presentation|appointment)\b/i.test(text);
  for (const item of tracked) if (item && item.done === undefined && dates.includes(item.until) && item.what && relevant(String(item.what))) candidates.push({ text: String(item.what), due: item.until });
  for (const note of notes) {
    const text = String(note && note.text || '');
    if (!relevant(text)) continue;
    const date = text.match(/\b\d{4}-\d{2}-\d{2}\b/);
    if (date && dates.includes(date[0])) candidates.push({ text, due: date[0] });
  }
  candidates.sort((a, b) => a.due.localeCompare(b.due));
  return candidates[0] || null;
}
function read(file, now = new Date()) {
  try { const c = JSON.parse(fs.readFileSync(file, 'utf8')); return c.day === dayKey(now) && c.text ? c : null; } catch (_) { return null; }
}
function write(file, card) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = file + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(card)); fs.renameSync(tmp, file);
}
async function prepare({ file, notes, tracked, now = new Date(), generate }) {
  if (read(file, now)) return null;
  const item = pick({ notes, tracked, now }); if (!item) return null;
  const text = String(await generate(item) || '').trim().slice(0, 4000);
  if (!text) return null;
  const card = { day: dayKey(now), item: item.text, due: item.due, text };
  write(file, card); return card;
}
module.exports = { pick, read, write, prepare };
