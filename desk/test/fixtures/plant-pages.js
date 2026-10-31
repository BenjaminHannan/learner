'use strict';
// Builds a throwaway userData folder for the "planted page" test (option B). Used by test/webtruth.test.js and
// sleepmlx/tests/test_webtruth.py. Usage: node plant-pages.js <emptyDir>
// One FALSE fact from a single site; one TRUE fact from two independent sites; Glim repeats both in chat.
const fs = require('fs'), path = require('path');
const { createMemory } = require('../../src/memory');
const { EvidenceRegistry, attachSourceRead } = require('../../src/evidence');

const FALSE_CARD = 'Luma Ferry => home dock => Mossbank';
const TRUE_CARD = 'Tidewick Light => keeper => Odile Marsh';

function plant(dir) {
  const memory = createMemory(dir);
  const read = (reg, url, body) => {
    const header = 'Page 1 of 1 (' + url + ')\n';
    const res = attachSourceRead({ text: header + body }, { url, body, bodyStart: header.length, page: 1, readAt: Date.now() });
    return reg.recordRead('browser_read', res, 'call1', 8000).readId;
  };
  const saveFrom = (fact, url, body, quote) => {
    const reg = new EvidenceRegistry({ enabled: true, threadId: 't1', helperId: 'mote' });
    const id = read(reg, url, body);
    return memory.save(fact, 'card', { research: reg.metadata({ source_read_id: id, source_quote: quote }) });
  };
  saveFrom(FALSE_CARD, 'https://only-one-site.example.net/ferries', 'Gossip page. The Luma Ferry docks at Mossbank every night.', 'The Luma Ferry docks at Mossbank every night.');
  saveFrom(TRUE_CARD, 'https://lighthouses.example.org/tidewick', 'Tidewick Light is kept by Odile Marsh since 1999.', 'Tidewick Light is kept by Odile Marsh since 1999.');
  saveFrom(TRUE_CARD, 'https://www.coastwatch.example.com/lights', 'Keeper of Tidewick Light: Odile Marsh, appointed 1999.', 'Keeper of Tidewick Light: Odile Marsh, appointed 1999.');
  // Glim repeats the false fact in chat (and the true one), as the Desk gateway logs it.
  fs.mkdirSync(path.join(dir, 'raw'), { recursive: true });
  const turn = (ts, user, answer) => JSON.stringify({ ts, model: 'k2-main', conv_id: 'c1', status: 200,
    messages: [{ role: 'system', content: 'You are the Desk.' }, { role: 'user', content: user }], response: { content: answer } });
  fs.writeFileSync(path.join(dir, 'raw', '2026-10-20.jsonl'), [
    turn(1700000000, 'Where does the Luma Ferry dock?', 'The Luma Ferry docks at Mossbank.'),
    turn(1700000001, 'Who keeps Tidewick Light?', 'Odile Marsh keeps Tidewick Light.'),
    turn(1700000002, 'Remember that I like jazz', 'Saved.')
  ].join('\n') + '\n');
  return memory;
}

module.exports = { plant, FALSE_CARD, TRUE_CARD };
if (require.main === module) plant(process.argv[2]);
