// Internal mix engine — results go to the Telegram summary only, never to the customer.
//
// For every lead it builds every mortgage made of 3 EQUAL tracks (1/3 of the
// balance each, 3 different track types), across 5 track types and several terms, keeps only mixes that
// meet the Bank of Israel rule (at least 1/3 at a fixed rate), and picks:
//   payment — the lowest first monthly payment
//   both    — lower payment AND lower total cost than today, best balance of the two
//   total   — the lowest total cost without raising today's monthly payment
//
// Rates live in /track-rates.json (update it when rates or the prime change).
// Assumptions: the prime and variable tracks stay at today's rate, linked tracks
// grow with the inflation in track-rates.json, no early-repayment fees or bank
// fees are included. Indicative only.

const RATES = require('../track-rates.json');

const TYPES = {
  P:   { name: 'פריים', linked: false, fixed: false, minYears: 1 },
  KL:  { name: 'קבועה לא צמודה', linked: false, fixed: true, minYears: 4 },
  KZ:  { name: 'קבועה צמודה', linked: true, fixed: true, minYears: 4 },
  ML5: { name: 'משתנה כל 5 לא צמודה', linked: false, fixed: false, minYears: 5 },
  MZ5: { name: 'משתנה כל 5 צמודה', linked: true, fixed: false, minYears: 5 },
};

function byTerm(table, years) {
  const keys = Object.keys(table).map(Number).sort((a, b) => a - b);
  if (years <= keys[0]) return table[keys[0]];
  if (years >= keys[keys.length - 1]) return table[keys[keys.length - 1]];
  for (let i = 1; i < keys.length; i++) {
    if (years <= keys[i]) {
      const a = keys[i - 1], b = keys[i];
      return table[a] + (table[b] - table[a]) * (years - a) / (b - a);
    }
  }
  return table[keys[keys.length - 1]];
}

function rateFor(type, years, r) {
  switch (type) {
    case 'P': return r.prime + r.primeMargin;
    case 'KL': return byTerm(r.fixedUnlinked, years);
    case 'KZ': return byTerm(r.fixedLinked, years);
    case 'ML5': return r.var5Unlinked;
    case 'MZ5': return r.var5Linked;
  }
  return null;
}

// Monthly annuity payment.
function pmt(principal, ratePct, months) {
  const i = ratePct / 100 / 12;
  if (months <= 0) return principal;
  if (i === 0) return principal / months;
  return principal * i / (1 - Math.pow(1 + i, -months));
}

// Total nominal payments. A linked loan's payment grows with the CPI each month.
function totalPaid(payment, months, linked, inflationPct) {
  if (!linked || !inflationPct) return payment * months;
  const g = Math.pow(1 + inflationPct / 100, 1 / 12) - 1;
  return payment * (1 + g) * (Math.pow(1 + g, months) - 1) / g;
}

function isLinkedName(name) {
  const s = String(name || '');
  return /צמוד/.test(s) && !/לא[\s-]*צמוד/.test(s);
}

function currentState(lead, r) {
  const tracks = Array.isArray(lead.tracks) ? lead.tracks.filter(t => t && t.balance > 0 && t.term > 0) : [];
  if (tracks.length) {
    let pay = 0, total = 0, bal = 0;
    for (const t of tracks) {
      const p = t.rate != null ? pmt(t.balance, Number(t.rate), t.term) : null;
      if (p == null) continue;
      pay += p; bal += t.balance;
      total += totalPaid(p, t.term, isLinkedName(t.name), r.inflation);
    }
    if (bal > 0) {
      return {
        balance: Number(lead.balance) > 0 ? Number(lead.balance) : bal,
        // From the tracks' current rates: the report's "last charge" can predate a rate reset.
        payment: pay,
        reportedPayment: Number(lead.payment) > 0 ? Number(lead.payment) : null,
        total,
        years: Number(lead.years) > 0 ? Number(lead.years) : Math.max(...tracks.map(t => t.term)) / 12,
        fromTracks: true,
      };
    }
  }
  const balance = Number(lead.balance), payment = Number(lead.payment), years = Number(lead.years);
  if (!(balance > 0 && payment > 0 && years > 0)) return null;
  return { balance, payment, total: payment * years * 12, years, fromTracks: false };
}

function buildMixes(balance, years, r) {
  const termSet = [...new Set([Math.min(30, Math.max(4, Math.round(years))), 10, 15, 20, 25, 30])].sort((a, b) => a - b);
  const options = [];
  for (const type of Object.keys(TYPES)) {
    for (const y of termSet) {
      if (y < TYPES[type].minYears) continue;
      options.push({ type, years: y });
    }
  }
  const part = balance / 3;
  const legs = options.map(o => {
    const rate = rateFor(o.type, o.years, r);
    const p = pmt(part, rate, o.years * 12);
    return { ...o, rate, payment: p, total: totalPaid(p, o.years * 12, TYPES[o.type].linked, r.inflation) };
  });
  const mixes = [];
  for (let a = 0; a < legs.length; a++)
    for (let b = a + 1; b < legs.length; b++)
      for (let c = b + 1; c < legs.length; c++) {
        const mix = [legs[a], legs[b], legs[c]];
        if (new Set(mix.map(l => l.type)).size < 3) continue;   // 3 different track types
        if (!mix.some(l => TYPES[l.type].fixed)) continue;      // at least 1/3 fixed (BOI rule)
        mixes.push({ legs: mix, payment: mix.reduce((s, l) => s + l.payment, 0), total: mix.reduce((s, l) => s + l.total, 0) });
      }
  return mixes;
}

function pick(mixes, cur) {
  const minBy = (arr, f) => arr.reduce((best, m) => (best == null || f(m) < f(best) ? m : best), null);
  const payment = minBy(mixes, m => m.payment + m.total * 1e-9);
  const total = minBy(mixes.filter(m => m.payment <= cur.payment && m.total < cur.total), m => m.total);
  const both = minBy(
    mixes.filter(m => m.payment <= cur.payment * 0.98 && m.total <= cur.total),
    m => m.payment / cur.payment + m.total / cur.total
  );
  return { payment, both, total };
}

function ils(n) {
  if (typeof n !== 'number' || !isFinite(n)) return '—';
  return '₪' + Math.round(n).toLocaleString('he-IL');
}
function signed(n) { return (n >= 0 ? '−' : '+') + ils(Math.abs(n)); }

function mixLines(lead, r = RATES) {
  try {
    const cur = currentState(lead, r);
    if (!cur) return [];
    const mixes = buildMixes(cur.balance, cur.years, r);
    const best = pick(mixes, cur);
    const out = [' ', `🧮 תמהילים (3 מסלולים שווים, שליש כל אחד) — נבדקו ${mixes.length.toLocaleString('he-IL')} שילובים. רק אצלך, הלקוח לא רואה.`];
    out.push(`היום: החזר ${ils(cur.payment)} | עלות כוללת משוערת ${ils(cur.total)}${cur.fromTracks ? ' (לפי הריביות הנוכחיות של המסלולים בדוח)' : ' (לפי החזר × שנים שנותרו)'}`);
    if (cur.reportedPayment && Math.abs(cur.reportedPayment - cur.payment) > 50) {
      out.push(`  (החיוב האחרון בדוח: ${ils(cur.reportedPayment)}. ההפרש בדרך כלל משינוי ריבית במסלול משתנה)`);
    }
    const titles = { payment: 'החזר חודשי מינימלי', both: 'שילוב', total: 'עלות כוללת מינימלית' };
    for (const key of ['payment', 'both', 'total']) {
      const m = best[key];
      out.push(' ', `▪️ ${titles[key]}:`);
      if (!m) {
        out.push(key === 'total' ? '  אין תמהיל שמוריד את העלות הכוללת בלי להעלות את ההחזר החודשי.'
          : '  אין תמהיל שמוריד גם את ההחזר וגם את העלות הכוללת.');
        continue;
      }
      const legs = [...m.legs].sort((x, y) => y.years - x.years);
      for (const l of legs) out.push(`  • ${TYPES[l.type].name} | ${l.years} שנה | ${l.rate.toFixed(2)}% | ${ils(l.payment)}`);
      out.push(`  החזר ${ils(m.payment)} (${signed(cur.payment - m.payment)} בחודש) | עלות כוללת ${ils(m.total)} (${signed(cur.total - m.total)})`);
    }
    out.push(' ', `הנחות: ריביות מ-${r.updatedAt} (פריים ${r.prime}%), אינפלציה ${r.inflation}% בשנה, פריים ומשתנות בלי שינוי, בלי עמלות פירעון מוקדם.`);
    return out;
  } catch (e) {
    console.error('mix engine failed', e && e.message);
    return [];
  }
}

module.exports = { mixLines, buildMixes, currentState, pick, pmt, totalPaid, rateFor };
