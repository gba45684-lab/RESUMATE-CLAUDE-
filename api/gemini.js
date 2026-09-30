export default async function handler(req, res) {
  const origin = req.headers.origin || '*';
  res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Gemini-Model, X-Device-Id');
  res.setHeader('Vary', 'Origin');

  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ error: { message: 'POST only' } });

  const key = process.env.GEMINI_API_KEY;
  if (!key) return res.status(500).json({ error: { message: 'GEMINI_API_KEY is not configured on the server.' } });

  const allowed = new Set([
    'gemini-2.5-flash-lite',
    'gemini-2.5-flash',
    'gemini-2.5-pro',
    'gemini-2.0-flash',
    'gemini-1.5-flash'
  ]);
  const requested = String(req.headers['x-gemini-model'] || 'gemini-2.5-flash');
  const model = allowed.has(requested) ? requested : 'gemini-2.5-flash';

  try {
    const response = await fetch(
      'https://generativelanguage.googleapis.com/v1beta/models/' +
      encodeURIComponent(model) + ':generateContent?key=' + encodeURIComponent(key),
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req.body)
      }
    );

    const body = await response.text();
    res.status(response.status);
    res.setHeader('Content-Type', 'application/json');
    return res.send(body);
  } catch (error) {
    return res.status(502).json({ error: { message: 'Gemini proxy request failed.' } });
  }
}
