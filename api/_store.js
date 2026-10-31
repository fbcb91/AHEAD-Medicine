// Archivio delle risposte anonime: Redis via REST (Upstash, collegabile da Vercel Marketplace).
// Variabili: KV_REST_API_URL + KV_REST_API_TOKEN (nomi impostati dall'integrazione Vercel),
// UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN, oppure le stesse con un prefisso
// personalizzato scelto nell'integrazione (es. STORAGE_KV_REST_API_URL).
export const LIST_KEY = 'survey:responses';

function config() {
  const env = process.env;
  const url = env.KV_REST_API_URL || env.UPSTASH_REDIS_REST_URL;
  const token = env.KV_REST_API_TOKEN || env.UPSTASH_REDIS_REST_TOKEN;
  if (url && token) return { url, token };
  // Prefisso personalizzato: cerca <PREFISSO>_..._REST_API_URL e il token corrispondente (non quello di sola lettura).
  for (const key of Object.keys(env)) {
    if (key.endsWith('_REST_API_URL') || key.endsWith('_REST_URL')) {
      const tokenKey = key.replace(/_URL$/, '_TOKEN');
      if (env[key] && env[tokenKey]) return { url: env[key], token: env[tokenKey] };
    }
  }
  return null;
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
