/**
 * ברור משכנתאות — שמירת דוחות יתרות בגוגל דרייב, תיקייה לכל ליד.
 *
 * רץ כ-Google Apps Script בחשבון הגוגל של העסק ("Execute as: Me"), כך שהקבצים
 * נשמרים בדרייב שלכם בתוך התיקייה "לידים". האתר (Vercel) קורא לו עם סוד משותף.
 *
 * התקנה חד-פעמית: ראו docs/drive-leads-setup.md
 */

const LEADS_FOLDER_ID = '1sGAOEeK7IixEmnel77KHGpqaNHKoDZDX'; // ברור משכנתאות / לידים
const STAGING_NAME = '_ממתינים לשיוך';   // דוחות שהועלו לפני שהושארו פרטים
const STAGING_HOURS = 48;                // דוח שלא שויך לליד נמחק (לאשפה) אחרי 48 שעות

// הרצה ידנית פעם אחת: יוצר סוד, יוצר את תיקיית ההמתנה ומתזמן ניקוי יומי.
function setup() {
  const props = PropertiesService.getScriptProperties();
  let secret = props.getProperty('DRIVE_SECRET');
  if (!secret) {
    secret = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
    props.setProperty('DRIVE_SECRET', secret);
  }
  staging_();
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'cleanStaging')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('cleanStaging').timeBased().everyDays(1).atHour(4).create();
  Logger.log('העתיקו את הערך הזה ל-Vercel כמשתנה DRIVE_SECRET:\n' + secret);
}

function doPost(e) {
  try {
    const req = JSON.parse(e.postData.contents);
    const secret = PropertiesService.getScriptProperties().getProperty('DRIVE_SECRET');
    if (!secret || req.secret !== secret) return json_({ ok: false, error: 'unauthorized' });
    if (req.action === 'stage') return json_(stage_(req));
    if (req.action === 'file') return json_(fileLead_(req));
    return json_({ ok: false, error: 'unknown_action' });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}

// שלב 1: הדוח הועלה ונקרא בהצלחה — נשמר בתיקיית ההמתנה.
function stage_(req) {
  const ext = { 'application/pdf': 'pdf', 'image/png': 'png', 'image/jpeg': 'jpg' }[req.mimeType] || 'bin';
  const bytes = Utilities.base64Decode(req.data);
  const name = 'דוח יתרות ' + stamp_() + '.' + ext;
  const file = staging_().createFile(Utilities.newBlob(bytes, req.mimeType, name));
  return { ok: true, fileId: file.getId() };
}

// שלב 2: הליד נשלח — תיקייה לליד (לפי טלפון), הדוח עובר אליה ונשמרת הודעת הטלגרם.
function fileLead_(req) {
  const root = DriveApp.getFolderById(LEADS_FOLDER_ID);
  const phone = String(req.phone || '').replace(/\D/g, '');
  const folderName = (phone || 'ללא טלפון') + ' · ' + String(req.name || '').trim();
  let folder = null;
  if (phone) {
    const it = root.getFolders();
    while (it.hasNext()) {
      const f = it.next();
      if (f.getName().indexOf(phone + ' ') === 0) { folder = f; break; }
    }
  }
  if (!folder) folder = root.createFolder(folderName);

  if (req.fileId) {
    try {
      const file = DriveApp.getFileById(req.fileId);
      const parents = file.getParents();
      const inStaging = parents.hasNext() && parents.next().getName() === STAGING_NAME;
      if (inStaging) file.moveTo(folder);
    } catch (err) { /* הקובץ כבר נוקה או הועבר */ }
  }
  if (req.text) {
    folder.createFile('הודעת טלגרם ' + stamp_() + '.txt', req.text, MimeType.PLAIN_TEXT);
  }
  return { ok: true, folderUrl: folder.getUrl() };
}

// ניקוי יומי: דוח שאף אחד לא השאיר פרטים אחריו לא נשמר אצלנו.
function cleanStaging() {
  const cutoff = Date.now() - STAGING_HOURS * 3600 * 1000;
  const it = staging_().getFiles();
  while (it.hasNext()) {
    const f = it.next();
    if (f.getDateCreated().getTime() < cutoff) f.setTrashed(true);
  }
}

function staging_() {
  const root = DriveApp.getFolderById(LEADS_FOLDER_ID);
  const it = root.getFoldersByName(STAGING_NAME);
  return it.hasNext() ? it.next() : root.createFolder(STAGING_NAME);
}

function stamp_() {
  return Utilities.formatDate(new Date(), 'Asia/Jerusalem', 'yyyy-MM-dd HH-mm');
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
