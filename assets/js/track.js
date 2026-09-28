// ברור משכנתאות — מדידה (Meta Pixel + GA4)
// נטען רק אחרי שהמבקר אישר עוגיות. אירועים שקרו לפני האישור נשמרים בזיכרון
// ונשלחים ברגע האישור (באותו ביקור בלבד). בלי אישור — שום דבר לא נטען ולא נשלח.
(function () {
  var META_PIXEL_ID = "1776166563647834";
  var GA4_ID = ""; // למלא כשיהיה מזהה G-XXXXXXX. ריק = GA4 כבוי.

  var loaded = false;
  var queue = [];

  function consent() {
    try { return localStorage.getItem("cookie-consent"); } catch (e) { return null; }
  }

  function loadMeta() {
    if (!META_PIXEL_ID || window.fbq) return;
    !function (f, b, e, v, n, t, s) {
      if (f.fbq) return; n = f.fbq = function () {
        n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
      };
      if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = "2.0";
      n.queue = []; t = b.createElement(e); t.async = !0;
      t.src = v; s = b.getElementsByTagName(e)[0];
      s.parentNode.insertBefore(t, s);
    }(window, document, "script", "https://connect.facebook.net/en_US/fbevents.js");
    window.fbq("init", META_PIXEL_ID);
    window.fbq("track", "PageView");
  }

  function loadGA() {
    if (!GA4_ID || window.gtag) return;
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + GA4_ID;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", GA4_ID);
  }

  // שמות אירועים: standard של מטא כשיש כזה, אחרת custom.
  var META_STANDARD = { Lead: 1, ViewContent: 1, InitiateCheckout: 1, Contact: 1 };
  var GA_NAMES = { Lead: "generate_lead", Contact: "contact" };

  function send(name, params) {
    params = params || {};
    if (window.fbq) {
      window.fbq(META_STANDARD[name] ? "track" : "trackCustom", name, params);
    }
    if (window.gtag) {
      window.gtag("event", GA_NAMES[name] || name, params);
    }
  }

  function load() {
    if (loaded) return;
    loaded = true;
    loadMeta();
    loadGA();
    while (queue.length) { var q = queue.shift(); send(q[0], q[1]); }
  }

  // ממשק ציבורי: barurTrack("Lead", {...})
  window.barurTrack = function (name, params) {
    if (loaded) send(name, params);
    else if (consent() !== "declined") queue.push([name, params]);
  };
  window.barurLoadTracking = load;
  // אירועים שנרשמו בדף לפני שהקובץ הזה נטען
  (window.__barurQ || []).forEach(function (q) { window.barurTrack(q[0], q[1]); });
  window.__barurQ = [];

  // הודעת עוגיות לדפים שאין בהם אחת (כמו דף הבדיקה)
  function injectBar() {
    var bar = document.createElement("div");
    bar.id = "barur-consent";
    bar.setAttribute("role", "region");
    bar.setAttribute("aria-label", "הודעה על עוגיות");
    bar.style.cssText = "position:fixed;inset-inline:12px;bottom:12px;z-index:9999;background:#0F2A47;color:#F5F3EE;" +
      "border-radius:12px;padding:14px 16px;font:400 14px/1.5 'IBM Plex Sans Hebrew',Arial,sans-serif;" +
      "box-shadow:0 6px 24px rgba(0,0,0,.25);display:flex;gap:12px;align-items:center;flex-wrap:wrap;max-width:720px;margin:0 auto";
    bar.innerHTML =
      '<p style="margin:0;flex:1 1 260px">אנחנו משתמשים בעוגיות למדידה ולפרסום (Meta, Google) רק אם תאשרו. ' +
      '<a href="/cookies" style="color:#4FB3A2">מדיניות העוגיות</a></p>' +
      '<div style="display:flex;gap:8px">' +
      '<button type="button" data-c="declined" style="background:transparent;color:#F5F3EE;border:1px solid #7C8794;border-radius:8px;padding:8px 14px;font:inherit;cursor:pointer">דחייה</button>' +
      '<button type="button" data-c="accepted" style="background:#11978A;color:#fff;border:0;border-radius:8px;padding:8px 14px;font:inherit;font-weight:600;cursor:pointer">אישור</button>' +
      "</div>";
    bar.addEventListener("click", function (e) {
      var v = e.target && e.target.getAttribute("data-c");
      if (!v) return;
      try { localStorage.setItem("cookie-consent", v); } catch (err) {}
      window.cookieConsent = v;
      bar.remove();
      if (v === "accepted") load(); else queue = [];
    });
    document.body.appendChild(bar);
  }

  function init() {
    var c = consent();
    if (c === "accepted") { load(); return; }
    // דפים עם הודעת העוגיות של האתר (main.js): מאזינים ללחיצה על "אישור"
    document.addEventListener("click", function (e) {
      var t = e.target && e.target.closest && e.target.closest("#cookie-accept, #cookie-decline");
      if (!t) return;
      if (t.id === "cookie-accept") load(); else queue = [];
    });
    if (!c && !document.getElementById("cookie-bar")) injectBar();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
