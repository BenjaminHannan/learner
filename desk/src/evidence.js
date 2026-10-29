'use strict';
// Observed browser reads are attribution data, never factual verification or
// authority to act. The page/model cannot create this private transport field.
const crypto = require('crypto');
const SOURCE_READ = Symbol('premonition.observedSourceRead');
const MAX_QUOTE = 600;
const MAX_READS = 16;
const sha256 = value => crypto.createHash('sha256').update(value, 'utf8').digest('hex');
const validText = value => typeof value === 'string' && Buffer.from(value, 'utf8').toString('utf8') === value;

function attachSourceRead(result, metadata) {
  Object.defineProperty(result, SOURCE_READ, { value: Object.freeze({ ...metadata }), enumerable: false });
  return result;
}

function sourceUrl(value) {
  if (!validText(value) || value.length > 2048) return null;
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch (e) { return null; }
}

function expiry(value) {
  if (value == null || value === '') return null;
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value) || Number(value.slice(0, 4)) < 1) throw new Error('Expiry must be a real YYYY-MM-DD date.');
  const date = new Date(value + 'T00:00:00Z');
  if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== value) throw new Error('Expiry must be a real YYYY-MM-DD date.');
  return value;
}

class EvidenceRegistry {
  constructor({ enabled = false, threadId = null, helperId = null, isSecret = () => false, now = Date.now } = {}) {
    this.enabled = enabled === true;
    this.context = { run_id: crypto.randomUUID(), thread_id: threadId, helper_id: helperId };
    this.isSecret = isSecret;
    this.now = now;
    this.reads = new Map();
  }

  recordRead(tool, result, toolCallId, maxChars) {
    if (!this.enabled || tool !== 'browser_read' || !result || result.error || typeof result.text !== 'string') return null;
    const source = result[SOURCE_READ];
    if (!source || !validText(source.body) || !source.body.trim() || source.body === '(no readable text)' ||
        !Number.isInteger(source.bodyStart) || source.bodyStart < 0 ||
        result.text.slice(source.bodyStart, source.bodyStart + source.body.length) !== source.body) return null;
    const url = sourceUrl(source.url);
    if (!url || this.isSecret(url)) return null;
    const readId = 'read_' + crypto.randomBytes(8).toString('hex');
    const marker = '\n[Source read: ' + readId + ']';
    const limit = Math.floor(Number(maxChars)) - marker.length;
    if (!Number.isFinite(limit) || limit < 1) return null;
    const clipped = result.text.length > limit;
    const end = clipped ? Math.max(0, limit - '\n[truncated]'.length) : result.text.length;
    const visibleBody = source.body.slice(0, Math.max(0, end - source.bodyStart));
    if (!visibleBody.trim()) return null;
    this.reads.set(readId, { read_id: readId,
      tool_call_id: typeof toolCallId === 'string' && /^[A-Za-z0-9_-]{1,80}$/.test(toolCallId) ? toolCallId : null,
      url, page: Number.isInteger(source.page) ? source.page : 1,
      read_at: new Date(Number.isFinite(source.readAt) ? source.readAt : this.now()).toISOString(),
      body: visibleBody, visible_body_sha256: sha256(visibleBody) });
    while (this.reads.size > MAX_READS) this.reads.delete(this.reads.keys().next().value);
    return { readId, text: result.text.slice(0, end) + (clipped ? '\n[truncated]' : '') + marker };
  }

  metadata(args = {}) {
    if (!this.enabled) return null;
    const expires = expiry(args.expires);
    const source = typeof args.source_read_id === 'string' ? this.reads.get(args.source_read_id) : null;
    const quote = typeof args.source_quote === 'string' ? args.source_quote.trim() : '';
    let reason = !args.source_read_id ? 'no_source_read' : !source ? 'unknown_source_read' : null;
    if (!reason && (!validText(quote) || quote.length < 12 || quote.length > MAX_QUOTE)) reason = 'invalid_quote';
    if (!reason && !source.body.includes(quote)) reason = 'quote_not_visible';
    if (!reason && (this.isSecret(quote) || this.isSecret(source.url))) reason = 'secret_metadata';
    const attribution = { status: reason ? 'unattributed' : 'attributed', verified: false, reason, source: null };
    if (!reason) {
      const { body, ...record } = source;
      attribution.source = { ...record, quote, quote_sha256: sha256(quote) };
    }
    // Origin/context are application values. No model-supplied origin, status,
    // user role, or verified flag is copied into the ledger request.
    return { origin: 'learn-research', context: { ...this.context }, attribution, expires };
  }
}

module.exports = { SOURCE_READ, attachSourceRead, EvidenceRegistry, MAX_QUOTE, MAX_READS, expiry, sha256 };
