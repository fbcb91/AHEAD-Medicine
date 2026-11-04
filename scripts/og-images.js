// Genera le immagini social (Open Graph, 1200x630) elencate da build.py in og/pages.json,
// più logo e apple-touch-icon. Uso: node scripts/og-images.js [--force] && python3 build.py
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = path.join(__dirname, '..');
const force = process.argv.includes('--force');
const esc = s => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// Font incorporati dal sito (fonts/*.woff2): le immagini non dipendono dalla rete.
const font = (family, file, weights) => `@font-face{font-family:'${family}';src:url(data:font/woff2;base64,${fs.readFileSync(path.join(ROOT, 'fonts', file)).toString('base64')}) format('woff2');font-weight:${weights}}`;
const FONTS = `<style>${font('Cinzel', 'cinzel.woff2', '400 900')}${font('DM Sans', 'dm-sans.woff2', '100 1000')}${font('Manrope', 'manrope.woff2', '200 800')}</style>`;
const card = ({ title, kicker }) => `<!doctype html><html><head><meta charset="utf-8">${FONTS}<style>
  *{margin:0;box-sizing:border-box}
  body{width:1200px;height:630px;background:#10191d;color:#f4f7f6;font-family:'DM Sans',system-ui,sans-serif;position:relative;overflow:hidden}
  .orbit{position:absolute;border:1px solid #2c4249;border-radius:50%}
  .o1{width:620px;height:620px;right:-170px;top:-60px}.o2{width:420px;height:420px;right:-70px;top:40px}
  .core{position:absolute;right:120px;top:225px;width:180px;height:180px;border-radius:50%;background:radial-gradient(circle at 35% 35%,#bed7ed,#6f97b8 60%,#2c4249)}
  .wrap{position:absolute;left:80px;top:70px;right:380px;bottom:70px;display:flex;flex-direction:column}
  .logo{display:flex;align-items:center;gap:18px}
  .word{font-family:Cinzel,serif;font-weight:500;font-size:40px;letter-spacing:.06em;color:#f3efe7;position:relative}
  .bar{width:1px;height:38px;background:#f3efe766}
  .med{font-family:'DM Sans',sans-serif;font-weight:500;font-size:18px;letter-spacing:.42em;color:#6cc3cf}
  .kicker{margin-top:auto;font-size:18px;letter-spacing:.2em;font-weight:700;color:#6cc3cf}
  h1{font-family:Manrope,sans-serif;font-weight:600;letter-spacing:-.045em;line-height:1.05;margin-top:18px;font-size:${title.length > 48 ? 54 : title.length > 28 ? 64 : 84}px}
  .foot{margin-top:28px;font-size:18px;color:#9fb7bc}
</style></head><body><div class="orbit o1"></div><div class="orbit o2"></div><div class="core"></div>
<div class="wrap"><div class="logo"><span class="word">Areyon</span><span class="bar"></span><span class="med">MED</span></div>
<div class="kicker">${esc(kicker)}</div><h1>${esc(title)}</h1><div class="foot">Emerging medicine · Eccellenza, nel tempo.</div></div></body></html>`;

const icon = size => `<!doctype html><html><head><meta charset="utf-8">${FONTS}<style>*{margin:0}body{width:${size}px;height:${size}px;background:#10191d;display:grid;place-items:center}
span{font-family:Cinzel,serif;font-weight:500;color:#f3efe7;font-size:${Math.round(size * 0.62)}px;line-height:1}</style></head><body><span>A</span></body></html>`;

(async () => {
  const jobs = JSON.parse(fs.readFileSync(path.join(ROOT, 'og/pages.json'), 'utf8'));
  jobs.push({ file: 'og/default.jpg', title: 'La medicina di domani. Le risposte di oggi.', kicker: 'AREYON MED' });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
  let made = 0;
  for (const job of jobs) {
    const out = path.join(ROOT, job.file);
    if (!force && fs.existsSync(out)) continue;
    await page.setContent(card(job), { waitUntil: 'networkidle' }).catch(() => {});
    await page.screenshot({ path: out, type: 'jpeg', quality: 82 });
    made++;
  }
  for (const [file, size] of [['og/logo.png', 512], ['og/apple-touch-icon.png', 180]]) {
    const out = path.join(ROOT, file);
    if (!force && fs.existsSync(out)) continue;
    await page.setViewportSize({ width: size, height: size });
    await page.setContent(icon(size), { waitUntil: 'networkidle' }).catch(() => {});
    await page.screenshot({ path: out });
    made++;
  }
  await browser.close();
  console.log(`Immagini generate: ${made}`);
})();
