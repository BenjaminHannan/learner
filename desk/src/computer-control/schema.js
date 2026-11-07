'use strict';
const fn = (name, description, properties, required = []) => ({ type:'function', function:{ name, description, parameters:{ type:'object', properties, required } } });
const string = description => ({ type:'string', description });
const defs = [
  fn('computer_look', 'Look at a real Mac display. The screenshot is sent to your eyes. No mouse or key is sent.', { displayId:string('Optional display identifier') }),
  fn('computer_prepare', 'Give one step intent and action based on the latest screen. Returns a fresh picture to check before acting.', {
    observationId:string('Most recent observation id'), intent:string('What this one step should do'),
    action:{ type:'object', description:'One action: click, drag, scroll, type, press, or open. Coordinates default to pixels in the latest screenshot.', properties:{
      type:{type:'string',enum:['click','drag','scroll','type','press','open']}, coordinateSpace:{type:'string',enum:['image','desktop']}, x:{type:'number'}, y:{type:'number'}, toX:{type:'number'}, toY:{type:'number'}, button:{type:'string',enum:['left','right','middle']}, count:{type:'integer'}, dy:{type:'integer'}, text:{type:'string'}, combo:{type:'string'}, name:{type:'string'} }, required:['type'] }
  }, ['observationId','intent','action']),
  fn('computer_execute', 'After checking the fresh picture, confirm one prepared step. Returns the after picture.', { preparedId:string('Prepared step id'), confirmed:{type:'boolean',description:'True only when the fresh picture confirms the action is correct'}, actor:{type:'string',enum:['glim','hands'],description:'Which proposed action to use; hands only if a proposal was shown'} }, ['preparedId','confirmed','actor']),
  fn('computer_verify', 'Check the after picture and record what visibly happened before the next step.', { observationId:string('After-observation id'), result:{type:'string',enum:['pass','fail','unknown']}, evidence:string('What the picture actually shows') }, ['observationId','result','evidence']),
  fn('computer_finish', 'Finish the desktop task after its last step was checked.', { result:{type:'string',enum:['pass','fail','unknown']}, evidence:string('What was checked') }, ['result','evidence'])
];
const names = new Set(defs.map(d => d.function.name));
const legacy = new Set(['screen_look','screen_click','screen_type','screen_key','open_app']);
// A request for instructions is not permission to demonstrate them on the Mac.
const guidanceOnly = text => {
  const s = String(text || '').trim();
  if (/^(?:(?:please|can|could|would|will)\s+(?:you\s+)?)*(?:open|launch|start|click|tap|drag|scroll|type|press|write|create|make|select|change|set|switch|turn|move|close|save|fill|enter|navigate|go)\b/i.test(s)) return false;
  return /\b(?:how\s+(?:to|do|can|would|should)|instructions\s+(?:on|for)|steps\s+(?:to|for))\b/i.test(s) || /^(?:(?:please|can|could|would|will)\s+(?:you\s+)?)*(?:explain|describe|tell|teach|walk me through)\b/i.test(s);
};
const desktopRequest = text => !guidanceOnly(text) && (/\b(?:desktop|screen|mouse|keyboard|click|drag|scroll|type|press|finder|downloads|textedit|notes|safari|calculator|calendar|preview|photos|music|terminal|system settings|appearance|dark mode|light mode|open (?:the )?(?:app|application)|(?:app|application|folder|file))\b/i.test(String(text || '')) || /\b(?:open|launch)\s+(?:the\s+)?[A-Z][\w-]*/.test(String(text || '')));
const actionRequested = text => {
  const s = String(text || '').trim();
  if (guidanceOnly(s)) return false;
  if (/^(?:what|why|when|where|how|which|who)\b/i.test(s)) return false;
  return /\b(?:open|launch|start|click|tap|drag|scroll|type|press|write|create|make|select|change|set|switch|turn|move|close|save|fill|enter|navigate|go)\b/i.test(s);
};
const instruction = 'For this explicit desktop task, use only computer_look, computer_prepare, computer_execute, computer_verify and computer_finish for the Mac. Observe, prepare one action, confirm its new screenshot, execute, then verify the after screenshot. If the screen or watcher is unavailable, stop. Never claim success without visible evidence. Coordinates default to pixels in the picture. Never send messages, buy, delete, or post unless Ben explicitly requested it.';
module.exports = { defs, names, legacy, desktopRequest, actionRequested, instruction };
