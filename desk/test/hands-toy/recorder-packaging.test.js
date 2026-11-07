'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const vm = require('node:vm');
const { EventEmitter } = require('node:events');
const { spawnSync } = require('node:child_process');
const root = path.resolve(__dirname, '../..');

test('Mac packaging builds and includes the recorder-owned native resources', () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'recorder-package-test-'));
  try {
    const bin = path.join(temporary, 'bin');
    const headers = path.join(temporary, 'include');
    const output = path.join(temporary, 'glim-recorder');
    const log = path.join(temporary, 'commands.jsonl');
    fs.mkdirSync(bin); fs.mkdirSync(headers);
    fs.writeFileSync(path.join(headers, 'node_api.h'), '');
    const stub = `#!${process.execPath}
const fs = require('node:fs'), path = require('node:path');
const args = process.argv.slice(2);
fs.appendFileSync(process.env.RECORDER_BUILD_LOG, JSON.stringify({tool:path.basename(process.argv[1]),args})+'\\n');
const position = args.indexOf('-o');
if (position >= 0) fs.writeFileSync(args[position+1], 'test artifact');
`;
    for (const tool of ['swiftc', 'clang++', 'codesign']) fs.writeFileSync(path.join(bin, tool), stub, { mode: 0o700 });
    const result = spawnSync('/usr/bin/python3', [path.join(root, 'tools/hands-recorder/build-native.py'), '--output', output, '--node-include', headers], {
      encoding: 'utf8', env: { ...process.env, PATH: bin + path.delimiter + process.env.PATH, RECORDER_BUILD_LOG: log }
    });
    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(fs.readdirSync(output).sort(), ['canary.dylib', 'capture.dylib', 'native-bridge.node']);
    const commands = fs.readFileSync(log, 'utf8').trim().split('\n').map(line => JSON.parse(line));
    assert.equal(commands.filter(command => command.tool === 'codesign').length, 3);
    const bridge = commands.find(command => command.tool === 'clang++');
    assert.ok(bridge.args.includes(path.join(root, 'helper/hands-toy/native-bridge.cc')));
    assert.ok(!bridge.args.some(argument => argument.includes('src/computer-control')));
    const build = fs.readFileSync(path.join(root, 'build-mac.sh'), 'utf8');
    assert.match(build, /python3 tools\/hands-recorder\/build-native\.py --output build\/glim-recorder/);
    assert.match(build, /EXTRA\+=\(--extra-resource=build\/glim-recorder\)/);
    assert.ok(build.indexOf('compiling recorder resources') < build.indexOf('==> packaging'));
  } finally { fs.rmSync(temporary, { recursive: true, force: true }); }
});

test('control CLI strips both inherited Electron overrides before LaunchServices startup', async () => {
  const launches = [];
  let connections = 0;
  const source = fs.readFileSync(path.join(root, 'tools/hands-recorder/control.js'), 'utf8');
  const env = { ELECTRON_RUN_AS_NODE: '1', ELECTRON_NO_ATTACH_CONSOLE: '1', RECORDER_TEST: 'kept' };
  await new Promise((resolve, reject) => {
    const fakeNet = { createConnection() {
      const client = new EventEmitter();
      client.setTimeout = () => {};
      client.write = () => queueMicrotask(() => {
        client.emit('data', JSON.stringify({ result: { screen: true } })); client.emit('end');
      });
      connections++;
      queueMicrotask(() => connections === 1 ? client.emit('error', Object.assign(Error('missing'), { code: 'ENOENT' })) : client.emit('connect'));
      return client;
    } };
    vm.runInNewContext(source, {
      __dirname: '/fake-recorder',
      process: { argv: ['node', 'control.js', 'preflight'], env },
      setTimeout: callback => setImmediate(callback),
      console: { log: resolve, error: reject },
      require: name => name === 'node:net' ? fakeNet
        : name === 'node:fs' ? { existsSync: () => false }
        : name === 'node:child_process' ? { execFileSync(file, args, options) { launches.push({ file, args, options }); } }
        : require(name)
    });
  });
  assert.equal(launches.length, 1);
  assert.equal(launches[0].file, '/usr/bin/open');
  assert.equal(launches[0].options.env.ELECTRON_RUN_AS_NODE, undefined);
  assert.equal(launches[0].options.env.ELECTRON_NO_ATTACH_CONSOLE, undefined);
  assert.equal(launches[0].options.env.RECORDER_TEST, 'kept');
  assert.equal(env.ELECTRON_RUN_AS_NODE, '1');
});

test('recording retention defaults match the local storage contract', () => {
  const { DEFAULTS, GiB } = require('../../src/hands-toy/retention');
  assert.equal(DEFAULTS.daily, 3 * GiB);
  assert.equal(DEFAULTS.total, 12 * GiB);
  assert.equal(DEFAULTS.minFree, 10 * GiB);
  assert.equal(DEFAULTS.ageMs, 7 * 86400000);
});
