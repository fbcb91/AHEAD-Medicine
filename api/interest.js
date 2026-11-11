// Iscrizione agli aggiornamenti. Salva solo l'email (mai area, servizio o dati sanitari).
// - Con MAILERLITE_API_TOKEN e MAILERLITE_GROUP_ID: iscrive su MailerLite (con il double opt-in
//   attivo nell'account MailerLite).
// - Altrimenti, o se MailerLite non risponde: salva l'email nella lista d'attesa su Upstash
//   (chiave "waitlist:emails"), da esportare con /api/waitlist-export e importare in MailerLite.
import { redis, storeConfigured } from './_store.js';

// Best-effort rate limit: memory is per serverless instance, so this only slows down
// simple abuse. Use a shared store (e.g. Vercel KV) or a WAF rule for stronger limits.
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

async function toMailerLite(email) {
  const response = await fetch('https://connect.mailerlite.com/api/subscribers', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${process.env.MAILERLITE_API_TOKEN}`, 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify({ email, groups: [process.env.MAILERLITE_GROUP_ID] })
  });
  return response.ok;
}

async function toWaitlist(email) {
  // Data del consenso (senza ora), utile come prova quando la lista viene importata.
  await redis('HSET', 'waitlist:emails', email, JSON.stringify({ data: new Date().toISOString().slice(0, 10), consenso: true }));
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Metodo non consentito.' });
  const ip = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim() || 'unknown';
  if (rateLimited(ip)) return res.status(429).json({ error: 'Troppe richieste. Riprova tra qualche minuto.' });
  const { email, consent, website } = req.body || {};
  // Honeypot: the hidden "website" field is empty for people and often filled by bots.
  if (website) return res.status(200).json({ ok: true, mode: 'lista' });
  const cleanEmail = typeof email === 'string' ? email.trim().toLowerCase() : '';
  if (!consent || cleanEmail.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) {
    return res.status(400).json({ error: 'Inserisci un’email valida e conferma il consenso.' });
  }
  const mailerLiteReady = Boolean(process.env.MAILERLITE_API_TOKEN && process.env.MAILERLITE_GROUP_ID);
  try {
    if (mailerLiteReady && await toMailerLite(cleanEmail)) return res.status(200).json({ ok: true, mode: 'mailerlite' });
    if (storeConfigured()) {
      await toWaitlist(cleanEmail);
      return res.status(200).json({ ok: true, mode: 'lista' });
    }
  } catch (_) { /* gestito sotto */ }
  // Do not expose API error details or subscriber information to the public client.
  return res.status(503).json({ error: 'Non riusciamo a registrare l’iscrizione in questo momento. Riprova tra qualche minuto.' });
}
