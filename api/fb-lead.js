// Meta instant-form leads -> Telegram.
//
// Meta calls this URL (a "Page" webhook, field "leadgen") every time someone
// submits the instant form. We verify the signature, fetch the lead's answers
// from the Graph API, and send them to the same Telegram chat as the site leads.
//
// Environment variables (Vercel -> Project Settings -> Environment Variables):
//   FB_APP_SECRET    the Meta app's App Secret (App settings -> Basic)
//   FB_VERIFY_TOKEN  any long random string you choose; the same string goes
//                    into the webhook setup in the Meta app
//   FB_ACCESS_TOKEN  a never-expiring System User token with access to the Page
//   FB_PAGE_ID       optional, defaults to 1311897388675254 (ברור משכנתאות)
//   TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID  already set for send-lead.js
//
// One-time setup call (subscribes the Page to this app's leadgen webhook):
//   https://barur-mashkanta.co.il/api/fb-lead?setup=1&key=<FB_VERIFY_TOKEN>
// Status check (no secrets shown):
//   https://barur-mashkanta.co.il/api/fb-lead?status=1&key=<FB_VERIFY_TOKEN>

const crypto = require('crypto');

const GRAPH = 'https://graph.facebook.com/v21.0';
const PAGE_ID = process.env.FB_PAGE_ID || '1311897388675254';

const LABELS = {
  full_name: 'שם',
  first_name: 'שם פרטי',
  last_name: 'שם משפחה',
  phone_number: 'טלפון',
  email: 'אימייל',
  city: 'עיר',
};

// Prefer the untouched request stream. If the platform already consumed it,
// fall back to whatever body it parsed (Meta sends compact JSON, so
// re-serialising gives the same bytes for leadgen payloads).
function readRaw(req) {
  return new Promise((resolve) => {
    if (req.readableEnded || req.complete && !req.readable) return resolve(fallbackBody(req));
    const chunks = [];
    const done = () => resolve(chunks.length ? Buffer.concat(chunks) : fallbackBody(req));
    const timer = setTimeout(done, 3000);
    req.on('data', (c) => chunks.push(Buffer.isBuffer(c) ? c : Buffer.from(c)));
    req.on('end', () => { clearTimeout(timer); done(); });
    req.on('error', () => { clearTimeout(timer); done(); });
  });
}

function fallbackBody(req) {
  const b = req.body;
  if (Buffer.isBuffer(b)) return b;
  if (typeof b === 'string') return Buffer.from(b);
  if (b && typeof b === 'object') return Buffer.from(JSON.stringify(b));
  return Buffer.alloc(0);
}

function validSignature(raw, header, secret) {
  if (!header || !secret || !header.startsWith('sha256=')) return false;
  const expected = 'sha256=' + crypto.createHmac('sha256', secret).update(raw).digest('hex');
  const a = Buffer.from(header);
  const b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function keyOk(q) {
  const k = process.env.FB_VERIFY_TOKEN;
  return !!k && q.key === k;
}

async function graph(path, token, init) {
  const sep = path.includes('?') ? '&' : '?';
  const r = await fetch(`${GRAPH}/${path}${sep}access_token=${encodeURIComponent(token)}`, init);
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.error) {
    const msg = (j.error && (j.error.message || j.error.type)) || `http_${r.status}`;
    throw new Error(msg);
  }
  return j;
}

// The System User token can read leads directly, but some setups need a Page
// token. Ask for the Page token first and fall back to the System User token.
let pageTokenCache = null;
async function pageToken() {
  const base = process.env.FB_ACCESS_TOKEN;
  if (!base) throw new Error('FB_ACCESS_TOKEN missing');
  if (pageTokenCache) return pageTokenCache;
  try {
    const j = await graph(`${PAGE_ID}?fields=access_token`, base);
    pageTokenCache = j.access_token || base;
  } catch (e) {
    pageTokenCache = base;
  }
  return pageTokenCache;
}

function prettyValue(v) {
  return String(v || '').replace(/_/g, ' ').trim();
}

function prettyKey(k) {
  if (LABELS[k]) return LABELS[k];
  return String(k).replace(/_/g, ' ').replace(/\?$/, '').trim() + '?';
}

function ilTime(iso) {
  const d = iso ? new Date(iso) : new Date();
  return d.toLocaleString('he-IL', {
    timeZone: 'Asia/Jerusalem', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
  });
}

function localPhone(p) {
  const s = String(p || '').replace(/[^\d+]/g, '');
  if (s.startsWith('+972')) return '0' + s.slice(4);
  if (s.startsWith('972')) return '0' + s.slice(3);
  return s || p;
}

async function telegram(text) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) throw new Error('telegram_not_configured');
  const r = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text, disable_web_page_preview: true }),
  });
  if (!r.ok) throw new Error('telegram_' + r.status + ' ' + (await r.text()).slice(0, 200));
}

async function handleLead(change) {
  const v = change.value || {};
  const leadId = v.leadgen_id;
  const lines = ['📋 ליד חדש מטופס פייסבוק — ברור משכנתאות', ''];
  try {
    const tok = await pageToken();
    const lead = await graph(
      `${leadId}?fields=created_time,field_data,ad_name,adset_name,campaign_name,form_id,platform,is_organic`,
      tok,
    );
    const fields = Array.isArray(lead.field_data) ? lead.field_data : [];
    const contact = [];
    const answers = [];
    for (const f of fields) {
      const val = (f.values || []).map(prettyValue).join(', ');
      if (f.name === 'phone_number') contact.push(`טלפון: ${localPhone(f.values && f.values[0])}`);
      else if (LABELS[f.name]) contact.push(`${LABELS[f.name]}: ${val}`);
      else answers.push(`• ${prettyKey(f.name)} ${val}`);
    }
    lines.push(...contact);
    if (answers.length) lines.push('', ...answers);
    lines.push('');
    lines.push(`שעה: ${ilTime(lead.created_time)}`);
    if (lead.ad_name) lines.push(`מודעה: ${lead.ad_name}`);
    if (lead.platform) lines.push(`פלטפורמה: ${lead.platform === 'ig' ? 'אינסטגרם' : lead.platform === 'fb' ? 'פייסבוק' : lead.platform}`);
    if (lead.is_organic) lines.push('אורגני (לא ממודעה)');
    lines.push('', 'אם הלקוח עשה גם בדיקה באתר, תגיע הודעה "🔗 בדיקה מהאתר" עם שעה קרובה.');
  } catch (e) {
    console.error('lead fetch failed', leadId, e.message);
    lines.push(
      '⚠️ נכנס ליד, אבל לא הצלחתי למשוך את הפרטים ממטא.',
      `סיבה: ${e.message}`,
      `שעה: ${ilTime(v.created_time ? new Date(v.created_time * 1000).toISOString() : null)}`,
      'הפרטים נמצאים ב-Leads Center:',
      'https://business.facebook.com/latest/leads_center',
    );
  }
  await telegram(lines.join('\n'));
}

module.exports = async (req, res) => {
  const q = req.query || {};

  if (req.method === 'GET') {
    // Meta webhook verification
    if (q['hub.mode'] === 'subscribe') {
      if (q['hub.verify_token'] && q['hub.verify_token'] === process.env.FB_VERIFY_TOKEN) {
        res.setHeader('Content-Type', 'text/plain');
        return res.status(200).send(String(q['hub.challenge'] || ''));
      }
      return res.status(403).send('forbidden');
    }

    // One-time: subscribe the Page to this app's leadgen events
    if (q.setup && keyOk(q)) {
      try {
        const tok = await pageToken();
        const sub = await graph(`${PAGE_ID}/subscribed_apps?subscribed_fields=leadgen`, tok, { method: 'POST' });
        const list = await graph(`${PAGE_ID}/subscribed_apps`, tok);
        return res.status(200).json({ subscribed: sub, apps: (list.data || []).map((a) => ({ name: a.name, fields: a.subscribed_fields })) });
      } catch (e) {
        return res.status(500).json({ error: e.message });
      }
    }

    // Health check, no secrets
    if (q.status && keyOk(q)) {
      const out = {
        app_secret: !!process.env.FB_APP_SECRET,
        verify_token: !!process.env.FB_VERIFY_TOKEN,
        access_token: !!process.env.FB_ACCESS_TOKEN,
        telegram: !!(process.env.TELEGRAM_BOT_TOKEN && process.env.TELEGRAM_CHAT_ID),
      };
      try {
        const tok = await pageToken();
        const list = await graph(`${PAGE_ID}/subscribed_apps`, tok);
        out.page_subscriptions = (list.data || []).map((a) => ({ name: a.name, fields: a.subscribed_fields }));
      } catch (e) {
        out.page_error = e.message;
      }
      return res.status(200).json(out);
    }

    return res.status(404).send('not found');
  }

  if (req.method !== 'POST') return res.status(405).send('method not allowed');

  const raw = await readRaw(req);
  if (!validSignature(raw, req.headers['x-hub-signature-256'], process.env.FB_APP_SECRET)) {
    console.error('fb-lead: bad signature');
    return res.status(401).send('bad signature');
  }

  let body;
  try { body = JSON.parse(raw.toString('utf8')); } catch (e) { return res.status(400).send('bad json'); }

  const jobs = [];
  for (const entry of body.entry || []) {
    for (const change of entry.changes || []) {
      if (change.field === 'leadgen') jobs.push(handleLead(change));
    }
  }
  const results = await Promise.allSettled(jobs);
  results.filter((r) => r.status === 'rejected').forEach((r) => console.error('fb-lead job failed', r.reason && r.reason.message));
  // Always 200 so Meta does not retry and flood the chat with duplicates.
  return res.status(200).send('ok');
};

// Raw body is needed to check Meta's signature.
module.exports.config = { api: { bodyParser: false } };
