// ברור משכנתאות — סקריפט אתר
// מספר וואטסאפ עסקי — להחליף למספר האמיתי בפורמט בינלאומי ללא + (למשל 972501234567)
const WA_NUMBER = "972500000000";

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
});
