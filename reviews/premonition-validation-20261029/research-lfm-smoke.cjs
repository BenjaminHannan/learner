'use strict';
// Opt-in synthetic Agent/tool smoke against the already-running local gateway.
// It cannot browse, write production memory, or execute system tools. Test flags
// keep all requests out of the diary; a source quote is attribution, not proof.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { Agent } = require('../../desk/src/agent');
const { setTestProfile } = require('../../desk/src/llm');
const { buildTools } = require('../../desk/src/prompt');
const { attachSourceRead } = require('../../desk/src/evidence');
const { createMemory } = require('../../desk/src/memory');

if (!process.argv.includes('--allow-local-model')) {
  process.stderr.write('Use --allow-local-model after resource coordination.\n');
  process.exit(2);
}
setTestProfile(true); // This process only; never changes app settings.
const fixtures = [
  ['ferry', 'The fictional Luma Ferry uses Mossbank as its home dock.', 'Luma Ferry => home dock => Mossbank'],
  ['observatory', 'The fictional Cloudmint Observatory studies pale winter comets.', 'Cloudmint Observatory => studies => pale winter comets'],
  ['library', 'The fictional Willow Library opens its west reading room on Tuesdays.', 'Willow Library => west reading room opens => Tuesdays']
];

(async () => {
  for (const [name, body, fact] of fixtures) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'premonition-research-native-'));
    const memory = createMemory(dir), calls = [], events = [];
    const url = 'https://example.test/' + name;
    const header = 'Page 1 of 1 (' + url + ')\n';
    const agent = new Agent({
      learnResearch: true, helperId: 'synthetic-research-smoke', memory,
      getSettings: () => ({ gatewayUrl: 'http://127.0.0.1:8090/v1', model: 'lfm3-fast', modelMain: 'lfm3',
        modelFast: 'lfm3-fast', backendModelFamily: 'lfm3', thinkActing: false, mode: 'hands-off',
        verify: false, maxSteps: 5, contextTokens: 4500, compactTokens: 4500, maxToolChars: 3000 }),
      toolDefs: buildTools({}),
      tools: { browser_read: async () => {
        calls.push('browser_read');
        return attachSourceRead({ text: header + body }, { url, body, bodyStart: header.length, page: 1, readAt: Date.now() });
      } },
      emit: event => { if (event.type === 'error') events.push(event.message); }
    });
    const thread = { id: 'synthetic-research-' + name, messages: [], items: [] };
    const timer = setTimeout(() => agent.stop(), 60000);
    const start = Date.now();
    try {
      const result = await agent.run(thread, 'Synthetic reference test. First call browser_read to read the current page. Then call memory_save exactly once with fact "' + fact + '" and topic "card". Set source_read_id to the Source read ID returned by browser_read and source_quote to the exact source sentence. Keep URLs out of fact text. Do not call any other tools. Finish briefly after saving.');
      const ledger = path.join(dir, 'memory-provenance.jsonl');
      const rows = fs.existsSync(ledger) ? fs.readFileSync(ledger, 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse) : [];
      const prepared = rows.filter(row => row.type === 'research-note-prepare');
      const observed = { fixture: name, elapsedMs: Date.now() - start, result, errors: events,
        browserReads: calls.length, saved: memory.list(),
        provenance: prepared.map(row => ({ status: row.attribution.status, reason: row.attribution.reason,
          verified: row.attribution.verified, quoteMatches: row.attribution.source?.quote === body })),
        committed: rows.filter(row => row.type === 'research-note-commit').length,
        toolNames: thread.messages.filter(m => m.tool_calls).flatMap(m => m.tool_calls.map(c => c.function.name)),
        final: thread.items.filter(item => item.t === 'assistant').at(-1)?.text || '' };
      observed.structural_pass = !result.error && !result.stopped && calls.length === 1 && observed.saved.length === 1 &&
        observed.saved[0].text === fact && observed.committed === 1 && prepared.length === 1 &&
        prepared[0].attribution.status === 'attributed' && prepared[0].attribution.verified === false &&
        prepared[0].attribution.source.quote === body && observed.toolNames.join(',') === 'browser_read,memory_save';
      if (!observed.structural_pass) process.exitCode = 1;
      process.stdout.write(JSON.stringify(observed) + '\n');
    } finally { clearTimeout(timer); fs.rmSync(dir, { recursive: true, force: true }); }
  }
})().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 1; });
