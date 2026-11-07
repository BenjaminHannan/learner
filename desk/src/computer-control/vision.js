'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const Glim = require('../glimside');
const { EYE_ID, SHAPE } = require('../eyes');
const budget = require('../context-budget');

// Ask the existing Glim process to encode the screenshot. A missing or failed
// eye is a hard stop; a text-only placeholder must never authorize a click.
async function encode(image, signal) {
  if (signal?.aborted) throw Error('task stopped');
  const parts = await Glim.probe();
  if (!parts?.eyes || !parts?.brain || !parts?.gateway) throw Error('Glim eyes are unavailable');
  if (typeof image !== 'string' || !image.startsWith('data:image/png;base64,')) throw Error('screenshot unavailable');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'glim-eye-')); fs.chmodSync(dir,0o700);
  const file = path.join(dir,'frame.png');
  try {
    fs.writeFileSync(file,Buffer.from(image.slice(image.indexOf(',')+1),'base64'),{mode:0o600});
    const result = await Glim.post('/eyes',{id:randomUUID(),path:file},30000);
    if (signal?.aborted) throw Error('task stopped');
    if (!result?.ok || result.eye !== EYE_ID || !Array.isArray(result.shape) || result.shape[0] !== SHAPE[0] || result.shape[1] !== SHAPE[1] || typeof result.f16 !== 'string' || Buffer.from(result.f16,'base64').length !== SHAPE[0]*SHAPE[1]*2) throw Error('Glim could not read the screenshot');
    return { type:'image_features', image_features:{ f16:result.f16, shape:result.shape, eye:result.eye } };
  } finally { try { fs.unlinkSync(file); } catch (_) {} try { fs.rmdirSync(dir); } catch (_) {} }
}

// The model receives 64 projected rows, not 130 KB worth of text tokens.
// Fit a shadow copy and restore surviving feature payloads before the request.
function shadow(messages) {
  const restore = new Map();
  const copy = messages.map(m => {
    if (!Array.isArray(m.content) || !m.content.some(p => p?.type === 'image_features')) return m;
    const content = m.content.map(p => p?.type === 'image_features' ? { ...p, image_features:{ ...p.image_features, f16:'x'.repeat(2500) } } : p);
    restore.set(content,m.content); return { ...m, content };
  });
  return { copy, restore };
}
function fit(messages, tools, limit, protectedIndex, retainedContext) {
  const { copy, restore } = shadow(messages), result = budget.fitRequest(copy,tools,limit,protectedIndex,retainedContext);
  result.messages = result.messages.map(m => restore.has(m.content) ? { ...m, content:restore.get(m.content) } : m);
  return result;
}
function tokens(messages, tools) { return budget.requestTokens(shadow(messages).copy,tools); }
module.exports = { encode, fit, tokens };
