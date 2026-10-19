// One-time TikTok connection for the organic publisher (scripts/tiktok.py).
// Open https://barur-mashkanta.co.il/api/tiktok-auth while logged in to the
// business TikTok account, approve, and the page shows the refresh token once,
// to paste into GitHub -> Settings -> Secrets -> TIKTOK_REFRESH_TOKEN.
// Environment variables (Vercel): TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, BARUR_SECRET.

const crypto = require('crypto');

const REDIRECT = 'https://barur-mashkanta.co.il/api/tiktok-auth';
const SCOPES = 'user.info.basic,video.upload,video.publish';

function sign(v) {
  return crypto.createHmac('sha256', 'tiktok-state:' + (process.env.BARUR_SECRET || '')).update(v).digest('hex').slice(0, 32);
}
function esc(s) {
  return String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function page(res, status, title, body) {
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Robots-Tag', 'noindex');
  res.status(status).end(`<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>${esc(title)}</title><style>body{font-family:system-ui,Arial,sans-serif;max-width:640px;margin:48px auto;padding:0 16px;color:#0F2A47;line-height:1.6}
textarea{width:100%;height:110px;direction:ltr;font-family:monospace;font-size:13px}button{padding:10px 18px;font-size:16px;margin-top:8px}</style></head>
<body><h1>${esc(title)}</h1>${body}</body></html>`);
}

module.exports = async (req, res) => {
  const key = process.env.TIKTOK_CLIENT_KEY;
  const secret = process.env.TIKTOK_CLIENT_SECRET;
  if (!key || !secret || !process.env.BARUR_SECRET) {
    return page(res, 500, 'חסרים משתנים ב-Vercel', '<p>צריך להגדיר TIKTOK_CLIENT_KEY ו-TIKTOK_CLIENT_SECRET ולעשות Redeploy.</p>');
  }
  const q = req.query || {};

  if (!q.code && !q.error) {
    const nonce = crypto.randomBytes(12).toString('hex');
    const state = nonce + '.' + sign(nonce);
    const url = 'https://www.tiktok.com/v2/auth/authorize/?' + new URLSearchParams({
      client_key: key, scope: SCOPES, response_type: 'code', redirect_uri: REDIRECT, state,
    });
    res.setHeader('Location', url);
    return res.status(302).end();
  }
  if (q.error) {
    return page(res, 400, 'החיבור לטיקטוק בוטל', `<p>${esc(q.error_description || q.error)}</p>`);
  }
  const [nonce, sig] = String(q.state || '').split('.');
  if (!nonce || sig !== sign(nonce)) {
    return page(res, 400, 'קישור לא תקין', '<p>פתחו שוב את הכתובת /api/tiktok-auth והתחילו מההתחלה.</p>');
  }

  try {
    const r = await fetch('https://open.tiktokapis.com/v2/oauth/token/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_key: key, client_secret: secret, code: String(q.code),
        grant_type: 'authorization_code', redirect_uri: REDIRECT,
      }),
    });
    const t = await r.json();
    if (!t.refresh_token) {
      return page(res, 502, 'טיקטוק לא החזירה טוקן', `<p>${esc(t.error_description || t.error || r.status)}</p>`);
    }
    const days = Math.round((t.refresh_expires_in || 0) / 86400);
    return page(res, 200, 'טיקטוק מחובר ✓', `
<p>הרשאות שאושרו: <b dir="ltr">${esc(t.scope)}</b></p>
<p>העתיקו את הטוקן הזה ל-GitHub ← Settings ← Secrets and variables ← Actions ← <b>TIKTOK_REFRESH_TOKEN</b>.
הוא מוצג פעם אחת בלבד ותקף כ-${days} ימים. לא לשלוח אותו בצ'אט או במייל.</p>
<textarea id="t" readonly>${esc(t.refresh_token)}</textarea>
<button onclick="navigator.clipboard.writeText(document.getElementById('t').value);this.textContent='הועתק'">העתקה</button>`);
  } catch (err) {
    console.error('tiktok-auth', err && err.message);
    return page(res, 500, 'שגיאה', '<p>משהו נכשל בחיבור. נסו שוב בעוד דקה.</p>');
  }
};
