'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const { performance } = require('node:perf_hooks');
const { TextDecoder } = require('node:util');

const CEILINGS = Object.freeze({ maxVideoBytes: 67108864, maxLedgerBytes: 262144, maxProofBytes: 262144, maxSealBytes: 262144, maxLineBytes: 4096, maxRows: 4096, maxFrames: 600, maxWidth: 1280, maxHeight: 720, maxDurationMs: 30000, maxRecords: 64, maxRejects: 256, timeoutMs: 10000 });
const DEFAULT_POLICY = Object.freeze({ schema: 'screen-candidate-policy/v1', minSeparationMs: 5, maxGapMs: 100, maxClockUncertaintyMs: 1, maxTransformUncertaintyPx: 0.5 });
const COMPILER = Object.freeze({ id: 'offline-screen-candidates', version: '1', sha256: hash(fs.readFileSync(__filename)) });
const HEX = /^[a-f0-9]{64}$/;
const digestPattern = value => typeof value === 'string' && HEX.test(value);
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const integer = value => Number.isSafeInteger(value) && value > 0;
const identifier = value => typeof value === 'string' && value.length > 0 && Buffer.byteLength(value) <= 256;
const finite = value => typeof value === 'number' && Number.isFinite(value);
const rational = value => object(value) && Number.isSafeInteger(value.value) && integer(value.timescale);
const comparePts = (left, right) => BigInt(left.value) * BigInt(right.timescale) - BigInt(right.value) * BigInt(left.timescale);

function hash(bytes) { return crypto.createHash('sha256').update(bytes).digest('hex'); }

function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (object(value)) return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
  return JSON.stringify(value);
}

function frozen(value) {
  if (value && typeof value === 'object') {
    for (const child of Object.values(value)) frozen(child);
    Object.freeze(value);
  }
  return value;
}

function safeJson(bytes, check) {
  check();
  const parsed = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
  const pending = [[parsed, 0]];
  let nodes = 0;
  while (pending.length) {
    check();
    const [value, depth] = pending.pop();
    if (++nodes > 20000 || depth > 24) throw Error('JSON complexity limit');
    if (value && typeof value === 'object') {
      for (const child of Object.values(value)) pending.push([child, depth + 1]);
    }
  }
  check();
  return parsed;
}

function snapshot(value, maxBytes, check) {
  const bytes = Buffer.from(JSON.stringify(value));
  if (bytes.length > maxBytes) throw Error('JSON byte limit');
  return safeJson(bytes, check);
}

function boundBytes(value, expected, ceiling, name, check) {
  if (!(value instanceof Uint8Array) || value.buffer instanceof SharedArrayBuffer || value.byteLength < 1 || value.byteLength > ceiling) throw Error(name + ' byte limit');
  if (!object(expected) || !integer(expected.bytes) || !digestPattern(expected.sha256)) throw Error(name + ' expected binding missing');
  const bytes = Buffer.from(value);
  const actual = { sha256: hash(bytes), bytes: bytes.length };
  check();
  if (expected.bytes !== actual.bytes || expected.sha256 !== actual.sha256) throw Error(name + ' binding mismatch');
  return { bytes, binding: actual };
}

function readDecoder(decoder, video, caps, check) {
  if (!decoder) return null;
  if (decoder.schema !== 'screen-video-decoder/v1' || typeof decoder.readFrame !== 'function') throw Error('decoder interface invalid');
  const source = snapshot(decoder.source, 512, check);
  if (source.bytes !== video.bytes || source.sha256 !== video.sha256) throw Error('decoder source mismatch');
  const implementation = snapshot(decoder.implementation, 1024, check);
  if (!identifier(implementation.id) || !identifier(implementation.version) || !digestPattern(implementation.sha256)) throw Error('decoder identity invalid');
  if (!Array.isArray(decoder.index) || !decoder.index.length || decoder.index.length > caps.maxFrames) throw Error('decoder frame limit');
  const index = snapshot(decoder.index, caps.maxProofBytes, check);
  index.forEach((entry, offset) => {
    check();
    if (entry.encodedOrdinal !== offset + 1 || !rational(entry.encodedPts) || !integer(entry.width) || !integer(entry.height) || entry.width > caps.maxWidth || entry.height > caps.maxHeight) throw Error('decoder index invalid');
    if (offset && comparePts(entry.encodedPts, index[offset - 1].encodedPts) <= 0n) throw Error('decoder PTS order');
  });
  const elapsed = index[index.length - 1].encodedPts.value / index[index.length - 1].encodedPts.timescale - index[0].encodedPts.value / index[0].encodedPts.timescale;
  if (!finite(elapsed) || elapsed * 1000 > caps.maxDurationMs) throw Error('decoder duration limit');
  return { implementation, index, readFrame: ordinal => decoder.readFrame(ordinal) };
}

function prepare(args) {
  const started = performance.now();
  const caps = { ...CEILINGS };
  if (!object(args.limits || {})) throw Error('invalid limits');
  for (const [key, value] of Object.entries(args.limits || {})) {
    if (!Object.hasOwn(CEILINGS, key) || !integer(value) || value > CEILINGS[key]) throw Error('invalid limit ' + key);
    caps[key] = value;
  }
  const check = () => { if (performance.now() - started >= caps.timeoutMs) throw Error('elapsed timeout'); };
  const segment = snapshot(args.segment, 4096, check);
  if (!object(segment) || segment.schema !== 'screen-learning-segment/v1' || !['synthetic', 'native'].includes(segment.kind) || !identifier(segment.sessionId) || !identifier(segment.segmentId) || !object(segment.expected)) throw Error('invalid segment');
  const ledger = boundBytes(args.ledgerBytes, segment.expected.ledger, caps.maxLedgerBytes, 'ledger', check);
  const video = boundBytes(args.videoBytes, segment.expected.video, caps.maxVideoBytes, 'video', check);
  let proof = null;
  let proofBinding = null;
  if (args.proofBytes !== undefined && args.proofBytes !== null) {
    const bound = boundBytes(args.proofBytes, segment.expected.proof, caps.maxProofBytes, 'proof', check);
    proof = safeJson(bound.bytes, check);
    proofBinding = bound.binding;
    if (!object(proof)) throw Error('invalid proof JSON');
  } else if (segment.expected.proof !== null) throw Error('proof binding mismatch');
  const rows = [];
  const text = new TextDecoder('utf-8', { fatal: true }).decode(ledger.bytes);
  const lines = text.split('\n');
  if (lines[lines.length - 1] === '') lines.pop();
  for (const line of lines) {
    check();
    if (!line.length || Buffer.byteLength(line) > caps.maxLineBytes || rows.length >= caps.maxRows) throw Error('ledger line limit');
    rows.push(safeJson(Buffer.from(line), check));
  }
  const frames = rows.filter(row => object(row) && row.type === 'frame');
  const events = rows.filter(row => object(row) && ['mouse', 'key', 'event'].includes(row.type));
  if (frames.length > caps.maxFrames) throw Error('source frame limit');
  const decoder = readDecoder(args.decoder, video.binding, caps, check);
  const inputs = { ledger: ledger.binding, video: video.binding, proof: proofBinding };
  const sourceSha256 = hash(canonical({ ledger: inputs.ledger, video: inputs.video }));
  check();
  return { segment, rows, frames, events, proof, decoder, caps, check, inputs, sourceSha256 };
}

function diagnose(context, policy) {
  const { segment, rows, frames, proof, decoder, caps } = context;
  const reasons = new Set();
  const add = reason => reasons.add(reason);
  if (!decoder) add('DECODER_UNAVAILABLE');
  if (!proof) add('PROOF_MISSING');
  if (segment.kind === 'native') {
    if (proof?.schema === 'synthetic-screen-evidence/v1' || proof?.synthetic === true) throw Error('synthetic evidence cannot bind native input');
    add('NATIVE_LABELS_UNSUPPORTED');
    add('CLOCK_MAPPING_UNPROVEN');
    add('GEOMETRY_UNVERIFIED');
    const ends = rows.filter(row => object(row) && row.type === 'source_end');
    if (ends.length !== 1 || ends[0].complete !== true) add('SOURCE_INCOMPLETE');
    if (proof?.version === 2) {
      add('TEMPORAL_ONLY_PROOF');
      if (!object(proof.output) || proof.output.sha256 !== context.inputs.video.sha256 || proof.output.bytes !== context.inputs.video.bytes || proof.session !== segment.sessionId) throw Error('native proof output binding mismatch');
    } else if (proof) add('UNSUPPORTED_PROOF');
    return { reasons: [...reasons].sort(), mappings: [], captures: [], geometry: null, clock: null };
  }
  if (proof?.schema !== 'synthetic-screen-evidence/v1' || proof.synthetic !== true) {
    if (proof) add('SYNTHETIC_PROOF_REQUIRED');
    return { reasons: [...reasons].sort(), mappings: [], captures: [], geometry: null, clock: null };
  }
  if (proof.sessionId !== segment.sessionId || proof.segmentId !== segment.segmentId || canonical(proof.bindings) !== canonical({ ledger: context.inputs.ledger, video: context.inputs.video })) throw Error('synthetic proof binding mismatch');
  const source = proof.source;
  const terminal = rows.filter(row => object(row) && row.type === 'source_end');
  if (!object(source) || source.complete !== true || terminal.length !== 1 || terminal[0] !== rows[rows.length - 1] || terminal[0].complete !== true || terminal[0].sessionId !== segment.sessionId || terminal[0].frameCount !== frames.length || source.frameCount !== frames.length) add('SOURCE_INCOMPLETE');
  if (!source || !integer(source.generation) || !identifier(source.sourceId) || !identifier(source.windowId) || !identifier(source.displayId)) add('SOURCE_IDENTITY_UNPROVEN');
  if (rows.some(row => !object(row) || !['frame', 'mouse', 'key', 'source_end'].includes(row.type))) add('SOURCE_GAP_OR_ERROR');
  if (rows.some(row => object(row) && row.sessionId !== segment.sessionId)) add('SOURCE_SESSION_MISMATCH');
  const clock = proof.clock;
  if (!object(clock) || clock.verified !== true || !identifier(clock.id) || !identifier(clock.epoch) || clock.domain !== 'synthetic-monotonic-ms' || !Array.isArray(clock.validIntervalMs) || clock.validIntervalMs.length !== 2 || !clock.validIntervalMs.every(finite) || clock.validIntervalMs[0] < 0 || clock.validIntervalMs[1] <= clock.validIntervalMs[0] || !finite(clock.sourceScale) || clock.sourceScale <= 0 || !finite(clock.sourceOffsetMs) || !finite(clock.eventScale) || clock.eventScale <= 0 || !finite(clock.eventOffsetMs) || !finite(clock.uncertaintyMs) || clock.uncertaintyMs < 0 || clock.uncertaintyMs > policy.maxClockUncertaintyMs) add('CLOCK_MAPPING_UNPROVEN');
  if (clock?.validIntervalMs && clock.validIntervalMs[1] - clock.validIntervalMs[0] > caps.maxDurationMs) add('CLOCK_VALIDITY_LIMIT');
  const geometry = proof.geometry;
  const rectangle = rect => object(rect) && ['x', 'y', 'width', 'height'].every(key => finite(rect[key])) && rect.width > 0 && rect.height > 0;
  if (!object(geometry) || geometry.verified !== true || !identifier(geometry.id) || geometry.generation !== source?.generation || geometry.sourceId !== source?.sourceId || geometry.windowId !== source?.windowId || geometry.displayId !== source?.displayId || !rectangle(geometry.pointBounds) || !rectangle(geometry.contentRect) || !finite(geometry.scaleX) || geometry.scaleX <= 0 || !finite(geometry.scaleY) || geometry.scaleY <= 0 || !finite(geometry.offsetX) || !finite(geometry.offsetY) || !finite(geometry.backingScale) || geometry.backingScale <= 0 || !finite(geometry.uncertaintyPx) || geometry.uncertaintyPx < 0 || geometry.uncertaintyPx > policy.maxTransformUncertaintyPx || !integer(geometry.outputWidth) || !integer(geometry.outputHeight) || geometry.outputWidth > caps.maxWidth || geometry.outputHeight > caps.maxHeight) add('GEOMETRY_UNVERIFIED');
  if (!reasons.has('GEOMETRY_UNVERIFIED')) {
    const bounds = geometry.pointBounds;
    const rect = geometry.contentRect;
    const expected = { x: bounds.x * geometry.scaleX + geometry.offsetX, y: bounds.y * geometry.scaleY + geometry.offsetY, width: bounds.width * geometry.scaleX, height: bounds.height * geometry.scaleY };
    if (['x', 'y', 'width', 'height'].some(key => Math.abs(expected[key] - rect[key]) > 1e-8) || rect.x < 0 || rect.y < 0 || rect.x + rect.width > geometry.outputWidth || rect.y + rect.height > geometry.outputHeight) add('GEOMETRY_UNVERIFIED');
  }
  if (proof.observation?.cursor !== 'excluded' || proof.observation?.targetVisibility !== 'synthetic-all-visible') add('PRE_OBSERVATION_UNPROVEN');
  const mappings = proof.pipeline?.mappings;
  const captures = [];
  if (proof.pipeline?.verified !== true || proof.pipeline?.temporal !== 'identity' || !identifier(proof.pipeline?.id) || !Array.isArray(mappings) || mappings.length !== frames.length || !frames.length || !decoder || frames.length !== decoder.index.length) add('FRAME_MAPPING_UNPROVEN');
  if (!reasons.has('FRAME_MAPPING_UNPROVEN')) {
    frames.forEach((frame, offset) => {
      context.check();
      const mapping = mappings[offset];
      const entry = decoder.index[offset];
      const pts = { value: frame.presentationValue, timescale: frame.presentationTimescale };
      if (!object(mapping) || frame.frameId !== offset + 1 || frame.generation !== source?.generation || frame.transformId !== geometry?.id || frame.clockEpoch !== clock?.epoch || !digestPattern(frame.rawSha256) || frame.rawByteCount !== entry.width * entry.height * 4 || !rational(pts) || frame.presentationValue < 0 || mapping.sourceFrameId !== frame.frameId || mapping.submissionOrdinal !== offset + 1 || mapping.encodedOrdinal !== offset + 1 || mapping.rawSha256 !== frame.rawSha256 || mapping.rawByteCount !== frame.rawByteCount || !rational(mapping.sourcePts) || !rational(mapping.encodedPts) || comparePts(mapping.sourcePts, pts) !== 0n || comparePts(mapping.encodedPts, entry.encodedPts) !== 0n || entry.width !== geometry?.outputWidth || entry.height !== geometry?.outputHeight) {
        add('FRAME_MAPPING_UNPROVEN');
        return;
      }
      if (offset && (!rational({ value: frames[offset - 1].presentationValue, timescale: frames[offset - 1].presentationTimescale }) || comparePts(pts, { value: frames[offset - 1].presentationValue, timescale: frames[offset - 1].presentationTimescale }) <= 0n)) add('SOURCE_GAP_OR_ERROR');
      if (!reasons.has('CLOCK_MAPPING_UNPROVEN')) {
        const center = pts.value / pts.timescale * clock.sourceScale + clock.sourceOffsetMs;
        const interval = [center - clock.uncertaintyMs, center + clock.uncertaintyMs];
        if (!interval.every(finite) || interval[0] < clock.validIntervalMs[0] || interval[1] > clock.validIntervalMs[1]) add('CLOCK_MAPPING_UNPROVEN');
        if (offset && center - captures[offset - 1]?.center > policy.maxGapMs) add('SOURCE_GAP_OR_ERROR');
        captures.push({ center, interval });
      }
    });
  }
  return { reasons: [...reasons].sort(), mappings: Array.isArray(mappings) ? mappings : [], captures, geometry, clock };
}

function readPolicy(value, check) {
  const policy = snapshot(value === undefined ? DEFAULT_POLICY : value, 1024, check);
  if (!object(policy) || canonical(Object.keys(policy).sort()) !== canonical(Object.keys(DEFAULT_POLICY).sort()) || policy.schema !== DEFAULT_POLICY.schema || !finite(policy.minSeparationMs) || policy.minSeparationMs <= 0 || policy.minSeparationMs > 30000 || !finite(policy.maxGapMs) || policy.maxGapMs <= 0 || policy.maxGapMs > 1000 || !finite(policy.maxClockUncertaintyMs) || policy.maxClockUncertaintyMs < 0 || policy.maxClockUncertaintyMs > 100 || !finite(policy.maxTransformUncertaintyPx) || policy.maxTransformUncertaintyPx < 0 || policy.maxTransformUncertaintyPx > 10) throw Error('invalid candidate policy');
  return policy;
}

function report(context, diagnosis) {
  return { schema: 'screen-segment-inspection/v1', trainingEligible: false, kind: context.segment.kind, inputs: context.inputs, sourceSha256: context.sourceSha256, frames: context.frames.length, events: context.events.length, reasons: diagnosis.reasons, decoder: context.decoder?.implementation || null };
}

function inspectSegment(args) {
  const context = prepare(args);
  const diagnosis = diagnose(context, readPolicy(undefined, context.check));
  context.check();
  return frozen(report(context, diagnosis));
}

function membership(context, inputSeal) {
  const seal = snapshot(inputSeal, context.caps.maxSealBytes, context.check);
  if (!object(seal) || seal.schema !== 'screen-candidate-split-seal/v1' || !Array.isArray(seal.assignments) || !seal.assignments.length || seal.assignments.length > 256) throw Error('invalid split seal');
  const sessions = new Set();
  const groups = new Map();
  const artifacts = new Map();
  let selected;
  const bind = (map, key, split) => {
    if (map.has(key) && map.get(key) !== split) throw Error('split leakage conflict');
    map.set(key, split);
  };
  for (const assignment of seal.assignments) {
    context.check();
    if (!object(assignment) || !identifier(assignment.sessionId) || !identifier(assignment.groupId) || !['train', 'validation', 'test', 'audit'].includes(assignment.split) || sessions.has(assignment.sessionId)) throw Error('ambiguous session membership');
    sessions.add(assignment.sessionId);
    bind(groups, assignment.groupId, assignment.split);
    for (const field of ['sourceSha256s', 'contentSha256s', 'eventSha256s']) {
      const hashes = assignment[field];
      if (!Array.isArray(hashes) || hashes.length > 4096 || (field !== 'eventSha256s' && !hashes.length) || !hashes.every(digestPattern) || new Set(hashes).size !== hashes.length) throw Error('invalid split hashes');
      for (const digest of hashes) bind(artifacts, digest, assignment.split);
    }
    if (assignment.sessionId === context.segment.sessionId) selected = assignment;
  }
  if (!selected || !selected.sourceSha256s.includes(context.sourceSha256)) throw Error('session not sealed');
  const contents = new Set(selected.contentSha256s);
  const events = new Set(selected.eventSha256s);
  if (!contents.has(context.inputs.video.sha256) || context.frames.some(frame => digestPattern(frame.rawSha256) && !contents.has(frame.rawSha256)) || context.events.some(event => !events.has(hash(canonical(event))))) throw Error('content not sealed');
  return { assignment: selected, sha256: hash(canonical(seal)) };
}

function eventCandidate(context, diagnosis, policy, event) {
  const reasons = [...diagnosis.reasons];
  if (!identifier(event.eventId)) reasons.push('EVENT_ID_UNPROVEN');
  if (event.type !== 'mouse' || event.kind !== 'mouse_down' || ![0, 1].includes(event.button) || !Array.isArray(event.modifiers) || event.modifiers.length || event.down !== true) reasons.push('UNSUPPORTED_EVENT');
  if (event.source !== 'physical_unverified') reasons.push('ORIGIN_UNSUPPORTED');
  if (event.generation !== context.proof?.source?.generation || event.transformId !== diagnosis.geometry?.id) reasons.push('STALE_GENERATION_OR_TRANSFORM');
  let interval;
  if (!reasons.length) {
    const clock = diagnosis.clock;
    const center = event.eventTimestampNs * clock.eventScale + clock.eventOffsetMs;
    interval = [center - clock.uncertaintyMs, center + clock.uncertaintyMs];
    if (!Number.isSafeInteger(event.eventTimestampNs) || event.eventTimestampNs < 0 || event.clockEpoch !== clock.epoch || !interval.every(finite) || interval[0] < clock.validIntervalMs[0] || interval[1] > clock.validIntervalMs[1]) reasons.push('EVENT_CLOCK_UNPROVEN');
  }
  let frameOffset = -1;
  if (!reasons.length) {
    diagnosis.captures.forEach((capture, offset) => { if (capture.interval[1] < interval[0] && interval[0] - capture.interval[1] >= policy.minSeparationMs) frameOffset = offset; });
    if (frameOffset < 0 || interval[0] - diagnosis.captures[frameOffset].interval[1] > policy.maxGapMs) reasons.push('CAUSAL_PRE_FRAME_UNAVAILABLE');
  }
  let imagePoint;
  if (!reasons.length) {
    const geometry = diagnosis.geometry;
    const bounds = geometry.pointBounds;
    const rect = geometry.contentRect;
    imagePoint = { x: event.x * geometry.scaleX + geometry.offsetX, y: event.y * geometry.scaleY + geometry.offsetY };
    const uncertainty = geometry.uncertaintyPx;
    if (!finite(event.x) || !finite(event.y) || event.x < bounds.x || event.y < bounds.y || event.x >= bounds.x + bounds.width || event.y >= bounds.y + bounds.height || imagePoint.x - uncertainty < rect.x || imagePoint.y - uncertainty < rect.y || imagePoint.x + uncertainty >= rect.x + rect.width || imagePoint.y + uncertainty >= rect.y + rect.height) reasons.push('POINT_OUTSIDE_CONTENT');
  }
  return { reasons: [...new Set(reasons)].sort(), interval, frameOffset, imagePoint };
}

function compileSegment(args) {
  const context = prepare(args);
  const policy = readPolicy(args.policy, context.check);
  const diagnosis = diagnose(context, policy);
  const sealed = membership(context, args.splitSeal);
  const records = [];
  const rejects = [];
  const counts = {};
  const eventIds = new Set();
  let previousEventTime = -Infinity;
  for (const event of context.events) {
    context.check();
    if (identifier(event.eventId) && eventIds.has(event.eventId)) throw Error('duplicate event identity');
    eventIds.add(event.eventId);
    if (context.segment.kind === 'synthetic' && Number.isSafeInteger(event.eventTimestampNs)) {
      if (event.eventTimestampNs <= previousEventTime) throw Error('event timestamp order');
      previousEventTime = event.eventTimestampNs;
    }
    const candidate = eventCandidate(context, diagnosis, policy, event);
    if (candidate.reasons.length) {
      if (rejects.length >= context.caps.maxRejects) throw Error('rejection limit');
      rejects.push({ eventId: identifier(event.eventId) ? event.eventId : null, reasons: candidate.reasons });
      for (const reason of candidate.reasons) counts[reason] = (counts[reason] || 0) + 1;
      continue;
    }
    if (records.length >= context.caps.maxRecords) throw Error('record limit');
    const offset = candidate.frameOffset;
    const index = context.decoder.index[offset];
    const decoded = context.decoder.readFrame(index.encodedOrdinal);
    context.check();
    if (!decoded || decoded.encodedOrdinal !== index.encodedOrdinal || !rational(decoded.encodedPts) || comparePts(decoded.encodedPts, index.encodedPts) !== 0n || decoded.width !== index.width || decoded.height !== index.height || decoded.pixelFormat !== 'RGBA' || !(decoded.pixels instanceof Uint8Array) || decoded.pixels.buffer instanceof SharedArrayBuffer || decoded.pixels.byteLength !== index.width * index.height * 4) throw Error('decoded frame mismatch');
    const pre = { sourceFrameId: context.frames[offset].frameId, submissionOrdinal: diagnosis.mappings[offset].submissionOrdinal, encodedOrdinal: index.encodedOrdinal, encodedPts: index.encodedPts, captureIntervalMs: diagnosis.captures[offset].interval, generation: event.generation, imageSha256: hash(decoded.pixels), width: index.width, height: index.height };
    const postOffset = diagnosis.captures.findIndex(capture => capture.interval[0] > candidate.interval[1]);
    const postRefs = postOffset < 0 ? [] : [{ sourceFrameId: context.frames[postOffset].frameId, encodedOrdinal: context.decoder.index[postOffset].encodedOrdinal, auditOnly: true }];
    const record = { schema: 'synthetic-screen-action-candidate/v1', synthetic: true, trainingEligible: false, eligibility: 'candidate_only', sessionId: context.segment.sessionId, segmentId: context.segment.segmentId, split: sealed.assignment.split, pre, action: { eventId: event.eventId, kind: event.kind, button: event.button, timeIntervalMs: candidate.interval, origin: 'physical_unverified', globalPoint: { x: event.x, y: event.y }, imagePoint: candidate.imagePoint }, postRefs };
    records.push({ ...record, recordSha256: hash(canonical(record)) });
  }
  const manifest = { schema: 'screen-candidate-manifest/v1', trainingEligible: false, compiler: COMPILER, inputs: context.inputs, sourceSha256: context.sourceSha256, splitSealSha256: sealed.sha256, policy, policySha256: hash(canonical(policy)), decoder: context.decoder?.implementation || null, preprocessing: { pixelFormat: 'RGBA', crop: 'none', input: 'exact-pre-frame-digest-only' }, mappingProofId: identifier(context.proof?.pipeline?.id) ? context.proof.pipeline.id : null, clockProofId: identifier(context.proof?.clock?.id) ? context.proof.clock.id : null, transformProofId: identifier(context.proof?.geometry?.id) ? context.proof.geometry.id : null, inspection: report(context, diagnosis), coverage: { events: context.events.length, records: records.length, rejected: rejects.length, byReason: counts }, recordSha256s: records.map(record => record.recordSha256) };
  manifest.preprocessingSha256 = hash(canonical(manifest.preprocessing));
  context.check();
  return frozen({ trainingEligible: false, records, rejects, manifest });
}

module.exports = { inspectSegment, compileSegment };
