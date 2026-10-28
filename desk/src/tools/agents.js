'use strict';
// agent_start / agent_list / agent_update (also stops) / agent_stop. Glims get the same tool list as the main Glim (shared prompt cache).
// A Glim can do almost everything the main Glim can (Ben, Oct 28: "make the glims able to do as much as possible"):
// list Glims, edit or move its own schedule, stop itself or the Glims it started, never Ben's other Glims, and start new ones,
// up to MAX_DEPTH Glims deep and MAX_KIDS live children each (a runaway guard, not a policy).
const { fmtWhen, short } = require('../helpers');

const NO = "Error: Motes can't start Motes"; // a Glim run with no known id (should not happen)
const MAX_DEPTH = 2;
const MAX_KIDS = 5;

// what the model reads as a Glim's state: a running one says so, an idle one with no next time says it will not run
function liveStatus(h) { return h.status === 'idle' && !h.next && !h.paused ? 'idle, not scheduled' : h.status; }

function agentTools(mgr, opts) {
  const isHelper = !!(opts && opts.isHelper);
  const selfId = opts && opts.selfId;
  const err = (e) => ({ text: 'Error: ' + (e && e.message || e), error: true });
  const self = () => (selfId && mgr.items ? mgr.items.find((h) => h.id === selfId) : null);
  const started = (h, how) => "Started Mote '" + h.name + "' (id " + h.id + '): ' + how + '. Its report will arrive as a [helper updates] note.';
  // a Glim may change or stop itself or the Glims it started, never Ben's other Glims
  const notYours = (ref) => {
    if (!isHelper) return null;
    const t = mgr.find(ref);
    return t && t.id !== selfId && t.byHelper !== selfId ? { text: "Error: '" + t.name + "' is not yours to change; only Ben or the main Glim can", error: true } : null;
  };
  const stopTool = (a) => {
    const no = notYours(a.name_or_id); if (no) return no;
    const h = mgr.stop(a.name_or_id);
    return h ? { text: "Stopped Mote '" + h.name + "' and removed its schedule.", summary: 'Stopped Mote ' + h.name } : { text: "Error: no Mote '" + a.name_or_id + "'", error: true };
  };
  return {
    agent_start: (a, ctx) => {
      try {
        if (isHelper) {
          const me = self();
          const same = me && mgr.find(a.name);
          if (me && same && same.id === me.id) { // "change my time": move this Mote's own schedule
            if (!a.every && !a.at) return { text: 'Error: give at ("07:00") or every ("2h") to change your schedule', error: true };
            const v = mgr.reschedule(me.id, { every: a.every, at: a.at });
            return { text: "Your schedule is now '" + v.schedule + "', next run " + fmtWhen(v.next) + '. Finish this run as usual.', summary: 'Moved to ' + v.schedule };
          }
          if (!me) return { text: NO, error: true };
          if (mgr.depth(me.id) + 1 > MAX_DEPTH) return { text: 'Error: this Mote was started by another Mote, so it cannot start more. Do the work yourself.', error: true };
          const kids = mgr.items.filter((h) => h.byHelper === me.id && h.status !== 'stopped' && (mgr.isRunning(h.id) || h.every || h.at)).length; // a finished one-time child no longer counts
          if (kids >= MAX_KIDS) return { text: 'Error: you already run ' + kids + ' Motes; stop one first (agent_update with stop) or do the work yourself.', error: true };
        }
        const h = mgr.add({ name: a.name, task: a.task, every: a.every, at: a.at, parent: ctx && ctx.thread && ctx.thread.id, byHelper: isHelper ? selfId : undefined });
        const when = h.schedule === 'once' ? 'running now (one time)' : h.schedule.startsWith('daily') ? h.schedule + ', next run ' + fmtWhen(h.next) : 'running now, then ' + h.schedule + ', next run ' + fmtWhen(h.next);
        return { text: started(h, when), summary: 'Started Mote ' + h.name };
      } catch (e) { return err(e); }
    },
    agent_list: () => {
      const l = mgr.list();
      if (!l.length) return 'No Motes.';
      return l.map((h) => h.id + ' ' + h.name + (h.id === selfId ? ' (you)' : '') + ' | ' + liveStatus(h) + (h.paused ? ' (paused)' : '') + ' | ' + h.schedule + ' | next ' + (h.next ? fmtWhen(h.next) : 'none') + ' | last: ' + (short(h.lastSummary, 120) || 'none yet')).join('\n');
    },
    // edit in place: schedule (at / every, "" clears one), task, new_name, paused; stop: true cancels it
    agent_update: (a) => {
      try {
        const no = notYours(a.name_or_id); if (no) return no;
        if (a.stop) return stopTool(a);
        const patch = {};
        for (const k of ['task', 'every', 'at']) if (a[k] !== undefined && a[k] !== null) patch[k] = a[k];
        if (a.new_name !== undefined && a.new_name !== null) patch.name = a.new_name;
        const h = mgr.update(a.name_or_id, patch);
        if (!h) return { text: "Error: no Mote '" + a.name_or_id + "'", error: true };
        if (a.paused !== undefined) mgr.pause(h.id, !!a.paused);
        // run: true starts it now (Ben Oct 28: Glim set "once" with no time, then a time already past, and said they would run)
        let ran = '';
        if (a.run) {
          const kids = isHelper ? mgr.items.filter((k) => k.byHelper === selfId && k.id !== h.id && mgr.isRunning(k.id)).length : 0;
          ran = mgr.isRunning(h.id) ? 'it was already running'
            : mgr.o && mgr.o.hold && mgr.o.hold() ? 'not started: Glim is asleep, so it runs after wake if it is due'
            : kids >= MAX_KIDS ? 'not started: you already run ' + kids + ' Motes'
            : mgr.runNow(h.id) ? 'started now' + (mgr.find(h.id).paused ? ' (its schedule stays paused)' : '') : 'could not start it';
        }
        const v = mgr.find(h.id) ? mgr.view(mgr.find(h.id)) : h;
        const when = v.next ? ', next run ' + fmtWhen(v.next) : mgr.isRunning(v.id) ? '' : (v.paused ? '' : '. Not scheduled: it will not run unless you set at/every or run it now (run: true)');
        return { text: "Updated Mote '" + v.name + "': " + v.schedule + (v.paused ? ' (paused)' : '') + when + (ran ? '; ' + ran : '') + '; status ' + liveStatus(v), summary: (ran.startsWith('started now') ? 'Started Mote ' : 'Updated Mote ') + v.name };
      } catch (e) { return err(e); }
    },
    agent_stop: stopTool // still callable by name (older chats); the tool list offers it through agent_update
  };
}

module.exports = { agentTools, NO, MAX_DEPTH, MAX_KIDS };
