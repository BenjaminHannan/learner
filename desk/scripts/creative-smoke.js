'use strict';
// Opt-in local-only cold/hot probe. Does not start a model or app, alter settings,
// or save chat. Each call has the same diary exclusions as the private scratchpad.
// node desk/scripts/creative-smoke.js --gateway http://127.0.0.1:18087/v1 --model lfm3
const { propose } = require('../src/creative');
const { streamChat } = require('../src/llm');

async function main(args) {
  const option = (name, fallback) => { const i = args.indexOf(name); return i < 0 ? fallback : args[i + 1]; };
  const gatewayUrl = option('--gateway', '');
  if (!gatewayUrl) throw new Error('Pass --gateway for an already running local gateway. No service will be started.');
  const url = new URL(gatewayUrl);
  if (!['http:', 'https:'].includes(url.protocol) || !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname)) throw new Error('The smoke probe accepts only an explicit loopback gateway.');
  const model = option('--model', 'lfm3');
  const family = option('--family', 'lfm3');
  const repeats = Number(option('--repeat', '2'));
  if (!Number.isInteger(repeats) || repeats < 1 || repeats > 4) throw new Error('--repeat must be an integer from 1 to 4.');
  if (!['lfm3', 'apex35b'].includes(family)) throw new Error('--family must be lfm3 or apex35b.');
  const text = option('--prompt', 'Brainstorm memorable names for a neighborhood astronomy club. Favor a calm, welcoming mood.');
  const settings = { gatewayUrl, model, modelFast: option('--fast-model', ''), backendModelFamily: family, creativeProposer: true, apiKey: process.env.PREMONITION_SMOKE_API_KEY || '' };
  const controller = new AbortController();
  const onStop = () => controller.abort();
  process.once('SIGINT', onStop);
  try {
    for (let i = 0; i < repeats && !controller.signal.aborted; i++) {
      let raw = null, requestError = null, requestModel = null;
      const start = Date.now();
      const approaches = await propose({ text, settings, signal: controller.signal, request: async (opts) => {
        requestModel = opts.model;
        try { raw = await streamChat(opts); return raw; }
        catch (e) { requestError = { name: e.name || 'Error', message: e.message, code: e.cause && e.cause.code }; throw e; }
      } });
      process.stdout.write(JSON.stringify({ run: i + 1, model, requestModel, family, elapsedMs: Date.now() - start, valid: !!approaches, approaches,
        rawContent: raw && raw.content, finishReason: raw && raw.finishReason,
        reasoningChars: raw ? raw.reasoning.length : null, firstTokenMs: raw && raw.firstTokenMs, requestError }) + '\n');
    }
  } finally { process.removeListener('SIGINT', onStop); }
}

if (require.main === module) main(process.argv.slice(2)).catch((e) => { process.stderr.write(e.message + '\n'); process.exitCode = 1; });
module.exports = { main };
