// Esporta la lista d'attesa delle email in CSV, pronta da importare in MailerLite.
// Protetto da SURVEY_ADMIN_KEY: /api/waitlist-export?key=LA_TUA_CHIAVE
import { timingSafeEqual } from 'node:crypto';
import { redis, storeConfigured } from './_store.js';

function authorized(key) {
  const expected = process.env.SURVEY_ADMIN_KEY || '';
  if (expected.length < 16 || typeof key !== 'string') return false;
  const a = Buffer.from(key), b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

export default async function handler(req, res) {
  if (!authorized(req.query?.key || req.headers['x-admin-key'])) return res.status(401).json({ error: 'Non autorizzato.' });
  if (!storeConfigured()) return res.status(503).json({ error: 'Archivio non configurato.' });
  const flat = (await redis('HGETALL', 'waitlist:emails')) || [];
  const rows = [];
  for (let i = 0; i < flat.length; i += 2) {
    let info = {};
    try { info = JSON.parse(flat[i + 1]); } catch (_) {}
    rows.push(`"${flat[i].replace(/"/g, '""')}","${info.data || ''}"`);
  }
  const csv = '﻿' + ['email,data_consenso', ...rows].join('\r\n');
  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  res.setHeader('Content-Disposition', `attachment; filename="lista-attesa-${new Date().toISOString().slice(0, 10)}.csv"`);
  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).send(csv);
}
