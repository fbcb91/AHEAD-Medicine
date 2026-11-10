// Contatori aggregati degli eventi di interesse: solo totali, nessun dato sulla persona
// (niente IP, user agent, cookie o identificativi). Accetta solo nomi ed etichette note.
import SCHEMA from './_survey-schema.js';
import { redis, storeConfigured } from './_store.js';

const AREAS = new Set([...SCHEMA.aree.options, 'generale']);
const EVENTS = { interesse: 'servizio', questionario: 'area' };

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).end();
  if (!storeConfigured()) return res.status(204).end();
  let body = req.body;
  if (typeof body === 'string') { try { body = JSON.parse(body); } catch (_) { body = {}; } }
  const { e, v } = body || {};
  if (!(e in EVENTS) || !AREAS.has(v)) return res.status(400).end();
  const month = new Date().toISOString().slice(0, 7);
  try {
    await redis('HINCRBY', `events:${e}`, v, '1');
    await redis('HINCRBY', `events:${e}:${month}`, v, '1');
  } catch (_) { /* un contatore perso non deve disturbare il visitatore */ }
  return res.status(204).end();
}
