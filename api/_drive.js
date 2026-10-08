// Saves uploaded balance reports to Google Drive, one folder per lead, via a
// Google Apps Script web app that runs as the business Google account
// (source: scripts/drive-leads.gs). Environment variables (Vercel):
//   DRIVE_SCRIPT_URL  the Apps Script web app URL (…/exec)
//   DRIVE_SECRET      the secret printed by setup() in the script
// If either is missing, everything here is skipped silently. Never throws.

const crypto = require('crypto');

function configured() {
  return !!(process.env.DRIVE_SCRIPT_URL && process.env.DRIVE_SECRET);
}

async function call(payload, ms) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ms);
  try {
    const r = await fetch(process.env.DRIVE_SCRIPT_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: JSON.stringify({ ...payload, secret: process.env.DRIVE_SECRET }),
      redirect: 'follow',
      signal: ctrl.signal,
    });
    const out = await r.json();
    if (!out.ok) console.error('drive', payload.action, out.error);
    return out.ok ? out : null;
  } catch (err) {
    console.error('drive', payload.action, err && err.message);
    return null;
  } finally {
    clearTimeout(timer);
  }
}

// The browser only ever holds a signed reference, so nobody can attach
// someone else's file to their own lead.
function sign(id) {
  return crypto.createHmac('sha256', 'drive-ref:' + process.env.DRIVE_SECRET).update(id).digest('hex').slice(0, 24);
}
function readRef(ref) {
  const [id, sig] = String(ref || '').split('.');
  if (!id || !sig || !configured()) return null;
  const good = sign(id);
  return sig.length === good.length && crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(good)) ? id : null;
}

// Step 1 (extract-report): park the file in the staging folder.
async function stageReport(data, mimeType) {
  if (!configured()) return null;
  const out = await call({ action: 'stage', data, mimeType }, 8000);
  return out && out.fileId ? `${out.fileId}.${sign(out.fileId)}` : null;
}

// Step 2 (send-lead): lead folder by phone, move the file in, save the message.
async function fileLead({ ref, name, phone, text }) {
  if (!configured()) return null;
  const fileId = readRef(ref);
  if (!fileId) return null;
  const out = await call({ action: 'file', fileId, name, phone, text }, 8000);
  return out ? out.folderUrl : null;
}

module.exports = { stageReport, fileLead };
