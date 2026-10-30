'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { detectGap } = require('../src/curiosity-gaps');
// Hand-labelled before scoring: true means an unanswered public-information
// question worth researching, false means conversation, action or answered.
const fixtures = [
  ['What year did the Berlin Wall fall?', "I don't know.", [], true],
  ['Who discovered the neutron?', "I'm not sure.", [], true],
  ['How does a lithium ion battery work?', "I cannot answer that yet.", [], true],
  ['Why do leaves change color in autumn?', "I couldn't find an explanation.", [], true],
  ['Which country launched Sputnik?', "I don't know.", [], true],
  ['When was the first iPhone released?', "I was unable to find the date.", [], true],
  ['What is the capital of Bhutan?', "I'm not sure.", [], true],
  ['Who wrote The Left Hand of Darkness?', "I cannot determine that.", [], true],
  ['How many moons does Mars have?', "I can't tell from the sources.", [], true],
  ['Where was Marie Curie born?', "I couldn't identify the city.", [], true],
  ['Why is the sky blue?', "I don't know.", [], true],
  ['What causes ocean tides?', "I reached the step limit.", [], true],
  ['When did the Apollo 11 mission land?', 'I found an answer.', ['Not done yet: the date was not checked'], true],
  ['Which planet has the shortest year?', 'Here is my answer.', ['Not done: the answer is incomplete'], true],
  ['How does a vaccine train immunity?', "Unable to find a reliable explanation.", [], true],
  ['Who invented the World Wide Web?', "I wasn't able to verify that.", [], true],
  ['No thanks', "I don't know.", [], false],
  ['Can you open my email?', "I couldn't find your inbox.", [], false],
  ['What is two plus two?', 'Four.', [], false],
  ['Please stop', 'I reached the step limit.', [], false],
];
test('20 hand-labelled turns: measure gap precision and recall', () => {
  const flagged = fixtures.map(([q, a, c, truth]) => ({ truth, found: !!detectGap(q, a, c) }));
  const tp = flagged.filter(x => x.truth && x.found).length;
  const fp = flagged.filter(x => !x.truth && x.found).length;
  const fn = flagged.filter(x => x.truth && !x.found).length;
  console.log(`gap fixture: ${tp} true positives, ${fp} false positives, ${fn} missed; precision ${tp}/${tp + fp}, recall ${tp}/${tp + fn}`);
  assert.equal(tp, 16);
  assert.equal(fp, 0);
  assert.equal(fn, 0);
  // Only 16 were flagged: this fixture cannot establish the requested
  // precision over 20 flagged items, even though its observed precision is 100%.
});

test('a chat stores a gap on its thread and excludes hidden and helper turns', async () => {
  const { Agent } = require('../src/agent');
  const { startGateway } = require('./helpers');
  const gw = await startGateway([{ content: "I don't know." }, { content: "I don't know." }, { content: "I don't know." }]);
  try {
    const a = new Agent({ getSettings: () => ({ gatewayUrl: gw.url, model: 'm', verify: false, thinkActing: false }), toolDefs: [], tools: {}, emit: () => {} });
    const thread = { id: 't', messages: [], items: [] };
    await a.run(thread, 'What is the capital of Bhutan?');
    assert.equal(thread.curiosityGaps.length, 1);
    assert.equal(thread.curiosityGaps[0].question, 'What is the capital of Bhutan?');
    await a.run(thread, 'Who discovered the neutron?', { hidden: true });
    assert.equal(thread.curiosityGaps.length, 1);
    const helper = { id: 'h', helper: 'helper', messages: [], items: [] };
    await a.run(helper, 'Who discovered the neutron?');
    assert.equal(helper.curiosityGaps, undefined);
  } finally { gw.close(); }
});
