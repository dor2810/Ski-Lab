"""
Curated, per-resort ski/snowboard equipment rental URLs.

Researched and LIVE-VERIFIED for all 37 resorts in this project's data
in one pass -- see engine/links.py's equipment_search_url() for how
this is used. "Verified" means actually curling each candidate URL and
confirming both an HTTP 200 (or sane redirect) AND that the page
content plausibly relates to equipment rental for that resort -- not
trusting a search snippet alone. Independently spot-checked a further
sample across all four research batches before shipping.

Each entry is one of, in descending order of how often it applied:
  - a resort-scoped page on a real rental network (Skiset, INTERSPORT
    Rent, Snowit) -- e.g. skiset.co.uk/ski-resort/{slug}, verified per
    resort, NOT the network's bare homepage;
  - the resort's own official rental page (e.g. lesarcs.com,
    grandvalira.com) where the resort itself runs one;
  - a real, verified local rental operator where neither of the above
    covers that resort (Poiana Brasov -- outside every major network's
    published coverage; Krvavec -- covered by the resort's own lift
    operator directly).

Two corrections from earlier, less rigorous research in this project:
Skiset DOES have real, live resort pages for both Bulgarian resorts
(Bansko, Pamporovo) despite an earlier, wrong assumption that Skiset's
published network excludes Bulgaria. And Skiset's own resort-slug URLs
(skiset.co.uk or skiset.us -- both real, independently verified working
domains for this pattern; skiset.com does NOT reliably support it) DO
resolve directly for most single-village resorts -- an earlier pass
wrongly concluded this required an unresolvable internal autocomplete
ID, based on testing the wrong domain and a couple of bad slug guesses.

Keys MUST match Resort.name exactly as loaded by
data/resort_repository.py -- equipment_search_url() looks this dict up
by that name and falls back to Skiset's front door (or a plain Google
search, for countries outside Skiset's network) for any resort not
present.
"""

EQUIPMENT_RENTAL_URLS: dict[str, str] = {
    # Added 2026-08-28. Gudauri: no Skiset/Intersport coverage in
    # Georgia -- gudauri.com's own rentals page is the local aggregator.
    # Sella Ronda: Skiset serves Selva, the circuit's largest village.
    "Gudauri": "https://gudauri.com/about-gudauri/ski-rentals.html",
    "Grandvalira (Andorra)": "https://www.grandvalira.com/en/services/equipment-rental",
    "St. Anton am Arlberg": "https://www.intersportrent.com/skirent-st-anton-am-arlberg~12382",
    "Kitzbühel": "https://www.intersportrent.com/skirent-kitzbuehel~12413",
    "Ischgl": "https://www.intersportrent.com/skirent-ischgl~12420",
    "Sölden": "https://www.intersportrent.com/skirent-soelden~12400",
    "Saalbach-Hinterglemm": "https://www.intersportrent.com/skirent-saalbach-hinterglemm",
    "Mayrhofen": "https://www.intersportrent.at/skirent-mayrhofen~12406",
    "Zell am See": "https://www.intersportrent.at/skirent-zell-am-see~12383",
    "Bansko": "https://www.skiset.co.uk/ski-resort/bansko",
    "Chamonix": "https://www.skiset.co.uk/ski-resort/chamonix",
    "Val Thorens": "https://www.skiset.co.uk/ski-resort/val-thorens",
    "Courchevel": "https://www.skiset.co.uk/ski-resort/courchevel-1850",
    "Serre Chevalier": "https://www.skiset.co.uk/ski-resort/serre-chevalier",
    "Alpe d'Huez": "https://www.skiset.co.uk/ski-resort/alpe-d-huez",
    "Val d'Isère / Tignes": "https://www.skiset.co.uk/ski-resort/val-d-isere",
    "Les Deux Alpes": "https://reservation.les2alpes.com/location-materiel.html",
    "Grand Massif (Flaine)": "https://www.flaine.com/en/book-your-stay/ski-equipment-rental/",
    "Les Arcs": "https://en.lesarcs.com/equipment-rental",
    "Les Menuires": "https://www.intersportrent.com/skirent-les-menuires~12008583",
    "Livigno": "https://snowit.ski/noleggio-sci-snowboard/livigno",
    "Cervinia (Breuil-Cervinia)": "https://snowit.ski/noleggio-sci-snowboard/cervinia",
    "Val Gardena (Selva)": "https://snowit.ski/noleggio-sci-snowboard/selva-di-val-gardena",
    "Cortina d'Ampezzo": "https://snowit.ski/noleggio-sci-snowboard/cortina-d-ampezzo",
    "Bardonecchia": "https://www.skiset.us/ski-resort/bardonecchia",
    "Passo Tonale": "https://www.skiset.us/ski-resort/passo-tonale",
    "Kranjska Gora": "https://www.skiset.us/ski-resort/kranjska-gora",
    "Zermatt": "https://www.skiset.us/ski-resort/zermatt",
    "Verbier": "https://www.skiset.us/ski-resort/verbier",
}
