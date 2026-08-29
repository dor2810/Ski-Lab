# Resort / airport verification pass — 2026-08-29

Interactive review of all 39 resort+airport pairs. Outcome: **39 -> 29 resorts** (10 dropped).

Method: live TLV flight probes via the Google Flights adapter (SerpAPI), cross-checked
against published airline schedule data, plus coverage checks against
`transfer_quotes`, `transfer_drive_times`, `alps2alps_locations` and `omio_positions`.

## IMPORTANT METHOD CAVEAT

The live Google Flights probe produced **false negatives** for winter dates. Airports
returning "no route" at <=2 stops were, on schedule-data check, well served. A POSITIVE
probe result is trustworthy; a NEGATIVE result means "unconfirmed", never "no service".
Do not re-use the raw probe output as a source of truth.

## Verified airport facts

| IATA | TLV service | Note |
|---|---|---|
| SZG Salzburg | El Al + Israir direct, ~9/wk, EUR274-289 winter | best-connected ski gateway |
| VRN Verona | 4 airlines direct (Arkia, El Al, Israir, Neos) | excellent |
| GVA Geneva | direct El Al + Arkia | probe found only 1-stop EUR537 |
| INN Innsbruck | Israir direct, 1/wk **Fridays only** | constrains trips to Fri->Fri |
| GNB Grenoble | Israir direct, 2/wk | low frequency |
| TRN Turin | Neos direct, route launched Aug 2026 | unproven |
| LYS Lyon | Transavia direct, EUR642 | confirmed by probe |
| TLS Toulouse | no confirmed TLV->TLS direct; 3 airlines 1-stop from ~$284 rt | TUS flies TLS->TLV direct |
| BZO Bolzano | **no direct service** | connection only |
| CMF Chambery | **no confirmed scheduled service** | short transfers are misleading |

Confirmed by live probe (2 adults, round trip): BCN 478, SOF 396 (direct Wizz), VCE 430,
OTP 473, MUC 521 (direct LH), GVA 537, MXP 549, LIN 592, LJU 600, LYS 642 (direct), TBS 674,
BGY 1698.

## Dropped (10)

| Resort | Reason |
|---|---|
| Astun-Candanchu | 3h49 transfer (longest); no Alps2Alps and no Omio coverage at all |
| Formigal | same Pyrenees access problem; no Alps2Alps quote |
| Vallnord (Pal-Arinsal) | no transfer coverage; Grandvalira covers Andorra with a working quote |
| Poiana Brasov | niche with Israeli travellers; no Alps2Alps quote; Bulgaria covered by Bansko |
| Krvavec | 30 km piste / 521 m vertical — too small to justify a flight |
| Sella Ronda (Dolomiti) | a 1200 km **pass area**, not a bookable resort; no transfer or Omio coverage; distorts terrain scoring |
| Pamporovo | real transfer is 3h00 via Sofia (1h29 figure was via unconfirmed PDV); Bansko is better |
| Obergurgl-Hochgurgl | Solden dominates it in the same valley: bigger, cheaper, glacier, has a quote |
| Meribel | near-duplicate of Courchevel; corrupted location data (see BUGS) |
| Avoriaz | 477 m vertical (smallest in DB), 75 km piste, 3/5 snow at EUR140/night |

## Kept (29)

**Andorra (1)** Grandvalira — TLS primary, BCN retained as high-frequency fallback
**Austria (7)** Ischgl · Kitzbuhel · Mayrhofen · Saalbach-Hinterglemm · St. Anton (+MUC added) · Solden · Zell am See
**Bulgaria (1)** Bansko
**France (10)** Alpe d'Huez (GNB low priority) · Chamonix · Courchevel · Grand Massif (Flaine) · Les Arcs · Les Deux Alpes (GNB lower priority) · Les Menuires · Serre Chevalier (LYS added as primary) · Val Thorens · Val d'Isere/Tignes
**Georgia (1)** Gudauri
**Italy (6)** Bardonecchia · Cervinia · Cortina d'Ampezzo · Livigno (MXP+INN) · Passo Tonale (BZO dropped, VRN primary) · Val Gardena (VRN+INN, BZO dropped)
**Slovenia (1)** Kranjska Gora
**Switzerland (2)** Verbier · Zermatt

## BUGS FOUND

1. **Meribel location data is wrong.** Seed and measured drive time both say GVA 55 min /
   77.9 km. Meribel sits between Courchevel (128 min / 134.7 km) and Les Menuires
   (139 min / 145.6 km) in the same valley, so ~2h15 / ~140 km is correct. A geocode error
   that the "measured" drive time inherited. Resort is being dropped, but the geocoding
   path should still be checked — the same fault may affect others.
2. **Stale Olympics warning on Cortina.** Seed says the 2026 Winter Olympics "may affect
   pricing/crowds around that period". Those Games were February 2026 and have passed;
   for winter 2026/27 only the upgraded infrastructure remains.
3. **Zermatt is car-free and the model does not know it.** Every road transfer terminates
   at Tasch; travellers must switch to the shuttle train for the final leg. Alps2Alps and
   Omio quotes to "Zermatt" are really quotes to Tasch, so journey time and cost are
   understated.
4. **Flattering-airport problem (systemic).** Several resorts list a secondary airport with
   a short transfer but no realistic Israeli routing, making total journeys look shorter
   than they are. BZO and CMF are the main offenders. Airport ranking should weigh real
   door-to-door time, not transfer time alone.

## OPEN ACTIONS

- [ ] Apply the 10 drops to `data/ski_resort_database_seed.xlsx`
- [ ] Apply the airport re-pointings listed under "Kept"
- [ ] Fix or remove BZO where it is not a viable gateway; rank CMF below GVA
- [ ] Model Zermatt's Tasch shuttle-train final leg
- [ ] Source a Georgian transfer provider for Gudauri (Alps2Alps is Alps-only — structural gap)
- [ ] Source Omio routes: Saalbach (from SZG), Flaine (from GVA), Val d'Isere (from GVA), Grandvalira
- [ ] Verify Bardonecchia's Turin gateway once Neos' Aug-2026 route has a track record
- [ ] Re-check the geocoding path that produced Meribel's wrong coordinates
