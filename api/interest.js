// Vercel serverless endpoint. No health data, treatment or selected service stored with email.
// ENV: MAILERLITE_API_TOKEN, MAILERLITE_GROUP_ID, SITE_FORMS_ENABLED=true.
export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Metodo non consentito.' });
  if (process.env.SITE_FORMS_ENABLED !== 'true' || !process.env.MAILERLITE_API_TOKEN || !process.env.MAILERLITE_GROUP_ID) {
    return res.status(503).json({ error: 'Le iscrizioni non sono ancora attive. Il progetto è in preparazione.' });
  }
  const { email, consent } = req.body || {};
  const cleanEmail = typeof email === 'string' ? email.trim().toLowerCase() : '';
  if (!consent || cleanEmail.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) {
    return res.status(400).json({ error: 'Inserisci una email valida e conferma il consenso.' });
  }
  try {
    const response = await fetch('https://connect.mailerlite.com/api/subscribers', {
      method:'POST',
      headers:{'Authorization':`Bearer ${process.env.MAILERLITE_API_TOKEN}`,'Content-Type':'application/json','Accept':'application/json'},
      body: JSON.stringify({ email:cleanEmail, groups:[process.env.MAILERLITE_GROUP_ID] })
    });
    if (!response.ok) {
      // Do not expose API error details or subscriber information to the public client.
      return res.status(502).json({ error:'Impossibile completare l’iscrizione al momento.' });
    }
    return res.status(200).json({ ok:true });
  } catch (_) {
    return res.status(502).json({ error:'Servizio temporaneamente non disponibile.' });
  }
}
