'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

class Element {
  constructor(tag) {
    this.tagName = tag.toUpperCase(); this.children = []; this.dataset = {}; this.style = {}; this.hidden = false;
    this.classList = { add() {}, toggle() {}, contains() { return false; } };
  }
  append(...nodes) { this.children.push(...nodes); }
  set textContent(value) { this._text = value; this.children = []; }
  get textContent() { return this._text || ''; }
  get firstChild() { return this.children[0]; }
  setAttribute() {}
  addEventListener() {}
  focus() {}
  querySelector() { return null; }
  closest() { return null; }
}

const flush = () => new Promise(resolve => setImmediate(resolve));
function deferred() {
  let resolve, reject;
  const promise = new Promise((a, b) => { resolve = a; reject = b; });
  return { promise, resolve, reject };
}
function find(element, id) {
  if (element.id === id) return element;
  for (const child of element.children) {
    const found = find(child, id);
    if (found) return found;
  }
  return null;
}

test('setup serializes navigation while saving and unlocks after failure', async () => {
  const root = new Element('div'); root.hidden = true;
  const listeners = {}; let gate = null; const writes = [];
  const desk = {
    info: async () => ({ platform: 'test' }),
    settings: {
      get: async () => ({ uses: [], usesOther: '' }),
      set: patch => { writes.push(patch); return gate ? gate.promise : Promise.resolve(); }
    },
    helpers: { list: async () => [] }, onboard: { create: async () => [] }
  };
  const document = {
    getElementById: () => root, createElement: tag => new Element(tag),
    addEventListener: (name, fn) => { listeners[name] = fn; }
  };
  const window = { desk, dispatchEvent() {} };
  const context = {
    window, document, Platform: { needsPermsStep: () => false },
    Uses: { USES: [], IDS: [], cleanUses: () => [], templateFor: () => null },
    Mascot: { el: () => new Element('div') }, CustomEvent: class {}, setTimeout: () => 0
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../renderer/onboard.js'), 'utf8'), context);
  await window.Onboard.show();
  await find(root, 'obNext').onclick();
  assert.equal(window.Onboard._state().step, 1);

  gate = deferred();
  const first = find(root, 'obNext').onclick();
  const second = find(root, 'obNext').onclick();
  find(root, 'obBack').onclick();
  find(root, 'obSkip').onclick();
  listeners.keydown({ key: 'Escape', preventDefault() {}, stopImmediatePropagation() {} });
  assert.equal(window.Onboard._state().step, 1);
  assert.equal(root.hidden, false);
  assert.equal(writes.length, 1);
  assert.equal(find(root, 'obNext').disabled, true);
  gate.resolve();
  await Promise.all([first, second]);
  await flush();
  assert.equal(window.Onboard._state().step, 4);
  assert.equal(writes.length, 1); // The mode page has not been implicitly saved/skipped.
  assert.equal(find(root, 'obNext').disabled, false);

  gate = deferred();
  const pending = find(root, 'obNext').onclick();
  gate.reject(new Error('save failed'));
  await assert.rejects(pending, /save failed/);
  assert.equal(window.Onboard._state().step, 4);
  assert.equal(find(root, 'obNext').disabled, false);
  gate = null;
  await find(root, 'obNext').onclick();
  assert.equal(window.Onboard._state().step, 5);
});

for (const choice of [true, false]) test('Mac recording needs an explicit ' + (choice ? 'Yes' : 'No'), async () => {
  const root = new Element('div'); root.hidden = true;
  const listeners = {}, choices = [];
  let savedChoice = null, fail = true;
  const desk = {
    info: async () => ({ platform: 'darwin' }),
    settings: { get: async () => ({ uses: [], onboardAt: 'perms' }), set: async () => {} },
    helpers: { list: async () => [] },
    recorder: {
      status: async () => ({ choice: savedChoice, enabled: false, available: false, guidance: ['No sound is recorded.'] }),
      choose: async value => {
        choices.push(value);
        if (fail) throw Error('disk unavailable');
        savedChoice = value;
        return { choice: value, enabled: false };
      }
    }
  };
  const window = { desk, dispatchEvent() {} };
  const document = { getElementById: () => root, createElement: tag => new Element(tag), addEventListener: (name, fn) => { listeners[name] = fn; } };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../renderer/onboard.js'), 'utf8'), {
    window, document, Platform: { needsPermsStep: () => false },
    Uses: { USES: [], cleanUses: () => [] }, Mascot: { el: () => new Element('div') }, setTimeout: () => 0
  });
  await window.Onboard.show();
  assert.equal(window.Onboard._state().step, 6);
  assert.equal(find(root, 'obNext').hidden, true);
  assert.equal(find(root, 'obSkip').hidden, true);
  for (const key of ['Enter', 'Escape']) listeners.keydown({ key, preventDefault() {}, stopImmediatePropagation() {} });
  await flush();
  assert.deepEqual(choices, []);
  assert.equal(window.Onboard._state().step, 6);
  const button = find(root, choice ? 'obRecorderYes' : 'obRecorderNo');
  await button.onclick();
  assert.equal(window.Onboard._state().step, 6);
  fail = false;
  await button.onclick();
  assert.equal(window.Onboard._state().step, 0);
  assert.equal(find(root, 'obNext').hidden, false);
  await window.Onboard.show();
  assert.equal(window.Onboard._state().step, 0);
  assert.deepEqual(choices, [choice, choice]);
});
