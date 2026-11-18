// SPDX-License-Identifier: GPL-3.0-or-later
// rfpgen 사이드카: HWPX/HWP → (rhwp, MIT) 쪽별 SVG → (Chromium, Playwright) 벡터 PDF.
//
// 사용: node hwpx_to_pdf.mjs <input.hwpx> <output.pdf> [--svg-dir DIR] [--info info.json] [--font-alias "문서 글꼴=설치 글꼴" …]
// 출력: info JSON {pages, width_px, height_px, source_format}
//
// 설계서 7.9절 server 경로. 한글 렌더와 픽셀 단위로 같다는 보장은 없다(쪽수·넘침 점검과 제출용 PDF의 기본 경로).
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
if (args.length < 2) {
  console.error('사용: node hwpx_to_pdf.mjs <input.hwpx> <output.pdf> [--svg-dir DIR] [--info info.json]');
  process.exit(2);
}
const [input, output] = args;
const opt = (name) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};

const rhwp = await import(join(here, 'node_modules/@rhwp/core/rhwp.js'));
rhwp.initSync({ module: readFileSync(join(here, 'node_modules/@rhwp/core/rhwp_bg.wasm')) });
const doc = new rhwp.HwpDocument(new Uint8Array(readFileSync(input)));
const pages = doc.pageCount();
const svgs = [];
for (let i = 0; i < pages; i++) svgs.push(doc.renderPageSvg(i));

const svgDir = opt('--svg-dir');
if (svgDir) {
  mkdirSync(svgDir, { recursive: true });
  svgs.forEach((s, i) => writeFileSync(join(svgDir, `page-${String(i + 1).padStart(3, '0')}.svg`), s));
}

const size = (s) => {
  const m = /<svg[^>]*\swidth="([\d.]+)"[^>]*\sheight="([\d.]+)"/.exec(s);
  return m ? [parseFloat(m[1]), parseFloat(m[2])] : [793.7, 1122.5];
};
const [w, h] = size(svgs[0] ?? '');

// 글꼴 별칭: 문서의 글꼴 이름 → 서버에 설치된 글꼴 이름(@font-face local()).
// 예: Google Fonts 이름 'Noto Sans KR' ↔ Debian 패키지 이름 'Noto Sans CJK KR'.
const aliases = [];
for (let i = 0; i < args.length; i++) if (args[i] === '--font-alias') aliases.push(args[i + 1]);
if (!aliases.length) aliases.push('Noto Sans KR=Noto Sans CJK KR', 'Noto Serif KR=Noto Serif CJK KR');
const fontFaces = aliases
  .map((a) => a.split('='))
  .filter((p) => p.length === 2)
  .map(([from, to]) => `
    @font-face { font-family: "${from}"; font-weight: 400; src: local("${to}"), local("${to} Regular"), local("${from}"), local("${from} Regular"); }
    @font-face { font-family: "${from}"; font-weight: 700; src: local("${to} Bold"), local("${to}"), local("${from} Bold"), local("${from}"); }`)
  .join('');
const pxToMm = (px) => (px * 25.4) / 96;

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
try {
  const page = await browser.newPage();
  // 쪽 SVG마다 id(cell-clip-15 등)가 다시 1부터 매겨진다. 한 HTML에 이어 붙이면 url(#id)가 앞쪽의
  // 같은 id를 가리켜 다른 쪽의 잘라내기 영역이 적용된다(표 칸 글이 첫 줄만 남는 등). 쪽마다 접두어를 붙인다.
  const scopeIds = (s, i) => s
    .replace(/\sid="([^"]+)"/g, ` id="p${i}-$1"`)
    .replace(/url\(\s*(['"]?)#([^'")\s]+)\1\s*\)/g, `url(#p${i}-$2)`)
    .replace(/(\s(?:xlink:)?href=")#([^"]+)"/g, `$1#p${i}-$2"`);
  const body = svgs
    .map((s, i) => `<div class="p">${scopeIds(s.replace(/<\?xml[^>]*>/, ''), i + 1)}</div>`)
    .join('\n');
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>${fontFaces}
    @page { size: ${pxToMm(w).toFixed(2)}mm ${pxToMm(h).toFixed(2)}mm; margin: 0 }
    html, body { margin: 0; padding: 0 }
    .p { width: ${pxToMm(w).toFixed(2)}mm; height: ${pxToMm(h).toFixed(2)}mm; overflow: hidden; break-after: page }
    .p:last-child { break-after: auto }
    .p > svg { width: 100%; height: 100% }
  </style></head><body>${body}</body></html>`, { waitUntil: 'load' });
  await page.pdf({ path: output, preferCSSPageSize: true, printBackground: true });
} finally {
  await browser.close();
}
const info = { pages, width_px: w, height_px: h, source_format: doc.getSourceFormat ? doc.getSourceFormat() : null };
const infoPath = opt('--info');
if (infoPath) writeFileSync(infoPath, JSON.stringify(info));
console.log(JSON.stringify(info));
