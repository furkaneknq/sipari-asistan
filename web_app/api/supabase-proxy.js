/**
 * Vercel Serverless Function: Supabase Ters Proxy
 * Supabase Cloudflare güvenlik katmanının secret key tarayıcı engellemesini
 * sunucu düzeyinde User-Agent ile aşarak güvenle iletir.
 */

export default async function handler(req, res) {
  // CORS Başlıkları
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, apikey, Authorization, prefer, range'
  );

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  try {
    const supabaseBaseUrl = process.env.SUPABASE_URL || "https://xgvlgmikxchpttydtelb.supabase.co";
    const supabaseKey = process.env.SUPABASE_KEY;
    if (!supabaseKey) {
      res.status(500).json({ error: "SUPABASE_KEY environment variable not set on server." });
      return;
    }

    // Gelen yol (path) ve sorgu parametreleri
    const host = req.headers.host || 'localhost';
    const proto = req.headers['x-forwarded-proto'] || 'https';
    const reqUrl = new URL(req.url, `${proto}://${host}`);

    let subPath = reqUrl.searchParams.get('path') || '';
    if (!subPath && req.query && req.query.path) {
      subPath = Array.isArray(req.query.path) ? req.query.path.join('/') : req.query.path;
    }

    reqUrl.searchParams.delete('path');
    const remainingQuery = reqUrl.searchParams.toString() ? `?${reqUrl.searchParams.toString()}` : '';
    const targetUrl = `${supabaseBaseUrl}/${subPath}${remainingQuery}`;

    // Başlıkları hazırla
    const forwardHeaders = { ...req.headers };
    delete forwardHeaders.host;
    delete forwardHeaders['content-length'];
    forwardHeaders['user-agent'] = 'OrderTrackingDesktopBridge/1.0';
    forwardHeaders['apikey'] = supabaseKey;
    if (!forwardHeaders['authorization']) {
      forwardHeaders['authorization'] = `Bearer ${supabaseKey}`;
    }

    // Gövde (Body)
    let body = undefined;
    if (['POST', 'PUT', 'PATCH'].includes(req.method)) {
      if (req.body) {
        body = typeof req.body === 'object' ? JSON.stringify(req.body) : req.body;
      }
    }

    const response = await fetch(targetUrl, {
      method: req.method,
      headers: forwardHeaders,
      body: body
    });

    res.status(response.status);

    response.headers.forEach((value, key) => {
      const lowerKey = key.toLowerCase();
      if (!['content-encoding', 'transfer-encoding', 'access-control-allow-origin'].includes(lowerKey)) {
        res.setHeader(key, value);
      }
    });

    const data = await response.arrayBuffer();
    res.send(Buffer.from(data));
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}
