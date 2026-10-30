# עריכת סרטונים: דקה ברורה וסדרת המילניום

התבניות נשמרות כאן כדי שלא ילכו לאיבוד בין שיחות (explainer4.py המקורי אבד).

- `dkengine.py`: מנוע "דקה ברורה" (נבנה מחדש 15.10.2026): רקע עם עיגולים זזים ומילת רקע, עיגול עם דוד, שם, לוגו ו"נוצר באמצעות AI" בתוך האזור הבטוח של 4:5 (y 285–1635), כתוביות בתיבה כחולה, אייקונים קוויים, כפתור עקבו, מסך סיום.
- `ep10.py`: סצנות של טיפ #10, דוגמה לפרק. כל פרק = קובץ סצנות שמסונכרן למילים מ-`social/heygen/words/<name>.json`.
- תמלול: `.github/workflows/transcribe.yml` (Whisper עברית של ivrit.ai על GitHub Actions). מוסיפים שם קובץ ל-`social/heygen/transcribe.txt`.
- `millennium_series.py`: עריכת פרקי המילניום מ-spec JSON (כתוביות, שקופית "לא צריך לחכות מילניום", מסך סיום).

הנתיבים לפונטים וללוגו בקוד הם של סביבת העבודה של Claude; הפונט: @fontsource/ibm-plex-sans-hebrew (npm), הלוגו: barur-logo-assets.zip בתיקיית המיתוג.

## epgen.py (16.10.2026, tips 11-23)
Spec-driven renderer. One small spec per episode (`specs/epNN.py`): scenes start at a spoken word, each with elements
(head, lines, title, chips, grid, cards, balance, timeline, meter, icon, strike). Captions and the closing scene
(follow, share/comment, tomorrow teaser) are built automatically. The approved script text (`scripts.json`) is aligned
onto Whisper's word timings, so captions show the script even when Whisper mishears.
Run: `PREVIEW=auto python3 -I epgen.py epNN` (stills per scene) or `python3 -I epgen.py epNN out.mp4`.
`stage.py N..` copies a render into social/video, makes the cover, adds the FB/IG post and the .vercelignore line.

## mill.py / gremlin.py (30.10.2026)
- `mill.py spec.json`: מילניום בלי תלות בתיקיית pharaoh. כתוביות דרך Playwright (74px, תיבה כחולה), שקופית "לא צריך לחכות מילניום" (slogan.png) ומסך סיום (endcard.png, נחתך מקליאו). spec: {src,out,L,caps:[[start,end,[[text,"w"|"t"]]]]}.
- `gremlin.py <image> <out> <hint_html> <place>`: פרק "שדון הריבית" חדש מתמונה. משתמש בפתיח, ב"תפסנו אותך", במסך הסיום ובפסקול של פרק 3 (שדון הריבית 3 - העמלה.mp4), מכסה את שורת הרמז הישנה בכתובית חדשה, מדביק את ראש השדון (series_assets/head.png) בתמונה ומייצר ספירה לאחור, עיגול אדום וזום. place: ring:cx,cy,rin,rout,dx,dy,w (מציץ מאחורי טבעת) או win:x0,y0,x1,y1,w (מציץ מחלון). הנתיבים בקוד הם של /home/claude/mil.
