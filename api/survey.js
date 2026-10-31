// Riceve il questionario anonimo di /inizia/. Nessun dato identificativo: niente nome,
// email, IP o user agent vengono salvati. Valida ogni risposta contro lo schema generato da build.py.
import SCHEMA from './_survey-schema.js';
import { LIST_KEY, redis, storeConfigured } from './_store.js';

// Best-effort rate limit per istanza serverless (vedi api/interest.js).
const WINDOW_MS = 10 * 60 * 1000;
const MAX_REQUESTS = 5;
const hits = new Map();
function rateLimited(ip) {
  const now = Date.now();
  const recent = (hits.get(ip) || []).filter(t => now - t < WINDOW_MS);
  recent.push(now);
  hits.set(ip, recent);
  if (hits.size > 5000) hits.clear();
  return recent.length > MAX_REQUESTS;
}

export function clean(body) {
  const answers = {};
  for (const [id, q] of Object.entries(SCHEMA)) {
    const raw = body[id];
    if (q.type === 'text') {
      const text = typeof raw === 'string' ? raw.trim().slice(0, q.max || 500) : '';
      if (text) answers[id] = text;
    } else {
      const list = (Array.isArray(raw) ? raw : raw == null || raw === '' ? [] : [raw]).filter(v => q.options.includes(v));
      const unique = [...new Set(list)];
      if (q.type === 'single' && unique.length > 1) return { error: id };
      if (q.max && unique.length > q.max) return { error: id };
      if (unique.length) answers[id] = q.type === 'single' ? unique[0] : unique;
    }
    if (q.required && !(id in answers)) return { error: id };
  }
  return { answers };
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Metodo non consentito.' });
  const ip = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim() || 'unknown';
  if (rateLimited(ip)) return res.status(429).json({ error: 'Troppe richieste. Riprova tra qualche minuto.' });
  if (!storeConfigured()) return res.status(503).json({ error: 'Il questionario non è ancora attivo. Riprova presto.' });

  const body = req.body && typeof req.body === 'object' ? req.body : {};
  // Honeypot: risposta positiva ai bot, ma nessun salvataggio.
  if (body.website) return res.status(200).json({ ok: true });
  const { answers, error } = clean(body);
  if (error) return res.status(400).json({ error: 'Alcune risposte non sono valide. Controlla e riprova.', field: error });

  // Solo la data (non l'ora) per ridurre ulteriormente la possibilità di identificare chi risponde.
  const record = { data: new Date().toISOString().slice(0, 10), ...answers };
  try {
    await redis('RPUSH', LIST_KEY, JSON.stringify(record));
    return res.status(200).json({ ok: true });
  } catch (_) {
    return res.status(502).json({ error: 'Impossibile salvare le risposte al momento. Riprova più tardi.' });
  }
}
