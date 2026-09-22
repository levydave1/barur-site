// Vercel serverless function.
// Receives a base64-encoded balance-payoff report (PDF or image) and asks
// Gemini to extract structured mortgage data from it.
//
// Requires the environment variable GEMINI_API_KEY to be set in the Vercel
// project (Project Settings -> Environment Variables). Never hard-code the
// key here and never send it to the client.

const MODEL = 'gemini-3.5-flash-lite';

const EXTRACTION_PROMPT = `אתה מקבל דוח יתרות לסילוק של משכנתא מבנק ישראלי (PDF או תמונה סרוקה).
המשימה שלך: לחלץ מהדוח את הנתונים הבאים, ולהחזיר אך ורק JSON תקין במבנה הבא, בלי טקסט נוסף:

{
  "bankName": string | null,
  "payment": number | null,           // סך ההחזר החודשי הכולל של כל המסלולים, בשקלים
  "tracks": [
    {
      "name": string,                 // תיאור קצר של סוג המסלול, למשל "פריים", "קבועה לא צמודה", "קבועה צמודה", "משתנה כל 5 שנים"
      "balance": number,               // יתרה לסילוק של המסלול, בשקלים
      "rate": number,                  // ריבית שנתית של המסלול, באחוזים (למשל 4.35)
      "termMonths": number | null      // מספר החודשים שנותרו לסיום המסלול, אם מצוין או ניתן לחשב מתאריך הסיום
    }
  ],
  "confidence": "high" | "medium" | "low"   // כמה אתה בטוח בחילוץ הכולל
}

הנחיות:
- אם ערך כלשהו לא מופיע בדוח או לא ברור, שים null באותו שדה, אל תמציא מספרים.
- אם יש כמה מסלולים, תחזיר את כולם במערך tracks.
- termMonths: אם הדוח נותן תאריך סיום ולא מספר חודשים, חשב את ההפרש מהיום (${new Date().toISOString().slice(0, 10)}) בקירוב.
- אל תוסיף הסברים, הערות, או טקסט מחוץ ל-JSON.`;

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

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ error: 'server_not_configured', message: 'GEMINI_API_KEY is not set' });
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { body = null; }
  }
  const { data, mimeType } = body || {};
  if (!data || !mimeType) {
    return res.status(400).json({ error: 'missing_file' });
  }
  const allowedMime = ['application/pdf', 'image/png', 'image/jpeg'];
  if (!allowedMime.includes(mimeType)) {
    return res.status(400).json({ error: 'unsupported_file_type' });
  }
  // Rough size guard on the base64 payload (~ (bytes*4)/3). 15MB file cap.
  if (data.length > 20 * 1024 * 1024) {
    return res.status(413).json({ error: 'file_too_large' });
  }

  try {
    const geminiRes = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-goog-api-key': apiKey,
        },
        body: JSON.stringify({
          contents: [
            {
              parts: [
                { text: EXTRACTION_PROMPT },
                { inline_data: { mime_type: mimeType, data } },
              ],
            },
          ],
          generationConfig: {
            responseMimeType: 'application/json',
            temperature: 0.1,
          },
        }),
      }
    );

    if (!geminiRes.ok) {
      const errText = await geminiRes.text();
      console.error('Gemini API error', geminiRes.status, errText);
      return res.status(502).json({ error: 'extraction_failed' });
    }

    const geminiJson = await geminiRes.json();
    const text = geminiJson?.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!text) {
      return res.status(502).json({ error: 'empty_response' });
    }

    let parsed;
    try {
      parsed = JSON.parse(text);
    } catch (e) {
      console.error('Failed to parse Gemini JSON output', text);
      return res.status(502).json({ error: 'invalid_json_from_model' });
    }

    // Basic sanity checks before handing back to the client.
    if (!Array.isArray(parsed.tracks) || parsed.tracks.length === 0) {
      return res.status(422).json({ error: 'no_tracks_found' });
    }
    for (const t of parsed.tracks) {
      if (typeof t.balance !== 'number' || typeof t.rate !== 'number') {
        return res.status(422).json({ error: 'incomplete_track_data' });
      }
    }

    return res.status(200).json(parsed);
  } catch (err) {
    console.error('extract-report failed', err);
    return res.status(500).json({ error: 'internal_error' });
  }
};

