// Vercel serverless function.
// Receives a lead submitted from check.html and forwards it to a Telegram
// chat via the Bot API. The bot token and chat id live only here, as
// environment variables (Project Settings -> Environment Variables):
//   TELEGRAM_BOT_TOKEN
//   TELEGRAM_CHAT_ID
//   META_CAPI_TOKEN        (optional) Conversions API access token
//   META_TEST_EVENT_CODE   (optional) only while testing in Events Manager
// They are never sent to, or readable from, the browser.

const crypto = require('crypto');
const { readToken, uploadLink, sendPreciseEmail } = require('./_mail');
const { mixLines } = require('./_mixes');
const { fileLead } = require('./_drive');
const META_PIXEL_ID = '1776166563647834';
const META_API_VERSION = 'v21.0';

function sha256(v) {
  return crypto.createHash('sha256').update(v).digest('hex');
}

// Israeli phone to E.164 digits without '+': 0501234567 -> 972501234567
function normPhone(phone) {
  const d = String(phone || '').replace(/\D/g, '');
  if (!d) return '';
  if (d.startsWith('972')) return d;
  if (d.startsWith('0')) return '972' + d.slice(1);
  return d;
}

// Server-side Lead event for Meta (Conversions API). Shares event_id with the
// browser Pixel event so Meta counts the lead once. Skipped entirely when the
// visitor declined cookies, or when the token isn't configured. Never throws.
async function sendMetaLead(req, lead, phone, email) {
  const capiToken = process.env.META_CAPI_TOKEN;
  // Cold leads (no savings right now) and report updates are not counted as
  // Meta leads, so the ads optimise for people who actually have a gap.
  if (!capiToken || lead.cookieConsent === 'declined' || lead.leadType === 'cold' || lead.reportUpdate || lead.emailUpdate) return;
  const fwd = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim();
  const userData = {
    ph: [sha256(normPhone(phone))],
    client_user_agent: String(req.headers['user-agent'] || ''),
  };
  if (email) userData.em = [sha256(email.trim().toLowerCase())];
  if (fwd) userData.client_ip_address = fwd;
  if (lead.fbp) userData.fbp = String(lead.fbp);
  if (lead.fbc) userData.fbc = String(lead.fbc);
  const payload = {
    data: [{
      event_name: 'Lead',
      event_time: Math.floor(Date.now() / 1000),
      event_id: lead.eventId ? String(lead.eventId) : undefined,
      action_source: 'website',
      event_source_url: lead.pageUrl ? String(lead.pageUrl) : 'https://barur-mashkanta.co.il/check',
      user_data: userData,
      custom_data: { content_name: 'refinance_check' },
    }],
  };
  if (process.env.META_TEST_EVENT_CODE) payload.test_event_code = process.env.META_TEST_EVENT_CODE;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 4000);
  try {
    const r = await fetch(`https://graph.facebook.com/${META_API_VERSION}/${META_PIXEL_ID}/events?access_token=${encodeURIComponent(capiToken)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: ctrl.signal,
    });
    if (!r.ok) console.error('Meta CAPI failed', r.status, await r.text());
  } catch (err) {
    console.error('Meta CAPI error', err && err.message);
  } finally {
    clearTimeout(timer);
  }
}

function ils(n) {
  if (typeof n !== 'number' || !isFinite(n)) return '—';
  return '₪' + Math.round(n).toLocaleString('he-IL');
}

// TEMPORARY debug block — includes the raw extracted tracks and the computed
// savings scenarios in the Telegram message, so we can QA the extraction
// pipeline against the real bank document without asking the customer for
// anything. Remove once we trust the extraction (see check.html for context).
function debugLines(lead) {
  const out = [];
  if (Array.isArray(lead.tracks) && lead.tracks.length) {
    out.push('', '🔍 נתונים גולמיים שחולצו (מסלולים):');
    lead.tracks.forEach((t, i) => {
      const origin = (t.originRate != null && t.originRate !== t.rate) ? ` (מקורית בעת מתן ההלוואה: ${t.originRate}%)` : '';
      out.push(`  ${i + 1}. ${t.name || '—'} | יתרה: ${ils(t.balance)} | ריבית נוכחית: ${t.rate ?? '—'}%${origin} | תקופה: ${t.term ? Math.round(t.term / 12) + ' שנה' : '—'}`);
    });
  }
  const sc = lead.scenarios;
  if (sc) {
    out.push('', '🔍 תרחישי חיסכון שחושבו:');
    out.push(`  עלות כוללת היום: ${ils(sc.currentTotal)}`);
    const scenarioLabel = { payment: 'מינימום החזר חודשי', total: 'מינימום עלות כוללת', both: 'גם וגם' };
    ['payment', 'total', 'both'].forEach((key) => {
      const s = sc[key];
      if (!s) { out.push(`  ${scenarioLabel[key]}: לא רלוונטי / ללא הבדל משמעותי`); return; }
      const rec = sc.bestKey === key ? ' ⭐ הכי משתלם' : '';
      out.push(`  ${scenarioLabel[key]}${rec}: החזר חדש ${ils(s.newPayment)} | עלות כוללת חדשה ${ils(s.newTotal)} | חיסכון ${ils(s.totalSavings)}`);
    });
  }
  return out;
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    return res.status(204).end();
  }
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'method_not_allowed' });
  }

  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) {
    return res.status(500).json({ error: 'server_not_configured' });
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { body = null; }
  }
  const lead = body || {};

  // A report uploaded from a personal email link carries a signed token:
  // trust the name/phone/email in it over whatever the browser sent.
  const fromLink = lead.u ? readToken(lead.u) : null;
  if (fromLink) { lead.name = fromLink.name; lead.phone = fromLink.phone; lead.email = lead.email || fromLink.email; }

  const name = String(lead.name || '').trim();
  // Accept +972 / spaces / dashes from autofill; store as 05XXXXXXXX.
  let phone = String(lead.phone || '').replace(/\D/g, '');
  if (phone.startsWith('972')) phone = '0' + phone.slice(3);
  if (phone.length === 9 && phone[0] !== '0') phone = '0' + phone;
  const email = String(lead.email || '').trim();

  if (!name || !phone) {
    return res.status(400).json({ error: 'missing_required_fields' });
  }
  // Basic server-side validation, mirrors the client-side checks.
  const phoneDigits = phone.replace(/\D/g, '');
  if (!/^0\d{8,9}$/.test(phoneDigits)) {
    return res.status(400).json({ error: 'invalid_phone' });
  }
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
    return res.status(400).json({ error: 'invalid_email' });
  }

  const prefLabel = { payment: 'הקטנת החזר חודשי', total: 'הקטנת עלות כוללת', both: 'גם וגם' }[lead.pref] || lead.pref || '—';
  const source = lead.source === 'upload' ? 'העלאת דוח' : 'שאלון ידני';

  const header = lead.emailUpdate ? '📧 עדכון ליד: נוסף מייל לשליחת קישור — ברור משכנתאות'
    : lead.reportUpdate ? '📄 עדכון ליד: הועלה דוח יתרות — ברור משכנתאות'
    : lead.leadType === 'cold' ? '⏳ ליד למעקב: לפי הנתונים שהזין אין כרגע פער (ביקש עדכון) — ברור משכנתאות'
    : '📩 ליד חדש — ברור משכנתאות';
  const teaser = lead.teaser && lead.leadType !== 'cold'
    ? `טעימה שהוצגה: ${ils(lead.teaser.lo)}–${ils(lead.teaser.hi)} בחודש` : null;
  const lines = [
    header,
    `שם: ${name}`,
    `טלפון: ${phone}`,
    email ? `אימייל: ${email}` : null,
    `מקור: ${source}`,
    lead.variant ? `דף: ${lead.variant}` : null,
    lead.estimatedRate ? `ריבית משוערת היום: ${Number(lead.estimatedRate).toFixed(2)}%` : null,
    teaser,
    lead.variant ? null : `העדפה: ${prefLabel}`,
    `יתרת משכנתא: ${ils(lead.balance)}`,
    `החזר חודשי נוכחי: ${ils(lead.payment)}`,
    lead.years ? `שנים שנותרו: ${lead.years}` : null,
    ...debugLines(lead),
    // Internal: best 3-equal-track mixes per goal. Telegram only, never shown to the customer.
    ...(lead.emailUpdate ? [] : mixLines(lead)),
  ].filter(Boolean);

  // Email with the personal upload link: automatically for every lead that
  // has a gap (not cold), and when an email is added from the results page.
  const isCold = lead.leadType === 'cold';
  // Everyone with an email gets the precise-check link, including leads whose
  // rough numbers showed no gap: the real report may tell a different story.
  const wantsEmail = email && !lead.reportUpdate;
  const link = !lead.reportUpdate ? uploadLink({ name, phone, email }) : null;

  // Runs in parallel with Telegram; its outcome never affects the response.
  const metaPromise = sendMetaLead(req, lead, phone, email);
  const mail = wantsEmail ? await sendPreciseEmail({ name, phone, email }) : null;
  if (lead.reportUpdate) lines.push(fromLink ? '✔️ הגיע מקישור אישי (מאומת)' : 'הגיע מאותו ביקור באתר');
  if (mail) lines.push(mail.ok ? `📧 נשלח מייל עם קישור ל-${email}` : `⚠️ המייל לא נשלח (${mail.reason})`);
  if (link) lines.push('', 'קישור אישי להעלאת דוח (אפשר לשלוח גם בווטסאפ):', link);
  // Uploaded report -> its own Drive folder, with a copy of this message.
  if (lead.reportFile) {
    const folderUrl = await fileLead({ ref: lead.reportFile, name, phone, text: lines.join('\n') });
    lines.push('', folderUrl ? `📁 הדוח נשמר בדרייב:\n${folderUrl}` : '⚠️ הדוח לא נשמר בדרייב');
  }
  const replyMarkup = email && !lead.reportUpdate
    ? { inline_keyboard: [[{ text: '📧 שלח שוב קישור במייל', callback_data: 'mail' }]] } : undefined;

  try {
    const tgRes = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text: lines.join('\n'), reply_markup: replyMarkup, disable_web_page_preview: true }),
    });
    if (!tgRes.ok) {
      const errText = await tgRes.text();
      console.error('Telegram send failed', tgRes.status, errText);
      await metaPromise;
      return res.status(502).json({ error: 'telegram_send_failed' });
    }
    await metaPromise;
    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error('send-lead failed', err);
    return res.status(500).json({ error: 'internal_error' });
  }
};
