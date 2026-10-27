'use strict';
const http = require('http');

// Scripted OpenAI-compatible streaming gateway. script: array of responses or functions(req)->response.
// response: {content?, reasoning?, tool_calls?: [{name, arguments(object)}], delayMs?, hang?: true}
function startGateway(script) {
  const requests = [];
  const headers = [];   // headers of each real request (parallel to requests)
  const warms = [];     // warm-up requests (X-Premonition-Warm): {body, headers}; they never consume the script
  let i = 0;
  const server = http.createServer((req, res) => {
    let body = '';
    req.on('data', (d) => (body += d));
    req.on('end', async () => {
      if (req.url.endsWith('/models')) { res.setHeader('content-type', 'application/json'); return res.end('{"data":[]}'); }
      const parsed = JSON.parse(body || '{}');
      if (req.headers['x-premonition-warm']) { warms.push({ body: parsed, headers: req.headers }); res.setHeader('content-type', 'application/json'); return res.end(JSON.stringify({ choices: [{ message: { role: 'assistant', content: '.' }, finish_reason: 'length' }] })); }
      requests.push(parsed); headers.push(req.headers);
      let r = script[Math.min(i, script.length - 1)];
      i++;
      if (typeof r === 'function') r = r(parsed, requests.length - 1);
      if (r.holdMs) await new Promise((x) => setTimeout(x, r.holdMs)); // a slow first token (lets a test act while the model is busy)
      res.writeHead(200, { 'content-type': 'text/event-stream' });
      const send = (delta, finish) => res.write('data: ' + JSON.stringify({ choices: [{ index: 0, delta, finish_reason: finish || null }] }) + '\n\n');
      if (r.reasoning) for (const c of chunk(r.reasoning, 7)) send({ reasoning_content: c });
      if (r.content) for (const c of chunk(r.content, 5)) { send({ content: c }); if (r.delayMs) await new Promise((x) => setTimeout(x, r.delayMs)); }
      if (r.hang) { await new Promise((x) => { const t = setTimeout(x, 30000); t.unref(); res.on("close", () => { clearTimeout(t); x(); }); }); if (res.destroyed) return; }
      if (r.tool_calls) {
        r.tool_calls.forEach((tc, idx) => {
          const args = JSON.stringify(tc.arguments || {});
          send({ tool_calls: [{ index: idx, id: 'call_' + i + '_' + idx, type: 'function', function: { name: tc.name, arguments: '' } }] });
          for (const c of chunk(args, 9)) send({ tool_calls: [{ index: idx, function: { arguments: c } }] });
        });
      }
      send({}, r.tool_calls ? 'tool_calls' : 'stop');
      res.end('data: [DONE]\n\n');
    });
  });
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve({
    url: 'http://127.0.0.1:' + server.address().port + '/v1', requests, headers, warms, close: () => { server.closeAllConnections && server.closeAllConnections(); server.close(); }
  })));
}
function chunk(s, n) { const o = []; for (let k = 0; k < s.length; k += n) o.push(s.slice(k, k + n)); return o; }

module.exports = { startGateway };
