import React, { useState, useMemo } from "react";

const RESORTS = [{"name":"Bansko","country":"Bulgaria","region":"Pirin Mountains","baseElev":990,"summitElev":2600,"vertical":1610,"lifts":14,"pisteKm":75.0,"beginner":0.4,"intermediate":0.4,"advanced":0.2,"terrainQuality":"sourced","offPiste":2,"snow":3,"nightlife":4,"family":4,"airport":"Sofia (SOF)","airportDist":160.0,"transferMin":135,"pass6day":260.0,"accomPerNight":70.0,"needsVerification":false},{"name":"Chamonix","country":"France","region":"Mont Blanc Valley","baseElev":1035,"summitElev":3842,"vertical":2807,"lifts":49,"pisteKm":170.0,"beginner":0.23,"intermediate":0.31,"advanced":0.46,"terrainQuality":"sourced","offPiste":5,"snow":5,"nightlife":4,"family":3,"airport":"Geneva (GVA)","airportDist":100.0,"transferMin":68,"pass6day":380.0,"accomPerNight":140.0,"needsVerification":false},{"name":"Val Thorens","country":"France","region":"Les Trois Vall\u00e9es","baseElev":2300,"summitElev":3230,"vertical":930,"lifts":31,"pisteKm":150.0,"beginner":0.29,"intermediate":0.61,"advanced":0.1,"terrainQuality":"sourced","offPiste":4,"snow":5,"nightlife":4,"family":4,"airport":"Geneva (GVA) / Chamb\u00e9ry (CMF)","airportDist":150.0,"transferMin":128,"pass6day":430.0,"accomPerNight":160.0,"needsVerification":false},{"name":"St. Anton am Arlberg","country":"Austria","region":"Ski Arlberg","baseElev":1304,"summitElev":2811,"vertical":1507,"lifts":88,"pisteKm":305.0,"beginner":0.36,"intermediate":0.26,"advanced":0.38,"terrainQuality":"sourced","offPiste":5,"snow":4,"nightlife":5,"family":3,"airport":"Innsbruck (INN)","airportDist":100.0,"transferMin":75,"pass6day":380.0,"accomPerNight":130.0,"needsVerification":false},{"name":"Zermatt","country":"Switzerland","region":"Matterhorn Glacier Paradise","baseElev":1620,"summitElev":3883,"vertical":2263,"lifts":40,"pisteKm":360.0,"beginner":0.2,"intermediate":0.55,"advanced":0.25,"terrainQuality":"sourced_conflicting","offPiste":4,"snow":5,"nightlife":3,"family":3,"airport":"Geneva (GVA) / Milan Malpensa (MXP)","airportDist":231.0,"transferMin":170,"pass6day":450.0,"accomPerNight":180.0,"needsVerification":false},{"name":"Livigno","country":"Italy","region":"Alta Valtellina","baseElev":1816,"summitElev":2798,"vertical":981,"lifts":31,"pisteKm":115.0,"beginner":0.18,"intermediate":0.65,"advanced":0.17,"terrainQuality":"sourced","offPiste":3,"snow":5,"nightlife":3,"family":4,"airport":"Milan (MXP/LIN) / Bergamo (BGY) / Innsbruck (INN)","airportDist":200.0,"transferMin":225,"pass6day":280.0,"accomPerNight":100.0,"needsVerification":false},{"name":"Kitzb\u00fchel","country":"Austria","region":"Kitzb\u00fcheler Alpen (KitzSki)","baseElev":800,"summitElev":2000,"vertical":1200,"lifts":57,"pisteKm":233.0,"beginner":0.2,"intermediate":0.65,"advanced":0.15,"terrainQuality":"estimated","offPiste":3,"snow":3,"nightlife":5,"family":4,"airport":"Innsbruck (INN) / Salzburg (SZG)","airportDist":90.0,"transferMin":75,"pass6day":380.0,"accomPerNight":150.0,"needsVerification":true},{"name":"Grandvalira (Andorra)","country":"Andorra","region":"Grandvalira / Soldeu-El Tarter-Pas de la Casa","baseElev":1710,"summitElev":2640,"vertical":930,"lifts":65,"pisteKm":210.0,"beginner":0.35,"intermediate":0.45,"advanced":0.2,"terrainQuality":"estimated","offPiste":2,"snow":3,"nightlife":4,"family":4,"airport":"Barcelona (BCN) / Toulouse (TLS)","airportDist":220.0,"transferMin":180,"pass6day":260.0,"accomPerNight":90.0,"needsVerification":true},{"name":"Cervinia (Breuil-Cervinia)","country":"Italy","region":"Matterhorn Ski Paradise (linked to Zermatt)","baseElev":2050,"summitElev":3883,"vertical":1833,"lifts":22,"pisteKm":180.0,"beginner":0.25,"intermediate":0.65,"advanced":0.1,"terrainQuality":"estimated","offPiste":3,"snow":5,"nightlife":3,"family":4,"airport":"Milan Malpensa (MXP)","airportDist":160.0,"transferMin":165,"pass6day":300.0,"accomPerNight":100.0,"needsVerification":true},{"name":"Val Gardena (Selva)","country":"Italy","region":"Sella Ronda / Dolomiti Superski","baseElev":1563,"summitElev":2518,"vertical":955,"lifts":79,"pisteKm":175.0,"beginner":0.2,"intermediate":0.65,"advanced":0.15,"terrainQuality":"estimated","offPiste":2,"snow":3,"nightlife":3,"family":5,"airport":"Innsbruck (INN) / Bolzano (BZO) / Verona (VRN)","airportDist":100.0,"transferMin":90,"pass6day":320.0,"accomPerNight":120.0,"needsVerification":true},{"name":"Courchevel","country":"France","region":"Les Trois Vall\u00e9es","baseElev":1100,"summitElev":2738,"vertical":1638,"lifts":58,"pisteKm":150.0,"beginner":0.39,"intermediate":0.51,"advanced":0.1,"terrainQuality":"sourced","offPiste":3,"snow":4,"nightlife":3,"family":4,"airport":"Chamb\u00e9ry (CMF) / Geneva (GVA)","airportDist":110.0,"transferMin":135,"pass6day":420.0,"accomPerNight":200.0,"needsVerification":false},{"name":"Verbier","country":"Switzerland","region":"4 Vall\u00e9es","baseElev":1500,"summitElev":3330,"vertical":1830,"lifts":93,"pisteKm":410.0,"beginner":0.26,"intermediate":0.49,"advanced":0.25,"terrainQuality":"sourced","offPiste":5,"snow":4,"nightlife":5,"family":3,"airport":"Geneva (GVA)","airportDist":160.0,"transferMin":135,"pass6day":460.0,"accomPerNight":190.0,"needsVerification":false},{"name":"Ischgl","country":"Austria","region":"Silvretta Arena (Ischgl/Samnaun)","baseElev":1400,"summitElev":2872,"vertical":1472,"lifts":45,"pisteKm":239.0,"beginner":0.45,"intermediate":0.41,"advanced":0.14,"terrainQuality":"sourced","offPiste":4,"snow":5,"nightlife":5,"family":3,"airport":"Innsbruck (INN)","airportDist":100.0,"transferMin":90,"pass6day":400.0,"accomPerNight":160.0,"needsVerification":false},{"name":"S\u00f6lden","country":"Austria","region":"\u00d6tztal Valley (S\u00f6lden/Hochs\u00f6lden)","baseElev":1350,"summitElev":3340,"vertical":1990,"lifts":31,"pisteKm":144.0,"beginner":0.25,"intermediate":0.56,"advanced":0.19,"terrainQuality":"sourced","offPiste":3,"snow":5,"nightlife":5,"family":4,"airport":"Innsbruck (INN)","airportDist":83.0,"transferMin":82,"pass6day":400.0,"accomPerNight":150.0,"needsVerification":false},{"name":"Serre Chevalier","country":"France","region":"Serre Chevalier Vall\u00e9e","baseElev":1200,"summitElev":2800,"vertical":1600,"lifts":61,"pisteKm":250.0,"beginner":0.3,"intermediate":0.4,"advanced":0.3,"terrainQuality":"estimated","offPiste":3,"snow":3,"nightlife":3,"family":4,"airport":"Turin (TRN) / Grenoble (GNB)","airportDist":150.0,"transferMin":120,"pass6day":320.0,"accomPerNight":110.0,"needsVerification":true},{"name":"Saalbach-Hinterglemm","country":"Austria","region":"Skicircus Saalbach-Hinterglemm-Leogang-Fieberbrunn","baseElev":1003,"summitElev":2096,"vertical":1093,"lifts":70,"pisteKm":270.0,"beginner":0.35,"intermediate":0.5,"advanced":0.15,"terrainQuality":"estimated","offPiste":2,"snow":3,"nightlife":5,"family":4,"airport":"Salzburg (SZG)","airportDist":75.0,"transferMin":60,"pass6day":380.0,"accomPerNight":140.0,"needsVerification":true},{"name":"Alpe d'Huez","country":"France","region":"Alpe d'Huez Grand Domaine Ski","baseElev":1860,"summitElev":3330,"vertical":1470,"lifts":84,"pisteKm":250.0,"beginner":0.3,"intermediate":0.45,"advanced":0.25,"terrainQuality":"estimated","offPiste":3,"snow":3,"nightlife":3,"family":4,"airport":"Grenoble (GNB) / Lyon (LYS)","airportDist":65.0,"transferMin":75,"pass6day":350.0,"accomPerNight":120.0,"needsVerification":true},{"name":"Pamporovo","country":"Bulgaria","region":"Rhodope Mountains","baseElev":1450,"summitElev":1926,"vertical":476,"lifts":22,"pisteKm":40.0,"beginner":0.5,"intermediate":0.4,"advanced":0.1,"terrainQuality":"estimated","offPiste":1,"snow":3,"nightlife":3,"family":5,"airport":"Plovdiv (PDV) / Sofia (SOF)","airportDist":90.0,"transferMin":90,"pass6day":180.0,"accomPerNight":55.0,"needsVerification":true},{"name":"Poiana Brasov","country":"Romania","region":"Southern Carpathians","baseElev":1030,"summitElev":1775,"vertical":745,"lifts":10,"pisteKm":24.0,"beginner":0.4,"intermediate":0.45,"advanced":0.15,"terrainQuality":"estimated","offPiste":1,"snow":2,"nightlife":3,"family":4,"airport":"Bucharest (OTP) / Brasov (BRV, seasonal)","airportDist":170.0,"transferMin":150,"pass6day":150.0,"accomPerNight":50.0,"needsVerification":true},{"name":"Kranjska Gora","country":"Slovenia","region":"Julian Alps","baseElev":810,"summitElev":1570,"vertical":760,"lifts":20,"pisteKm":30.0,"beginner":0.45,"intermediate":0.45,"advanced":0.1,"terrainQuality":"estimated","offPiste":1,"snow":3,"nightlife":3,"family":5,"airport":"Ljubljana (LJU)","airportDist":90.0,"transferMin":75,"pass6day":220.0,"accomPerNight":90.0,"needsVerification":true},{"name":"M\u00e9ribel","country":"France","region":"Les Trois Vall\u00e9es","baseElev":1450,"summitElev":2952,"vertical":1502,"lifts":53,"pisteKm":150.0,"beginner":0.58,"intermediate":0.3,"advanced":0.12,"terrainQuality":"sourced","offPiste":4,"snow":4,"nightlife":4,"family":4,"airport":"Chamb\u00e9ry (CMF) / Geneva (GVA)","airportDist":100.0,"transferMin":120,"pass6day":420.0,"accomPerNight":190.0,"needsVerification":false},{"name":"Val d'Is\u00e8re / Tignes","country":"France","region":"Espace Killy","baseElev":1550,"summitElev":3456,"vertical":1906,"lifts":90,"pisteKm":300.0,"beginner":0.36,"intermediate":0.47,"advanced":0.17,"terrainQuality":"sourced","offPiste":4,"snow":5,"nightlife":4,"family":4,"airport":"Chamb\u00e9ry (CMF) / Geneva (GVA) / Lyon (LYS)","airportDist":145.0,"transferMin":128,"pass6day":440.0,"accomPerNight":180.0,"needsVerification":false},{"name":"Obergurgl-Hochgurgl","country":"Austria","region":"\u00d6tztal Valley","baseElev":1793,"summitElev":3082,"vertical":1289,"lifts":25,"pisteKm":112.0,"beginner":0.3,"intermediate":0.55,"advanced":0.15,"terrainQuality":"estimated","offPiste":2,"snow":5,"nightlife":2,"family":5,"airport":"Innsbruck (INN)","airportDist":97.0,"transferMin":100,"pass6day":430.0,"accomPerNight":170.0,"needsVerification":false},{"name":"Cortina d'Ampezzo","country":"Italy","region":"Dolomiti Superski","baseElev":1224,"summitElev":3243,"vertical":2019,"lifts":30,"pisteKm":120.0,"beginner":0.35,"intermediate":0.5,"advanced":0.15,"terrainQuality":"estimated","offPiste":3,"snow":4,"nightlife":3,"family":4,"airport":"Venice Marco Polo (VCE) / Innsbruck (INN)","airportDist":148.0,"transferMin":120,"pass6day":380.0,"accomPerNight":160.0,"needsVerification":false},{"name":"Les Deux Alpes","country":"France","region":"Is\u00e8re / Alpe d'Huez region","baseElev":1300,"summitElev":3600,"vertical":2300,"lifts":51,"pisteKm":200.0,"beginner":0.65,"intermediate":0.23,"advanced":0.12,"terrainQuality":"sourced","offPiste":3,"snow":4,"nightlife":4,"family":3,"airport":"Grenoble (GNB) / Lyon (LYS)","airportDist":75.0,"transferMin":90,"pass6day":350.0,"accomPerNight":130.0,"needsVerification":false},{"name":"Formigal","country":"Spain","region":"Aragonese Pyrenees","baseElev":1500,"summitElev":2250,"vertical":740,"lifts":22,"pisteKm":176.0,"beginner":0.3,"intermediate":0.55,"advanced":0.15,"terrainQuality":"estimated","offPiste":2,"snow":3,"nightlife":4,"family":4,"airport":"Zaragoza (ZAZ) / Lourdes (LDE, France)","airportDist":170.0,"transferMin":120,"pass6day":260.0,"accomPerNight":100.0,"needsVerification":false},{"name":"Grand Massif (Flaine)","country":"France","region":"Haute-Savoie","baseElev":700,"summitElev":2561,"vertical":1861,"lifts":71,"pisteKm":265.0,"beginner":0.53,"intermediate":0.37,"advanced":0.1,"terrainQuality":"sourced","offPiste":3,"snow":4,"nightlife":3,"family":4,"airport":"Geneva (GVA)","airportDist":70.0,"transferMin":60,"pass6day":340.0,"accomPerNight":130.0,"needsVerification":false},{"name":"Krvavec","country":"Slovenia","region":"Kamnik-Savinja Alps","baseElev":1450,"summitElev":1971,"vertical":521,"lifts":11,"pisteKm":30.0,"beginner":0.4,"intermediate":0.45,"advanced":0.15,"terrainQuality":"estimated","offPiste":1,"snow":3,"nightlife":2,"family":4,"airport":"Ljubljana (LJU)","airportDist":10.0,"transferMin":120,"pass6day":200.0,"accomPerNight":85.0,"needsVerification":true},{"name":"Ast\u00fan-Candanch\u00fa","country":"Spain","region":"Aragonese Pyrenees","baseElev":1700,"summitElev":2300,"vertical":600,"lifts":13,"pisteKm":72.0,"beginner":0.4,"intermediate":0.5,"advanced":0.1,"terrainQuality":"estimated","offPiste":1,"snow":3,"nightlife":2,"family":4,"airport":"Zaragoza (ZAZ) / Pau (PUF, France)","airportDist":160.0,"transferMin":120,"pass6day":220.0,"accomPerNight":85.0,"needsVerification":true},{"name":"Bardonecchia","country":"Italy","region":"Milky Way (Via Lattea) / Piedmont","baseElev":1312,"summitElev":2750,"vertical":1438,"lifts":22,"pisteKm":140.0,"beginner":0.35,"intermediate":0.45,"advanced":0.2,"terrainQuality":"estimated","offPiste":3,"snow":3,"nightlife":3,"family":4,"airport":"Turin (TRN)","airportDist":90.0,"transferMin":75,"pass6day":300.0,"accomPerNight":110.0,"needsVerification":true}];

/* ---------------- ported engine logic (mirrors ski_optimizer/engine) ---------------- */

const FLIGHT_EST = {
  France: 280, Switzerland: 320, Austria: 260, Italy: 240, Bulgaria: 160,
  Andorra: 300, Romania: 150, Slovenia: 220, Spain: 260,
};
const WESTERN = new Set(["France", "Switzerland", "Austria", "Italy", "Andorra", "Spain"]);
const FOOD_W = { budget: 28, normal: 48, luxury: 85 };
const FOOD_E = { budget: 16, normal: 30, luxury: 55 };
const EQUIP = { standard: 22, premium: 38 };

// Ski pass day-count multipliers -- MUST stay in sync with
// _PASS_DAY_MULTIPLIER in ski_optimizer/engine/cost_calculator.py.
// Real passes give a per-day discount as day count rises (anchored on
// Ski Arlberg 2025/26: 1-day EUR 81.50 vs 6-day EUR 450, so the 1-day
// rate is ~1.09x the naive per-day figure). Normalized so day 6 == 1.0,
// keeping each resort's sourced 6-day price exact.
const PASS_DAY_MULTIPLIER = { 1: 1.09, 2: 1.07, 3: 1.05, 4: 1.03, 5: 1.01, 6: 1.00, 7: 0.99, 8: 0.98, 9: 0.97, 10: 0.96 };
const PASS_LONG_TRIP_MULTIPLIER = 0.95; // 11+ days

function computeCost(r, prefs) {
  const nights = prefs.nights;
  const flight = FLIGHT_EST[r.country] ?? 260;
  const transferRT = Math.max(50, 2 * (15 + 0.22 * r.airportDist));
  const groupSafe = Math.max(1, prefs.group); // defense in depth -- inputs are clamped
  // at the UI layer too, but this function shouldn't trust that if it's ever reused
  // elsewhere. Division by an unguarded prefs.group produced Infinity for group=0
  // and a silently-wrong negative accommodation cost for a negative group size.
  const transfer = transferRT / Math.pow(groupSafe, 0.3);
  const rooms = Math.max(1, Math.ceil(groupSafe / 2));
  const accommodation = (r.accomPerNight * nights * rooms) / groupSafe;
  const pass = (r.pass6day / 6) * nights * (PASS_DAY_MULTIPLIER[nights] ?? PASS_LONG_TRIP_MULTIPLIER);
  // ?? fallback rather than a bare lookup: an unrecognized equipment/food key
  // previously produced `undefined * nights` = NaN, which then SURVIVED the
  // budget filter entirely (NaN > budget is false in JS, so `> budget` never
  // matches and the row isn't skipped) and rendered as the literal string
  // "NaN" in the price. Falling back to a sane default is the right call for
  // a client-side prototype; a real backend should reject instead (see the
  // Python UserPreferences validation for that stricter version).
  const equipment = (EQUIP[prefs.equipment] ?? EQUIP.standard) * nights;
  const foodTable = WESTERN.has(r.country) ? FOOD_W : FOOD_E;
  const food = (foodTable[prefs.food] ?? foodTable.normal) * nights;
  const subtotal = flight + transfer + accommodation + pass + equipment + food;
  const misc = subtotal * 0.05;
  return { flight, transfer, accommodation, pass, equipment, food, misc, total: subtotal + misc };
}

const SKI_WEIGHTS = {
  beginner: [0.2, 0.05, 0.75],
  intermediate: [0.2, 0.35, 0.45],
  advanced: [0.2, 0.5, 0.3],
  expert: [0.15, 0.55, 0.3],
};

function skillMatch(r, skill) {
  const { beginner: b, intermediate: i, advanced: a } = r;
  const suit = skill === "beginner" ? b : skill === "intermediate" ? b + i : b + i + a;
  const chall = skill === "beginner" ? b + i + a : skill === "intermediate" ? i + a : a;
  if (skill === "beginner") return suit;
  if (skill === "intermediate") return 0.7 * suit + 0.3 * chall;
  return 0.3 * suit + 0.7 * chall;
}

function norm(v, lo, hi) {
  if (hi === lo) return 0.5;
  return Math.max(0, Math.min(1, (v - lo) / (hi - lo)));
}

function scoreResort(r, prefs, cost, ranges) {
  const [wp, wo, ws] = SKI_WEIGHTS[prefs.skill] ?? SKI_WEIGHTS.intermediate;
  const pisteScore = norm(r.pisteKm, ranges.piste[0], ranges.piste[1]);
  const skillScore = skillMatch(r, prefs.skill);
  const skiQuality = wp * pisteScore + wo * (r.offPiste / 5) + ws * skillScore;

  const price = Math.max(0, Math.min(1, 1 - cost.total / prefs.budget));
  const snow = r.snow / 5;
  const nightlife = r.nightlife / 5;
  const convenience = 1 - norm(r.transferMin, ranges.transfer[0], ranges.transfer[1]);
  const accomPct = norm(r.accomPerNight, ranges.accom[0], ranges.accom[1]);
  const target = { budget: 0.15, standard: 0.5, luxury: 0.85 }[prefs.accomTier] ?? 0.5;
  const accommodation = 1 - Math.abs(accomPct - target);

  return { ski_quality: skiQuality, price, snow, nightlife, convenience, accommodation };
}

function rankTrips(prefs) {
  let pool = RESORTS;
  if (prefs.targetResort && prefs.targetResort !== "any") {
    pool = RESORTS.filter((r) => r.name === prefs.targetResort);
  }
  const piste = [Math.min(...RESORTS.map((r) => r.pisteKm)), Math.max(...RESORTS.map((r) => r.pisteKm))];
  const transfer = [Math.min(...RESORTS.map((r) => r.transferMin)), Math.max(...RESORTS.map((r) => r.transferMin))];
  const accom = [Math.min(...RESORTS.map((r) => r.accomPerNight)), Math.max(...RESORTS.map((r) => r.accomPerNight))];
  const ranges = { piste, transfer, accom };

  const wSum = Object.values(prefs.weights).reduce((a, b) => a + b, 0) || 1;
  const weights = Object.fromEntries(Object.entries(prefs.weights).map(([k, v]) => [k, v / wSum]));

  const results = [];
  for (const r of pool) {
    // Explicit rejection, not just "did the cost happen to end up positive":
    // nights=0 doesn't produce a negative total (flight/transfer don't scale
    // with nights), so the cost-sign check alone would have let a
    // nonsensical 0-night trip through. Reject the malformed input directly,
    // the same way Python's UserPreferences.__post_init__ does.
    if (!(prefs.nights > 0) || !(prefs.group >= 1)) continue;
    const cost = computeCost(r, prefs);
    // Number.isFinite rejects NaN, Infinity, AND -Infinity in one check.
    // Previously `cost.total > prefs.budget` was the only gate: a NaN total
    // (invalid equipment/food key) evaluates that comparison as false and
    // was silently INCLUDED in results (rendered as literal "NaN" in the
    // UI); a negative total (negative nights) trivially satisfied "under
    // budget" and was included too. Neither is a real trip.
    if (!Number.isFinite(cost.total) || cost.total <= 0 || cost.total > prefs.budget) continue;
    const comp = scoreResort(r, prefs, cost, ranges);
    // comp[k] ?? 0 rather than a bare lookup: an unrecognized weight key
    // (one not present in comp, e.g. a typo) previously multiplied
    // `undefined * w`, corrupting the ENTIRE score to NaN -- not just that
    // one dimension -- which then sorted unpredictably and rendered as
    // "NaN" in the score badge.
    const score = Object.entries(weights).reduce((s, [k, w]) => s + (comp[k] ?? 0) * w, 0);
    if (!Number.isFinite(score)) continue;
    results.push({ resort: r, cost, comp, score });
  }
  results.sort((a, b) => b.score - a.score);
  return results.slice(0, 6);
}

function explain(t) {
  const labels = {
    ski_quality: "strong skiing/off-piste", price: "good value against your budget",
    snow: "reliable snow", nightlife: "good nightlife", convenience: "short transfer",
    accommodation: "matches your accommodation comfort level",
  };
  const top = Object.entries(t.comp).sort((a, b) => b[1] - a[1]).slice(0, 2).map(([k]) => labels[k]);
  return top.join(" · ");
}

/* ---------------- UI ---------------- */

const FONTS_CSS = `
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root{
  --crevasse:#0B1526; --dusk:#141F33; --panel:#182746; --line:#2A3B5C;
  --snow:#EAF1FB; --snowdim:#9FB3D1;
  --blue:#4A8FE0; --red:#D64545; --amber:#E8A548;
}
* { box-sizing: border-box; }
.lab-root{
  min-height:100vh; background:
    radial-gradient(ellipse 900px 400px at 15% -10%, rgba(74,143,224,0.14), transparent),
    radial-gradient(ellipse 700px 400px at 100% 0%, rgba(232,165,72,0.10), transparent),
    var(--crevasse);
  color:var(--snow); font-family:'Inter',sans-serif;
  padding: 28px 20px 80px;
}
.disp{ font-family:'Space Grotesk',sans-serif; }
.mono{ font-family:'IBM Plex Mono',monospace; }
.wrap{ max-width: 960px; margin:0 auto; }

.topbar{ display:flex; align-items:center; justify-content:space-between; margin-bottom:6px; }
.logo{ display:flex; align-items:center; gap:9px; }
.logo .ski{ font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:19px; letter-spacing:0.01em; }
.logo .lab-tag{ font-family:'IBM Plex Mono',monospace; font-size:10px; letter-spacing:0.1em;
  padding:3px 8px 2px; border:1px solid var(--amber); border-radius:999px; color:var(--amber); }
.auth-cluster{ display:flex; align-items:center; gap:10px; }
.chip{ font-family:'IBM Plex Mono',monospace; font-size:11px; letter-spacing:0.06em; text-transform:uppercase;
  padding:6px 12px; border:1px solid var(--line); border-radius:999px; color:var(--snowdim); background:rgba(255,255,255,0.02);}
.btn-ghost{ font-family:'Inter',sans-serif; font-size:13px; font-weight:500; color:var(--snow); background:transparent;
  border:1px solid var(--line); border-radius:8px; padding:8px 14px; cursor:pointer; transition:all .15s ease;}
.btn-ghost:hover{ border-color:var(--blue); background:rgba(74,143,224,0.08); }

.elevline{ height:42px; margin: 18px 0 30px; opacity:0.55; }

.hero-head{ margin-bottom: 26px; }
.hero-head h1{ font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:40px; line-height:1.05;
  margin:0 0 8px; letter-spacing:-0.01em;}
.hero-head p{ color:var(--snowdim); font-size:15px; margin:0; max-width:520px; }

.panel{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:22px 22px 24px;
  box-shadow: 0 20px 60px -30px rgba(0,0,0,0.6); }

.field-grid{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:18px;}
@media (max-width:760px){ .field-grid{ grid-template-columns:repeat(2,1fr); } }
.field label{ display:block; font-family:'IBM Plex Mono',monospace; font-size:10px; letter-spacing:0.1em;
  text-transform:uppercase; color:var(--snowdim); margin-bottom:7px;}
.field select, .field input[type=number]{
  width:100%; background:var(--dusk); border:1px solid var(--line); border-radius:8px; color:var(--snow);
  font-family:'IBM Plex Mono',monospace; font-size:14px; padding:9px 10px; outline:none; }
.field select:focus, .field input:focus{ border-color:var(--blue); }

.weights-row{ margin-top:4px; }
.weights-label{ font-family:'IBM Plex Mono',monospace; font-size:10px; letter-spacing:0.1em; text-transform:uppercase;
  color:var(--snowdim); margin-bottom:12px; display:block; }
.weight-grid{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px 20px; margin-bottom:20px;}
@media (max-width:760px){ .weight-grid{ grid-template-columns:repeat(2,1fr); } }
.weight-item .wlabel{ display:flex; justify-content:space-between; font-size:12px; color:var(--snowdim); margin-bottom:5px;}
.weight-item .wlabel b{ color:var(--snow); font-weight:500; }
.weight-item .wval{ font-family:'IBM Plex Mono',monospace; color:var(--amber); }
input[type=range]{ width:100%; accent-color:var(--blue); }

.search-btn{ font-family:'Space Grotesk',sans-serif; font-weight:600; font-size:15px; letter-spacing:0.01em;
  background:linear-gradient(135deg,var(--blue),#3A6FB0); color:white; border:none; border-radius:9px;
  padding:13px 22px; cursor:pointer; transition:transform .12s ease, box-shadow .12s ease; width:100%;}
.search-btn:hover{ transform:translateY(-1px); box-shadow:0 10px 30px -10px rgba(74,143,224,0.6);}
.search-btn:active{ transform:translateY(0px) scale(0.99); }

.results-head{ display:flex; justify-content:space-between; align-items:baseline; margin:34px 0 16px; }
.results-head h2{ font-family:'Space Grotesk',sans-serif; font-size:15px; font-weight:600; margin:0;
  color:var(--snowdim); letter-spacing:0.02em; text-transform:uppercase; font-size:11px; }
.results-count{ font-family:'IBM Plex Mono',monospace; font-size:11px; color:var(--snowdim); }

.ticket{ display:grid; grid-template-columns: 230px 1px 1fr; background:var(--panel); border:1px solid var(--line);
  border-radius:16px; margin-bottom:16px; overflow:hidden; opacity:0; transform:translateY(10px);
  animation: rise .5s ease forwards; position:relative; }
@keyframes rise{ to{ opacity:1; transform:translateY(0);} }
@media (max-width:700px){ .ticket{ grid-template-columns: 1fr; } .ticket .perf{ display:none; } }

.ticket:hover{ border-color:var(--blue); }
.ticket .stub{ padding:20px; position:relative; display:flex; flex-direction:column; justify-content:space-between; }
.punch{ position:absolute; width:16px; height:16px; border-radius:50%; background:var(--crevasse);
  border:1px solid var(--line); right:-9px; top:50%; transform:translateY(-50%); z-index:2; }
.perf{ background: repeating-linear-gradient(to bottom, var(--line) 0 6px, transparent 6px 12px); }

.rank-badge{ font-family:'IBM Plex Mono',monospace; font-size:10px; color:var(--snowdim); letter-spacing:0.08em;}
.resort-name{ font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:19px; margin:4px 0 2px; line-height:1.15;}
.resort-sub{ font-size:12px; color:var(--snowdim); margin-bottom:14px; }

.terrain-bar{ display:flex; height:8px; border-radius:5px; overflow:hidden; margin-bottom:6px; }
.terrain-bar .seg-b{ background:var(--blue); } .terrain-bar .seg-i{ background:var(--red); } .terrain-bar .seg-a{ background:var(--amber); }
.terrain-legend{ font-family:'IBM Plex Mono',monospace; font-size:10px; color:var(--snowdim); display:flex; gap:10px; flex-wrap:wrap;}
.terrain-legend span{ display:inline-flex; align-items:center; gap:4px;}
.dot{ width:7px; height:7px; border-radius:50%; display:inline-block; }
.est-flag{ font-size:9px; color:var(--amber); margin-top:6px; font-family:'IBM Plex Mono',monospace; }

.score-block{ text-align:right; }
.score-num{ font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:26px; color:var(--amber); line-height:1;}
.score-lbl{ font-size:10px; color:var(--snowdim); font-family:'IBM Plex Mono',monospace; letter-spacing:0.08em; text-transform:uppercase;}

.detail{ padding:20px 22px; display:flex; flex-direction:column; gap:14px; }
.cost-total{ display:flex; justify-content:space-between; align-items:baseline; border-bottom:1px solid var(--line); padding-bottom:12px;}
.cost-total .amt{ font-family:'IBM Plex Mono',monospace; font-size:24px; font-weight:600; color:var(--snow);}
.cost-total .lbl{ font-size:11px; color:var(--snowdim); }
.cost-grid{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px 16px; }
.cost-line{ font-family:'IBM Plex Mono',monospace; font-size:12px; display:flex; justify-content:space-between; color:var(--snowdim);}
.cost-line b{ color:var(--snow); font-weight:500; }
.why{ font-size:12.5px; color:var(--snowdim); border-top:1px solid var(--line); padding-top:12px; }
.why b{ color:var(--snow); }

.empty{ text-align:center; padding:50px 20px; color:var(--snowdim); font-size:14px; }

.modal-overlay{ position:fixed; inset:0; background:rgba(6,10,18,0.7); backdrop-filter:blur(3px);
  display:flex; align-items:center; justify-content:center; z-index:50; padding:20px;}
.modal{ background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:28px; width:100%; max-width:380px;}
.modal h3{ font-family:'Space Grotesk',sans-serif; margin:0 0 4px; font-size:20px; }
.modal .sub{ color:var(--snowdim); font-size:12px; margin-bottom:20px; }
.google-btn{ width:100%; background:var(--dusk); border:1px solid var(--line); color:var(--snow); border-radius:8px;
  padding:11px; font-family:'Inter',sans-serif; font-size:14px; font-weight:500; cursor:pointer; margin-bottom:12px;
  display:flex; align-items:center; justify-content:center; gap:10px; transition:border-color .15s;}
.google-btn:hover{ border-color:var(--blue); }
.divider{ display:flex; align-items:center; gap:10px; color:var(--snowdim); font-size:11px; margin:14px 0; }
.divider::before, .divider::after{ content:""; flex:1; height:1px; background:var(--line);}
.modal input{ width:100%; background:var(--dusk); border:1px solid var(--line); border-radius:8px; color:var(--snow);
  padding:10px 12px; font-size:13px; margin-bottom:10px; font-family:'Inter',sans-serif;}
.modal-submit{ width:100%; background:var(--blue); color:white; border:none; border-radius:8px; padding:11px;
  font-weight:600; cursor:pointer; margin-top:4px; }
.honesty-note{ margin-top:16px; padding:11px 12px; background:rgba(232,165,72,0.08); border:1px solid rgba(232,165,72,0.3);
  border-radius:8px; font-size:11.5px; color:var(--amber); line-height:1.5; }
.modal-close{ background:none; border:none; color:var(--snowdim); float:right; cursor:pointer; font-size:18px; margin-top:-6px;}
`;

function ElevationLine() {
  return (
    <svg className="elevline" width="100%" height="42" viewBox="0 0 960 42" preserveAspectRatio="none">
      <polyline
        points="0,32 60,28 110,10 170,22 230,6 300,18 360,4 430,20 500,12 560,26 630,8 700,24 780,14 850,28 960,20"
        fill="none" stroke="url(#g1)" strokeWidth="1.5"
      />
      <defs>
        <linearGradient id="g1" x1="0" x2="1">
          <stop offset="0%" stopColor="#4A8FE0" />
          <stop offset="55%" stopColor="#E8A548" />
          <stop offset="100%" stopColor="#D64545" />
        </linearGradient>
      </defs>
    </svg>
  );
}

function AuthModal({ mode, onClose }) {
  const [showNote, setShowNote] = useState(false);
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>&times;</button>
        <h3 className="disp">{mode === "signup" ? "Create account" : "Sign in"}</h3>
        <div className="sub">Track trips and save your search preferences.</div>
        <button className="google-btn" onClick={() => setShowNote(true)}>
          <svg width="16" height="16" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.9 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.1 8 3l6-6C34.5 5.1 29.5 3 24 3 12.4 3 3 12.4 3 24s9.4 21 21 21 21-9.4 21-21c0-1.3-.1-2.7-.4-3.5z"/><path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.5 15.1 18.9 12 24 12c3.1 0 5.8 1.1 8 3l6-6C34.5 5.1 29.5 3 24 3c-7.7 0-14.3 4.4-17.7 10.7z"/><path fill="#4CAF50" d="M24 45c5.4 0 10.3-1.8 14-5l-6.5-5.3c-2 1.4-4.6 2.3-7.5 2.3-5.3 0-9.7-3.1-11.3-7.6l-6.6 5.1C9.6 40.6 16.2 45 24 45z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.4-2.3 4.4-4.3 5.8l6.5 5.3C41.4 35.6 45 30.2 45 24c0-1.3-.1-2.7-.4-3.5z"/></svg>
          Continue with Google
        </button>
        <div className="divider">or</div>
        <input placeholder="Email" />
        <input placeholder="Password" type="password" />
        <button className="modal-submit" onClick={() => setShowNote(true)}>
          {mode === "signup" ? "Sign up" : "Sign in"}
        </button>
        {showNote && (
          <div className="honesty-note">
            Account sign-in isn't wired up yet — this UI is real, but Google OAuth and
            email accounts need a registered backend (real credentials, a hosted domain,
            a database) that we'll set up once we're working on your Mac. Nothing here
            is faking a successful login.
          </div>
        )}
      </div>
    </div>
  );
}

const WEIGHT_LABELS = {
  ski_quality: "Ski quality", price: "Price", snow: "Snow reliability",
  nightlife: "Nightlife", convenience: "Convenience", accommodation: "Accommodation",
};

export default function SkiTripOptimizer() {
  const [budget, setBudget] = useState(1500);
  const [nights, setNights] = useState(5);
  const [group, setGroup] = useState(2);
  const [skill, setSkill] = useState("advanced");
  const [accomTier, setAccomTier] = useState("budget");
  const [food, setFood] = useState("normal");
  const [equipment, setEquipment] = useState("standard");
  const [targetResort, setTargetResort] = useState("any");
  const [weights, setWeights] = useState({
    ski_quality: 35, price: 15, snow: 15, nightlife: 15, convenience: 5, accommodation: 15,
  });
  const [hasSearched, setHasSearched] = useState(false);
  const [authModal, setAuthModal] = useState(null);

  const prefs = { budget, nights, group, skill, accomTier, food, equipment, targetResort, weights };
  const results = useMemo(() => rankTrips(prefs), [budget, nights, group, skill, accomTier, food, equipment, targetResort, weights]);

  return (
    <div className="lab-root">
      <style>{FONTS_CSS}</style>
      <div className="wrap">
        <div className="topbar">
          <div className="logo">
            <svg width="24" height="24" viewBox="0 0 48 48" fill="none">
              <path d="M4,38 L20,12 L26,20 L32,6 L44,38 Z" stroke="url(#logoGrad)" strokeWidth="2.6" strokeLinejoin="round" fill="rgba(74,143,224,0.08)" />
              <circle cx="32" cy="6" r="3" fill="#E8A548" />
              <defs>
                <linearGradient id="logoGrad" x1="0" y1="1" x2="1" y2="0">
                  <stop offset="0%" stopColor="#4A8FE0" />
                  <stop offset="100%" stopColor="#E8A548" />
                </linearGradient>
              </defs>
            </svg>
            <span className="ski disp">SKI</span>
            <span className="lab-tag mono">LAB</span>
          </div>
          <div className="auth-cluster">
            <span className="chip">Guest</span>
            <button className="btn-ghost" onClick={() => setAuthModal("signin")}>Sign in</button>
            <button className="btn-ghost" onClick={() => setAuthModal("signup")}>Sign up</button>
          </div>
        </div>
        <ElevationLine />

        <div className="hero-head">
          <h1 className="disp">Find your run.</h1>
          <p>Set your budget, dates, and what you actually care about — we'll price out real
             trips across {RESORTS.length} European resorts and rank them for you.</p>
        </div>

        <div className="panel">
          <div className="field-grid">
            <div className="field">
              <label>Budget / person (EUR)</label>
              <input type="number" value={budget} min="200" step="50"
                onChange={(e) => setBudget(Math.max(1, Number(e.target.value) || 0))} />
            </div>
            <div className="field">
              <label>Nights</label>
              <input type="number" value={nights} min="2" max="14"
                onChange={(e) => setNights(Math.max(1, Number(e.target.value) || 0))} />
            </div>
            <div className="field">
              <label>Group size</label>
              <input type="number" value={group} min="1" max="12"
                onChange={(e) => setGroup(Math.max(1, Number(e.target.value) || 0))} />
            </div>
            <div className="field">
              <label>Skill level</label>
              <select value={skill} onChange={(e) => setSkill(e.target.value)}>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
                <option value="expert">Expert</option>
              </select>
            </div>
            <div className="field">
              <label>Accommodation</label>
              <select value={accomTier} onChange={(e) => setAccomTier(e.target.value)}>
                <option value="budget">Budget</option>
                <option value="standard">Standard</option>
                <option value="luxury">Luxury</option>
              </select>
            </div>
            <div className="field">
              <label>Food style</label>
              <select value={food} onChange={(e) => setFood(e.target.value)}>
                <option value="budget">Budget</option>
                <option value="normal">Normal</option>
                <option value="luxury">Luxury</option>
              </select>
            </div>
            <div className="field">
              <label>Equipment</label>
              <select value={equipment} onChange={(e) => setEquipment(e.target.value)}>
                <option value="standard">Standard</option>
                <option value="premium">Premium</option>
              </select>
            </div>
            <div className="field">
              <label>Resort</label>
              <select value={targetResort} onChange={(e) => setTargetResort(e.target.value)}>
                <option value="any">Any (discover)</option>
                {RESORTS.map((r) => <option key={r.name} value={r.name}>{r.name}</option>)}
              </select>
            </div>
          </div>

          <div className="weights-row">
            <span className="weights-label">What matters to you (auto-balanced)</span>
            <div className="weight-grid">
              {Object.keys(weights).map((k) => (
                <div className="weight-item" key={k}>
                  <div className="wlabel"><b>{WEIGHT_LABELS[k]}</b><span className="wval">{weights[k]}</span></div>
                  <input type="range" min="0" max="50" value={weights[k]}
                    onChange={(e) => setWeights({ ...weights, [k]: Number(e.target.value) })} />
                </div>
              ))}
            </div>
          </div>

          <button className="search-btn" onClick={() => setHasSearched(true)}>Search trips &#9656;</button>
        </div>

        {hasSearched && (
          <>
            <div className="results-head">
              <h2>Ranked results</h2>
              <span className="results-count mono">{results.length} trip{results.length !== 1 ? "s" : ""} within budget</span>
            </div>

            {results.length === 0 && (
              <div className="empty">No resorts fit €{budget}/person at {nights} nights for a group of {group}.
                Try raising the budget or shortening the trip.</div>
            )}

            {results.map((t, idx) => {
              const r = t.resort;
              return (
                <div className="ticket" key={r.name} style={{ animationDelay: `${idx * 60}ms` }}>
                  <div className="stub">
                    <div className="punch" />
                    <div>
                      <div className="rank-badge mono">TRIP {String(idx + 1).padStart(2, "0")}</div>
                      <div className="resort-name">{r.name}</div>
                      <div className="resort-sub">{r.country} &middot; {r.pisteKm}km piste &middot; {r.transferMin}min from {r.airport}</div>
                    </div>
                    <div>
                      <div className="terrain-bar">
                        <div className="seg-b" style={{ width: `${r.beginner * 100}%` }} />
                        <div className="seg-i" style={{ width: `${r.intermediate * 100}%` }} />
                        <div className="seg-a" style={{ width: `${r.advanced * 100}%` }} />
                      </div>
                      <div className="terrain-legend">
                        <span><i className="dot" style={{ background: "#4A8FE0" }} />{Math.round(r.beginner * 100)}% beg</span>
                        <span><i className="dot" style={{ background: "#D64545" }} />{Math.round(r.intermediate * 100)}% int</span>
                        <span><i className="dot" style={{ background: "#E8A548" }} />{Math.round(r.advanced * 100)}% adv</span>
                      </div>
                      {r.terrainQuality === "estimated" && <div className="est-flag">terrain % estimated, not published</div>}
                      {r.terrainQuality === "sourced_conflicting" && <div className="est-flag">sources disagree on terrain split</div>}
                    </div>
                    <div className="score-block">
                      <div className="score-num mono">{t.score.toFixed(2)}</div>
                      <div className="score-lbl">match score</div>
                    </div>
                  </div>
                  <div className="perf" />
                  <div className="detail">
                    <div className="cost-total">
                      <span className="lbl">Total est. cost / person</span>
                      <span className="amt">&euro;{Math.round(t.cost.total).toLocaleString()}</span>
                    </div>
                    <div className="cost-grid">
                      <div className="cost-line"><span>Flight</span><b>&euro;{Math.round(t.cost.flight)}</b></div>
                      <div className="cost-line"><span>Transfer</span><b>&euro;{Math.round(t.cost.transfer)}</b></div>
                      <div className="cost-line"><span>Stay</span><b>&euro;{Math.round(t.cost.accommodation)}</b></div>
                      <div className="cost-line"><span>Ski pass</span><b>&euro;{Math.round(t.cost.pass)}</b></div>
                      <div className="cost-line"><span>Equipment</span><b>&euro;{Math.round(t.cost.equipment)}</b></div>
                      <div className="cost-line"><span>Food</span><b>&euro;{Math.round(t.cost.food)}</b></div>
                    </div>
                    <div className="why"><b>Why:</b> {explain(t)}
                      {r.needsVerification && " · some resort data here is flagged for verification"}
                    </div>
                  </div>
                </div>
              );
            })}
          </>
        )}
      </div>

      {authModal && <AuthModal mode={authModal} onClose={() => setAuthModal(null)} />}
    </div>
  );
}
