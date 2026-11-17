// SPDX-License-Identifier: GPL-3.0-or-later
// rfpgen 사이드카: 도식 SVG → PNG(Chromium, Playwright). 브라우저 하나로 여러 장을 한 번에 바꾼다.
//
// 사용: node svg_to_png.mjs [--dpi 200] [--font-alias "문서 글꼴=설치 글꼴" …] <in.svg> <out.png> [<in.svg> <out.png> …]
// 출력: JSON 배열 [{png, width_px, height_px}] (width_px·height_px는 PNG 픽셀)
//
// 설계서 7.9절 '도식'. SVG의 px는 96dpi 기준이므로 deviceScaleFactor = dpi / 96.
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { join } from 'node:path';

const args = process.argv.slice(2);
let dpi = 200;
const aliases = [];
const files = [];
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--dpi') dpi = parseFloat(args[++i]);
  else if (args[i] === '--font-alias') aliases.push(args[++i]);
  else files.push(args[i]);
}
if (files.length < 2 || files.length % 2) {
  console.error('사용: node svg_to_png.mjs [--dpi 200] <in.svg> <out.png> [...]');
  process.exit(2);
}
if (!aliases.length) aliases.push('Noto Sans KR=Noto Sans CJK KR', 'Noto Serif KR=Noto Serif CJK KR');
const fontFaces = aliases
  .map((a) => a.split('='))
  .filter((p) => p.length === 2)
  .map(([from, to]) => `
    @font-face { font-family: "${from}"; font-weight: 400; src: local("${to}"), local("${to} Regular"), local("${from}"), local("${from} Regular"); }
    @font-face { font-family: "${from}"; font-weight: 700; src: local("${to} Bold"), local("${to}"), local("${from} Bold"), local("${from}"); }`)
  .join('');

const require = createRequire(import.meta.url);
let playwright;
try {
  playwright = require('playwright');
} catch {
  playwright = require(join(process.env.NODE_PATH || '', 'playwright'));
}
// 브라우저: Playwright가 받은 Chromium. 다른 Chrome을 쓰려면 RFPGEN_CHROMIUM_PATH에 실행 파일 경로를 준다.
const executablePath = process.env.RFPGEN_CHROMIUM_PATH || undefined;
const browser = await playwright.chromium.launch(executablePath ? { executablePath } : {});
const out = [];
try {
  const context = await browser.newContext({ deviceScaleFactor: dpi / 96 });
  const page = await context.newPage();
  for (let i = 0; i < files.length; i += 2) {
    const svg = readFileSync(files[i], 'utf8').replace(/<\?xml[^>]*>/, '');
    const m = /<svg[^>]*\swidth="([\d.]+)"[^>]*\sheight="([\d.]+)"/.exec(svg);
    const [w, h] = m ? [Math.ceil(parseFloat(m[1])), Math.ceil(parseFloat(m[2]))] : [800, 600];
    await page.setViewportSize({ width: w, height: h });
    await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>${fontFaces}
      html, body { margin: 0; padding: 0; background: #fff }
      svg { display: block }
    </style></head><body>${svg}</body></html>`, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    await page.locator('svg').first().screenshot({ path: files[i + 1] });
    out.push({ png: files[i + 1], width_px: Math.round((w * dpi) / 96), height_px: Math.round((h * dpi) / 96) });
  }
} finally {
  await browser.close();
}
console.log(JSON.stringify(out));
