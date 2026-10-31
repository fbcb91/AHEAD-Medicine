// Genera le immagini social (Open Graph, 1200x630) elencate da build.py in og/pages.json,
// più logo e apple-touch-icon. Uso: node scripts/og-images.js [--force] && python3 build.py
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = path.join(__dirname, '..');
const force = process.argv.includes('--force');
const esc = s => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const FONTS = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@500;700&family=Manrope:wght@600;700&display=block">';
const card = ({ title, kicker }) => `<!doctype html><html><head><meta charset="utf-8">${FONTS}<style>
  *{margin:0;box-sizing:border-box}
  body{width:1200px;height:630px;background:#10191d;color:#f4f7f6;font-family:'DM Sans',system-ui,sans-serif;position:relative;overflow:hidden}
  .orbit{position:absolute;border:1px solid #2c4249;border-radius:50%}
  .o1{width:620px;height:620px;right:-170px;top:-60px}.o2{width:420px;height:420px;right:-70px;top:40px}
  .core{position:absolute;right:120px;top:225px;width:180px;height:180px;border-radius:50%;background:radial-gradient(circle at 35% 35%,#bed7ed,#6f97b8 60%,#2c4249)}
  .wrap{position:absolute;left:80px;top:70px;right:380px;bottom:70px;display:flex;flex-direction:column}
  .logo{display:flex;align-items:center;gap:14px;font-family:Manrope,sans-serif;font-weight:700;font-size:30px;letter-spacing:-.04em}
  .mark{width:48px;height:48px;background:#bed7ed;color:#10191d;display:grid;place-items:center;font-size:28px}
  .kicker{margin-top:auto;font-size:18px;letter-spacing:.2em;font-weight:700;color:#89b9d1}
  h1{font-family:Manrope,sans-serif;font-weight:600;letter-spacing:-.045em;line-height:1.05;margin-top:18px;font-size:${title.length > 48 ? 54 : title.length > 28 ? 64 : 84}px}
  .foot{margin-top:28px;font-size:18px;color:#9fb7bc}
</style></head><body><div class="orbit o1"></div><div class="orbit o2"></div><div class="core"></div>
<div class="wrap"><div class="logo"><span class="mark">A</span><span>AHEAD<span style="color:#89b9d1">.</span></span></div>
<div class="kicker">${esc(kicker)}</div><h1>${esc(title)}</h1><div class="foot">Medicina emergente, senza hype.</div></div></body></html>`;

const icon = size => `<!doctype html><html><head><meta charset="utf-8">${FONTS}<style>*{margin:0}body{width:${size}px;height:${size}px;background:#10191d;display:grid;place-items:center}
span{font-family:Manrope,sans-serif;font-weight:700;color:#bed7ed;font-size:${Math.round(size * 0.62)}px;line-height:1}</style></head><body><span>A</span></body></html>`;

(async () => {
  const jobs = JSON.parse(fs.readFileSync(path.join(ROOT, 'og/pages.json'), 'utf8'));
  jobs.push({ file: 'og/default.jpg', title: 'La medicina di domani. Le risposte di oggi.', kicker: 'AHEAD MEDICINE' });
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
