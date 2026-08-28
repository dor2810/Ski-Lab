"""
The MAINSTREAM shortlist: resorts the frontend shows by default.

WHY: searching all 37 resorts surfaced genuinely obscure destinations
(Krvavec, Astun-Candanchu, Poiana Brasov...) alongside the ones people
actually plan trips to, which made results feel random rather than
curated. NOTHING IS DELETED -- every resort remains in the database,
remains fully priced and searchable, and the frontend offers a "show
all" escape hatch. This is a default, not a restriction.

HOW THE LIST WAS BUILT, in two parts:

1. OPERATOR-VERIFIED (24 resorts). Researched 2026-08-27 against the
   real current lineups of three actual ski-package operators, read
   from their own machine-readable sources rather than inferred:
     - skideal.co.il -- site-sitemap.xml (with per-page lastmod dates,
       which distinguishes "currently sold" from "legacy page still
       online") plus the live /winter/ index.
     - Penguin / pingwin.co.il -- sitemap.xml plus their live ski-
       holiday listing page, which is RICHER than their sitemap
       (Zell am See, Avoriaz, Flaine and Les 2 Alpes appear only there).
     - Club Med -- the published Alps village lists on their US, UK and
       FR sites, cross-checked against each other.

2. MARQUEE (7 resorts). A deliberate addition on top of the operator
   data, and the one judgement call in this file. Operator evidence
   alone would have hidden ZERMATT, CHAMONIX, COURCHEVEL, KITZBUHEL,
   CORTINA D'AMPEZZO, VERBIER and OBERGURGL -- among the best-known ski
   destinations in the world. They are absent from those three
   operators not because they are poor destinations but because these
   specific operators do not package them (Zermatt and Verbier are
   expensive with no Club Med village; Courchevel and Chamonix are not
   in the Israeli charter market). A "mainstream" list that omitted
   Zermatt would read as a bug, not as curation.

WHAT IS DEFAULT-HIDDEN (6): Bardonecchia, Poiana Brasov, Kranjska Gora,
Krvavec, Formigal, Astun-Candanchu. These are exactly the resorts that
prompted the complaint -- no operator in the study sells them and none
is a marquee name.

ADJACENCY WAS NOT COUNTED SILENTLY. Club Med's Grand Massif village is
at Samoens/Morillon, not Flaine; both are in the same lift domain, so
Flaine is included on PENGUIN's evidence (which names the village
exactly), not Club Med's. Val Gardena is sold by both Israeli operators
as part of the "Sella Ronda" circuit rather than as the village, which
is recorded honestly below.

Keys MUST match Resort.name exactly as loaded by
data/resort_repository.py -- a test asserts this.
"""

# resort -> why it's on the list. The reason is stored, not just
# membership, so a future reviewer can re-verify or overrule any single
# entry without re-doing the whole study.
MAINSTREAM_RESORTS: dict[str, str] = {
    # --- Sold by all three operators ---
    "Val Thorens": "skideal + Penguin + Club Med (Val Thorens Sensations)",
    "Alpe d'Huez": "skideal + Penguin + Club Med",
    "Val d'Isère / Tignes": "skideal + Penguin + Club Med (villages at both)",
    "Les Arcs": "skideal + Penguin + Club Med (Les Arcs Panorama and Peisey-Vallandry, the resort's own linked domain)",

    # --- Sold by both Israeli operators ---
    "Vallnord (Pal-Arinsal)": "skideal /winter/ + Penguin",
    "St. Anton am Arlberg": "skideal /winter/ + Penguin",
    "Ischgl": "skideal /winter/ + Penguin",
    "Mayrhofen": "skideal /winter/ + Penguin",
    "Zell am See": "skideal /winter/ + Penguin",
    "Bansko": "skideal /winter/ + Penguin",
    "Avoriaz": "skideal /winter/ + Penguin",
    "Les Menuires": "skideal /winter/ + Penguin",

    # --- Sold by one operator ---
    "Pamporovo": "skideal /winter/",
    "Cervinia (Breuil-Cervinia)": "skideal /winter/",
    "Passo Tonale": "skideal /winter/",
    "Grandvalira (Andorra)": "Penguin (Grand Valira + Pas de la Casa)",
    "Sölden": "Penguin",
    "Saalbach-Hinterglemm": "Penguin",
    "Méribel": "Penguin",
    "Les Deux Alpes": "Penguin",
    "Grand Massif (Flaine)": "Penguin (names Flaine exactly; Club Med's village is Samoens/Morillon, same domain but a different village)",
    "Serre Chevalier": "Club Med",
    "Livigno": "skideal page present, though not currently on their /winter/ index",
    "Val Gardena (Selva)": "sold by skideal and Penguin as the Sella Ronda circuit, which includes Selva",

    # --- Added 2026-08-28 at the owner's request, research pass ---
    "Gudauri": "one of the largest Israeli ski markets outside Europe; direct TLV-TBS scheduled service (probed live)",
    "Sella Ronda (Dolomiti)": "the circuit both Israeli operators actually SELL (recorded on the Val Gardena entry since the original study); now a first-class destination row",

    # --- Marquee: no operator in the study, kept anyway. See docstring. ---
    "Zermatt": "MARQUEE -- world-famous; no Club Med village and outside the Israeli charter market",
    "Chamonix": "MARQUEE -- world-famous; not in the studied operators' lineups",
    "Courchevel": "MARQUEE -- world-famous; not in the studied operators' lineups",
    "Kitzbühel": "MARQUEE -- world-famous",
    "Cortina d'Ampezzo": "MARQUEE -- world-famous, 2026 Winter Olympics host",
    "Verbier": "MARQUEE -- world-famous",
    "Obergurgl-Hochgurgl": "MARQUEE -- major Otztal destination, shares the Otztal pass with Solden, which IS sold",
}


# Deliberately default-hidden, with the reason. Kept as data rather than
# a comment so the test suite can assert the two sets partition the
# database exactly, the same way ski_pass_prices.UNPRICED_RESORTS does.
NON_MAINSTREAM_RESORTS: dict[str, str] = {
    "Bardonecchia": "no operator evidence; small Italian resort",
    "Poiana Brasov": "no operator evidence; Romania is outside all three lineups",
    "Kranjska Gora": "no operator evidence; small Slovenian resort",
    "Krvavec": "no operator evidence; small Slovenian resort",
    "Formigal": "no operator evidence; Spanish Pyrenees, outside all three lineups",
    "Astún-Candanchú": "no operator evidence; small Spanish Pyrenees pair",
}


def is_mainstream(resort_name: str) -> bool:
    return resort_name in MAINSTREAM_RESORTS


# The "most popular" one-tap selection, chosen BY THE PROJECT OWNER by
# hand-picking them in the UI on 2026-08-28 and asking for a button that
# selects the set in one tap. It is a curated shortlist of shortlists:
# the destinations worth offering first when someone has no particular
# resort in mind.
#
# NOT derived from the operator research above, and deliberately so --
# that data answers "who sells this?", which is a different question
# from "where would we send someone who hasn't decided?". Recorded as
# an explicit list precisely so it can be re-chosen later without
# anyone having to reverse-engineer the reasoning from the code.
#
# Every entry is asserted to be a real resort name AND a member of
# MAINSTREAM_RESORTS by the test suite -- a name that fell out of the
# mainstream shortlist would otherwise be silently unselectable, since
# the picker only shows mainstream resorts by default.
MOST_POPULAR_RESORTS: tuple[str, ...] = (
    "St. Anton am Arlberg",
    "Ischgl",
    "Sölden",
    "Mayrhofen",
    "Zell am See",
    "Kitzbühel",
    "Val Thorens",
    "Les Arcs",
    "Zermatt",
    "Bansko",
)
