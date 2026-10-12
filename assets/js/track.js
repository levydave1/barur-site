// ברור משכנתאות — מדידה (Meta Pixel + GA4)
// נטען רק אחרי שהמבקר אישר עוגיות. אירועים שקרו לפני האישור נשמרים בזיכרון
// ונשלחים ברגע האישור (באותו ביקור בלבד). בלי אישור — שום דבר לא נטען ולא נשלח.
(function () {
  var META_PIXEL_ID = "1776166563647834";
  var GA4_ID = "G-D0Z2T0P9EX";

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
    // event_id is for Meta de-duplication (Pixel + Conversions API), not a
    // reporting parameter, so it travels as the 4th fbq argument.
    var eventId = params.event_id;
    if (eventId) {
      params = Object.assign({}, params);
      delete params.event_id;
    }
    if (window.fbq) {
      var method = META_STANDARD[name] ? "track" : "trackCustom";
      if (eventId) window.fbq(method, name, params, { eventID: eventId });
      else window.fbq(method, name, params);
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
    // Compact strip pinned to the bottom edge, so it doesn't sit on top of the
    // page's main button on a phone; the page gets matching bottom padding so
    // nothing ends up hidden behind it.
    bar.style.cssText = "position:fixed;left:0;right:0;bottom:0;z-index:9999;background:#0F2A47;color:#F5F3EE;" +
      "padding:8px 12px calc(8px + env(safe-area-inset-bottom));font:400 13px/1.4 'IBM Plex Sans Hebrew',Arial,sans-serif;" +
      "box-shadow:0 -4px 16px rgba(0,0,0,.18);display:flex;gap:10px;align-items:center;justify-content:center";
    bar.innerHTML =
      '<p style="margin:0;flex:1 1 auto;max-width:520px">עוגיות למדידה ולפרסום (Meta, Google), רק באישור. ' +
      '<a href="/cookies" style="color:#4FB3A2;text-decoration:underline">מדיניות</a></p>' +
      '<div style="display:flex;gap:6px;flex:none">' +
      '<button type="button" data-c="declined" style="background:transparent;color:#F5F3EE;border:1px solid #5E6875;border-radius:8px;padding:6px 12px;font:inherit;cursor:pointer">דחייה</button>' +
      '<button type="button" data-c="accepted" style="background:#0C7268;color:#fff;border:0;border-radius:8px;padding:6px 12px;font:inherit;font-weight:600;cursor:pointer">אישור</button>' +
      "</div>";
    bar.addEventListener("click", function (e) {
      var v = e.target && e.target.getAttribute("data-c");
      if (!v) return;
      try { localStorage.setItem("cookie-consent", v); } catch (err) {}
      window.cookieConsent = v;
      bar.remove();
      document.body.style.paddingBottom = "";
      if (v === "accepted") load(); else queue = [];
    });
    document.body.appendChild(bar);
    document.body.style.paddingBottom = bar.offsetHeight + "px";
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
