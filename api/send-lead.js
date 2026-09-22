// Vercel serverless function.
// Receives a lead submitted from check.html and forwards it to a Telegram
// chat via the Bot API. The bot token and chat id live only here, as
// environment variables (Project Settings -> Environment Variables):
//   TELEGRAM_BOT_TOKEN
//   TELEGRAM_CHAT_ID
// They are never sent to, or readable from, the browser.

function ils(n) {
  if (typeof n !== 'number' || !isFinite(n)) return '—';
  return '₪' + Math.round(n).toLocaleString('he-IL');
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

  const name = String(lead.name || '').trim();
  const phone = String(lead.phone || '').trim();
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

  const lines = [
    '📩 ליד חדש — ברור משכנתאות',
    `שם: ${name}`,
    `טלפון: ${phone}`,
    email ? `אימייל: ${email}` : null,
    `מקור: ${source}`,
    `העדפה: ${prefLabel}`,
    `יתרת משכנתא: ${ils(lead.balance)}`,
    `החזר חודשי נוכחי: ${ils(lead.payment)}`,
    lead.years ? `שנים שנותרו: ${lead.years}` : null,
  ].filter(Boolean);

  try {
    const tgRes = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text: lines.join('\n') }),
    });
    if (!tgRes.ok) {
      const errText = await tgRes.text();
      console.error('Telegram send failed', tgRes.status, errText);
      return res.status(502).json({ error: 'telegram_send_failed' });
    }
    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error('send-lead failed', err);
    return res.status(500).json({ error: 'internal_error' });
  }
};

