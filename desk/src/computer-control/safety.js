'use strict';
const { labelCategory } = require('../safety-levels');

// An explicit task is consent to its ordinary mouse/keyboard steps. Existing
// Never settings and other sensitive categories still apply.
function checkAction(safety, safetyCtx, action, intent, request) {
  if (!safety) throw Error('Safety settings unavailable');
  if (safety.level('hands') === 'never') throw Error('Mouse and keyboard use is set to Never');
  const names = { click:'screen_click', drag:'screen_click', scroll:'screen_key', type:'screen_type', press:'screen_key', open:'open_app' };
  const name = names[action.type]; if (!name) throw Error('Unknown desktop action');
  const args = action.type === 'press' ? { keys:action.combo } : action;
  let context = {};
  try { context = safetyCtx ? safetyCtx(name, args) : {}; } catch (_) { throw Error('Safety context unavailable'); }
  const decision = safety.check(name, args, context);
  if (decision?.refuse) throw Error(decision.refuse);
  const sensitive = labelCategory(intent);
  if (sensitive && ['send','post','buy','delete','install'].includes(sensitive)) {
    const allowed = { send:/\b(send|email|message|reply|forward)\b/i, post:/\b(post|publish|share|upload|submit|comment)\b/i, buy:/\b(buy|purchase|pay|order|subscribe)\b/i, delete:/\b(delete|remove|trash|erase)\b/i, install:/\b(install)\b/i };
    if (!allowed[sensitive].test(request)) throw Error('This sensitive action was not explicitly requested');
    if (safety.level(sensitive) === 'never') throw Error('That action is set to Never');
    return { cat:sensitive, level:safety.level(sensitive) };
  }
  return decision || { cat:null, level:null };
}
function explicitlyRequested(cat, request) {
  const patterns = { system:/\b(system settings|system preferences|appearance|dark mode|light mode)\b/i,
    send:/\b(send|email|message|reply|forward)\b/i, post:/\b(post|publish|share|upload|submit|comment)\b/i,
    buy:/\b(buy|purchase|pay|order|subscribe)\b/i, delete:/\b(delete|remove|trash|erase)\b/i, install:/\binstall\b/i };
  return !!(patterns[cat] && patterns[cat].test(String(request || '')));
}
module.exports = { checkAction, explicitlyRequested };
