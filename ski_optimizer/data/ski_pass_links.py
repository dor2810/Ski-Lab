"""
Curated, per-resort official (or clearly legitimate authorized reseller)
ski-pass purchase URLs.

Researched and LIVE-VERIFIED for all 37 resorts in this project's data
in one pass -- see engine/links.py's ski_pass_search_url() for how this
is used. "Verified" means actually curling each candidate URL and
confirming both an HTTP 200 (or sane redirect) AND that the page
content plausibly relates to that resort's lift passes -- not trusting
a search snippet alone. Several resorts share one regional pass system
(e.g. Val Thorens/Meribel/Courchevel all sell "Les 3 Vallees"; Val
Gardena/Cortina d'Ampezzo both sell "Dolomiti Superski") -- pointing
those at the same URL is expected, not a data error.

Two known caveats, both real limitations of the underlying sites, not
research shortcuts:
  - Bardonecchia's likely true official domain (vialattea.it) is
    Cloudflare-protected and returned 403 to both curl and an
    automated fetch during verification -- this points at a verified
    authorized reseller (snowit.ski) instead.
  - Val Gardena's regional aggregator (dolomitisuperski.com) is
    similarly bot-protected -- this points at the resort's own
    valgardena.it page instead, which is real and equivalent.

Keys MUST match Resort.name exactly as loaded by
data/resort_repository.py -- ski_pass_search_url() looks this dict up
by that name and falls back to a plain Google search for any resort
not present (e.g. a resort added to the spreadsheet later, before this
table is extended to cover it).
"""

SKI_PASS_URLS: dict[str, str] = {
    # ORDER-PAGE PASS, 2026-08-29: every link re-checked live (37 of 39
    # resolved; the 2 "failures" were a broken TLS cert and a 403 to
    # automated requests, not dead pages). Where a resort publishes a
    # real WEBSHOP rather than a price list, the link now points at the
    # shop -- Val Gardena's e-shop (5% online discount), Val d'Isere's
    # buy/recharge page, Grand Massif's rates+booking page, Serre
    # Chevalier's pass shop, Vallnord's ski-pass section (its day-pass
    # deep link 404s). Gudauri now points at MTA, the lift operator that
    # actually sells the pass, because gudauri.com's own certificate is
    # broken.
    # Added 2026-08-28 with the Gudauri / Sella Ronda research pass.
    "Gudauri": "https://mta.ski/en",
    "Sella Ronda (Dolomiti)": "https://www.dolomitisuperski.com/en/plan-and-book/lift-pass",
    "Grandvalira (Andorra)": "https://www.grandvalira.com/en/ski-pass/day",
    "Vallnord (Pal-Arinsal)": "https://www.palarinsal.com/en/ski-pass",
    "St. Anton am Arlberg": "https://www.skiarlberg.at/en/tickets-season-times/webshop",
    "Kitzbühel": "https://www.kitzski.at/en/ticket-shop-kitzski.html",
    "Ischgl": "https://tickets.ischgl.com/en/",
    "Sölden": "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview",
    "Saalbach-Hinterglemm": "https://tickets.saalbach.com/en/winter/store",
    "Obergurgl-Hochgurgl": "https://www.gurgl.com/en/activities/winter/skiing-snowboarding/ski-pass-online",
    "Mayrhofen": "https://www.mayrhofen.at/en/pages/skiticket-mountopolis-zillertal",
    "Zell am See": "https://tickets.schmitten.at/en/winter/store",
    "Bansko": "https://www.banskoski.com/en",
    "Pamporovo": "https://webshop.pamporovo.me/en",
    "Chamonix": "https://www.montblancnaturalresort.com/en/ticketing",
    "Val Thorens": "https://www.les3vallees.com/en/skipass",
    "Courchevel": "https://www.les3vallees.com/en/skipass",
    "Serre Chevalier": "https://www.serrechevalier-pass.com/en/",
    "Alpe d'Huez": "https://skipass.alpedhuez.com/hiver/en/all-skipasses/",
    "Méribel": "https://www.les3vallees.com/en/skipass",
    "Val d'Isère / Tignes": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/",
    "Les Deux Alpes": "https://www.skipass-2alpes.com/en/",
    "Grand Massif (Flaine)": "https://www.grand-massif.com/en/ski-offers/package-rates/",
    "Les Arcs": "https://www.lesarcs-peiseyvallandry.com/en/forfaits_offre",
    "Avoriaz": "https://www.skipass-avoriaz.com/en/winter/tickets",
    "Les Menuires": "https://www.skipass-lesmenuires.com/en/",
    "Livigno": "https://www.skipasslivigno.com/en/skipass-shop-online/",
    "Cervinia (Breuil-Cervinia)": "https://www.cervinia.it/en/shop-e-promo",
    "Val Gardena (Selva)": "https://www.valgardena.it/en/winter-holidays-dolomites/ski-passes/skipass-eshop/",
    "Cortina d'Ampezzo": "https://skipasscortina.com/EN/art9-online-is-better",
    "Bardonecchia": "https://snowit.ski/skipass/bardonecchia",
    "Passo Tonale": "https://www.pontedilegnotonale.com/en/ski-pass-and-ski-lifts/pontedilegno-tonale-ski-passes/",
    "Poiana Brasov": "https://ski-poiana-brasov.ro/en/poiana-brasov-ski-pass/",
    "Kranjska Gora": "https://ski-kranjska-gora.axess.shop/",
    "Krvavec": "https://www.skipass.krvavec.eu/",
    "Formigal": "https://www.formigal-panticosa.com/comprar-forfait-formigal-panticosa",
    "Astún-Candanchú": "https://tienda.astuncandanchu.com/tienda/",
    "Zermatt": "https://www.matterhornparadise.ch/en/book/tickets/ski-pass-winter",
    "Verbier": "https://verbier4vallees.ch/en/online-shop/tickets",
}
