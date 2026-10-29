'use strict';
const WORDS = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, eleven: 11, twelve: 12 };
const number = '(?:\\d+(?:\\.\\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)';
const value = (s) => WORDS[s.toLowerCase()] || Number(s);
function parseLearnConfig(text) {
  const t = String(text || '').trim().toLowerCase();
  if (/^(?:please\s+)?(?:stop|cancel|never\s*mind|nevermind|forget it)(?:[.!\s]|$)/.test(t)) return { cancel: true };
  const countMatch = t.match(new RegExp('\\b(' + number + ')\\s+motes?\\b')) || t.match(new RegExp('^\\s*(' + number + ')\\s*[.!]?\\s*$'));
  const durationMatch = t.match(new RegExp('\\b(?:for\\s+)?(' + number + ')\\s*(hours?|hrs?|h|minutes?|mins?|m)\\b'));
  const count = countMatch ? value(countMatch[1]) : null;
  let hours = null, lifetime = 'missing';
  if (durationMatch) { hours = value(durationMatch[1]) / (/^(?:m|min)/.test(durationMatch[2]) ? 60 : 1); lifetime = hours > 0 ? 'finite' : 'invalid'; }
  else if (/\b(?:forever|no limit|until (?:i|you|we) stop (?:them|it)|until stopped)\b/.test(t)) lifetime = 'forever';
  else if (/\b(?:until|for|hours?|hrs?|minutes?|mins?|stop them|stop it)\b/.test(t) || /\d/.test(t.replace(countMatch ? countMatch[0] : '', ''))) lifetime = 'invalid';
  if (count !== null && (!Number.isInteger(count) || count < 1 || count > 12)) return { cancel: false, count, lifetime: 'invalid', hours: null };
  return { cancel: false, count, lifetime, hours };
}
function isLearnConfigReply(text) {
  return new RegExp('^\\s*' + number + '\\s*[.!]?\\s*$', 'i').test(String(text || '')) || /\b(?:motes?|hours?|hrs?|minutes?|mins?|until|forever|no limit|for|stop|cancel|never\s*mind|nevermind|forget it)\b|^\s*\d+\s*$/i.test(String(text || ''));
}
function parseLearnRequest(text) {
  let topic = String(text || '').replace(/^\s*(?:(?:please|ok|okay|hey)[ ,]+)?(?:go\s+|can you\s+|could you\s+)?(?:learn|study)\s+(?:about\s+|how to\s+|to\s+)?/i, '');
  const config = parseLearnConfig(topic);
  topic = topic.replace(new RegExp('\\b(?:with\\s+|using\\s+)?' + number + '\\s+motes?\\b', 'i'), ' ')
    .replace(new RegExp('\\bfor\\s+' + number + '\\s*(?:hours?|hrs?|h|minutes?|mins?|m)\\b', 'i'), ' ')
    .replace(/\b(?:until (?:i|you|we) stop (?:them|it)|until stopped|forever|no limit)\b/i, ' ')
    .replace(/\buntil\s+[^,.;]+/i, ' ')
    .replace(/\bthen\s+stop\s+(?:them|it)\b/i, ' ')
    .replace(/\s+/g, ' ').replace(/[\s,.;]+$/, '').trim();
  return { topic, ...config };
}
// Pure routing apart from the injected startup operation. The caller owns per-thread pending state.
function learnFlow({ pending, text, isAsk, start }) {
  const ask = (topic) => '[Learn mode: Ben wants to learn "' + topic + '". Ask how many Motes and for how long; offer "3 Motes, until I stop them", "1 Mote, 1 hour", and "6 Motes, 8 hours". Do nothing else yet.] ';
  const resultNote = (r, a) => r.ok
    ? '[Learn mode: started ' + r.count + ' Motes studying "' + r.topic + '" quietly' + (a.lifetime === 'finite' ? ' for ' + a.hours + ' hours' : ' until Ben stops them') + (r.error ? '. Only some started: ' + r.error : '') + '. Their saved notes may be eligible for sleep training; training has not been confirmed. State this briefly. Do not research it yourself.] '
    : '[Learn mode could not start any Motes: ' + r.error + '. Tell Ben this plainly. Do not research it yourself.] ';
  const validCount = (n) => Number.isInteger(n) && n >= 1 && n <= 12;
  if (pending && isLearnConfigReply(text)) {
    const a = parseLearnConfig(text);
    if (a.cancel) return { handled: true, pending: null, note: '[Learn setup was cancelled. Acknowledge briefly. Do not start Motes or research.] ' };
    if (a.lifetime === 'finite' || a.lifetime === 'forever') return { handled: true, pending: null, note: resultNote(start(pending.topic, a.count || pending.count || 3, a.lifetime === 'finite' ? a.hours : 0), a) };
    return { handled: true, pending: { topic: pending.topic, count: validCount(a.count) ? a.count : pending.count }, note: '[Learn setup is still pending. Ask for a duration in hours or minutes, or whether to run until stopped. Do not start Motes or research.] ' };
  }
  if (isAsk) {
    const a = parseLearnRequest(text);
    if (a.topic && (a.lifetime === 'finite' || a.lifetime === 'forever')) return { handled: true, pending: null, note: resultNote(start(a.topic, a.count || 3, a.lifetime === 'finite' ? a.hours : 0), a) };
    if (a.topic) return { handled: true, pending: { topic: a.topic, count: validCount(a.count) ? a.count : null }, note: ask(a.topic) };
    return { handled: true, pending: null, note: '[Ask what topic Ben wants to learn. Do not start Motes or research yet.] ' };
  }
  return { handled: false, pending: null };
}
module.exports = { parseLearnConfig, parseLearnRequest, isLearnConfigReply, learnFlow };
