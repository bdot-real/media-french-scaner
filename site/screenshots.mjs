// Capture the report screenshots the site shows, in both languages.
//
//   node site/screenshots.mjs
//
// Drives the local Chrome over the DevTools protocol, so there is nothing to
// install: Node 22+ ships fetch and WebSocket. Each capture is one section of
// the report, cropped from its heading to the bottom of its card, at 2x.
//
// The French captures are taken with the report's own toggle rather than by
// re-navigating, and the script asserts the page language before every set,
// because an English capture on the French page is exactly the defect this
// project exists to catch.

import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.dirname(HERE);
const OUT = path.join(HERE, 'static', 'img');
const CHROME = process.env.CHROME ||
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9333;

// Section index is the h2 order in the report. Names are what the site uses.
const SHOTS = [
  { report: 'report.html', name: 'overview', section: 'top' },
  { report: 'report.html', name: 'severity', section: 0 },
  { report: 'report.html', name: 'dimensions', section: 1 },
  { report: 'report.html', name: 'drift', section: 3 },
  { report: 'report.html', name: 'media', section: 4 },
  { report: 'report.html', name: 'segments', section: 7 },
  { report: 'report_embed.html', name: 'embedding-overview', section: 'top' },
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const profile = fs.mkdtempSync(path.join(process.env.TMPDIR || '/tmp', 'bqh-shots-'));
  const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${profile}`, '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' });
  try {
    let tabs;
    for (let i = 0; i < 50 && !tabs; i++) {
      try { tabs = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); }
      catch { await sleep(200); }
    }
    const ws = new WebSocket(tabs.find((t) => t.type === 'page').webSocketDebuggerUrl);
    await new Promise((r) => (ws.onopen = r));
    let id = 0;
    const pending = {};
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && pending[d.id]) { pending[d.id](d); delete pending[d.id]; }
    };
    const send = (method, params = {}) => new Promise((r) => {
      const i = ++id; pending[i] = r; ws.send(JSON.stringify({ id: i, method, params }));
    });
    const ev = async (expr) =>
      (await send('Runtime.evaluate', { expression: expr, returnByValue: true })).result.result.value;

    await send('Emulation.setDeviceMetricsOverride',
      { width: 1200, height: 900, deviceScaleFactor: 2, mobile: false });

    for (const report of [...new Set(SHOTS.map((s) => s.report))]) {
      await send('Page.navigate', { url: pathToFileURL(path.join(ROOT, report)).href });
      await sleep(1500);
      for (const lang of ['en', 'fr']) {
        await ev(`(function(){
          var b=[...document.querySelectorAll('.langtog')]
            .find(function(b){return b.getAttribute('data-switch')==='${lang}' && b.offsetParent;});
          if (b) b.click(); window.scrollTo(0,0); })()`);
        await sleep(300);
        const got = await ev('document.documentElement.lang');
        if (got !== lang) throw new Error(`${report}: wanted ${lang}, page is ${got}`);
        fs.mkdirSync(path.join(OUT, lang), { recursive: true });
        for (const s of SHOTS.filter((s) => s.report === report)) {
          const r = await ev(`(function(){
            var root=[...document.querySelectorAll('[data-lang]')].find(function(v){return !v.hidden;});
            if (${JSON.stringify(s.section)} === 'top') {
              var hero=root.querySelector('.hero').getBoundingClientRect();
              var t=root.getBoundingClientRect();
              return {x:t.left+scrollX, y:t.top+scrollY, w:t.width, h:hero.bottom-t.top+28};
            }
            var h=root.querySelectorAll('h2')[${Number(s.section) || 0}];
            var n=h.nextElementSibling; while(n && !n.classList.contains('card')) n=n.nextElementSibling;
            var a=h.getBoundingClientRect(), c=n.getBoundingClientRect();
            return {x:c.left+scrollX-20, y:a.top+scrollY-20, w:c.width+40, h:c.bottom-a.top+40};
          })()`);
          const shot = await send('Page.captureScreenshot', {
            format: 'png', captureBeyondViewport: true,
            clip: { x: Math.max(0, r.x), y: Math.max(0, r.y), width: r.w,
                    height: Math.min(r.h, 1500), scale: 1 },
          });
          const f = path.join(OUT, lang, `${s.name}.png`);
          fs.writeFileSync(f, Buffer.from(shot.result.data, 'base64'));
          console.log(path.relative(ROOT, f), `${Math.round(r.w)}x${Math.round(Math.min(r.h, 1500))}`);
        }
      }
    }
    ws.close();
  } finally {
    // Chrome keeps writing to its profile until it has exited.
    const exited = new Promise((r) => chrome.once('exit', r));
    chrome.kill();
    await exited;
    fs.rmSync(profile, { recursive: true, force: true });
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
