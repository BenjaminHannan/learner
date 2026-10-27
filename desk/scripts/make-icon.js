'use strict';
// Renders the mascot onto an espresso rounded-square tile -> assets/icon.png (1024) and assets/icon.icns.
// Run: xvfb-run -a npx electron scripts/make-icon.js --no-sandbox
const { app, BrowserWindow, nativeImage } = require('electron');
const fs = require('fs');
const path = require('path');
const Mascot = require('../renderer/mascot.js');

const ASSETS = path.join(__dirname, '..', 'assets');

function html() {
  return '<!doctype html><meta charset=utf-8><style>html,body{margin:0;background:transparent;width:1024px;height:1024px;overflow:hidden}' +
    '.tile{position:absolute;left:100px;top:100px;width:824px;height:824px;border-radius:186px;box-sizing:border-box;border:3px solid rgba(255,214,140,.16);' +
    'background:radial-gradient(circle at 50% 42%,#4a3220 0%,#2a1d14 52%,#17110d 100%);box-shadow:0 22px 40px rgba(0,0,0,.38)}' +
    '.glow{position:absolute;left:262px;top:230px;width:500px;height:500px;border-radius:50%;background:radial-gradient(circle,rgba(245,165,36,.42),rgba(245,165,36,0) 68%)}' +
    '.m{position:absolute;left:202px;top:196px;width:620px;height:620px}.m svg{width:100%;height:100%;overflow:visible}</style>' +
    '<div class=tile></div><div class=glow></div><div class=m>' + Mascot.svg('idle', { still: true }) + '</div>';
}

// ICNS: 'icns' + total length, then entries of type + length + PNG bytes.
function icns(entries) {
  const parts = entries.map(([type, png]) => { const h = Buffer.alloc(8); h.write(type, 0, 'ascii'); h.writeUInt32BE(png.length + 8, 4); return Buffer.concat([h, png]); });
  const body = Buffer.concat(parts);
  const head = Buffer.alloc(8); head.write('icns', 0, 'ascii'); head.writeUInt32BE(body.length + 8, 4);
  return Buffer.concat([head, body]);
}

app.disableHardwareAcceleration();
app.whenReady().then(async () => {
  const win = new BrowserWindow({ show: false, width: 1024, height: 1024, useContentSize: true, transparent: true, frame: false, webPreferences: { offscreen: true } });
  await win.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(html()));
  await new Promise((r) => setTimeout(r, 600));
  let img = await win.webContents.capturePage();
  if (img.getSize().width !== 1024) img = img.resize({ width: 1024, height: 1024, quality: 'best' });
  fs.mkdirSync(ASSETS, { recursive: true });
  const png = (n) => (n === 1024 ? img : img.resize({ width: n, height: n, quality: 'best' })).toPNG();
  fs.writeFileSync(path.join(ASSETS, 'icon.png'), png(1024));
  fs.writeFileSync(path.join(ASSETS, 'icon.icns'), icns([['ic07', png(128)], ['ic08', png(256)], ['ic09', png(512)], ['ic10', png(1024)]]));
  console.log('icon written to ' + ASSETS);
  app.quit();
});
