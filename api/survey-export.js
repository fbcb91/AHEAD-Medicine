// Esporta le risposte del questionario in CSV (apribile con Excel o Google Sheets).
// Protetto da SURVEY_ADMIN_KEY: /api/survey-export?key=LA_TUA_CHIAVE
import SCHEMA from './_survey-schema.js';
import { LIST_KEY, redis, storeConfigured } from './_store.js';
import { timingSafeEqual } from 'node:crypto';

function authorized(key) {
  const expected = process.env.SURVEY_ADMIN_KEY || '';
  if (expected.length < 16 || typeof key !== 'string') return false;
  const a = Buffer.from(key), b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

const cell = v => {
  const text = Array.isArray(v) ? v.join('; ') : v == null ? '' : String(v);
  // Evita che un testo libero venga interpretato come formula dal foglio di calcolo.
  const safe = /^[=+\-@]/.test(text) ? "'" + text : text;
  return '"' + safe.replace(/"/g, '""') + '"';
};

export default async function handler(req, res) {
  if (!authorized(req.query?.key || req.headers['x-admin-key'])) return res.status(401).json({ error: 'Non autorizzato.' });
  if (!storeConfigured()) return res.status(503).json({ error: 'Archivio non configurato.' });
  const rows = (await redis('LRANGE', LIST_KEY, '0', '-1')).map(r => JSON.parse(r));
  const columns = ['data', ...Object.keys(SCHEMA)];
  const csv = '﻿' + [columns.join(','), ...rows.map(r => columns.map(c => cell(r[c])).join(','))].join('\r\n');
  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  res.setHeader('Content-Disposition', `attachment; filename="questionario-${new Date().toISOString().slice(0, 10)}.csv"`);
  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).send(csv);
}
