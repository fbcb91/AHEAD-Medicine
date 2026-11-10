// Riepilogo dei contatori e del numero di questionari, protetto da SURVEY_ADMIN_KEY:
// /api/stats?key=LA_TUA_CHIAVE
import { timingSafeEqual } from 'node:crypto';
import { LIST_KEY, redis, storeConfigured } from './_store.js';

function authorized(key) {
  const expected = process.env.SURVEY_ADMIN_KEY || '';
  if (expected.length < 16 || typeof key !== 'string') return false;
  const a = Buffer.from(key), b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}
const toObject = flat => Object.fromEntries((flat || []).reduce((acc, x, i) => (i % 2 ? acc[acc.length - 1].push(Number(x)) : acc.push([x]), acc), []));

export default async function handler(req, res) {
  if (!authorized(req.query?.key || req.headers['x-admin-key'])) return res.status(401).json({ error: 'Non autorizzato.' });
  if (!storeConfigured()) return res.status(503).json({ error: 'Archivio non configurato.' });
  const month = new Date().toISOString().slice(0, 7);
  const [interesse, interesseMese, questionari, questionariMese, risposte] = await Promise.all([
    redis('HGETALL', 'events:interesse'), redis('HGETALL', `events:interesse:${month}`),
    redis('HGETALL', 'events:questionario'), redis('HGETALL', `events:questionario:${month}`), redis('LLEN', LIST_KEY)]);
  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).json({
    questionari_completati: risposte,
    clic_interesse_per_area: { totale: toObject(interesse), [month]: toObject(interesseMese) },
    questionari_per_area: { totale: toObject(questionari), [month]: toObject(questionariMese) },
  });
}
