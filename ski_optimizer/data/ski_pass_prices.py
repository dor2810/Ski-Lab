"""
Curated, per-resort REAL published 6-day adult lift pass prices.

Researched 2026-08-27 from each resort's own official ticketing pages
(the ones curated in ski_pass_links.py). Replaces the single
spreadsheet `ski_pass_6day_eur` estimate for the 29 resorts below;
engine/cost_calculator.ski_pass_cost() falls back to the spreadsheet
figure + the global season multiplier for the 8 that are not here.

WHY THIS EXISTS: a real production search on 2026-08-27 showed the ski
pass was the single largest line in a trip total (EUR352 of EUR1,322,
larger than the live flight price) and was a pure static guess. The
blueprint ranks estimate-vs-reality as the project's #1 risk.

THREE DELIBERATE CONVENTIONS, all chosen explicitly by the project
owner rather than defaulted:

  1. ONLINE/ADVANCE rate over counter/walk-up rate, where the operator
     publishes both FOR BOTH SEASON BANDS. Ski Lab users are booking
     ahead by definition, so the counter rate systematically overstates
     what they will actually pay. Where an operator publishes an online
     rate for only ONE band (Soelden/Gurgl publish online for
     pre-season only), the COUNTER rate is used for both bands instead
     -- mixing bases within one resort would corrupt its peak/shoulder
     ratio, which matters more than the ~12% level shift. Each such
     case says so in its note.

  2. LOCAL resort pass over the wider linked-area pass (Courchevel's
     own valley, not all of Les 3 Vallees; Zermatt's Swiss side, not
     the Cervinia-inclusive international pass). This matches what the
     engine actually models: one resort, ranked on its own merits.
     Where the local price is genuinely unobtainable but an area price
     is solid, the area price is used and `scope` is set to "area" so
     the difference is explicit in the data rather than hidden.

  3. PER-RESORT peak prices over one global multiplier. The research
     measured real peak/shoulder ratios from 1.06 (Soelden) to 1.32
     (Bansko) to 2.10 (Passo Tonale, EUR155->EUR325) -- far too wide a
     spread for the engine's single global 1.18 step, which
     under-priced peak weeks at some resorts and over-priced them at
     others.

SEASONS ARE NOT ALIGNED. Some operators had published 2026/27 when this
was researched; others were still on 2025/26. Each entry records which,
because a 2025/26 figure is a year stale, not wrong.

NEVER INVENT A NUMBER: every figure below was read directly off a
published page. Nothing is extrapolated, averaged across sources, or
interpolated between durations. The 8 missing resorts are missing
because a real 6-day adult price could not be honestly obtained -- see
UNPRICED_RESORTS at the bottom for exactly why, one by one.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SkiPassPrice:
    """
    A researched 6-day adult pass price.

    shoulder_eur / peak_eur: at least one is always present. When both
    are, the engine selects by the trip's own season band directly.
    When only one is, the engine scales from it using the global season
    multiplier -- documented, and still far better than the spreadsheet
    estimate, but not the same quality as a two-band entry.

    scope: "local" (this resort's own ski area -- the default and the
    project owner's stated preference) or "area" (a wider linked
    domain, used only where a local figure was genuinely unobtainable).

    quality: "sourced" (read off the operator's own page),
    "sourced_conflicting" (operator page unusable, figure from a
    credible third party, or sources disagreed). Matches the tagging
    convention used everywhere else in this project's data.
    """
    shoulder_eur: Optional[float]
    peak_eur: Optional[float]
    season: str
    scope: str
    quality: str
    note: str

    def __post_init__(self):
        if self.shoulder_eur is None and self.peak_eur is None:
            raise ValueError("a SkiPassPrice needs at least one of shoulder_eur / peak_eur")
        if self.scope not in ("local", "area"):
            raise ValueError(f"scope must be 'local' or 'area', got {self.scope!r}")


# Currency conversions use the ECB reference rates for 2026-08-26
# (frankfurter.dev): CHF->EUR 1.0661, RON->EUR 0.19023. The native
# figure is preserved in each note so the conversion can be redone.
SKI_PASS_PRICES: dict[str, SkiPassPrice] = {

    # --- Austria ---
    "St. Anton am Arlberg": SkiPassPrice(
        380.00, 450.00, "2025/26", "local", "sourced_conflicting",
        "Ski Arlberg. Peak EUR450 confirmed on an operator page (main season 20.12.25-06.04.26); "
        "the EUR380 shoulder figure could NOT be found on an operator page and comes from a "
        "third-party guide -- it does exactly match the value already in the project spreadsheet, "
        "so it is at least self-consistent, but treat it as the weakest number here. Operator's "
        "2026/27 prices were 'being finalized' at research time."),
    "Kitzbühel": SkiPassPrice(
        351.00, 423.00, "2026/27", "local", "sourced",
        "KitzSki, three published bands: Super Saver EUR351 (season start-05.12.26 and "
        "30.03-end), Saver EUR387, Premium EUR423 (20.12.26-13.03.27)."),
    "Ischgl": SkiPassPrice(
        451.00, 451.00, "2026/27", "local", "sourced",
        "Silvretta Ski Pass. FLAT RATE 26.11.26-02.05.27 -- this operator publishes no season "
        "banding at all, so shoulder and peak are deliberately identical, not a copy-paste error."),
    "Sölden": SkiPassPrice(
        450.00, 478.50, "2026/27", "local", "sourced",
        "Oetztal Super Ski Pass, COUNTER rates (pre-season EUR450, main EUR469, peak EUR478.50). "
        "Counter rather than online despite the project's online-first rule: Soelden publishes an "
        "online rate (EUR396) for the pre-season band ONLY, and mixing an online shoulder with a "
        "counter peak would inflate this resort's real 1.06 ratio to 1.21. Booking online is "
        "genuinely ~12% cheaper than shown."),
    "Saalbach-Hinterglemm": SkiPassPrice(
        396.00, 440.00, "2026/27", "local", "sourced",
        "Ski ALPIN CARD. Winter start (27.11-18.12.26) and bonus (13.03-04.04.27) EUR396; peak "
        "(19.12.26-12.03.27) EUR440. Same pass as Zell am See by design -- identical figures there "
        "are correct, not duplication."),
    "Obergurgl-Hochgurgl": SkiPassPrice(
        450.00, 478.50, "2026/27", "local", "sourced",
        "Oetztal Super Ski Pass -- identical to Soelden by design (same pass). Counter rates, for "
        "the same reason given in Soelden's note."),
    "Mayrhofen": SkiPassPrice(
        399.00, 399.00, "2026/27", "local", "sourced",
        "Zillertal Superskipass. FLAT RATE 05.12-12.04, no season bands published -- identical "
        "shoulder/peak is deliberate."),
    "Zell am See": SkiPassPrice(
        396.00, 440.00, "2026/27", "local", "sourced",
        "Ski ALPIN CARD -- same pass as Saalbach-Hinterglemm by design. Main season "
        "19.12.26-12.03.27."),

    # --- Bulgaria ---
    "Bansko": SkiPassPrice(
        259.00, 341.00, "2025/26", "local", "sourced",
        "Operator publishes EUR and BGN side by side (BGN506.56 / BGN666.94), so no conversion was "
        "needed. Ratio 1.32 -- one of the steepest real peak steps found, well above the engine's "
        "old global 1.18."),

    # --- France ---
    "Serre Chevalier": SkiPassPrice(
        276.00, 345.00, "2026/27", "local", "sourced",
        "Standard rates. The operator also publishes an advance-purchase column, but only its low "
        "band is a single figure (EUR220.80); its peak is a RANGE (EUR293.25-331.20), which cannot "
        "be stored as one honest number -- so both bands use the standard rate for consistency. "
        "Booking in advance is genuinely ~20% cheaper than shown."),
    "Val d'Isère / Tignes": SkiPassPrice(
        402.00, 468.00, "2026/27", "local", "sourced",
        "Tignes-Val d'Isere combined pass (300km). Scope is 'local' because this project's resort "
        "entry IS the combined pair -- the Val d'Isere-only zone publishes no 6-day option at all. "
        "Sold as '6 = 7 days'."),
    "Alpe d'Huez": SkiPassPrice(
        None, 336.50, "2026/27", "local", "sourced",
        "Grand Domaine. PEAK ONLY: the operator states reduced rates exist (05-12.12.26, "
        "10-18.04.27) but does not print them, so the shoulder figure is scaled from peak by the "
        "engine's global multiplier rather than invented here."),
    "Courchevel": SkiPassPrice(
        None, 385.00, "2026/27", "local", "sourced",
        "Courchevel valley local pass, peak figure. A low-season column exists on the page but does "
        "not render to text. A +EUR49.50 add-on extends this to all of Les 3 Vallees (EUR421 "
        "direct) -- deliberately NOT used, per the local-pass convention."),
    "Méribel": SkiPassPrice(
        None, 356.00, "2026/27", "local", "sourced",
        "Meribel valley local pass, peak figure; low-season column exists but does not render. "
        "+EUR51 extends to Les 3 Vallees."),
    "Val Thorens": SkiPassPrice(
        None, 421.00, "2026/27", "area", "sourced",
        "SCOPE=AREA, the one French exception: the Val Thorens/Orelle LOCAL 6-day product exists "
        "but its price renders only behind a JS shop, and valthorens.com returns 403 to automated "
        "requests. EUR421 is the verified Les 3 Vallees area pass -- real and valid for Val "
        "Thorens, but broader than this resort alone, so it will overstate a skier who only wants "
        "the local domain."),
    "Grand Massif (Flaine)": SkiPassPrice(
        364.20, 364.20, "2026/27", "local", "sourced_conflicting",
        "Flaine local. FLAT all winter. Flagged conflicting because the operator publishes a "
        "PER-DAY tariff (EUR60.70/day for 2-7 days) rather than a 6-day line item -- EUR364.20 is "
        "that rate times six, which is how they price it, but it is arithmetic rather than a "
        "quoted total. Grand Massif area pass is EUR63.00/day."),
    "Gudauri": SkiPassPrice(
        116.00, None, "2025/26", "local", "sourced",
        "gudauri.com official ski-pass page, researched 2026-08-28: 6-day adult 340 GEL, "
        "converted at ~2.93 GEL/EUR. Single-band tariff (no published season split); the "
        "engine scales peak via the global season multiplier."),
    "Sella Ronda (Dolomiti)": SkiPassPrice(
        None, 357.00, "2025/26", "area", "sourced",
        "SCOPE=AREA by definition: the Sella Ronda circuit is skied on the Dolomiti Superski "
        "pass (450 lifts / 1,200km) -- EUR357 6-day adult, the operator's published 25/26 "
        "figure (26/27 not yet out at research time, dolomitisuperski.com)."),
    "Les Menuires": SkiPassPrice(
        315.00, None, "2026/27", "local", "sourced",
        "Official lesmenuires.com ski-passes page, researched 2026-08-28: 6-day pass EUR315 for "
        "the 5-18 Dec 2026 and 10-18 Apr 2027 windows -- a SHOULDER figure; the peak-season "
        "tariff was not published there yet, so the engine scales peak from this via the global "
        "season multiplier. Replaces the earlier UNPRICED entry (SPA-only site at first research; "
        "the tariff page has since been published)."),
    "Les Deux Alpes": SkiPassPrice(
        263.00, 311.00, "2026/27", "local", "sourced",
        "Official skipass-2alpes.com pricing, researched 2026-08-28: adult 6-day EUR263 for "
        "5-18 Dec 2026 (EUR246.50 for the pre-season 28 Nov-4 Dec week, not used -- outside "
        "any trip this engine prices) and EUR311 peak. Replaces the earlier UNPRICED entry "
        "(site had flipped to summer content at first research)."),
    "Les Arcs": SkiPassPrice(
        368.00, 368.00, "2026/27", "local", "sourced",
        "CLASSIC = Les Arcs/Peisey-Vallandry local, page states '6 DAYS EUR368', no season bands. "
        "Paradiski (ESSENTIAL) EUR412 and PREMIUM EUR491 deliberately not used."),
    "Avoriaz": SkiPassPrice(
        299.00, 352.00, "2026/27", "area", "sourced",
        "SCOPE=AREA: Portes du Soleil INTERNET rates (cash EUR317/EUR373). The Avoriaz-only figure "
        "(~EUR199 internet) was found but in tables whose scope labels are interleaved in embedded "
        "JSON, and EUR33/day is low enough to distrust -- the researcher explicitly flagged it as "
        "needing human confirmation, so the solid area figure is used instead."),

    # --- Italy ---
    "Livigno": SkiPassPrice(
        258.50, 374.50, "2026/27", "local", "sourced",
        "Three published bands: promotional EUR258.50, season EUR331.00, high EUR374.50. Ratio "
        "1.45 -- another well above the old global 1.18."),
    "Cervinia (Breuil-Cervinia)": SkiPassPrice(
        338.00, 338.00, "2026/27", "local", "sourced",
        "Cervinia-Valtournenche local, single price. The Cervinia-Valtournenche-ZERMATT "
        "international pass (EUR464.50) is deliberately not used -- note that Zermatt is a separate "
        "resort in this project's data, so that product would double-count if ever priced jointly."),
    "Val Gardena (Selva)": SkiPassPrice(
        345.80, 383.80, "2025/26", "local", "sourced",
        "Val Gardena/Alpe di Siusi local, ONLINE rates: published EUR364/EUR404 less the "
        "operator's own -5% online discount (applied to both bands equally, so the real ratio is "
        "preserved). Dolomiti Superski area pass would be EUR392/EUR436. Note dolomitisuperski.com "
        "itself returns 403 to automated requests -- figures came from the resort's own site."),
    "Cortina d'Ampezzo": SkiPassPrice(
        345.80, 383.80, "2025/26", "local", "sourced",
        "Cortina local, ONLINE rates: EUR364/EUR404 less the same published -5% online discount. "
        "Same Dolomiti banding as Val Gardena (high = 21.12-10.01 and 01.02-21.03)."),
    "Bardonecchia": SkiPassPrice(
        194.00, 236.50, "2025/26", "local", "sourced_conflicting",
        "THIRD-PARTY SOURCE (dovesciare.it), verified verbatim in static HTML: 'Skipass 6 giorni - "
        "alta stagione 236,50 EUR / bassa stagione 194 EUR'. The operator's own shop is a JS app "
        "with no static content and vialattea.it returns 403 -- so this is the weakest sourcing in "
        "the Italian set. High season 20.12.25-06.01.26 + 01.02-01.03.26."),
    "Passo Tonale": SkiPassPrice(
        155.00, 325.00, "2025/26", "local", "sourced",
        "Pontedilegno-Tonale, from the operator's full consecutive-days table (12 date bands). "
        "RATIO 2.10 -- by far the most extreme real season step found, and the clearest single "
        "justification for storing per-resort peaks instead of one global 1.18 multiplier. Full "
        "6-day spread across all bands: 155/245/255/268/315/325."),

    # --- Romania ---
    "Poiana Brasov": SkiPassPrice(
        171.21, 171.21, "not stated", "local", "sourced",
        "RON900 flat, converted at ECB 2026-08-26 RON->EUR 0.19023. Operator publishes no season "
        "bands for multi-day passes and its page does not state a season year."),

    # --- Slovenia ---
    "Kranjska Gora": SkiPassPrice(
        233.00, 233.00, "2025/26", "local", "sourced",
        "'6 days (with photo - consecutive days) ADULTS 233,00' under a 'WINTER SEASON 2025/26' "
        "header. Contradicts a search snippet claiming EUR162; the operator page was used. NOTE the "
        "price lives on ski-kranjska-gora.com, not the axess.shop buy-link in ski_pass_links.py."),
    "Krvavec": SkiPassPrice(
        198.00, 198.00, "2026/27", "local", "sourced",
        "'6 DNI zaporedni dnevi koriscenja, Odrasli 198,00 EUR' under 'ZIMSKA SEZONA 2026/27'. "
        "TRAP: the same page also carries a stale 2024/25 table (EUR194/EUR190) -- do not re-scrape "
        "this page naively. Price lives on rtc-krvavec.si, not the skipass.krvavec.eu buy-link."),

    # --- Switzerland ---
    "Zermatt": SkiPassPrice(
        409.38, None, "2026/27", "local", "sourced",
        "Zermatt-only (Swiss side): CHF384, converted at ECB 2026-08-26 CHF->EUR 1.0661. SHOULDER "
        "ONLY -- the operator's footnote confirms CHF384 is the lowest price (01-27.11.26 and "
        "19.04-02.05.27) and its peak pricing is dynamic with no published figure, so peak is "
        "scaled by the engine's global multiplier. International pass incl. Cervinia would be "
        "CHF432; deliberately not used."),
    "Verbier": SkiPassPrice(
        398.72, 398.72, "2026/27", "local", "sourced",
        "Verbier-Tzoumaz local: CHF374, converted at ECB 2026-08-26 CHF->EUR 1.0661. No season "
        "bands published (searched explicitly for them). 4 Vallees area pass would be CHF409, "
        "Bruson CHF290."),
}


# The 8 resorts deliberately NOT in the table above, and exactly why.
# Most are structural facts about how those resorts sell passes, not
# research failures -- three of them do not sell a 6-day pass at all.
# These keep using the spreadsheet's ski_pass_6day_eur estimate plus
# the global season multiplier, and stay tagged `estimated`.
UNPRICED_RESORTS: dict[str, str] = {
    "Grandvalira (Andorra)":
        "DYNAMIC PRICING, no published tariff. The operator's own page states 'ski pass prices are "
        "dynamic and may vary throughout the season'; the booking assistant is JS-only. No fixed "
        "6-day price exists to source.",
    "Vallnord (Pal-Arinsal)":
        "DYNAMIC PRICING, same operator group and same model as Grandvalira ('price varies "
        "depending on the purchase date'). No multi-day tariff table exists on the site.",
    "Pamporovo":
        "NO 6-DAY PRODUCT EXISTS. The official Axess webshop's full catalogue is half-day, 1, 2, 3, "
        "4 days, and season. Also a scraping trap for anyone revisiting this: the shop's 'From EUR' "
        "figures are the CHILD price, matching the child column of the operator's own PDF exactly.",
    "Formigal":
        "NO FIXED 6-DAY PRODUCT. Dynamic daily pricing (adult from EUR51.50 counter / EUR43.80 "
        "web) plus a duration discount of 5% rest-of-season and 0% at Christmas. Separate 'Dias "
        "Libres' packs exist for 5d (EUR324.50), 10d and 20d -- but not 6d, and multiplying out a "
        "6-day figure would be invention.",
    "Astún-Candanchú":
        "NO 6-DAY PRODUCT. Multi-day passes are sold only as 3, 5 or 7 consecutive days.",
    "Chamonix":
        "The Mont Blanc Unlimited page is a React app using div-based pseudo-tables. Flattening it "
        "yields six price triplets for six duration headers, but two consecutive triplets are "
        "byte-identical, so the duration-to-price mapping is genuinely ambiguous: the 6-day adult "
        "figure is either EUR240.00-284.00 or EUR329.80-471.20. Picking either would be a guess. "
        "The Chamonix Le Pass page publishes only an unbroken 'Holiday pass' row.",
}
