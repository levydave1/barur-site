// Shared helpers: signed personal upload links + the "precise check" email.
// Files starting with "_" are not exposed as Vercel routes.
//
// Environment variables (Vercel -> Project Settings -> Environment Variables):
//   GMAIL_USER          the Gmail address the email is sent from
//   GMAIL_APP_PASSWORD  a Google "app password" for that account (not the normal password)
//   BARUR_SECRET        a long random string; encrypts the personal links and
//                       protects the Telegram webhook
// None of these ever reach the browser.

const crypto = require('crypto');

const SITE = 'https://barur-mashkanta.co.il';
const LINK_DAYS = 30;

function b64url(buf) {
  return Buffer.from(buf).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function fromB64url(s) {
  return Buffer.from(String(s).replace(/-/g, '+').replace(/_/g, '/'), 'base64');
}
function key() {
  return crypto.createHash('sha256').update('barur-link:' + (process.env.BARUR_SECRET || '')).digest();
}

// Personal link token: name + phone + email, ENCRYPTED (AES-256-GCM) so no
// personal details are readable in the URL, logs or analytics. Valid LINK_DAYS.
function makeToken({ name, phone, email }) {
  if (!process.env.BARUR_SECRET) return null;
  const iv = crypto.randomBytes(12);
  const c = crypto.createCipheriv('aes-256-gcm', key(), iv);
  const body = Buffer.concat([c.update(JSON.stringify({ n: name || '', p: phone || '', e: email || '', t: Date.now() }), 'utf8'), c.final()]);
  return b64url(Buffer.concat([iv, c.getAuthTag(), body]));
}
function readToken(token) {
  if (!token || !process.env.BARUR_SECRET) return null;
  try {
    const raw = fromB64url(token);
    if (raw.length < 29) return null;
    const d = crypto.createDecipheriv('aes-256-gcm', key(), raw.subarray(0, 12));
    d.setAuthTag(raw.subarray(12, 28));
    const json = Buffer.concat([d.update(raw.subarray(28)), d.final()]).toString('utf8');
    const o = JSON.parse(json);
    if (!o.t || Date.now() - o.t > LINK_DAYS * 864e5) return null;
    return { name: o.n, phone: o.p, email: o.e };
  } catch (e) { return null; }
}
function uploadLink(lead) {
  const t = makeToken(lead);
  return t ? `${SITE}/checkad?u=${t}` : null;
}

function esc(s) {
  return String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function preciseEmail(name, link) {
  const first = String(name || '').trim().split(/\s+/)[0] || '';
  const hello = first ? `שלום ${first},` : 'שלום,';
  const subject = 'הקישור לבדיקה המדויקת שלכם – ברור משכנתאות';
  const text = [
    hello,
    '',
    'תודה שבדקתם את המשכנתה אצלנו.',
    'ההערכה שקיבלתם מבוססת על ממוצעים. כדי לקבל מספר מדויק, העלו את דוח היתרות לסילוק מהבנק (PDF או צילום מסך).',
    'הבדיקה קוראת את הדוח לבד ומתעדכנת לפי המסלולים והריביות האמיתיים שלכם.',
    '',
    'להעלאת הדוח:',
    link,
    '',
    'לא בטוחים איך מוציאים את הדוח? בעמוד יש הוראות לפי בנק.',
    `הקישור אישי ותקף ל-${LINK_DAYS} יום.`,
    '',
    'אם לא משתלם, נגיד.',
    'ברור משכנתאות',
    SITE,
  ].join('\n');
  const html = `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body style="margin:0;background:#F5F3EE;font-family:Arial,Helvetica,sans-serif;color:#0F2A47">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F5F3EE"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#ffffff;border-radius:14px" dir="rtl">
<tr><td style="background:#0F2A47;border-radius:14px 14px 0 0;padding:18px 24px;color:#ffffff;font-size:18px;font-weight:bold;text-align:right">ברור משכנתאות</td></tr>
<tr><td style="padding:24px;text-align:right;font-size:16px;line-height:1.6">
<p style="margin:0 0 14px">${esc(hello)}</p>
<p style="margin:0 0 14px">תודה שבדקתם את המשכנתה אצלנו. ההערכה שקיבלתם מבוססת על ממוצעים. כדי לקבל <b>מספר מדויק</b>, העלו את דוח היתרות לסילוק מהבנק (PDF או צילום מסך).</p>
<p style="margin:0 0 22px">הבדיקה קוראת את הדוח לבד ומתעדכנת לפי המסלולים והריביות האמיתיים שלכם.</p>
<p style="margin:0 0 22px;text-align:center"><a href="${esc(link)}" style="display:inline-block;background:#0C7268;color:#ffffff;text-decoration:none;font-weight:bold;font-size:17px;padding:14px 28px;border-radius:10px">להעלאת דוח היתרות</a></p>
<p style="margin:0 0 6px;font-size:14px;color:#5E6875">לא בטוחים איך מוציאים את הדוח? בעמוד יש הוראות לפי בנק.</p>
<p style="margin:0 0 18px;font-size:14px;color:#5E6875">הקישור אישי ותקף ל-${LINK_DAYS} יום.</p>
<p style="margin:0;font-weight:bold">אם לא משתלם, נגיד.</p>
</td></tr>
<tr><td style="padding:14px 24px 20px;text-align:right;font-size:12px;color:#5E6875;border-top:1px solid #DCD8CF">ברור משכנתאות · <a href="${SITE}" style="color:#0C7268">barur-mashkanta.co.il</a></td></tr>
</table></td></tr></table></body></html>`;
  return { subject, text, html };
}

let _transport = null;
function transport() {
  if (_transport) return _transport;
  const nodemailer = require('nodemailer');
  _transport = process.env.MAIL_TEST_JSON
    ? nodemailer.createTransport({ jsonTransport: true })
    : nodemailer.createTransport({
        service: 'gmail',
        auth: { user: process.env.GMAIL_USER, pass: process.env.GMAIL_APP_PASSWORD },
      });
  return _transport;
}

// Returns { ok: true } or { ok: false, reason }. Never throws.
async function sendPreciseEmail(lead) {
  const email = String(lead.email || '').trim();
  if (!email) return { ok: false, reason: 'no_email' };
  if (!process.env.MAIL_TEST_JSON && (!process.env.GMAIL_USER || !process.env.GMAIL_APP_PASSWORD)) return { ok: false, reason: 'mail_not_configured' };
  const link = uploadLink(lead);
  if (!link) return { ok: false, reason: 'secret_not_configured' };
  const { subject, text, html } = preciseEmail(lead.name, link);
  try {
    const info = await Promise.race([
      transport().sendMail({
        from: { name: 'ברור משכנתאות', address: process.env.GMAIL_USER || 'test@example.com' },
        to: email,
        subject, text, html,
      }),
      new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 7000)),
    ]);
    return { ok: true, info };
  } catch (e) {
    console.error('email failed', e && e.message);
    return { ok: false, reason: (e && e.message) || 'send_failed' };
  }
}

module.exports = { makeToken, readToken, uploadLink, sendPreciseEmail, preciseEmail };
