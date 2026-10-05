// Vercel serverless function: Telegram bot webhook.
// Handles the "📧 שלח שוב קישור במייל" button under each lead message.
// The lead's name/phone/email are read back from the lead message itself,
// so nothing has to be stored anywhere.
//
// One-time setup (after BARUR_SECRET, TELEGRAM_BOT_TOKEN are set in Vercel):
//   open https://barur-mashkanta.co.il/api/telegram-webhook?setup=<BARUR_SECRET>
//   in the browser once. It registers this URL with Telegram.

const { sendPreciseEmail } = require('./_mail');

const SITE = 'https://barur-mashkanta.co.il';

async function tg(method, body) {
  const r = await fetch(`https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return r.json().catch(() => ({}));
}

function field(text, label) {
  const m = String(text || '').match(new RegExp('^' + label + ':\\s*(.+)$', 'm'));
  return m ? m[1].trim() : '';
}

module.exports = async (req, res) => {
  const secret = process.env.BARUR_SECRET;
  const botToken = process.env.TELEGRAM_BOT_TOKEN;
  if (!secret || !botToken) return res.status(500).json({ error: 'server_not_configured' });

  // One-time registration from the browser.
  if (req.method === 'GET') {
    if (req.query && req.query.setup === secret) {
      const out = await tg('setWebhook', {
        url: `${SITE}/api/telegram-webhook`,
        secret_token: secret.replace(/[^A-Za-z0-9_-]/g, '').slice(0, 256),
        allowed_updates: ['callback_query'],
      });
      return res.status(200).json({ webhook: out.ok ? 'registered' : 'failed', description: out.description || '' });
    }
    return res.status(404).end();
  }
  if (req.method !== 'POST') return res.status(405).end();

  // Only Telegram knows the secret header.
  const expected = secret.replace(/[^A-Za-z0-9_-]/g, '').slice(0, 256);
  if (req.headers['x-telegram-bot-api-secret-token'] !== expected) return res.status(401).end();

  let update = req.body;
  if (typeof update === 'string') { try { update = JSON.parse(update); } catch (e) { update = {}; } }
  const cq = update && update.callback_query;
  if (!cq || cq.data !== 'mail' || !cq.message) return res.status(200).json({ ok: true });

  // Only from the lead chat itself.
  if (String(cq.message.chat && cq.message.chat.id) !== String(process.env.TELEGRAM_CHAT_ID)) {
    await tg('answerCallbackQuery', { callback_query_id: cq.id, text: 'לא מורשה' });
    return res.status(200).json({ ok: true });
  }

  const text = cq.message.text || '';
  const lead = { name: field(text, 'שם'), phone: field(text, 'טלפון'), email: field(text, 'אימייל') };
  if (!lead.email) {
    await tg('answerCallbackQuery', { callback_query_id: cq.id, text: 'אין מייל בליד הזה' });
    return res.status(200).json({ ok: true });
  }

  const r = await sendPreciseEmail(lead);
  await tg('answerCallbackQuery', { callback_query_id: cq.id, text: r.ok ? 'נשלח' : 'לא נשלח' });
  await tg('sendMessage', {
    chat_id: cq.message.chat.id,
    reply_to_message_id: cq.message.message_id,
    text: r.ok ? `📧 נשלח שוב מייל עם קישור ל-${lead.email}` : `⚠️ המייל ל-${lead.email} לא נשלח (${r.reason})`,
  });
  return res.status(200).json({ ok: true });
};
