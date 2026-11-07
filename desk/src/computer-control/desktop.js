'use strict';
const { randomUUID, createHash } = require('node:crypto');
const { NativeSession } = require('./native');
const { Attempt } = require('./attempt');
const { actionPlan, execute } = require('./actions');

async function capture(native, displayId) {
  const image = await native.command('look', { displayId });
  if (typeof image.png !== 'string' || !image.png || typeof image.fingerprint !== 'string' || !image.bounds || !image.size || typeof image.frontApp !== 'string' || !image.frontApp.trim()) throw Error('screen image or front app unavailable');
  const bytes = Buffer.from(image.png, 'base64');
  return { id:randomUUID(), at:new Date().toISOString(), hash:createHash('sha256').update(bytes).digest('hex'), image:'data:image/png;base64,' + image.png, fingerprint:image.fingerprint, displayId:image.displayId, bounds:image.bounds, size:image.size, cursor:image.cursor, displays:image.displays, frontApp:image.frontApp };
}
const ref = shot => ({ id:shot.id, at:shot.at, sha256:shot.hash, displayId:shot.displayId, bounds:shot.bounds, size:shot.size });
const result = (shot, text) => ({ text, image:shot.image });
function desktopAction(input, shot) {
  if (!input || typeof input !== 'object') throw Error('action required');
  const action = { ...input }, space = action.coordinateSpace || 'image';
  delete action.coordinateSpace;
  if (!['image','desktop'].includes(space)) throw Error('unknown coordinate space');
  if (space === 'image' && ['click','drag'].includes(action.type)) {
    const pairs = action.type === 'drag' ? [['x','y'],['toX','toY']] : [['x','y']];
    for (const [x,y] of pairs) {
      if (!Number.isFinite(action[x]) || !Number.isFinite(action[y]) || action[x] < 0 || action[x] >= shot.size.width || action[y] < 0 || action[y] >= shot.size.height) throw Error('point is outside the screenshot');
      action[x] = shot.bounds.x + action[x] * shot.bounds.width / shot.size.width;
      action[y] = shot.bounds.y + action[y] * shot.bounds.height / shot.size.height;
    }
  }
  return action;
}
function stableScreen(before, after, action) {
  if (JSON.stringify(before.bounds) !== JSON.stringify(after.bounds) || before.frontApp !== after.frontApp) return false;
  const a = Buffer.from(before.fingerprint || '', 'base64'), b = Buffer.from(after.fingerprint || '', 'base64');
  if (a.length !== 64000 || b.length !== a.length) return false;
  let changed = 0;
  const points = [[action.x,action.y], ...(action.type === 'drag' ? [[action.toX,action.toY]] : [])].map(([x,y]) => ({
    x:Math.floor((x-before.bounds.x)/before.bounds.width*160), y:Math.floor((y-before.bounds.y)/before.bounds.height*100), changed:0, total:0
  })).filter(p => Number.isFinite(p.x) && Number.isFinite(p.y));
  for (let i = 0; i < 16000; i++) {
    const o = i*4, different = Math.abs(a[o]-b[o]) + Math.abs(a[o+1]-b[o+1]) + Math.abs(a[o+2]-b[o+2]) > 60;
    if (different) changed++;
    const x = i % 160, y = Math.floor(i / 160);
    for (const p of points) if (Math.abs(x-p.x) <= 4 && Math.abs(y-p.y) <= 4) { p.total++; if (different) p.changed++; }
  }
  return changed / 16000 < 0.01 && points.every(p => !p.total || p.changed / p.total < 0.1);
}

class Desktop {
  constructor({ request, signal, captureScreen, startNative = NativeSession.start, predictor, logRoot, minIdleSeconds = 120, idleSeconds, deferFinish = false, onTakeover } = {}) {
    this.signal = signal; this.captureScreen = captureScreen; this.startNative = startNative; this.predictor = predictor === undefined ? require('./predictor').propose : predictor;
    this.deferFinish = deferFinish;
    this.onTakeover = onTakeover;
    this.minIdleSeconds = minIdleSeconds; this.idleSeconds = idleSeconds; this.idleChecked = false;
    this.attempt = new Attempt(request, logRoot); this.pending = null; this.awaiting = null; this.stopped = false;
  }
  async init() {
    if (this.stopped || this.signal?.aborted) throw Error('task stopped');
    if (!this.native) {
      this.native = await this.startNative();
      this.native.onRevoke = row => { if (row.terminal && this.onTakeover) this.onTakeover(row); };
      this.onAbort = () => this.native.stop('task stopped');
      if (this.signal) { this.signal.addEventListener('abort', this.onAbort, { once:true }); if (this.signal.aborted) this.onAbort(); }
    }
    if (this.native.cancelled) throw Error(this.native.stopReason || 'Ben took control');
  }
  async look(args = {}) {
    await this.init();
    if (this.awaiting) throw Error('Verify the last result first');
    this.pending = null; // looking again abandons a proposed, unsent action
    if (!this.idleChecked) {
      const deadline = Date.now() + 10 * 60000;
      while ((this.idleSeconds ? await this.idleSeconds() : (await this.native.command('idle')).seconds) < this.minIdleSeconds) {
        if (this.signal?.aborted || this.native.cancelled) throw Error('Ben took control');
        if (Date.now() >= deadline) throw Error('Ben is using the computer');
        await new Promise(resolve => setTimeout(resolve, 250));
      }
      if (this.native.cancelled || this.signal?.aborted) throw Error('Ben took control');
      this.idleChecked = true;
    }
    const shot = this.captureScreen ? await this.captureScreen(args.displayId) : await capture(this.native, args.displayId); this.lastShot = shot;
    return result(shot, `Observation ${shot.id}; front app ${shot.frontApp || 'unknown'}; display ${shot.displayId}; screenshot ${shot.size.width}×${shot.size.height} pixels maps to desktop rectangle ${JSON.stringify(shot.bounds)}. Displays: ${JSON.stringify(shot.displays || [{ id:shot.displayId, bounds:shot.bounds }])}. SHA-256 ${shot.hash}. Use pixel coordinates from this picture, then prepare the action.`);
  }
  async prepare(args) {
    await this.init();
    if (this.awaiting) throw Error('Verify the last result first');
    if (this.pending) throw Error('Execute the prepared step or look again');
    if (!this.lastShot || args.observationId !== this.lastShot.id) throw Error('Look at the screen first');
    if (typeof args.intent !== 'string' || !args.intent.trim()) throw Error('step intent required');
    const fresh = this.captureScreen ? await this.captureScreen(this.lastShot.displayId) : await capture(this.native, this.lastShot.displayId);
    if (JSON.stringify(fresh.bounds) !== JSON.stringify(this.lastShot.bounds) || JSON.stringify(fresh.size) !== JSON.stringify(this.lastShot.size)) throw Error('Display geometry changed; look again');
    const action = desktopAction(args.action, this.lastShot); actionPlan(action); let proposal = null;
    if (this.predictor && ['click','drag'].includes(action.type)) {
      try {
        proposal = await this.predictor({ shot:fresh, intent:args.intent, action });
        if (proposal?.action) {
          actionPlan(proposal.action);
          const original = { ...action }, proposed = { ...proposal.action };
          delete original.x; delete original.y; delete proposed.x; delete proposed.y;
          if (JSON.stringify(original) !== JSON.stringify(proposed)) proposal = null;
        } else proposal = null;
      } catch (_) { proposal = null; }
    }
    this.attempt.prepare({ at:new Date().toISOString(), intent:args.intent, observation:ref(fresh), proposedAction:action, proposal:proposal || { status:'unavailable', reason:'no approved desktop pixel policy' } });
    this.pending = { id:randomUUID(), intent:args.intent, action, proposal, actor:'glim', shot:fresh, at:Date.now() };
    const suggestion = proposal ? `The small network suggests ${JSON.stringify(proposal.action)}. ${proposal.note} You may choose actor=hands only for that proposal.` : 'The small network is unavailable; this does not block your own action. Use actor=glim.';
    return result(fresh, `Prepared ${this.pending.id}. Glim chose ${JSON.stringify(action)}. ${suggestion} Check this fresh picture. If correct, call computer_execute with this preparedId, confirmed=true, and actor=glim. Otherwise look again.`);
  }
  async execute(args) {
    await this.init();
    const p = this.pending;
    if (!p || args.preparedId !== p.id || args.confirmed !== true || Date.now() - p.at > 10 * 60000) throw Error('A fresh, explicitly confirmed prepared step is required');
    this.pending = null;
    try {
      if (args.actor === 'hands') {
        if (!p.proposal?.action) throw Error('No hands proposal is available');
        p.action = p.proposal.action; p.actor = 'hands';
      } else if (args.actor && args.actor !== 'glim') throw Error('Unknown actor');
      const current = this.captureScreen ? await this.captureScreen(p.shot.displayId) : await capture(this.native, p.shot.displayId);
      if (!stableScreen(p.shot, current, p.action)) throw Error('The screen changed after the check; look again');
      p.step = this.attempt.step({ at:new Date().toISOString(), intent:p.intent, observation:ref(p.shot), action:p.action, actor:p.actor, status:'dispatching' });
      await execute(this.native, p.action, this.signal);
      if (this.native.cancelled || this.signal?.aborted) throw Error('Ben took control');
      this.attempt.update(p.step, { status:'sent' });
      await new Promise(resolve => setTimeout(resolve, 300));
      if (this.native.cancelled || this.signal?.aborted) throw Error('Ben took control');
      const after = this.captureScreen ? await this.captureScreen(p.shot.displayId) : await capture(this.native, p.shot.displayId);
      this.attempt.update(p.step, { after:ref(after), status:'awaiting-verification' });
      this.awaiting = { step:p.step, shot:after };
      return result(after, `Action sent. After-observation ${after.id}, SHA-256 ${after.hash}. Check this picture and call computer_verify before the next step.`);
    } catch (error) {
      if (p.step != null) this.attempt.update(p.step, { status:'failed', error:String(error.message || error) });
      throw error;
    }
  }
  verify(args) {
    if (!this.awaiting || args.observationId !== this.awaiting.shot.id || !['pass','fail','unknown'].includes(args.result) || typeof args.evidence !== 'string' || !args.evidence.trim()) throw Error('A result and evidence for the after-picture are required');
    this.attempt.update(this.awaiting.step, { status:'checked', verification:{ source:'glim', result:args.result, evidence:args.evidence, observationId:args.observationId } });
    this.lastShot = this.awaiting.shot; this.awaiting = null;
    return { text:'The visible result was recorded. Look or prepare the next step; finish only when the task is checked.' };
  }
  finish(args = {}) {
    if (this.awaiting) throw Error('Verify the last result first');
    if (this.pending) throw Error('Execute the prepared step or look again');
    if (!['pass','fail','unknown'].includes(args.result) || typeof args.evidence !== 'string' || !args.evidence.trim()) throw Error('Result and evidence are required');
    if (args.result === 'pass' && (!this.attempt.row.steps.length || this.attempt.row.steps.at(-1).verification?.result !== 'pass')) throw Error('The final visible result has not passed verification');
    this.finished = true; this.claimed = args.result; this.evidence = args.evidence;
    return { text:'The desktop attempt is complete. Report only what the checked screen showed.' };
  }
  async close() {
    if (this.stopped) return; this.stopped = true;
    if (this.signal && this.onAbort) this.signal.removeEventListener('abort', this.onAbort);
    if (this.native) await this.native.close();
    const failed = this.claimed === 'fail' || (!this.finished && this.attempt.row.steps.some(s => s.status === 'failed' || s.verification?.result === 'fail'));
    const last = this.attempt.row.steps.at(-1);
    const evidence = this.finished ? { source:'glim', result:this.claimed || 'unknown', text:this.evidence || '', observationId:last?.after?.id || null, screenshotSha256:last?.after?.sha256 || null, note:'Model observation awaits independent check.' } : 'interrupted or not independently checked';
    if (this.deferFinish) { this.attempt.row.provisionalOutcome = { result:failed ? 'fail' : 'unknown', evidence }; this.attempt.save(); }
    else this.attempt.finish(failed ? 'fail' : 'unknown', evidence);
  }
}
module.exports = { Desktop, capture, ref, desktopAction, stableScreen };
