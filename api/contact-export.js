// Esporta i messaggi del modulo di contatto in CSV, protetto da SURVEY_ADMIN_KEY:
// /api/contact-export?key=LA_TUA_CHIAVE
import { timingSafeEqual } from 'node:crypto';
import { redis, storeConfigured } from './_store.js';

function authorized(key) {
  const expected = process.env.SURVEY_ADMIN_KEY || '';
  if (expected.length < 16 || typeof key !== 'string') return false;
  const a = Buffer.from(key), b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}
const cell = v => {
  const text = v == null ? '' : String(v);
  const safe = /^[=+\-@]/.test(text) ? "'" + text : text;  // niente formule nel foglio di calcolo
  return '"' + safe.replace(/"/g, '""') + '"';
};

export default async function handler(req, res) {
  if (!authorized(req.query?.key || req.headers['x-admin-key'])) return res.status(401).json({ error: 'Non autorizzato.' });
  if (!storeConfigured()) return res.status(503).json({ error: 'Archivio non configurato.' });
  const rows = ((await redis('LRANGE', 'contact:messages', '0', '-1')) || []).map(r => JSON.parse(r));
  const cols = ['data', 'nome', 'email', 'tema', 'messaggio'];
  const csv = '﻿' + [cols.join(','), ...rows.map(r => cols.map(c => cell(r[c])).join(','))].join('\r\n');
  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  res.setHeader('Content-Disposition', `attachment; filename="messaggi-${new Date().toISOString().slice(0, 10)}.csv"`);
  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).send(csv);
}
