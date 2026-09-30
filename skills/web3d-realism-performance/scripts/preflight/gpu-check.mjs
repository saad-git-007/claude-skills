// Run this before ANY GPU benchmark, screenshot run or recording. Exit code 0 = real GPU, 2 = software renderer.
//   node gpu-check.mjs            (CHROME=/usr/bin/google-chrome to override the binary)
//
// Why: when Chrome cannot open the GPU it silently falls back to llvmpipe (Mesa's CPU rasteriser). Everything "works"
// but a real scene never finishes loading (the first draw compiles every shader on the CPU: 10+ minutes for a heavy
// terrain shader), frame times mean nothing, and Chrome's own SwiftShader fallback may refuse to create a context.
// Typical Linux cause: no desktop session for your user (machine sitting at the login screen after a reboot, you are
// on SSH), so the ACL on /dev/dri/renderD128 is not granted to you. Fixes: log in on the machine's desktop, or
//   sudo setfacl -m u:$USER:rw /dev/dri/renderD128 /dev/dri/card0      (until next reboot)
// Do not run the sudo yourself without being asked; hand the one-liner to the person who owns the machine.
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
try { fs.closeSync(fs.openSync('/dev/dri/renderD128', 'r+')); console.log('/dev/dri/renderD128: access ok'); }
catch (e) { console.log('/dev/dri/renderD128:', e.code || e.message); }
const browser = await puppeteer.launch({ executablePath: process.env.CHROME || '/usr/bin/google-chrome', headless: 'new',
  args: ['--use-gl=angle', '--use-angle=gl-egl', '--enable-gpu', '--ignore-gpu-blocklist', '--no-sandbox'] });
const page = await browser.newPage();
await page.goto('data:text/html,<p>gpu</p>');
const r = await page.evaluate(() => { const g = document.createElement('canvas').getContext('webgl2'); const e = g?.getExtension('WEBGL_debug_renderer_info'); return e ? g.getParameter(e.UNMASKED_RENDERER_WEBGL) : 'no webgl2'; });
await browser.close();
console.log('WebGL renderer:', r);
if (/llvmpipe|swiftshader|software|no webgl2/i.test(r)) { console.log('SOFTWARE RENDERING: do not benchmark or record.'); process.exit(2); }
