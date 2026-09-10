// ברור משכנתאות — סקריפט אתר
// מספר וואטסאפ עסקי — להחליף למספר האמיתי בפורמט בינלאומי ללא + (למשל 972501234567)
const WA_NUMBER = "972507890222";

function waLink(text) {
  return "https://wa.me/" + WA_NUMBER + "?text=" + encodeURIComponent(text);
}

document.addEventListener("DOMContentLoaded", () => {
  // קישורי וואטסאפ
  document.querySelectorAll("[data-wa]").forEach((a) => {
    a.href = waLink(a.dataset.wa || "שלום, אשמח לבדיקת כדאיות מיחזור.");
    a.target = "_blank";
    a.rel = "noopener";
  });

  // תפריט נייד
  const mb = document.querySelector(".menu-btn");
  const nav = document.querySelector(".nav");
  if (mb && nav) mb.addEventListener("click", () => nav.classList.toggle("open"));

  // מחשבון מיחזור
  const calc = document.querySelector("#calc");
  if (calc) {
    const $ = (id) => calc.querySelector("#" + id);
    const fmt = (n) => "₪ " + Math.round(n).toLocaleString("en-US");
    const pmt = (P, annual, years) => {
      const r = annual / 100 / 12, n = years * 12;
      if (r === 0) return P / n;
      return (P * r) / (1 - Math.pow(1 + r, -n));
    };
    const run = () => {
      const P = +$("balance").value || 0, r1 = +$("rate").value || 0, y = +$("years").value || 0, r2 = +$("newrate").value || 0;
      if (P <= 0 || y <= 0) return;
      const a = pmt(P, r1, y), b = pmt(P, r2, y);
      const diff = a - b;
      $("now").textContent = fmt(a);
      $("new").textContent = fmt(b);
      $("monthly").textContent = (diff >= 0 ? "" : "−") + fmt(Math.abs(diff));
      $("total").textContent = (diff >= 0 ? "" : "−") + fmt(Math.abs(diff * y * 12));
      $("verdict").textContent = diff * y * 12 > 25000 ? "שווה בדיקה מעמיקה." : diff * y * 12 > 8000 ? "גבולי — תלוי בעמלת פירעון." : "כנראה לא משתלם לגעת.";
    };
    calc.querySelectorAll("input").forEach((i) => i.addEventListener("input", run));
    run();
    const send = calc.querySelector("[data-calc-wa]");
    if (send) send.addEventListener("click", (e) => {
      e.preventDefault();
      const msg = `שלום, בדקתי במחשבון באתר: יתרה ${$("balance").value} ₪, ריבית ${$("rate").value}%, ${$("years").value} שנים. אשמח לבדיקת כדאיות מיחזור.`;
      window.open(waLink(msg), "_blank");
    });
  }

  // טופס יצירת קשר → וואטסאפ
  const form = document.querySelector("#contact-form");
  if (form) form.addEventListener("submit", (e) => {
    e.preventDefault();
    const f = new FormData(form);
    const msg = `שלום, שמי ${f.get("name")}. ${f.get("topic")}. ${f.get("msg") || ""}`.trim();
    window.open(waLink(msg), "_blank");
  });

  // הודעת עוגיות — אישור/דחייה אמיתיים
  const cookieBar = document.querySelector("#cookie-bar");
  const cookieAccept = document.querySelector("#cookie-accept");
  const cookieDecline = document.querySelector("#cookie-decline");
  if (cookieBar && cookieAccept && cookieDecline) {
    try {
      const choice = localStorage.getItem("cookie-consent");
      if (choice !== "accepted" && choice !== "declined") cookieBar.classList.add("show");
      window.cookieConsent = choice || "declined"; // ברירת מחדל שמרנית: בלי הסכמה, בלי עוגיות לא-חיוניות
    } catch (e) {}
    const setChoice = (val) => {
      cookieBar.classList.remove("show");
      window.cookieConsent = val;
      try { localStorage.setItem("cookie-consent", val); } catch (e) {}
      // כרגע האתר לא טוען עוגיות מעקב/פרסום כלל, ללא קשר לבחירה.
      // כל כלי כזה שיתווסף בעתיד יבדוק את window.cookieConsent === "accepted" לפני טעינה.
    };
    cookieAccept.addEventListener("click", () => setChoice("accepted"));
    cookieDecline.addEventListener("click", () => setChoice("declined"));
  }

  // תפריט נגישות
  const a11yToggle = document.querySelector("#a11y-toggle");
  const a11yPanel = document.querySelector("#a11y-panel");
  if (a11yToggle && a11yPanel) {
    const TOGGLES = ["contrast", "grayscale", "underline", "stop-motion", "readable"];
    const applyState = (state) => {
      TOGGLES.forEach((key) => {
        const on = !!state[key];
        document.body.classList.toggle("a11y-" + key, on);
        const btn = a11yPanel.querySelector(`[data-a11y-toggle="${key}"]`);
        if (btn) { btn.classList.toggle("active", on); btn.textContent = on ? "כבוי" : "הפעל"; }
      });
      document.documentElement.classList.remove("a11y-fs-1", "a11y-fs-2", "a11y-fs-3");
      if (state.fs && state.fs !== "0") document.documentElement.classList.add("a11y-fs-" + state.fs);
      a11yPanel.querySelectorAll("[data-a11y-fs]").forEach((b) => b.classList.toggle("active", b.dataset.a11yFs === (state.fs || "0")));
    };
    let state = {};
    try { state = JSON.parse(localStorage.getItem("a11y-state") || "{}"); } catch (e) {}
    applyState(state);
    const save = () => { try { localStorage.setItem("a11y-state", JSON.stringify(state)); } catch (e) {} };

    a11yToggle.addEventListener("click", () => {
      const open = a11yPanel.classList.toggle("open");
      a11yToggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    document.addEventListener("click", (e) => {
      if (!a11yPanel.contains(e.target) && e.target !== a11yToggle && !a11yToggle.contains(e.target)) {
        a11yPanel.classList.remove("open");
        a11yToggle.setAttribute("aria-expanded", "false");
      }
    });
    a11yPanel.querySelectorAll("[data-a11y-toggle]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.dataset.a11yToggle;
        state[key] = !state[key];
        applyState(state);
        save();
      });
    });
    a11yPanel.querySelectorAll("[data-a11y-fs]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.fs = btn.dataset.a11yFs;
        applyState(state);
        save();
      });
    });
    document.querySelector("#a11y-reset")?.addEventListener("click", () => {
      state = {};
      applyState(state);
      save();
    });
  }
});
