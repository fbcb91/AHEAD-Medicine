// Modulo di contatto della pagina /contatti/. Salva email, argomento e messaggio nella lista
// "contact:messages" su Upstash (niente IP né user agent). Non è pensato per dati sanitari:
// la pagina invita a non inserirne e rimanda al questionario anonimo.
import TOPICS from './_contact-topics.js';
import { redis, storeConfigured } from './_store.js';

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

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Metodo non consentito.' });
  const ip = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim() || 'unknown';
  if (rateLimited(ip)) return res.status(429).json({ error: 'Troppe richieste. Riprova tra qualche minuto.' });
  const { nome, email, tema, messaggio, consent, website } = req.body || {};
  if (website) return res.status(200).json({ ok: true });  // honeypot
  const cleanEmail = typeof email === 'string' ? email.trim().toLowerCase() : '';
  const text = typeof messaggio === 'string' ? messaggio.trim() : '';
  const name = typeof nome === 'string' ? nome.trim().slice(0, 80) : '';
  if (!consent) return res.status(400).json({ error: 'Conferma di aver letto l’informativa privacy.' });
  if (cleanEmail.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) return res.status(400).json({ error: 'Inserisci un’email valida, così possiamo risponderti.' });
  if (!TOPICS.includes(tema)) return res.status(400).json({ error: 'Scegli l’argomento del messaggio.' });
  if (text.length < 10 || text.length > 2000) return res.status(400).json({ error: 'Scrivi un messaggio tra 10 e 2000 caratteri.' });
  if (!storeConfigured()) return res.status(503).json({ error: 'Non riusciamo a inviare il messaggio in questo momento. Riprova più tardi.' });
  try {
    await redis('RPUSH', 'contact:messages', JSON.stringify({ data: new Date().toISOString().slice(0, 16).replace('T', ' '), nome: name, email: cleanEmail, tema, messaggio: text }));
    return res.status(200).json({ ok: true });
  } catch (_) {
    return res.status(502).json({ error: 'Non riusciamo a inviare il messaggio in questo momento. Riprova più tardi.' });
  }
}
