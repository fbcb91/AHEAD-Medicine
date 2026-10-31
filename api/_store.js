// Archivio delle risposte anonime: Redis via REST (Upstash, collegabile da Vercel Marketplace).
// Variabili: KV_REST_API_URL + KV_REST_API_TOKEN (nomi impostati dall'integrazione Vercel)
// oppure UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN.
export const LIST_KEY = 'survey:responses';

function config() {
  const url = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
  return url && token ? { url, token } : null;
}

export function storeConfigured() {
  return config() !== null;
}

export async function redis(...command) {
  const { url, token } = config();
  const res = await fetch(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(command),
  });
  if (!res.ok) throw new Error(`Redis ${res.status}`);
  return (await res.json()).result;
}
