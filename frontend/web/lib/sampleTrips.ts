/**
 * REAL captured API responses -- the ONLY mock data in the frontend.
 *
 * WHY THIS FILE EXISTS: design iteration needs realistic values, and a
 * live search takes ~80s. These are verbatim /trips/search-dates
 * results captured from PRODUCTION on 2026-08-29, not invented tidy
 * numbers: Bansko at the budget end (EUR1,057), Zermatt mid
 * (EUR1,316.85) and Val Thorens premium (EUR1,740.19), so any layout
 * built against them survives the real price range, real resort names
 * ("Obergurgl-Hochgurgl" is longer than "Resort A"), missing return
 * flight durations, and mixed live/estimated provenance.
 *
 * The FastAPI backend replaces this entirely -- nothing here is used
 * by the shipped search path; it feeds /design-preview only.
 * Regenerate by capturing a real response rather than editing values
 * by hand, or the layout stops being tested against reality.
 */
import type { TripResult } from "./api";

export const SAMPLE_TRIPS: Record<string, TripResult> = {
  "bansko": {
    "resort": {
      "name": "Bansko",
      "country": "Bulgaria",
      "region": "Pirin Mountains",
      "piste_km": 75.0,
      "off_piste_rating": 2,
      "snow_reliability": 3,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Sofia (SOF)",
      "transfer_time_minutes": 125.0,
      "terrain": {
        "beginner": 0.4,
        "intermediate": 0.4,
        "advanced": 0.2,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2026-12-08",
    "end_date": "2026-12-14",
    "season": "shoulder",
    "cost": {
      "flight_eur": 209.0,
      "transfer_eur": 79.42,
      "accommodation_eur": 132.0,
      "ski_pass_eur": 217.99,
      "equipment_eur": 110.0,
      "food_eur": 180.0,
      "misc_eur": 46.42,
      "total_eur": 974.83,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "score": 0.5761,
    "score_components": {
      "ski_quality": 0.482,
      "price": 0.513,
      "snow": 0.6,
      "nightlife": 0.8,
      "convenience": 0.556,
      "accommodation": 0.633,
      "family": 0.8
    },
    "explanation": "Why: good nightlife, family-friendly, accommodation matching your comfort level. Terrain: 40% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/booking?tfs=CBwQAhpgEgoyMDI2LTEyLTA4Ih8KA1RMVhIKMjAyNi0xMi0wOBoDQVRIKgJBMzIDOTI5Ih8KA0FUSBIKMjAyNi0xMi0wOBoDU09GKgJBMzIDOTgyagcIARIDVExWcgcIARIDU09GGkASCjIwMjYtMTItMTQiIAoDU09GEgoyMDI2LTEyLTE0GgNUTFYqAlc2MgQ0NDI3agcIARIDU09GcgcIARIDVExWQAFIAXABggELCP___________wGYAQE&tfu=CmxDalJJY1ZsNWJGb3dUbXBETXpCQlRHZzJkbWRDUnkwdExTMHRMUzB0TFMwdGIzbGlORUZCUVVGQlIzRlRlRkZKVGxFd1VqWkJFZ1pYTmpRME1qY2FDd2lrb3dFUUFob0RSVlZTT0Ixd2xMMEISAggAIgMKATA&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Zigen%20House%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaQwolEiEyADodWmlnZW4gSG91c2UsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjqDxAMGAgSBwjqDxAMGA4YBjICCAEqCQoFOgNFVVIaAA",
    "accommodation_property_name": "Zigen House",
    "flight_options": [
      {
        "price_eur": 209.0,
        "airline": "Aegean",
        "duration_minutes": 890,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "A3 929",
          "A3 982"
        ],
        "trip_total_eur": 974.83,
        "booking_url": null
      },
      {
        "price_eur": 333.0,
        "airline": "Austrian",
        "duration_minutes": 495,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best"
        ],
        "flight_numbers": [
          "OS 80",
          "OS 779"
        ],
        "trip_total_eur": 1105.03,
        "booking_url": null
      },
      {
        "price_eur": 395.0,
        "airline": "Austrian",
        "duration_minutes": 355,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "OS 84",
          "OS 771"
        ],
        "trip_total_eur": 1170.13,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Zigen House",
        "price_eur_per_night": 44.0,
        "per_person_eur": 132.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 974.83,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Zigen%20House%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaQwolEiEyADodWmlnZW4gSG91c2UsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjqDxAMGAgSBwjqDxAMGA4YBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "BanskoVilla Zlateva House, Bansko",
        "price_eur_per_night": 52.0,
        "per_person_eur": 156.0,
        "is_cheapest": false,
        "rating": 4.6,
        "star_class": 4,
        "review_count": 359,
        "amenities": ["SPA", "PARKING"],
        "distance_to_lifts_km": 0.67,
        "trip_total_eur": 1000.03,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20BanskoVilla%20Zlateva%20House%2C%20Bansko%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWQo7EjcyADozQmFuc2tvVmlsbGEgWmxhdGV2YSBIb3VzZSwgQmFuc2tvLCBCYW5za28sIEJ1bGdhcmlhGgASGhIUCgcI6g8QDBgIEgcI6g8QDBgOGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "Central Apartment Complex / SPA/ Ski-Shuttle",
        "price_eur_per_night": 53.0,
        "per_person_eur": 159.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1003.18,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Central%20Apartment%20Complex%20/%20SPA/%20Ski-Shuttle%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaZApGEkIyADo-Q2VudHJhbCBBcGFydG1lbnQgQ29tcGxleCAvIFNQQS8gU2tpLVNodXR0bGUsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjqDxAMGAgSBwjqDxAMGA4YBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Iceberg Hotel Bansko",
        "price_eur_per_night": 53.0,
        "per_person_eur": 159.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1003.18,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Iceberg%20Hotel%20Bansko%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaTAouEioyADomSWNlYmVyZyBIb3RlbCBCYW5za28sIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjqDxAMGAgSBwjqDxAMGA4YBjICCAEqCQoFOgNFVVIaAA"
      }
    ],
    "total_eur_with_fastest_flight": 1170.13,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-44&to=resort-632&date=2026-12-08&time=14%3A00&adults=2&currency=EUR&vehicle=10",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 222.0,
      "duration_minutes": 180.0,
      "distance_km": 159.5,
      "vehicles_offered": 2,
      "unavailable_reason": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/bansko",
    "ski_pass_search_url": "https://www.banskoski.com/en",
    "weather": {
      "days": [
        {
          "date": "2026-12-08",
          "is_live_forecast": false,
          "temp_max_c": 7.0,
          "temp_min_c": -0.6,
          "snowfall_cm": 0.4,
          "snow_depth_cm": 9.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2026-12-09",
          "is_live_forecast": false,
          "temp_max_c": 9.9,
          "temp_min_c": -0.3,
          "snowfall_cm": 0.3,
          "snow_depth_cm": 9.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2026-12-10",
          "is_live_forecast": false,
          "temp_max_c": 9.2,
          "temp_min_c": 1.1,
          "snowfall_cm": 1.1,
          "snow_depth_cm": 9.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2026-12-11",
          "is_live_forecast": false,
          "temp_max_c": 9.3,
          "temp_min_c": 0.2,
          "snowfall_cm": 0.6,
          "snow_depth_cm": 9.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2026-12-12",
          "is_live_forecast": false,
          "temp_max_c": 8.6,
          "temp_min_c": -0.3,
          "snowfall_cm": 0.6,
          "snow_depth_cm": 8.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2026-12-13",
          "is_live_forecast": false,
          "temp_max_c": 7.5,
          "temp_min_c": -2.1,
          "snowfall_cm": 1.5,
          "snow_depth_cm": 10.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2026-12-14",
          "is_live_forecast": false,
          "temp_max_c": 7.7,
          "temp_min_c": -1.4,
          "snowfall_cm": 0.4,
          "snow_depth_cm": 11.0,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": 8.5,
      "avg_temp_min_c": -0.5,
      "avg_snowfall_cm": 0.7,
      "avg_snow_depth_cm": 9.6
    }
  },
  "valThorens": {
    "resort": {
      "name": "Val Thorens",
      "country": "France",
      "region": "Les Trois Vallées",
      "piste_km": 150.0,
      "off_piste_rating": 4,
      "snow_reliability": 5,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Geneva (GVA) / Chambéry (CMF)",
      "transfer_time_minutes": 151.0,
      "terrain": {
        "beginner": 0.29,
        "intermediate": 0.61,
        "advanced": 0.1,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-10",
    "end_date": "2027-01-16",
    "season": "high",
    "cost": {
      "flight_eur": 281.0,
      "transfer_eur": 102.0,
      "accommodation_eur": 546.0,
      "ski_pass_eur": 330.32,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 82.87,
      "total_eur": 1740.19,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 102.0,
        "duration_minutes": 240,
        "carrier": "AlpyBus",
        "departure": "2027-01-10T10:00:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAwODMiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTAiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIxMDowMCIsImFycml2YWxUaW1lIjoiMTQ6MDAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xNiIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjE0OjAwIiwiYXJyaXZhbFBvc2l0aW9uIjo0NDA0NzAsImRlcGFydHVyZVBvc2l0aW9uIjozMTQ1MjAsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.YUJ362F_ShWh6nLEBJ5M0KmbTT4fYFeie_mXByRI5jc",
        "is_round_trip": true,
        "roles": [
          "cheapest"
        ]
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 108.25,
        "duration_minutes": 195,
        "carrier": "Alpine Fleet",
        "departure": "2027-01-10T09:45:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTAiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIwOTo0NSIsImFycml2YWxUaW1lIjoiMTM6MDAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xNiIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjEzOjAwIiwiYXJyaXZhbFBvc2l0aW9uIjo0NDA0NzAsImRlcGFydHVyZVBvc2l0aW9uIjozMTQ1MjAsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.WgsvdWGjEk7kcncnql2SII1LpKGl8XxUH8iLZDGiIlY",
        "is_round_trip": true,
        "roles": []
      },
      {
        "kind": "private",
        "mode": "minivan",
        "price_eur_per_person": 327.25,
        "duration_minutes": 180,
        "carrier": "Standard minivan",
        "departure": null,
        "booking_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-1&to=resort-80&date=2027-01-10&time=09%3A15&adults=2&currency=EUR&source=claude&ski_bags=2&ski=1&vehicle=10",
        "is_round_trip": true,
        "roles": [
          "fastest"
        ]
      },
      {
        "kind": "private",
        "mode": "minivan",
        "price_eur_per_person": 331.5,
        "duration_minutes": 180,
        "carrier": "Standard XL minivan",
        "departure": null,
        "booking_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-1&to=resort-80&date=2027-01-10&time=09%3A15&adults=2&currency=EUR&source=claude&ski_bags=2&ski=1&vehicle=11",
        "is_round_trip": true,
        "roles": []
      },
      {
        "kind": "private",
        "mode": "minivan",
        "price_eur_per_person": 374.0,
        "duration_minutes": 180,
        "carrier": "Premium minivan",
        "departure": null,
        "booking_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-1&to=resort-80&date=2027-01-10&time=09%3A15&adults=2&currency=EUR&source=claude&ski_bags=2&ski=1&vehicle=12",
        "is_round_trip": true,
        "roles": []
      }
    ],
    "score": 0.6779,
    "score_components": {
      "ski_quality": 0.681,
      "price": 0.426,
      "snow": 1.0,
      "nightlife": 0.8,
      "convenience": 0.417,
      "accommodation": 0.767,
      "family": 0.8
    },
    "explanation": "Why: reliable snow, good nightlife, family-friendly. Terrain: 61% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [
      {
        "start_date": "2027-01-17",
        "end_date": "2027-01-23",
        "season": "high",
        "total_eur": 1768.54,
        "within_budget": true,
        "flight_price_is_live": true,
        "accommodation_price_is_live": true
      },
      {
        "start_date": "2027-01-18",
        "end_date": "2027-01-24",
        "season": "high",
        "total_eur": 1936.54,
        "within_budget": true,
        "flight_price_is_live": true,
        "accommodation_price_is_live": true
      }
    ],
    "flight_search_url": "https://www.google.com/travel/flights/booking?tfs=CBwQAhphEgoyMDI3LTAxLTEwIh8KA1RMVhIKMjAyNy0wMS0xMBoDWlJIKgJMWDIDMjUzIiAKA1pSSBIKMjAyNy0wMS0xMRoDR1ZBKgJMWDIEMjgwMmoHCAESA1RMVnIHCAESA0dWQRphEgoyMDI3LTAxLTE2IiAKA0dWQRIKMjAyNy0wMS0xNhoDWlJIKgJMWDIEMjgxOSIfCgNaUkgSCjIwMjctMDEtMTYaA1RMVioCTFgyAzI1NmoHCAESA0dWQXIHCAESA1RMVkABSAFwAYIBCwj___________8BmAEB&tfu=CnRDalJJVFVOS1JGQkNTRlZDWTI5QlRrdHNjbEZDUnkwdExTMHRMUzB0TFMxdmEzWjZPVUZCUVVGQlIzRlRMVTV6U3pGMk9YRkJFZ3hNV0RJNE1UbDhURmd5TlRZYUN3ankyZ0VRQWhvRFJWVlNPQjF3eWYwQhICCAAiAwoBMA&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20White%20Queen%20Residence%20-%20Queen%20White%20005%20-%20Apartment%20Val%20Thorens%20-4%20pers%20-%202%20Flocons%20Silver%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAalQEKdxJzMgA6b1doaXRlIFF1ZWVuIFJlc2lkZW5jZSAtIFF1ZWVuIFdoaXRlIDAwNSAtIEFwYXJ0bWVudCBWYWwgVGhvcmVucyAtNCBwZXJzIC0gMiBGbG9jb25zIFNpbHZlciwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYChIHCOsPEAEYEBgGMgIIASoJCgU6A0VVUhoA",
    "accommodation_property_name": "White Queen Residence - Queen White 005 - Apartment Val Thorens -4 pers - 2 Flocons Silver",
    "flight_options": [
      {
        "price_eur": 281.0,
        "airline": "SWISS",
        "duration_minutes": 930,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "LX 253",
          "LX 2802"
        ],
        "trip_total_eur": 1740.19,
        "booking_url": null
      },
      {
        "price_eur": 345.0,
        "airline": "Lufthansa",
        "duration_minutes": 695,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best"
        ],
        "flight_numbers": [
          "LH 695",
          "LH 1220"
        ],
        "trip_total_eur": 1807.39,
        "booking_url": null
      },
      {
        "price_eur": 1046.0,
        "airline": "El Al",
        "duration_minutes": 275,
        "stops": 0,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "LY 345"
        ],
        "trip_total_eur": 2543.44,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "White Queen Residence - Queen White 005 - Apartment Val Thorens -4 pers - 2 Flocons Silver",
        "price_eur_per_night": 182.0,
        "per_person_eur": 546.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1740.19,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20White%20Queen%20Residence%20-%20Queen%20White%20005%20-%20Apartment%20Val%20Thorens%20-4%20pers%20-%202%20Flocons%20Silver%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAalQEKdxJzMgA6b1doaXRlIFF1ZWVuIFJlc2lkZW5jZSAtIFF1ZWVuIFdoaXRlIDAwNSAtIEFwYXJ0bWVudCBWYWwgVGhvcmVucyAtNCBwZXJzIC0gMiBGbG9jb25zIFNpbHZlciwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYChIHCOsPEAEYEBgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Résidence & Spa Le Machu Pichu",
        "price_eur_per_night": 246.0,
        "per_person_eur": 738.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1941.79,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20R%C3%A9sidence%20%26%20Spa%20Le%20Machu%20Pichu%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWgo8EjgyADo0UsOpc2lkZW5jZSAmIFNwYSBMZSBNYWNodSBQaWNodSwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYChIHCOsPEAEYEBgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Residence Le Chalet du Mont Vallon",
        "price_eur_per_night": 312.0,
        "per_person_eur": 936.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 2149.69,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Residence%20Le%20Chalet%20du%20Mont%20Vallon%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaXQo_EjsyADo3UmVzaWRlbmNlIExlIENoYWxldCBkdSBNb250IFZhbGxvbiwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYChIHCOsPEAEYEBgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Village Club MMV Les Arolles",
        "price_eur_per_night": 318.0,
        "per_person_eur": 954.0,
        "is_cheapest": false,
        "rating": 3.8,
        "distance_to_lifts_km": 0.01,
        "trip_total_eur": 2168.59,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Village%20Club%20MMV%20Les%20Arolles%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVwo5EjUyADoxVmlsbGFnZSBDbHViIE1NViBMZXMgQXJvbGxlcywgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYChIHCOsPEAEYEBgGMgIIASoJCgU6A0VVUhoA"
      }
    ],
    "total_eur_with_fastest_flight": 2543.44,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-1&to=resort-80&date=2027-01-10&time=09%3A15&adults=2&currency=EUR&source=claude&vehicle=10",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 423.5,
      "duration_minutes": 200.0,
      "distance_km": 155.2,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/val-thorens",
    "ski_pass_search_url": "https://www.les3vallees.com/en/skipass",
    "weather": {
      "days": [
        {
          "date": "2027-01-10",
          "is_live_forecast": false,
          "temp_max_c": -6.4,
          "temp_min_c": -12.1,
          "snowfall_cm": 7.6,
          "snow_depth_cm": 138.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-11",
          "is_live_forecast": false,
          "temp_max_c": -3.3,
          "temp_min_c": -12.5,
          "snowfall_cm": 1.1,
          "snow_depth_cm": 137.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-12",
          "is_live_forecast": false,
          "temp_max_c": -2.6,
          "temp_min_c": -10.1,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 134.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": -2.1,
          "temp_min_c": -8.7,
          "snowfall_cm": 0.6,
          "snow_depth_cm": 132.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 0.3,
          "temp_min_c": -9.9,
          "snowfall_cm": 0.0,
          "snow_depth_cm": 130.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": -1.7,
          "temp_min_c": -9.6,
          "snowfall_cm": 2.8,
          "snow_depth_cm": 130.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-16",
          "is_live_forecast": false,
          "temp_max_c": -4.2,
          "temp_min_c": -14.9,
          "snowfall_cm": 1.4,
          "snow_depth_cm": 131.0,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": -2.9,
      "avg_temp_min_c": -11.1,
      "avg_snowfall_cm": 1.9,
      "avg_snow_depth_cm": 133.5
    }
  },
  "zermatt": {
    "resort": {
      "name": "Zermatt",
      "country": "Switzerland",
      "region": "Matterhorn Glacier Paradise",
      "piste_km": 360.0,
      "off_piste_rating": 4,
      "snow_reliability": 5,
      "nightlife_rating": 3,
      "family_friendliness": 3,
      "nearest_airport": "Geneva (GVA) / Milan Malpensa (MXP)",
      "transfer_time_minutes": 160.0,
      "terrain": {
        "beginner": 0.2,
        "intermediate": 0.55,
        "advanced": 0.25,
        "quality": "sourced_conflicting"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-13",
    "end_date": "2027-01-19",
    "season": "high",
    "cost": {
      "flight_eur": 236.0,
      "transfer_eur": 118.12,
      "accommodation_eur": 123.0,
      "ski_pass_eur": 379.02,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 62.71,
      "total_eur": 1316.85,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 118.12,
        "duration_minutes": 240,
        "carrier": "SBB",
        "departure": "2027-01-13T05:14:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjIiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTMiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIwNToxNCIsImFycml2YWxUaW1lIjoiMDk6MTQiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xOSIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjA5OjE0IiwiYXJyaXZhbFBvc2l0aW9uIjozNzMyOTAsImRlcGFydHVyZVBvc2l0aW9uIjozMTQ1MjAsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoidHJhaW4ifQ.99DWZE85CT2sJBi-ubG-UnYcba3mHaBENDN-YPHtAWA",
        "is_round_trip": true,
        "roles": [
          "cheapest"
        ]
      },
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 118.12,
        "duration_minutes": 242,
        "carrier": "SBB",
        "departure": "2027-01-13T05:45:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjIiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTMiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIwNTo0NSIsImFycml2YWxUaW1lIjoiMDk6NDciLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xOSIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjA5OjQ3IiwiYXJyaXZhbFBvc2l0aW9uIjozNzMyOTAsImRlcGFydHVyZVBvc2l0aW9uIjozMTQ1MjAsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoidHJhaW4ifQ.K0AaGSr7GVIc5_aFmDzOM8uzhKz_LJGWQ5x7Z5a-txY",
        "is_round_trip": true,
        "roles": []
      },
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 118.12,
        "duration_minutes": 262,
        "carrier": "SBB",
        "departure": "2027-01-13T05:25:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjIiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTMiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIwNToyNSIsImFycml2YWxUaW1lIjoiMDk6NDciLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xOSIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjA5OjQ3IiwiYXJyaXZhbFBvc2l0aW9uIjozNzMyOTAsImRlcGFydHVyZVBvc2l0aW9uIjozMTQ1MjAsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoidHJhaW4ifQ.cpteyt-qf7WStPDciFKKQRb9_Iu-lqBej59mXSZs2rg",
        "is_round_trip": true,
        "roles": []
      },
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 118.12,
        "duration_minutes": 468,
        "carrier": "SBB",
        "departure": "2027-01-13T00:26:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjIiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTMiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIwMDoyNiIsImFycml2YWxUaW1lIjoiMDg6MTQiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xOSIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjA4OjE0IiwiYXJyaXZhbFBvc2l0aW9uIjozNzMyOTAsImRlcGFydHVyZVBvc2l0aW9uIjozMTQ1MjAsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoidHJhaW4ifQ.qkGqAFbpYn9exVIvdywV4d2kF97G_DbiBD1cJ_8r3LI",
        "is_round_trip": true,
        "roles": []
      },
      {
        "kind": "private",
        "mode": "minivan",
        "price_eur_per_person": 515.0,
        "duration_minutes": 220,
        "carrier": "Standard minivan",
        "departure": null,
        "booking_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-1&to=resort-256&date=2027-01-13&time=10%3A55&adults=2&currency=EUR&source=claude&ski_bags=2&ski=1&vehicle=10",
        "is_round_trip": true,
        "roles": [
          "fastest"
        ]
      },
      {
        "kind": "private",
        "mode": "minivan",
        "price_eur_per_person": 525.0,
        "duration_minutes": 220,
        "carrier": "Standard XL minivan",
        "departure": null,
        "booking_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-1&to=resort-256&date=2027-01-13&time=10%3A55&adults=2&currency=EUR&source=claude&ski_bags=2&ski=1&vehicle=11",
        "is_round_trip": true,
        "roles": []
      }
    ],
    "score": 0.6495,
    "score_components": {
      "ski_quality": 0.681,
      "price": 0.525,
      "snow": 1.0,
      "nightlife": 0.6,
      "convenience": 0.369,
      "accommodation": 0.633,
      "family": 0.6
    },
    "explanation": "Why: reliable snow, strong skiing/off-piste, accommodation matching your comfort level. Terrain: 55% graded for intermediates (published sources disagree on this — treat as approximate). Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [
      {
        "start_date": "2027-01-10",
        "end_date": "2027-01-16",
        "season": "high",
        "total_eur": 1852.22,
        "within_budget": true,
        "flight_price_is_live": true,
        "accommodation_price_is_live": true
      },
      {
        "start_date": "2027-01-18",
        "end_date": "2027-01-24",
        "season": "high",
        "total_eur": 1822.82,
        "within_budget": true,
        "flight_price_is_live": true,
        "accommodation_price_is_live": true
      }
    ],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMTNqBRIDVExWcgUSA0dWQRoaEgoyMDI3LTAxLTE5agUSA0dWQXIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Testa%20Grigia%2C%20Zermatt%2C%20Switzerland&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaTgowEiwyADooSG90ZWwgVGVzdGEgR3JpZ2lhLCBaZXJtYXR0LCBTd2l0emVybGFuZBoAEhoSFAoHCOsPEAEYDRIHCOsPEAEYExgGMgIIASoJCgU6A0VVUhoA",
    "accommodation_property_name": "Hotel Testa Grigia",
    "flight_options": [
      {
        "price_eur": 236.0,
        "airline": "Aegean",
        "duration_minutes": 350,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest",
          "best"
        ],
        "flight_numbers": [
          "A3 929",
          "A3 660"
        ],
        "trip_total_eur": 1316.85,
        "booking_url": null
      },
      {
        "price_eur": 285.0,
        "airline": "El Al",
        "duration_minutes": 260,
        "stops": 0,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "LY 281"
        ],
        "trip_total_eur": 1368.3,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Hotel Testa Grigia",
        "price_eur_per_night": 41.0,
        "per_person_eur": 123.0,
        "is_cheapest": true,
        "rating": 4.6,
        "distance_to_lifts_km": 0.86,
        "trip_total_eur": 1316.85,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Testa%20Grigia%2C%20Zermatt%2C%20Switzerland&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaTgowEiwyADooSG90ZWwgVGVzdGEgR3JpZ2lhLCBaZXJtYXR0LCBTd2l0emVybGFuZBoAEhoSFAoHCOsPEAEYDRIHCOsPEAEYExgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Studio Alpine Zermatt: Village views & Terrace",
        "price_eur_per_night": 224.0,
        "per_person_eur": 672.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1893.3,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Studio%20Alpine%20Zermatt%3A%20Village%20views%20%26%20Terrace%2C%20Zermatt%2C%20Switzerland&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaagpMEkgyADpEU3R1ZGlvIEFscGluZSBaZXJtYXR0OiBWaWxsYWdlIHZpZXdzICYgVGVycmFjZSwgWmVybWF0dCwgU3dpdHplcmxhbmQaABIaEhQKBwjrDxABGA0SBwjrDxABGBMYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Apartments Zermatt Paradies",
        "price_eur_per_night": 231.0,
        "per_person_eur": 693.0,
        "is_cheapest": false,
        "rating": 4.591954,
        "distance_to_lifts_km": 0.22,
        "trip_total_eur": 1915.35,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Apartments%20Zermatt%20Paradies%2C%20Zermatt%2C%20Switzerland&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVwo5EjUyADoxQXBhcnRtZW50cyBaZXJtYXR0IFBhcmFkaWVzLCBaZXJtYXR0LCBTd2l0emVybGFuZBoAEhoSFAoHCOsPEAEYDRIHCOsPEAEYExgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Hotel Adonis Zermatt",
        "price_eur_per_night": 246.0,
        "per_person_eur": 738.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1962.6,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Adonis%20Zermatt%2C%20Zermatt%2C%20Switzerland&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaUAoyEi4yADoqSG90ZWwgQWRvbmlzIFplcm1hdHQsIFplcm1hdHQsIFN3aXR6ZXJsYW5kGgASGhIUCgcI6w8QARgNEgcI6w8QARgTGAYyAggBKgkKBToDRVVSGgA"
      }
    ],
    "total_eur_with_fastest_flight": 1368.3,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-1&to=resort-256&date=2027-01-13&time=10%3A55&adults=2&currency=EUR&return_date=2027-01-19&return_time=10%3A55&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 618.0,
      "duration_minutes": 240.0,
      "distance_km": 229.5,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.us/ski-resort/zermatt",
    "ski_pass_search_url": "https://www.matterhornparadise.ch/en/book/tickets/ski-pass-winter",
    "weather": {
      "days": [
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": 0.4,
          "temp_min_c": -5.4,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 1402.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 1.1,
          "temp_min_c": -4.3,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 1401.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": -0.1,
          "temp_min_c": -6.3,
          "snowfall_cm": 0.7,
          "snow_depth_cm": 1402.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-16",
          "is_live_forecast": false,
          "temp_max_c": -2.1,
          "temp_min_c": -8.8,
          "snowfall_cm": 1.2,
          "snow_depth_cm": 1241.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-17",
          "is_live_forecast": false,
          "temp_max_c": -1.2,
          "temp_min_c": -5.1,
          "snowfall_cm": 3.8,
          "snow_depth_cm": 759.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-18",
          "is_live_forecast": false,
          "temp_max_c": -0.8,
          "temp_min_c": -4.7,
          "snowfall_cm": 1.5,
          "snow_depth_cm": 760.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-19",
          "is_live_forecast": false,
          "temp_max_c": -2.5,
          "temp_min_c": -7.4,
          "snowfall_cm": 2.3,
          "snow_depth_cm": 761.4,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": -0.7,
      "avg_temp_min_c": -6.0,
      "avg_snowfall_cm": 1.4,
      "avg_snow_depth_cm": 1104.0
    }
  }
} as unknown as Record<string, TripResult>;


/** A real WIDE-WINDOW search (2027-01-04 -> 02-07, 4 resorts): 24
 *  results across 13 start dates, EUR912-1968. Feeds the price
 *  calendar, which needs a realistic spread of dates and gaps --
 *  not every day in a window returns a result, and the calendar
 *  must show those gaps honestly rather than interpolating. */
export const SAMPLE_DATED: TripResult[] = [
  {
    "resort": {
      "name": "Kitzbühel",
      "country": "Austria",
      "region": "Kitzbüheler Alpen (KitzSki)",
      "piste_km": 233.0,
      "off_piste_rating": 3,
      "snow_reliability": 3,
      "nightlife_rating": 5,
      "family_friendliness": 4,
      "nearest_airport": "Innsbruck (INN) / Salzburg (SZG) / Munich (MUC)",
      "transfer_time_minutes": 85.0,
      "terrain": {
        "beginner": 0.2,
        "intermediate": 0.65,
        "advanced": 0.15,
        "quality": "estimated"
      },
      "needs_verification": true
    },
    "start_date": "2027-01-09",
    "end_date": "2027-01-15",
    "season": "high",
    "cost": {
      "flight_eur": 296.0,
      "transfer_eur": 15.0,
      "accommodation_eur": 369.0,
      "ski_pass_eur": 329.09,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 70.36,
      "total_eur": 1477.4499999999998,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 15.0,
        "duration_minutes": 154,
        "carrier": "Train, line 860 bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Innsbruck-Airport/Kitzb%C3%BChel",
        "is_round_trip": false,
        "roles": [
          "cheapest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 75.0
      },
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 18.0,
        "duration_minutes": 136,
        "carrier": "Train",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Innsbruck-Airport/Kitzb%C3%BChel",
        "is_round_trip": false,
        "roles": [
          "fastest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 35.0
      }
    ],
    "score": 0.6452,
    "score_components": {
      "ski_quality": 0.621,
      "price": 0.293,
      "snow": 0.6,
      "nightlife": 1.0,
      "convenience": 0.77,
      "accommodation": 0.833,
      "family": 0.8
    },
    "explanation": "Why: good nightlife, accommodation matching your comfort level, family-friendly. Terrain: 65% graded for intermediates (estimated, not a published figure). (NOTE: some data for this resort is flagged NEEDS VERIFICATION in the seed DB) Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [
      {
        "start_date": "2027-01-11",
        "end_date": "2027-01-17",
        "season": "high",
        "total_eur": 1586.65,
        "within_budget": true,
        "flight_price_is_live": true,
        "accommodation_price_is_live": true
      },
      {
        "start_date": "2027-01-30",
        "end_date": "2027-02-05",
        "season": "high",
        "total_eur": 1594.0,
        "within_budget": true,
        "flight_price_is_live": true,
        "accommodation_price_is_live": true
      }
    ],
    "flight_search_url": "https://www.google.com/travel/flights/booking?tfs=CBwQAhpgEgoyMDI3LTAxLTA5Ih8KA1RMVhIKMjAyNy0wMS0wORoDQVRIKgJBMzIDOTI3Ih8KA0FUSBIKMjAyNy0wMS0xMBoDTVVDKgJBMzIDODAyagcIARIDVExWcgcIARIDTVVDGmASCjIwMjctMDEtMTUiHwoDTVVDEgoyMDI3LTAxLTE1GgNBVEgqAkEzMgM4MDciHwoDQVRIEgoyMDI3LTAxLTE2GgNUTFYqAkEzMgM5MjhqBwgBEgNNVUNyBwgBEgNUTFZAAUgBcAGCAQsI____________AZgBAQ&tfu=CnRDalJJVEZacllYWjNNVk15YjAxQlRscFZWV2RDUnkwdExTMHRMUzB0TFc5NVkydDBOVUZCUVVGQlIzRlVURWRWUVVWVlZHMUJFZ3RCTXpnd04zeEJNemt5T0JvTENKRG5BUkFDR2dORlZWSTRIWERnaXdJPRICCAAiAwoBMA&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Aurach%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaRwopEiUyADohSG90ZWwgQXVyYWNoLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgJEgcI6w8QARgPGAYyAggBKgkKBToDRVVSGgA",
    "accommodation_property_name": "Hotel Aurach",
    "flight_options": [
      {
        "price_eur": 296.0,
        "airline": "Aegean",
        "duration_minutes": 960,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "A3 927",
          "A3 802"
        ],
        "trip_total_eur": 1477.45,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 408.0,
        "airline": "Austrian",
        "duration_minutes": 335,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best",
          "fastest"
        ],
        "flight_numbers": [
          "OS 84",
          "OS 103"
        ],
        "trip_total_eur": 1595.05,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Hotel Aurach",
        "price_eur_per_night": 123.0,
        "per_person_eur": 369.0,
        "is_cheapest": true,
        "rating": 4.3,
        "distance_to_lifts_km": 1.36,
        "trip_total_eur": 1477.45,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Aurach%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaRwopEiUyADohSG90ZWwgQXVyYWNoLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgJEgcI6w8QARgPGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "Safestay Kitzbühel Centre",
        "price_eur_per_night": 178.0,
        "per_person_eur": 534.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1650.7,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Safestay%20Kitzb%C3%BChel%20Centre%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVQo3EjMyADovU2FmZXN0YXkgS2l0emLDvGhlbCBDZW50cmUsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGAkSBwjrDxABGA8YBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Hotel Kitzbühler Alpen",
        "price_eur_per_night": 190.0,
        "per_person_eur": 570.0,
        "is_cheapest": false,
        "rating": 4.6,
        "distance_to_lifts_km": 2.25,
        "trip_total_eur": 1688.5,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Kitzb%C3%BChler%20Alpen%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaUgo0EjAyADosSG90ZWwgS2l0emLDvGhsZXIgQWxwZW4sIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGAkSBwjrDxABGA8YBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Rosi's Sonnbergstuben - Rosi's Alm Kitzbühel",
        "price_eur_per_night": 206.0,
        "per_person_eur": 618.0,
        "is_cheapest": false,
        "rating": 4.5,
        "distance_to_lifts_km": 0.09,
        "trip_total_eur": 1738.9,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Rosi%27s%20Sonnbergstuben%20-%20Rosi%27s%20Alm%20Kitzb%C3%BChel%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaaApKEkYyADpCUm9zaSdzIFNvbm5iZXJnc3R1YmVuIC0gUm9zaSdzIEFsbSBLaXR6YsO8aGVsLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgJEgcI6w8QARgPGAYyAggBKgkKBToDRVVSGgA"
      }
    ],
    "total_eur_with_fastest_flight": 1595.05,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-19&to=resort-169&date=2027-01-09&time=10%3A55&adults=2&currency=EUR&source=claude&vehicle=10",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 306.0,
      "duration_minutes": 145.0,
      "distance_km": 97.8,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.intersportrent.com/skirent-kitzbuehel~12413",
    "ski_pass_search_url": "https://www.kitzski.at/en/ticket-shop-kitzski.html",
    "weather": {
      "days": [
        {
          "date": "2027-01-09",
          "is_live_forecast": false,
          "temp_max_c": 2.4,
          "temp_min_c": -6.1,
          "snowfall_cm": 4.0,
          "snow_depth_cm": 63.0,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-10",
          "is_live_forecast": false,
          "temp_max_c": 1.5,
          "temp_min_c": -7.2,
          "snowfall_cm": 3.9,
          "snow_depth_cm": 65.3,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-11",
          "is_live_forecast": false,
          "temp_max_c": 2.7,
          "temp_min_c": -8.5,
          "snowfall_cm": 1.3,
          "snow_depth_cm": 67.2,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-12",
          "is_live_forecast": false,
          "temp_max_c": 3.5,
          "temp_min_c": -10.8,
          "snowfall_cm": 0.9,
          "snow_depth_cm": 67.0,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": 6.6,
          "temp_min_c": -10.3,
          "snowfall_cm": 0.4,
          "snow_depth_cm": 66.8,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 6.9,
          "temp_min_c": -8.8,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 65.8,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": 5.9,
          "temp_min_c": -4.8,
          "snowfall_cm": 1.9,
          "snow_depth_cm": 65.8,
          "description": null,
          "years_sampled": 4
        }
      ],
      "avg_temp_max_c": 4.2,
      "avg_temp_min_c": -8.1,
      "avg_snowfall_cm": 1.8,
      "avg_snow_depth_cm": 65.8
    }
  },
  {
    "resort": {
      "name": "Val Thorens",
      "country": "France",
      "region": "Les Trois Vallées",
      "piste_km": 150.0,
      "off_piste_rating": 4,
      "snow_reliability": 5,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Geneva (GVA) / Chambéry (CMF)",
      "transfer_time_minutes": 151.0,
      "terrain": {
        "beginner": 0.29,
        "intermediate": 0.61,
        "advanced": 0.1,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-09",
    "end_date": "2027-01-15",
    "season": "high",
    "cost": {
      "flight_eur": 269.0,
      "transfer_eur": 102.0,
      "accommodation_eur": 510.0,
      "ski_pass_eur": 330.32,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 80.47,
      "total_eur": 1689.79,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 102.0,
        "duration_minutes": 240,
        "carrier": "AlpyBus",
        "departure": "2027-01-09T10:00:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAwODMiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMDkiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIxMDowMCIsImFycml2YWxUaW1lIjoiMTQ6MDAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xNSIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjE0OjAwIiwiYXJyaXZhbFBvc2l0aW9uIjo0NDA0NzAsImRlcGFydHVyZVBvc2l0aW9uIjozMTQ1MjAsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.faJq1set4o22B4Njo469Z2UBBTxN-6UTBrfLrQ4NHik",
        "is_round_trip": true,
        "roles": [
          "cheapest"
        ],
        "is_indicative": false,
        "price_high_eur_per_person": null
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 108.25,
        "duration_minutes": 195,
        "carrier": "Alpine Fleet",
        "departure": "2027-01-09T09:30:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMDkiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIwOTozMCIsImFycml2YWxUaW1lIjoiMTI6NDUiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xNSIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjEyOjQ1IiwiYXJyaXZhbFBvc2l0aW9uIjo0NDA0NzAsImRlcGFydHVyZVBvc2l0aW9uIjozMTQ1MjAsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.dULQe48y4RC_nMHGA2PYiTJ9Wy8y6GWLSrEZqU4P6OI",
        "is_round_trip": true,
        "roles": [
          "fastest"
        ],
        "is_indicative": false,
        "price_high_eur_per_person": null
      }
    ],
    "score": 0.6407,
    "score_components": {
      "ski_quality": 0.681,
      "price": 0.24,
      "snow": 1.0,
      "nightlife": 0.8,
      "convenience": 0.417,
      "accommodation": 0.767,
      "family": 0.8
    },
    "explanation": "Why: reliable snow, good nightlife, family-friendly. Terrain: 61% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [
      {
        "start_date": "2027-01-12",
        "end_date": "2027-01-18",
        "season": "high",
        "total_eur": 1677.19,
        "within_budget": true,
        "flight_price_is_live": false,
        "accommodation_price_is_live": false
      },
      {
        "start_date": "2027-01-18",
        "end_date": "2027-01-24",
        "season": "high",
        "total_eur": 1677.19,
        "within_budget": true,
        "flight_price_is_live": false,
        "accommodation_price_is_live": false
      }
    ],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMDlqBRIDVExWcgUSA0dWQRoaEgoyMDI3LTAxLTE1agUSA0dWQXIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Pichu%20Residence%20-%20Temples%20Of%20The%20Sun%20-%20Pichu%20503%20-%20Apartment%20Val%20Thorens%20-%205%20people%20-%202%20Flocons%20Bronze%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaogEKgwESfzIAOntQaWNodSBSZXNpZGVuY2UgLSBUZW1wbGVzIE9mIFRoZSBTdW4gLSBQaWNodSA1MDMgLSBBcGFydG1lbnQgVmFsIFRob3JlbnMgLSA1IHBlb3BsZSAtIDIgRmxvY29ucyBCcm9uemUsIFZhbCBUaG9yZW5zLCBGcmFuY2UaABIaEhQKBwjrDxABGAkSBwjrDxABGA8YBjICCAEqCQoFOgNFVVIaAA",
    "accommodation_property_name": "Pichu Residence - Temples Of The Sun - Pichu 503 - Apartment Val Thorens - 5 people - 2 Flocons Bronze",
    "flight_options": [
      {
        "price_eur": 269.0,
        "airline": "SWISS",
        "duration_minutes": 930,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "LX 253",
          "LX 2802"
        ],
        "trip_total_eur": 1689.79,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 391.0,
        "airline": "Lufthansa",
        "duration_minutes": 415,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best"
        ],
        "flight_numbers": [
          "LH 687",
          "LH 1222"
        ],
        "trip_total_eur": 1817.89,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 539.0,
        "airline": "ITA",
        "duration_minutes": 390,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "AZ 809",
          "AZ 576"
        ],
        "trip_total_eur": 1973.29,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Pichu Residence - Temples Of The Sun - Pichu 503 - Apartment Val Thorens - 5 people - 2 Flocons Bronze",
        "price_eur_per_night": 170.0,
        "per_person_eur": 510.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": 0.08,
        "trip_total_eur": 1689.79,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Pichu%20Residence%20-%20Temples%20Of%20The%20Sun%20-%20Pichu%20503%20-%20Apartment%20Val%20Thorens%20-%205%20people%20-%202%20Flocons%20Bronze%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaogEKgwESfzIAOntQaWNodSBSZXNpZGVuY2UgLSBUZW1wbGVzIE9mIFRoZSBTdW4gLSBQaWNodSA1MDMgLSBBcGFydG1lbnQgVmFsIFRob3JlbnMgLSA1IHBlb3BsZSAtIDIgRmxvY29ucyBCcm9uemUsIFZhbCBUaG9yZW5zLCBGcmFuY2UaABIaEhQKBwjrDxABGAkSBwjrDxABGA8YBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "White Queen Residence - Queen White 005 - Apartment Val Thorens -4 pers - 2 Flocons Silver",
        "price_eur_per_night": 182.0,
        "per_person_eur": 546.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": 0.1,
        "trip_total_eur": 1727.59,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20White%20Queen%20Residence%20-%20Queen%20White%20005%20-%20Apartment%20Val%20Thorens%20-4%20pers%20-%202%20Flocons%20Silver%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAalQEKdxJzMgA6b1doaXRlIFF1ZWVuIFJlc2lkZW5jZSAtIFF1ZWVuIFdoaXRlIDAwNSAtIEFwYXJ0bWVudCBWYWwgVGhvcmVucyAtNCBwZXJzIC0gMiBGbG9jb25zIFNpbHZlciwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYCRIHCOsPEAEYDxgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Résidence & Spa Le Machu Pichu",
        "price_eur_per_night": 246.0,
        "per_person_eur": 738.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1929.19,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20R%C3%A9sidence%20%26%20Spa%20Le%20Machu%20Pichu%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWgo8EjgyADo0UsOpc2lkZW5jZSAmIFNwYSBMZSBNYWNodSBQaWNodSwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYCRIHCOsPEAEYDxgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Residence Le Chalet du Mont Vallon",
        "price_eur_per_night": 284.0,
        "per_person_eur": 852.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 2048.89,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Residence%20Le%20Chalet%20du%20Mont%20Vallon%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaXQo_EjsyADo3UmVzaWRlbmNlIExlIENoYWxldCBkdSBNb250IFZhbGxvbiwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYCRIHCOsPEAEYDxgGMgIIASoJCgU6A0VVUhoA"
      }
    ],
    "total_eur_with_fastest_flight": 1973.29,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-1&to=resort-80&date=2027-01-09&time=09%3A15&adults=2&currency=EUR&return_date=2027-01-15&return_time=09%3A15&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 423.5,
      "duration_minutes": 200.0,
      "distance_km": 155.2,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/val-thorens",
    "ski_pass_search_url": "https://www.les3vallees.com/en/skipass",
    "weather": {
      "days": [
        {
          "date": "2027-01-09",
          "is_live_forecast": false,
          "temp_max_c": -4.3,
          "temp_min_c": -9.8,
          "snowfall_cm": 11.4,
          "snow_depth_cm": 132.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-10",
          "is_live_forecast": false,
          "temp_max_c": -6.4,
          "temp_min_c": -12.1,
          "snowfall_cm": 7.6,
          "snow_depth_cm": 138.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-11",
          "is_live_forecast": false,
          "temp_max_c": -3.3,
          "temp_min_c": -12.5,
          "snowfall_cm": 1.1,
          "snow_depth_cm": 137.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-12",
          "is_live_forecast": false,
          "temp_max_c": -2.6,
          "temp_min_c": -10.1,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 134.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": -2.1,
          "temp_min_c": -8.7,
          "snowfall_cm": 0.6,
          "snow_depth_cm": 132.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 0.3,
          "temp_min_c": -9.9,
          "snowfall_cm": 0.0,
          "snow_depth_cm": 130.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": -1.7,
          "temp_min_c": -9.6,
          "snowfall_cm": 2.8,
          "snow_depth_cm": 130.2,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": -2.9,
      "avg_temp_min_c": -10.4,
      "avg_snowfall_cm": 3.4,
      "avg_snow_depth_cm": 133.6
    }
  },
  {
    "resort": {
      "name": "Bansko",
      "country": "Bulgaria",
      "region": "Pirin Mountains",
      "piste_km": 75.0,
      "off_piste_rating": 2,
      "snow_reliability": 3,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Sofia (SOF)",
      "transfer_time_minutes": 125.0,
      "terrain": {
        "beginner": 0.4,
        "intermediate": 0.4,
        "advanced": 0.2,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-07",
    "end_date": "2027-01-13",
    "season": "high",
    "cost": {
      "flight_eur": 168.0,
      "transfer_eur": 118.12,
      "accommodation_eur": 132.0,
      "ski_pass_eur": 256.33,
      "equipment_eur": 110.0,
      "food_eur": 180.0,
      "misc_eur": 48.23,
      "total_eur": 1012.6800000000001,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 118.12,
        "duration_minutes": 240,
        "carrier": "SBB",
        "departure": "2027-01-09T05:14:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjIiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMDkiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIwNToxNCIsImFycml2YWxUaW1lIjoiMDk6MTQiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xNSIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjA5OjE0IiwiYXJyaXZhbFBvc2l0aW9uIjozNzMyOTAsImRlcGFydHVyZVBvc2l0aW9uIjozMTQ1MjAsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoidHJhaW4ifQ.u_x0kpUOJAhUYkSqRWtRUyBesN4FtgPPrdSHbW010Ac",
        "is_round_trip": true,
        "roles": [
          "cheapest",
          "fastest"
        ],
        "is_indicative": false,
        "price_high_eur_per_person": null
      }
    ],
    "score": 0.5851,
    "score_components": {
      "ski_quality": 0.482,
      "price": 0.558,
      "snow": 0.6,
      "nightlife": 0.8,
      "convenience": 0.556,
      "accommodation": 0.633,
      "family": 0.8
    },
    "explanation": "Why: good nightlife, family-friendly, accommodation matching your comfort level. Terrain: 40% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [
      {
        "start_date": "2027-01-11",
        "end_date": "2027-01-17",
        "season": "high",
        "total_eur": 990.94,
        "within_budget": true,
        "flight_price_is_live": true,
        "accommodation_price_is_live": true
      },
      {
        "start_date": "2027-01-30",
        "end_date": "2027-02-05",
        "season": "high",
        "total_eur": 1003.54,
        "within_budget": true,
        "flight_price_is_live": true,
        "accommodation_price_is_live": true
      }
    ],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMDdqBRIDVExWcgUSA1NPRhoaEgoyMDI3LTAxLTEzagUSA1NPRnIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Zigen%20House%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaQwolEiEyADodWmlnZW4gSG91c2UsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjrDxABGAcSBwjrDxABGA0YBjICCAEqCQoFOgNFVVIaAA",
    "accommodation_property_name": "Zigen House",
    "flight_options": [
      {
        "price_eur": 168.0,
        "airline": "Arkia",
        "duration_minutes": 320,
        "stops": 0,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "IZ 363"
        ],
        "trip_total_eur": 1012.68,
        "return_duration_minutes": 150,
        "booking_url": "https://kiwi.com/u/gtf8gt"
      },
      {
        "price_eur": 193.0,
        "airline": "Israir",
        "duration_minutes": 315,
        "stops": 0,
        "is_cheapest": false,
        "roles": [
          "best",
          "fastest"
        ],
        "flight_numbers": [
          "6H 749"
        ],
        "trip_total_eur": 1038.93,
        "return_duration_minutes": 150,
        "booking_url": "https://kiwi.com/u/xu87dg9"
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Zigen House",
        "price_eur_per_night": 44.0,
        "per_person_eur": 132.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1012.68,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Zigen%20House%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaQwolEiEyADodWmlnZW4gSG91c2UsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjrDxABGAcSBwjrDxABGA0YBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Family House Oreha - Suite (3 Adults)",
        "price_eur_per_night": 47.0,
        "per_person_eur": 141.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1022.13,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Family%20House%20Oreha%20-%20Suite%20%283%20Adults%29%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaXQo_EjsyADo3RmFtaWx5IEhvdXNlIE9yZWhhIC0gU3VpdGUgKDMgQWR1bHRzKSwgQmFuc2tvLCBCdWxnYXJpYRoAEhoSFAoHCOsPEAEYBxIHCOsPEAEYDRgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Cozy nature stay , Great view, free Parking",
        "price_eur_per_night": 62.0,
        "per_person_eur": 186.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1069.38,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Cozy%20nature%20stay%20%2C%20Great%20view%2C%20free%20Parking%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaYwpFEkEyADo9Q296eSBuYXR1cmUgc3RheSAsIEdyZWF0IHZpZXcsIGZyZWUgUGFya2luZywgQmFuc2tvLCBCdWxnYXJpYRoAEhoSFAoHCOsPEAEYBxIHCOsPEAEYDRgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Molerite Wine & Dine",
        "price_eur_per_night": 68.0,
        "per_person_eur": 204.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1088.28,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Molerite%20Wine%20%26%20Dine%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaTAouEioyADomTW9sZXJpdGUgV2luZSAmIERpbmUsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjrDxABGAcSBwjrDxABGA0YBjICCAEqCQoFOgNFVVIaAA"
      }
    ],
    "total_eur_with_fastest_flight": 1038.93,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-44&to=resort-632&date=2027-01-07&time=15%3A35&adults=2&currency=EUR&return_date=2027-01-13&return_time=15%3A35&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 222.0,
      "duration_minutes": 180.0,
      "distance_km": 159.5,
      "vehicles_offered": 2,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/bansko",
    "ski_pass_search_url": "https://www.banskoski.com/en",
    "weather": {
      "days": [
        {
          "date": "2027-01-07",
          "is_live_forecast": false,
          "temp_max_c": 8.7,
          "temp_min_c": 0.2,
          "snowfall_cm": 0.0,
          "snow_depth_cm": 9.8,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-08",
          "is_live_forecast": false,
          "temp_max_c": 8.4,
          "temp_min_c": 0.8,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 11.5,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-09",
          "is_live_forecast": false,
          "temp_max_c": 6.8,
          "temp_min_c": -1.4,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 11.0,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-10",
          "is_live_forecast": false,
          "temp_max_c": 5.9,
          "temp_min_c": -0.5,
          "snowfall_cm": 0.9,
          "snow_depth_cm": 8.5,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-11",
          "is_live_forecast": false,
          "temp_max_c": 4.3,
          "temp_min_c": -1.6,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 9.0,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-12",
          "is_live_forecast": false,
          "temp_max_c": 3.0,
          "temp_min_c": -5.0,
          "snowfall_cm": 3.6,
          "snow_depth_cm": 9.0,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": 2.2,
          "temp_min_c": -6.0,
          "snowfall_cm": 0.3,
          "snow_depth_cm": 8.5,
          "description": null,
          "years_sampled": 4
        }
      ],
      "avg_temp_max_c": 5.6,
      "avg_temp_min_c": -1.9,
      "avg_snowfall_cm": 0.7,
      "avg_snow_depth_cm": 9.6
    }
  },
  {
    "resort": {
      "name": "Zermatt",
      "country": "Switzerland",
      "region": "Matterhorn Glacier Paradise",
      "piste_km": 360.0,
      "off_piste_rating": 4,
      "snow_reliability": 5,
      "nightlife_rating": 3,
      "family_friendliness": 3,
      "nearest_airport": "Geneva (GVA) / Milan Malpensa (MXP)",
      "transfer_time_minutes": 160.0,
      "terrain": {
        "beginner": 0.2,
        "intermediate": 0.55,
        "advanced": 0.25,
        "quality": "sourced_conflicting"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-09",
    "end_date": "2027-01-15",
    "season": "high",
    "cost": {
      "flight_eur": 269.0,
      "transfer_eur": 93.0,
      "accommodation_eur": 408.0,
      "ski_pass_eur": 379.02,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 77.35,
      "total_eur": 1624.37,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 93.0,
        "duration_minutes": 237,
        "carrier": "Train",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Geneva-Airport-GVA/Zermatt",
        "is_round_trip": false,
        "roles": [
          "cheapest",
          "fastest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 265.0
      }
    ],
    "score": 0.5847,
    "score_components": {
      "ski_quality": 0.681,
      "price": 0.201,
      "snow": 1.0,
      "nightlife": 0.6,
      "convenience": 0.369,
      "accommodation": 0.633,
      "family": 0.6
    },
    "explanation": "Why: reliable snow, strong skiing/off-piste, accommodation matching your comfort level. Terrain: 55% graded for intermediates (published sources disagree on this — treat as approximate). Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [
      {
        "start_date": "2027-01-16",
        "end_date": "2027-01-22",
        "season": "high",
        "total_eur": 1978.22,
        "within_budget": true,
        "flight_price_is_live": false,
        "accommodation_price_is_live": false
      },
      {
        "start_date": "2027-01-23",
        "end_date": "2027-01-29",
        "season": "high",
        "total_eur": 1978.22,
        "within_budget": true,
        "flight_price_is_live": false,
        "accommodation_price_is_live": false
      }
    ],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMDlqBRIDVExWcgUSA0dWQRoaEgoyMDI3LTAxLTE1agUSA0dWQXIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Bahnhof%20Zermatt%2C%20Zermatt%2C%20Switzerland&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaUQozEi8yADorSG90ZWwgQmFobmhvZiBaZXJtYXR0LCBaZXJtYXR0LCBTd2l0emVybGFuZBoAEhoSFAoHCOsPEAEYCRIHCOsPEAEYDxgGMgIIASoJCgU6A0VVUhoA",
    "accommodation_property_name": "Hotel Bahnhof Zermatt",
    "flight_options": [
      {
        "price_eur": 269.0,
        "airline": "SWISS",
        "duration_minutes": 930,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "LX 253",
          "LX 2802"
        ],
        "trip_total_eur": 1624.37,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 391.0,
        "airline": "Lufthansa",
        "duration_minutes": 415,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best"
        ],
        "flight_numbers": [
          "LH 687",
          "LH 1222"
        ],
        "trip_total_eur": 1752.47,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 420.0,
        "airline": "Lufthansa + Air Dolomiti",
        "duration_minutes": 385,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "LH 683",
          "EN 1854"
        ],
        "trip_total_eur": 1782.92,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Hotel Bahnhof Zermatt",
        "price_eur_per_night": 136.0,
        "per_person_eur": 408.0,
        "is_cheapest": true,
        "rating": 4.5,
        "distance_to_lifts_km": 1.12,
        "trip_total_eur": 1624.37,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Bahnhof%20Zermatt%2C%20Zermatt%2C%20Switzerland&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaUQozEi8yADorSG90ZWwgQmFobmhvZiBaZXJtYXR0LCBaZXJtYXR0LCBTd2l0emVybGFuZBoAEhoSFAoHCOsPEAEYCRIHCOsPEAEYDxgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Hotel Alpina",
        "price_eur_per_night": 166.0,
        "per_person_eur": 498.0,
        "is_cheapest": false,
        "rating": 4.2,
        "distance_to_lifts_km": 0.71,
        "trip_total_eur": 1718.87,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Alpina%2C%20Zermatt%2C%20Switzerland&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaSAoqEiYyADoiSG90ZWwgQWxwaW5hLCBaZXJtYXR0LCBTd2l0emVybGFuZBoAEhoSFAoHCOsPEAEYCRIHCOsPEAEYDxgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Sonnmatten Restaurant & Suite",
        "price_eur_per_night": 182.0,
        "per_person_eur": 546.0,
        "is_cheapest": false,
        "rating": 4.5,
        "distance_to_lifts_km": 0.24,
        "trip_total_eur": 1769.27,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Sonnmatten%20Restaurant%20%26%20Suite%2C%20Zermatt%2C%20Switzerland&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWQo7EjcyADozU29ubm1hdHRlbiBSZXN0YXVyYW50ICYgU3VpdGUsIFplcm1hdHQsIFN3aXR6ZXJsYW5kGgASGhIUCgcI6w8QARgJEgcI6w8QARgPGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "Hotel Alphubel",
        "price_eur_per_night": 190.0,
        "per_person_eur": 570.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1794.47,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Alphubel%2C%20Zermatt%2C%20Switzerland&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaSgosEigyADokSG90ZWwgQWxwaHViZWwsIFplcm1hdHQsIFN3aXR6ZXJsYW5kGgASGhIUCgcI6w8QARgJEgcI6w8QARgPGAYyAggBKgkKBToDRVVSGgA"
      }
    ],
    "total_eur_with_fastest_flight": 1782.92,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-1&to=resort-256&date=2027-01-09&time=09%3A15&adults=2&currency=EUR&return_date=2027-01-15&return_time=09%3A15&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 618.0,
      "duration_minutes": 240.0,
      "distance_km": 229.5,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.us/ski-resort/zermatt",
    "ski_pass_search_url": "https://www.matterhornparadise.ch/en/book/tickets/ski-pass-winter",
    "weather": {
      "days": [
        {
          "date": "2027-01-09",
          "is_live_forecast": false,
          "temp_max_c": -2.1,
          "temp_min_c": -7.2,
          "snowfall_cm": 5.9,
          "snow_depth_cm": 922.0,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-10",
          "is_live_forecast": false,
          "temp_max_c": -4.5,
          "temp_min_c": -9.3,
          "snowfall_cm": 2.6,
          "snow_depth_cm": 922.0,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-11",
          "is_live_forecast": false,
          "temp_max_c": -1.4,
          "temp_min_c": -9.5,
          "snowfall_cm": 0.4,
          "snow_depth_cm": 921.5,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-12",
          "is_live_forecast": false,
          "temp_max_c": 0.8,
          "temp_min_c": -5.5,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 920.5,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": 1.9,
          "temp_min_c": -3.9,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 919.8,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 1.9,
          "temp_min_c": -3.5,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 919.0,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": 0.7,
          "temp_min_c": -6.1,
          "snowfall_cm": 0.9,
          "snow_depth_cm": 919.5,
          "description": null,
          "years_sampled": 4
        }
      ],
      "avg_temp_max_c": -0.4,
      "avg_temp_min_c": -6.4,
      "avg_snowfall_cm": 1.5,
      "avg_snow_depth_cm": 920.6
    }
  },
  {
    "resort": {
      "name": "Kitzbühel",
      "country": "Austria",
      "region": "Kitzbüheler Alpen (KitzSki)",
      "piste_km": 233.0,
      "off_piste_rating": 3,
      "snow_reliability": 3,
      "nightlife_rating": 5,
      "family_friendliness": 4,
      "nearest_airport": "Innsbruck (INN) / Salzburg (SZG) / Munich (MUC)",
      "transfer_time_minutes": 85.0,
      "terrain": {
        "beginner": 0.2,
        "intermediate": 0.65,
        "advanced": 0.15,
        "quality": "estimated"
      },
      "needs_verification": true
    },
    "start_date": "2027-01-07",
    "end_date": "2027-01-13",
    "season": "high",
    "cost": {
      "flight_eur": 286.0,
      "transfer_eur": 15.0,
      "accommodation_eur": 378.0,
      "ski_pass_eur": 329.09,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 70.31,
      "total_eur": 1476.3999999999999,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 15.0,
        "duration_minutes": 154,
        "carrier": "Train, line 860 bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Innsbruck-Airport/Kitzb%C3%BChel",
        "is_round_trip": false,
        "roles": [
          "cheapest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 75.0
      },
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 18.0,
        "duration_minutes": 136,
        "carrier": "Train",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Innsbruck-Airport/Kitzb%C3%BChel",
        "is_round_trip": false,
        "roles": [
          "fastest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 35.0
      }
    ],
    "score": 0.6452,
    "score_components": {
      "ski_quality": 0.621,
      "price": 0.293,
      "snow": 0.6,
      "nightlife": 1.0,
      "convenience": 0.77,
      "accommodation": 0.833,
      "family": 0.8
    },
    "explanation": "Why: good nightlife, accommodation matching your comfort level, family-friendly. Terrain: 65% graded for intermediates (estimated, not a published figure). (NOTE: some data for this resort is flagged NEEDS VERIFICATION in the seed DB) Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMDdqBRIDVExWcgUSA0lOThoaEgoyMDI3LTAxLTEzagUSA0lOTnIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Aurach%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaRwopEiUyADohSG90ZWwgQXVyYWNoLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgHEgcI6w8QARgNGAYyAggBKgkKBToDRVVSGgA",
    "accommodation_property_name": "Hotel Aurach",
    "flight_options": [
      {
        "price_eur": 286.0,
        "airline": "Aegean",
        "duration_minutes": 785,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "A3 929",
          "A3 806"
        ],
        "trip_total_eur": 1476.4,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 354.0,
        "airline": "Aegean",
        "duration_minutes": 365,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best"
        ],
        "flight_numbers": [
          "A3 925",
          "A3 806"
        ],
        "trip_total_eur": 1547.8,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 455.0,
        "airline": "Lufthansa",
        "duration_minutes": 250,
        "stops": 0,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "LH 681"
        ],
        "trip_total_eur": 1653.85,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Hotel Aurach",
        "price_eur_per_night": 126.0,
        "per_person_eur": 378.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1476.4,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Aurach%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaRwopEiUyADohSG90ZWwgQXVyYWNoLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgHEgcI6w8QARgNGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "Safestay Kitzbühel Centre",
        "price_eur_per_night": 149.0,
        "per_person_eur": 447.0,
        "is_cheapest": false,
        "rating": 4.8,
        "distance_to_lifts_km": 0.32,
        "trip_total_eur": 1548.85,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Safestay%20Kitzb%C3%BChel%20Centre%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVQo3EjMyADovU2FmZXN0YXkgS2l0emLDvGhlbCBDZW50cmUsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGAcSBwjrDxABGA0YBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Hotel Kitzbühler Alpen",
        "price_eur_per_night": 206.0,
        "per_person_eur": 618.0,
        "is_cheapest": false,
        "rating": 4.6,
        "distance_to_lifts_km": 2.25,
        "trip_total_eur": 1728.4,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Kitzb%C3%BChler%20Alpen%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaUgo0EjAyADosSG90ZWwgS2l0emLDvGhsZXIgQWxwZW4sIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGAcSBwjrDxABGA0YBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Rosi's Sonnbergstuben - Rosi's Alm Kitzbühel",
        "price_eur_per_night": 206.0,
        "per_person_eur": 618.0,
        "is_cheapest": false,
        "rating": 4.5,
        "distance_to_lifts_km": 0.09,
        "trip_total_eur": 1728.4,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Rosi%27s%20Sonnbergstuben%20-%20Rosi%27s%20Alm%20Kitzb%C3%BChel%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaaApKEkYyADpCUm9zaSdzIFNvbm5iZXJnc3R1YmVuIC0gUm9zaSdzIEFsbSBLaXR6YsO8aGVsLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgHEgcI6w8QARgNGAYyAggBKgkKBToDRVVSGgA"
      }
    ],
    "total_eur_with_fastest_flight": 1653.85,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-19&to=resort-169&date=2027-01-07&time=18%3A10&adults=2&currency=EUR&return_date=2027-01-13&return_time=18%3A10&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 306.0,
      "duration_minutes": 145.0,
      "distance_km": 97.8,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.intersportrent.com/skirent-kitzbuehel~12413",
    "ski_pass_search_url": "https://www.kitzski.at/en/ticket-shop-kitzski.html",
    "weather": {
      "days": [
        {
          "date": "2027-01-07",
          "is_live_forecast": false,
          "temp_max_c": 2.0,
          "temp_min_c": -6.8,
          "snowfall_cm": 2.9,
          "snow_depth_cm": 57.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-08",
          "is_live_forecast": false,
          "temp_max_c": 2.0,
          "temp_min_c": -9.3,
          "snowfall_cm": 1.3,
          "snow_depth_cm": 58.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-09",
          "is_live_forecast": false,
          "temp_max_c": 3.9,
          "temp_min_c": -5.3,
          "snowfall_cm": 3.5,
          "snow_depth_cm": 62.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-10",
          "is_live_forecast": false,
          "temp_max_c": 1.2,
          "temp_min_c": -8.4,
          "snowfall_cm": 3.5,
          "snow_depth_cm": 61.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-11",
          "is_live_forecast": false,
          "temp_max_c": 1.6,
          "temp_min_c": -9.7,
          "snowfall_cm": 1.1,
          "snow_depth_cm": 63.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-12",
          "is_live_forecast": false,
          "temp_max_c": 2.2,
          "temp_min_c": -10.0,
          "snowfall_cm": 0.9,
          "snow_depth_cm": 66.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": 4.7,
          "temp_min_c": -11.2,
          "snowfall_cm": 0.3,
          "snow_depth_cm": 65.8,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": 2.5,
      "avg_temp_min_c": -8.7,
      "avg_snowfall_cm": 1.9,
      "avg_snow_depth_cm": 62.2
    }
  },
  {
    "resort": {
      "name": "Kitzbühel",
      "country": "Austria",
      "region": "Kitzbüheler Alpen (KitzSki)",
      "piste_km": 233.0,
      "off_piste_rating": 3,
      "snow_reliability": 3,
      "nightlife_rating": 5,
      "family_friendliness": 4,
      "nearest_airport": "Innsbruck (INN) / Salzburg (SZG) / Munich (MUC)",
      "transfer_time_minutes": 85.0,
      "terrain": {
        "beginner": 0.2,
        "intermediate": 0.65,
        "advanced": 0.15,
        "quality": "estimated"
      },
      "needs_verification": true
    },
    "start_date": "2027-01-13",
    "end_date": "2027-01-19",
    "season": "high",
    "cost": {
      "flight_eur": 277.0,
      "transfer_eur": 15.0,
      "accommodation_eur": 390.0,
      "ski_pass_eur": 329.09,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 70.45,
      "total_eur": 1479.54,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 15.0,
        "duration_minutes": 154,
        "carrier": "Train, line 860 bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Innsbruck-Airport/Kitzb%C3%BChel",
        "is_round_trip": false,
        "roles": [
          "cheapest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 75.0
      },
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 18.0,
        "duration_minutes": 136,
        "carrier": "Train",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Innsbruck-Airport/Kitzb%C3%BChel",
        "is_round_trip": false,
        "roles": [
          "fastest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 35.0
      }
    ],
    "score": 0.645,
    "score_components": {
      "ski_quality": 0.621,
      "price": 0.292,
      "snow": 0.6,
      "nightlife": 1.0,
      "convenience": 0.77,
      "accommodation": 0.833,
      "family": 0.8
    },
    "explanation": "Why: good nightlife, accommodation matching your comfort level, family-friendly. Terrain: 65% graded for intermediates (estimated, not a published figure). (NOTE: some data for this resort is flagged NEEDS VERIFICATION in the seed DB) Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMTNqBRIDVExWcgUSA0lOThoaEgoyMDI3LTAxLTE5agUSA0lOTnIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Aurach%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaRwopEiUyADohSG90ZWwgQXVyYWNoLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgNEgcI6w8QARgTGAYyAggBKgkKBToDRVVSGgA",
    "accommodation_property_name": "Hotel Aurach",
    "flight_options": [
      {
        "price_eur": 277.0,
        "airline": "SKY express",
        "duration_minutes": 810,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "GQ 721",
          "GQ 870"
        ],
        "trip_total_eur": 1479.54,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 374.0,
        "airline": "Lufthansa",
        "duration_minutes": 425,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best"
        ],
        "flight_numbers": [
          "LH 695",
          "LH 106"
        ],
        "trip_total_eur": 1581.39,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 426.0,
        "airline": "ITA + Lufthansa",
        "duration_minutes": 400,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "AZ 815",
          "LH 1867"
        ],
        "trip_total_eur": 1635.99,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Hotel Aurach",
        "price_eur_per_night": 130.0,
        "per_person_eur": 390.0,
        "is_cheapest": true,
        "rating": 4.3,
        "distance_to_lifts_km": 1.36,
        "trip_total_eur": 1479.54,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Aurach%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaRwopEiUyADohSG90ZWwgQXVyYWNoLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgNEgcI6w8QARgTGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "Ferienhotel Alpenhof",
        "price_eur_per_night": 143.0,
        "per_person_eur": 429.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1520.49,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Ferienhotel%20Alpenhof%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaTwoxEi0yADopRmVyaWVuaG90ZWwgQWxwZW5ob2YsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGA0SBwjrDxABGBMYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Hotel Neuwirt Kaiserhotels",
        "price_eur_per_night": 205.0,
        "per_person_eur": 615.0,
        "is_cheapest": false,
        "rating": 4.4,
        "distance_to_lifts_km": 3.0,
        "trip_total_eur": 1715.79,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Neuwirt%20Kaiserhotels%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVQo3EjMyADovSG90ZWwgTmV1d2lydCBLYWlzZXJob3RlbHMsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGA0SBwjrDxABGBMYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Hotel Garni Entstrasser",
        "price_eur_per_night": 240.0,
        "per_person_eur": 720.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1826.04,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Garni%20Entstrasser%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaUgo0EjAyADosSG90ZWwgR2FybmkgRW50c3RyYXNzZXIsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGA0SBwjrDxABGBMYBjICCAEqCQoFOgNFVVIaAA"
      }
    ],
    "total_eur_with_fastest_flight": 1635.99,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-19&to=resort-169&date=2027-01-13&time=12%3A45&adults=2&currency=EUR&return_date=2027-01-19&return_time=12%3A45&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 306.0,
      "duration_minutes": 145.0,
      "distance_km": 97.8,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.intersportrent.com/skirent-kitzbuehel~12413",
    "ski_pass_search_url": "https://www.kitzski.at/en/ticket-shop-kitzski.html",
    "weather": {
      "days": [
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": 6.6,
          "temp_min_c": -10.3,
          "snowfall_cm": 0.4,
          "snow_depth_cm": 66.8,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 6.9,
          "temp_min_c": -8.8,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 65.8,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": 5.9,
          "temp_min_c": -4.8,
          "snowfall_cm": 1.9,
          "snow_depth_cm": 65.8,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-16",
          "is_live_forecast": false,
          "temp_max_c": 5.2,
          "temp_min_c": -8.6,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 65.2,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-17",
          "is_live_forecast": false,
          "temp_max_c": 5.0,
          "temp_min_c": -8.8,
          "snowfall_cm": 0.8,
          "snow_depth_cm": 65.5,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-18",
          "is_live_forecast": false,
          "temp_max_c": 5.1,
          "temp_min_c": -3.9,
          "snowfall_cm": 2.0,
          "snow_depth_cm": 70.5,
          "description": null,
          "years_sampled": 4
        },
        {
          "date": "2027-01-19",
          "is_live_forecast": false,
          "temp_max_c": 3.4,
          "temp_min_c": -8.7,
          "snowfall_cm": 1.3,
          "snow_depth_cm": 73.0,
          "description": null,
          "years_sampled": 4
        }
      ],
      "avg_temp_max_c": 5.4,
      "avg_temp_min_c": -7.7,
      "avg_snowfall_cm": 1.0,
      "avg_snow_depth_cm": 67.5
    }
  },
  {
    "resort": {
      "name": "Kitzbühel",
      "country": "Austria",
      "region": "Kitzbüheler Alpen (KitzSki)",
      "piste_km": 233.0,
      "off_piste_rating": 3,
      "snow_reliability": 3,
      "nightlife_rating": 5,
      "family_friendliness": 4,
      "nearest_airport": "Innsbruck (INN) / Salzburg (SZG) / Munich (MUC)",
      "transfer_time_minutes": 85.0,
      "terrain": {
        "beginner": 0.2,
        "intermediate": 0.65,
        "advanced": 0.15,
        "quality": "estimated"
      },
      "needs_verification": true
    },
    "start_date": "2027-01-10",
    "end_date": "2027-01-16",
    "season": "high",
    "cost": {
      "flight_eur": 315.0,
      "transfer_eur": 15.0,
      "accommodation_eur": 357.0,
      "ski_pass_eur": 329.09,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 70.7,
      "total_eur": 1484.79,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 15.0,
        "duration_minutes": 154,
        "carrier": "Train, line 860 bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Innsbruck-Airport/Kitzb%C3%BChel",
        "is_round_trip": false,
        "roles": [
          "cheapest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 75.0
      },
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 18.0,
        "duration_minutes": 136,
        "carrier": "Train",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Innsbruck-Airport/Kitzb%C3%BChel",
        "is_round_trip": false,
        "roles": [
          "fastest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 35.0
      }
    ],
    "score": 0.6444,
    "score_components": {
      "ski_quality": 0.621,
      "price": 0.289,
      "snow": 0.6,
      "nightlife": 1.0,
      "convenience": 0.77,
      "accommodation": 0.833,
      "family": 0.8
    },
    "explanation": "Why: good nightlife, accommodation matching your comfort level, family-friendly. Terrain: 65% graded for intermediates (estimated, not a published figure). (NOTE: some data for this resort is flagged NEEDS VERIFICATION in the seed DB) Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMTBqBRIDVExWcgUSA0lOThoaEgoyMDI3LTAxLTE2agUSA0lOTnIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Aurach%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaRwopEiUyADohSG90ZWwgQXVyYWNoLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgKEgcI6w8QARgQGAYyAggBKgkKBToDRVVSGgA",
    "accommodation_property_name": "Hotel Aurach",
    "flight_options": [
      {
        "price_eur": 315.0,
        "airline": "Aegean",
        "duration_minutes": 960,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "A3 927",
          "A3 802"
        ],
        "trip_total_eur": 1484.79,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 437.0,
        "airline": "Lufthansa",
        "duration_minutes": 415,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best"
        ],
        "flight_numbers": [
          "LH 687",
          "LH 1266"
        ],
        "trip_total_eur": 1612.89,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 1060.0,
        "airline": "El Al",
        "duration_minutes": 255,
        "stops": 0,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "LY 351"
        ],
        "trip_total_eur": 2267.04,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Hotel Aurach",
        "price_eur_per_night": 119.0,
        "per_person_eur": 357.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1484.79,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Aurach%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaRwopEiUyADohSG90ZWwgQXVyYWNoLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgKEgcI6w8QARgQGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "Safestay Kitzbühel Centre",
        "price_eur_per_night": 178.0,
        "per_person_eur": 534.0,
        "is_cheapest": false,
        "rating": 4.8,
        "distance_to_lifts_km": 0.32,
        "trip_total_eur": 1670.64,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Safestay%20Kitzb%C3%BChel%20Centre%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVQo3EjMyADovU2FmZXN0YXkgS2l0emLDvGhlbCBDZW50cmUsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGAoSBwjrDxABGBAYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Hotel Neuwirt Kaiserhotels",
        "price_eur_per_night": 205.0,
        "per_person_eur": 615.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1755.69,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Neuwirt%20Kaiserhotels%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVQo3EjMyADovSG90ZWwgTmV1d2lydCBLYWlzZXJob3RlbHMsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGAoSBwjrDxABGBAYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Hotel Garni Entstrasser",
        "price_eur_per_night": 207.0,
        "per_person_eur": 621.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1761.99,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Garni%20Entstrasser%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaUgo0EjAyADosSG90ZWwgR2FybmkgRW50c3RyYXNzZXIsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGAoSBwjrDxABGBAYBjICCAEqCQoFOgNFVVIaAA"
      }
    ],
    "total_eur_with_fastest_flight": 2267.04,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-19&to=resort-169&date=2027-01-10&time=10%3A55&adults=2&currency=EUR&return_date=2027-01-16&return_time=10%3A55&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 306.0,
      "duration_minutes": 145.0,
      "distance_km": 97.8,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.intersportrent.com/skirent-kitzbuehel~12413",
    "ski_pass_search_url": "https://www.kitzski.at/en/ticket-shop-kitzski.html",
    "weather": {
      "days": [
        {
          "date": "2027-01-10",
          "is_live_forecast": false,
          "temp_max_c": 1.2,
          "temp_min_c": -8.4,
          "snowfall_cm": 3.5,
          "snow_depth_cm": 61.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-11",
          "is_live_forecast": false,
          "temp_max_c": 1.6,
          "temp_min_c": -9.7,
          "snowfall_cm": 1.1,
          "snow_depth_cm": 63.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-12",
          "is_live_forecast": false,
          "temp_max_c": 2.2,
          "temp_min_c": -10.0,
          "snowfall_cm": 0.9,
          "snow_depth_cm": 66.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": 4.7,
          "temp_min_c": -11.2,
          "snowfall_cm": 0.3,
          "snow_depth_cm": 65.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 6.3,
          "temp_min_c": -10.2,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 64.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": 4.6,
          "temp_min_c": -5.7,
          "snowfall_cm": 1.9,
          "snow_depth_cm": 63.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-16",
          "is_live_forecast": false,
          "temp_max_c": 4.8,
          "temp_min_c": -8.4,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 65.4,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": 3.6,
      "avg_temp_min_c": -9.1,
      "avg_snowfall_cm": 1.1,
      "avg_snow_depth_cm": 64.3
    }
  },
  {
    "resort": {
      "name": "Kitzbühel",
      "country": "Austria",
      "region": "Kitzbüheler Alpen (KitzSki)",
      "piste_km": 233.0,
      "off_piste_rating": 3,
      "snow_reliability": 3,
      "nightlife_rating": 5,
      "family_friendliness": 4,
      "nearest_airport": "Innsbruck (INN) / Salzburg (SZG) / Munich (MUC)",
      "transfer_time_minutes": 85.0,
      "terrain": {
        "beginner": 0.2,
        "intermediate": 0.65,
        "advanced": 0.15,
        "quality": "estimated"
      },
      "needs_verification": true
    },
    "start_date": "2027-01-08",
    "end_date": "2027-01-14",
    "season": "high",
    "cost": {
      "flight_eur": 334.0,
      "transfer_eur": 15.0,
      "accommodation_eur": 351.0,
      "ski_pass_eur": 329.09,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 71.36,
      "total_eur": 1498.4499999999998,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 15.0,
        "duration_minutes": 154,
        "carrier": "Train, line 860 bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Innsbruck-Airport/Kitzb%C3%BChel",
        "is_round_trip": false,
        "roles": [
          "cheapest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 75.0
      },
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 18.0,
        "duration_minutes": 136,
        "carrier": "Train",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Innsbruck-Airport/Kitzb%C3%BChel",
        "is_round_trip": false,
        "roles": [
          "fastest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 35.0
      }
    ],
    "score": 0.6432,
    "score_components": {
      "ski_quality": 0.621,
      "price": 0.283,
      "snow": 0.6,
      "nightlife": 1.0,
      "convenience": 0.77,
      "accommodation": 0.833,
      "family": 0.8
    },
    "explanation": "Why: good nightlife, accommodation matching your comfort level, family-friendly. Terrain: 65% graded for intermediates (estimated, not a published figure). (NOTE: some data for this resort is flagged NEEDS VERIFICATION in the seed DB) Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMDhqBRIDVExWcgUSA0lOThoaEgoyMDI3LTAxLTE0agUSA0lOTnIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Aurach%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaRwopEiUyADohSG90ZWwgQXVyYWNoLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgIEgcI6w8QARgOGAYyAggBKgkKBToDRVVSGgA",
    "accommodation_property_name": "Hotel Aurach",
    "flight_options": [
      {
        "price_eur": 334.0,
        "airline": "SWISS + Lufthansa",
        "duration_minutes": 580,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "LX 257",
          "LH 2369"
        ],
        "trip_total_eur": 1498.45,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 372.0,
        "airline": "SKY express",
        "duration_minutes": 390,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best"
        ],
        "flight_numbers": [
          "GQ 721",
          "GQ 870"
        ],
        "trip_total_eur": 1538.35,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 494.0,
        "airline": "Lufthansa",
        "duration_minutes": 250,
        "stops": 0,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "LH 683"
        ],
        "trip_total_eur": 1666.45,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Hotel Aurach",
        "price_eur_per_night": 117.0,
        "per_person_eur": 351.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1498.45,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Aurach%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaRwopEiUyADohSG90ZWwgQXVyYWNoLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgIEgcI6w8QARgOGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "Safestay Kitzbühel Centre",
        "price_eur_per_night": 149.0,
        "per_person_eur": 447.0,
        "is_cheapest": false,
        "rating": 4.8,
        "distance_to_lifts_km": 0.32,
        "trip_total_eur": 1599.25,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Safestay%20Kitzb%C3%BChel%20Centre%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVQo3EjMyADovU2FmZXN0YXkgS2l0emLDvGhlbCBDZW50cmUsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGAgSBwjrDxABGA4YBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Safestay Kitzbühel Alpine",
        "price_eur_per_night": 188.0,
        "per_person_eur": 564.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1722.1,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Safestay%20Kitzb%C3%BChel%20Alpine%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVQo3EjMyADovU2FmZXN0YXkgS2l0emLDvGhlbCBBbHBpbmUsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGAgSBwjrDxABGA4YBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Hotel Kitzbühler Alpen",
        "price_eur_per_night": 198.0,
        "per_person_eur": 594.0,
        "is_cheapest": false,
        "rating": 4.6,
        "distance_to_lifts_km": 2.25,
        "trip_total_eur": 1753.6,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Kitzb%C3%BChler%20Alpen%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaUgo0EjAyADosSG90ZWwgS2l0emLDvGhsZXIgQWxwZW4sIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGAgSBwjrDxABGA4YBjICCAEqCQoFOgNFVVIaAA"
      }
    ],
    "total_eur_with_fastest_flight": 1666.45,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-19&to=resort-169&date=2027-01-08&time=14%3A45&adults=2&currency=EUR&return_date=2027-01-14&return_time=14%3A45&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 306.0,
      "duration_minutes": 145.0,
      "distance_km": 97.8,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.intersportrent.com/skirent-kitzbuehel~12413",
    "ski_pass_search_url": "https://www.kitzski.at/en/ticket-shop-kitzski.html",
    "weather": {
      "days": [
        {
          "date": "2027-01-08",
          "is_live_forecast": false,
          "temp_max_c": 2.0,
          "temp_min_c": -9.3,
          "snowfall_cm": 1.3,
          "snow_depth_cm": 58.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-09",
          "is_live_forecast": false,
          "temp_max_c": 3.9,
          "temp_min_c": -5.3,
          "snowfall_cm": 3.5,
          "snow_depth_cm": 62.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-10",
          "is_live_forecast": false,
          "temp_max_c": 1.2,
          "temp_min_c": -8.4,
          "snowfall_cm": 3.5,
          "snow_depth_cm": 61.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-11",
          "is_live_forecast": false,
          "temp_max_c": 1.6,
          "temp_min_c": -9.7,
          "snowfall_cm": 1.1,
          "snow_depth_cm": 63.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-12",
          "is_live_forecast": false,
          "temp_max_c": 2.2,
          "temp_min_c": -10.0,
          "snowfall_cm": 0.9,
          "snow_depth_cm": 66.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": 4.7,
          "temp_min_c": -11.2,
          "snowfall_cm": 0.3,
          "snow_depth_cm": 65.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 6.3,
          "temp_min_c": -10.2,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 64.4,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": 3.1,
      "avg_temp_min_c": -9.2,
      "avg_snowfall_cm": 1.5,
      "avg_snow_depth_cm": 63.2
    }
  },
  {
    "resort": {
      "name": "Kitzbühel",
      "country": "Austria",
      "region": "Kitzbüheler Alpen (KitzSki)",
      "piste_km": 233.0,
      "off_piste_rating": 3,
      "snow_reliability": 3,
      "nightlife_rating": 5,
      "family_friendliness": 4,
      "nearest_airport": "Innsbruck (INN) / Salzburg (SZG) / Munich (MUC)",
      "transfer_time_minutes": 85.0,
      "terrain": {
        "beginner": 0.2,
        "intermediate": 0.65,
        "advanced": 0.15,
        "quality": "estimated"
      },
      "needs_verification": true
    },
    "start_date": "2027-01-11",
    "end_date": "2027-01-17",
    "season": "high",
    "cost": {
      "flight_eur": 334.0,
      "transfer_eur": 15.0,
      "accommodation_eur": 360.0,
      "ski_pass_eur": 329.09,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 71.81,
      "total_eur": 1507.8999999999999,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 15.0,
        "duration_minutes": 154,
        "carrier": "Train, line 860 bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Innsbruck-Airport/Kitzb%C3%BChel",
        "is_round_trip": false,
        "roles": [
          "cheapest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 75.0
      },
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 18.0,
        "duration_minutes": 136,
        "carrier": "Train",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Innsbruck-Airport/Kitzb%C3%BChel",
        "is_round_trip": false,
        "roles": [
          "fastest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 35.0
      }
    ],
    "score": 0.6424,
    "score_components": {
      "ski_quality": 0.621,
      "price": 0.279,
      "snow": 0.6,
      "nightlife": 1.0,
      "convenience": 0.77,
      "accommodation": 0.833,
      "family": 0.8
    },
    "explanation": "Why: good nightlife, accommodation matching your comfort level, family-friendly. Terrain: 65% graded for intermediates (estimated, not a published figure). (NOTE: some data for this resort is flagged NEEDS VERIFICATION in the seed DB) Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMTFqBRIDVExWcgUSA0lOThoaEgoyMDI3LTAxLTE3agUSA0lOTnIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Aurach%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaRwopEiUyADohSG90ZWwgQXVyYWNoLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgLEgcI6w8QARgRGAYyAggBKgkKBToDRVVSGgA",
    "accommodation_property_name": "Hotel Aurach",
    "flight_options": [
      {
        "price_eur": 334.0,
        "airline": "SWISS + Lufthansa",
        "duration_minutes": 365,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest",
          "best"
        ],
        "flight_numbers": [
          "LX 257",
          "LH 2367"
        ],
        "trip_total_eur": 1507.9,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 712.0,
        "airline": "El Al",
        "duration_minutes": 255,
        "stops": 0,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "LY 353"
        ],
        "trip_total_eur": 1904.8,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Hotel Aurach",
        "price_eur_per_night": 120.0,
        "per_person_eur": 360.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1507.9,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Aurach%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaRwopEiUyADohSG90ZWwgQXVyYWNoLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgLEgcI6w8QARgRGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "Safestay Kitzbühel Centre",
        "price_eur_per_night": 149.0,
        "per_person_eur": 447.0,
        "is_cheapest": false,
        "rating": 4.8,
        "distance_to_lifts_km": 0.32,
        "trip_total_eur": 1599.25,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Safestay%20Kitzb%C3%BChel%20Centre%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVQo3EjMyADovU2FmZXN0YXkgS2l0emLDvGhlbCBDZW50cmUsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGAsSBwjrDxABGBEYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Hotel Neuwirt Kaiserhotels",
        "price_eur_per_night": 205.0,
        "per_person_eur": 615.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1775.65,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Neuwirt%20Kaiserhotels%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVQo3EjMyADovSG90ZWwgTmV1d2lydCBLYWlzZXJob3RlbHMsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGAsSBwjrDxABGBEYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Hotel Garni Entstrasser",
        "price_eur_per_night": 211.0,
        "per_person_eur": 633.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1794.55,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Garni%20Entstrasser%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaUgo0EjAyADosSG90ZWwgR2FybmkgRW50c3RyYXNzZXIsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGAsSBwjrDxABGBEYBjICCAEqCQoFOgNFVVIaAA"
      }
    ],
    "total_eur_with_fastest_flight": 1904.8,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-19&to=resort-169&date=2027-01-11&time=11%3A10&adults=2&currency=EUR&return_date=2027-01-17&return_time=11%3A10&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 306.0,
      "duration_minutes": 145.0,
      "distance_km": 97.8,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.intersportrent.com/skirent-kitzbuehel~12413",
    "ski_pass_search_url": "https://www.kitzski.at/en/ticket-shop-kitzski.html",
    "weather": {
      "days": [
        {
          "date": "2027-01-11",
          "is_live_forecast": false,
          "temp_max_c": 1.6,
          "temp_min_c": -9.7,
          "snowfall_cm": 1.1,
          "snow_depth_cm": 63.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-12",
          "is_live_forecast": false,
          "temp_max_c": 2.2,
          "temp_min_c": -10.0,
          "snowfall_cm": 0.9,
          "snow_depth_cm": 66.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": 4.7,
          "temp_min_c": -11.2,
          "snowfall_cm": 0.3,
          "snow_depth_cm": 65.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 6.3,
          "temp_min_c": -10.2,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 64.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": 4.6,
          "temp_min_c": -5.7,
          "snowfall_cm": 1.9,
          "snow_depth_cm": 63.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-16",
          "is_live_forecast": false,
          "temp_max_c": 4.8,
          "temp_min_c": -8.4,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 65.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-17",
          "is_live_forecast": false,
          "temp_max_c": 5.1,
          "temp_min_c": -9.2,
          "snowfall_cm": 0.7,
          "snow_depth_cm": 65.4,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": 4.2,
      "avg_temp_min_c": -9.2,
      "avg_snowfall_cm": 0.7,
      "avg_snow_depth_cm": 64.9
    }
  },
  {
    "resort": {
      "name": "Val Thorens",
      "country": "France",
      "region": "Les Trois Vallées",
      "piste_km": 150.0,
      "off_piste_rating": 4,
      "snow_reliability": 5,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Geneva (GVA) / Chambéry (CMF)",
      "transfer_time_minutes": 151.0,
      "terrain": {
        "beginner": 0.29,
        "intermediate": 0.61,
        "advanced": 0.1,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-17",
    "end_date": "2027-01-23",
    "season": "high",
    "cost": {
      "flight_eur": 277.0,
      "transfer_eur": 44.93,
      "accommodation_eur": 591.0,
      "ski_pass_eur": 330.32,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 82.07,
      "total_eur": 1723.32,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 44.93,
        "duration_minutes": 115,
        "carrier": "Infobus",
        "departure": "2027-01-07T22:25:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMDciLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIyMjoyNSIsImFycml2YWxUaW1lIjoiMDA6MjAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xMyIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjAwOjIwIiwiYXJyaXZhbFBvc2l0aW9uIjozNjk3MDcsImRlcGFydHVyZVBvc2l0aW9uIjozMTQwNjcsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.p45k3TIusYuvypDI4OuOgz_JSEAju3QAohh2C97IY0k",
        "is_round_trip": true,
        "roles": [
          "cheapest",
          "fastest"
        ],
        "is_indicative": false,
        "price_high_eur_per_person": null
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 45.53,
        "duration_minutes": 155,
        "carrier": "Infobus",
        "departure": "2027-01-07T22:15:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMDciLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIyMjoxNSIsImFycml2YWxUaW1lIjoiMDA6NTAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xMyIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjAwOjUwIiwiYXJyaXZhbFBvc2l0aW9uIjozNjk3MDcsImRlcGFydHVyZVBvc2l0aW9uIjozMTQwNjcsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.rM8tj9SPozc7nLWqVkfhT0S-pqs_V_5OTbXybYTOH5A",
        "is_round_trip": true,
        "roles": [],
        "is_indicative": false,
        "price_high_eur_per_person": null
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 46.64,
        "duration_minutes": 145,
        "carrier": "Infobus",
        "departure": "2027-01-07T22:25:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMDciLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIyMjoyNSIsImFycml2YWxUaW1lIjoiMDA6NTAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xMyIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjAwOjUwIiwiYXJyaXZhbFBvc2l0aW9uIjozNjk3MDcsImRlcGFydHVyZVBvc2l0aW9uIjozMTQwNjcsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.yz7TnCJ4wyqHZuMLTtaQ-P2DkmKLtlw6CQk3_wS5wC8",
        "is_round_trip": true,
        "roles": [],
        "is_indicative": false,
        "price_high_eur_per_person": null
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 49.98,
        "duration_minutes": 135,
        "carrier": "Infobus",
        "departure": "2027-01-07T22:25:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMDciLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIyMjoyNSIsImFycml2YWxUaW1lIjoiMDA6NDAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xMyIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjAwOjQwIiwiYXJyaXZhbFBvc2l0aW9uIjozNjk3MDcsImRlcGFydHVyZVBvc2l0aW9uIjozMTQwNjcsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.d3a1_kuVxV_RSh_PXDrl3wFUxiknQc5qvQA8g5moSVQ",
        "is_round_trip": true,
        "roles": [],
        "is_indicative": false,
        "price_high_eur_per_person": null
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 61.09,
        "duration_minutes": 155,
        "carrier": "Infobus",
        "departure": "2027-01-07T22:25:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMDciLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIyMjoyNSIsImFycml2YWxUaW1lIjoiMDE6MDAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xMyIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjAxOjAwIiwiYXJyaXZhbFBvc2l0aW9uIjozNjk3MDcsImRlcGFydHVyZVBvc2l0aW9uIjozMTQwNjcsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.sknlXDR4ZyZyvGIsYG0Pr5tyM2us3jNzT7g9tKRReQU",
        "is_round_trip": true,
        "roles": [],
        "is_indicative": false,
        "price_high_eur_per_person": null
      }
    ],
    "score": 0.6323,
    "score_components": {
      "ski_quality": 0.681,
      "price": 0.198,
      "snow": 1.0,
      "nightlife": 0.8,
      "convenience": 0.417,
      "accommodation": 0.767,
      "family": 0.8
    },
    "explanation": "Why: reliable snow, good nightlife, family-friendly. Terrain: 61% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMTdqBRIDVExWcgUSA0dWQRoaEgoyMDI3LTAxLTIzagUSA0dWQXIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Appartement%20cosy%20avec%20mezzanine%20%C3%A0%20Val%20Thorens%20-%205%20pers%2C%20ski%20aux%20pieds%2C%20%C3%A9quipements%20complets%20-%20FR-1-637-18%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaqQEKigEShQEyADqAAUFwcGFydGVtZW50IGNvc3kgYXZlYyBtZXp6YW5pbmUgw6AgVmFsIFRob3JlbnMgLSA1IHBlcnMsIHNraSBhdXggcGllZHMsIMOpcXVpcGVtZW50cyBjb21wbGV0cyAtIEZSLTEtNjM3LTE4LCBWYWwgVGhvcmVucywgRnJhbmNlGgASGhIUCgcI6w8QARgREgcI6w8QARgXGAYyAggBKgkKBToDRVVSGgA",
    "accommodation_property_name": "Appartement cosy avec mezzanine à Val Thorens - 5 pers, ski aux pieds, équipements complets - FR-1-637-18",
    "flight_options": [
      {
        "price_eur": 277.0,
        "airline": "Lufthansa",
        "duration_minutes": 990,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "LH 681",
          "LH 2382"
        ],
        "trip_total_eur": 1723.32,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 296.0,
        "airline": "Air France",
        "duration_minutes": 485,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best"
        ],
        "flight_numbers": [
          "AF 963",
          "AF 1242"
        ],
        "trip_total_eur": 1743.27,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 519.0,
        "airline": "ITA",
        "duration_minutes": 390,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "AZ 809",
          "AZ 576"
        ],
        "trip_total_eur": 1977.42,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Appartement cosy avec mezzanine à Val Thorens - 5 pers, ski aux pieds, équipements complets - FR-1-637-18",
        "price_eur_per_night": 197.0,
        "per_person_eur": 591.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1723.32,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Appartement%20cosy%20avec%20mezzanine%20%C3%A0%20Val%20Thorens%20-%205%20pers%2C%20ski%20aux%20pieds%2C%20%C3%A9quipements%20complets%20-%20FR-1-637-18%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaqQEKigEShQEyADqAAUFwcGFydGVtZW50IGNvc3kgYXZlYyBtZXp6YW5pbmUgw6AgVmFsIFRob3JlbnMgLSA1IHBlcnMsIHNraSBhdXggcGllZHMsIMOpcXVpcGVtZW50cyBjb21wbGV0cyAtIEZSLTEtNjM3LTE4LCBWYWwgVGhvcmVucywgRnJhbmNlGgASGhIUCgcI6w8QARgREgcI6w8QARgXGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "Résidence & Spa Le Machu Pichu",
        "price_eur_per_night": 246.0,
        "per_person_eur": 738.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1877.67,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20R%C3%A9sidence%20%26%20Spa%20Le%20Machu%20Pichu%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWgo8EjgyADo0UsOpc2lkZW5jZSAmIFNwYSBMZSBNYWNodSBQaWNodSwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYERIHCOsPEAEYFxgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Residence Le Chalet du Mont Vallon",
        "price_eur_per_night": 264.0,
        "per_person_eur": 792.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1934.37,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Residence%20Le%20Chalet%20du%20Mont%20Vallon%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaXQo_EjsyADo3UmVzaWRlbmNlIExlIENoYWxldCBkdSBNb250IFZhbGxvbiwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYERIHCOsPEAEYFxgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Village Club MMV Les Arolles",
        "price_eur_per_night": 358.0,
        "per_person_eur": 1074.0,
        "is_cheapest": false,
        "rating": 3.8,
        "distance_to_lifts_km": 0.01,
        "trip_total_eur": 2230.47,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Village%20Club%20MMV%20Les%20Arolles%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVwo5EjUyADoxVmlsbGFnZSBDbHViIE1NViBMZXMgQXJvbGxlcywgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYERIHCOsPEAEYFxgGMgIIASoJCgU6A0VVUhoA"
      }
    ],
    "total_eur_with_fastest_flight": 1977.42,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-1&to=resort-80&date=2027-01-17&time=09%3A25&adults=2&currency=EUR&return_date=2027-01-23&return_time=09%3A25&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 423.5,
      "duration_minutes": 200.0,
      "distance_km": 155.2,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/val-thorens",
    "ski_pass_search_url": "https://www.les3vallees.com/en/skipass",
    "weather": {
      "days": [
        {
          "date": "2027-01-17",
          "is_live_forecast": false,
          "temp_max_c": -2.6,
          "temp_min_c": -10.3,
          "snowfall_cm": 3.4,
          "snow_depth_cm": 133.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-18",
          "is_live_forecast": false,
          "temp_max_c": -3.3,
          "temp_min_c": -9.3,
          "snowfall_cm": 5.2,
          "snow_depth_cm": 136.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-19",
          "is_live_forecast": false,
          "temp_max_c": -5.3,
          "temp_min_c": -13.9,
          "snowfall_cm": 0.9,
          "snow_depth_cm": 136.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-20",
          "is_live_forecast": false,
          "temp_max_c": -7.5,
          "temp_min_c": -14.9,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 135.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-21",
          "is_live_forecast": false,
          "temp_max_c": -4.7,
          "temp_min_c": -17.4,
          "snowfall_cm": 0.0,
          "snow_depth_cm": 133.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-22",
          "is_live_forecast": false,
          "temp_max_c": -3.2,
          "temp_min_c": -10.8,
          "snowfall_cm": 2.9,
          "snow_depth_cm": 133.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-23",
          "is_live_forecast": false,
          "temp_max_c": -3.2,
          "temp_min_c": -9.6,
          "snowfall_cm": 2.5,
          "snow_depth_cm": 135.2,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": -4.3,
      "avg_temp_min_c": -12.3,
      "avg_snowfall_cm": 2.2,
      "avg_snow_depth_cm": 134.8
    }
  },
  {
    "resort": {
      "name": "Val Thorens",
      "country": "France",
      "region": "Les Trois Vallées",
      "piste_km": 150.0,
      "off_piste_rating": 4,
      "snow_reliability": 5,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Geneva (GVA) / Chambéry (CMF)",
      "transfer_time_minutes": 151.0,
      "terrain": {
        "beginner": 0.29,
        "intermediate": 0.61,
        "advanced": 0.1,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-15",
    "end_date": "2027-01-21",
    "season": "high",
    "cost": {
      "flight_eur": 246.0,
      "transfer_eur": 20.0,
      "accommodation_eur": 762.0,
      "ski_pass_eur": 330.32,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 87.82,
      "total_eur": 1844.1399999999999,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 20.0,
        "duration_minutes": 400,
        "carrier": "Bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Geneva-Airport-GVA/Val-Thorens",
        "is_round_trip": false,
        "roles": [
          "cheapest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 38.0
      },
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 24.0,
        "duration_minutes": 342,
        "carrier": "Bus, train",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Geneva-Airport-GVA/Val-Thorens",
        "is_round_trip": false,
        "roles": [],
        "is_indicative": true,
        "price_high_eur_per_person": 48.0
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 45.0,
        "duration_minutes": 210,
        "carrier": "Shuttle",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Geneva-Airport-GVA/Val-Thorens",
        "is_round_trip": false,
        "roles": [
          "fastest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 60.0
      }
    ],
    "score": 0.6189,
    "score_components": {
      "ski_quality": 0.681,
      "price": 0.131,
      "snow": 1.0,
      "nightlife": 0.8,
      "convenience": 0.417,
      "accommodation": 0.767,
      "family": 0.8
    },
    "explanation": "Why: reliable snow, good nightlife, family-friendly. Terrain: 61% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMTVqBRIDVExWcgUSA0dWQRoaEgoyMDI3LTAxLTIxagUSA0dWQXIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20R%C3%A9sidence%20%26%20Spa%20Le%20Machu%20Pichu%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWgo8EjgyADo0UsOpc2lkZW5jZSAmIFNwYSBMZSBNYWNodSBQaWNodSwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYDxIHCOsPEAEYFRgGMgIIASoJCgU6A0VVUhoA",
    "accommodation_property_name": "Résidence & Spa Le Machu Pichu",
    "flight_options": [
      {
        "price_eur": 246.0,
        "airline": "Aegean",
        "duration_minutes": 780,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "A3 929",
          "A3 856"
        ],
        "trip_total_eur": 1844.14,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 269.0,
        "airline": "SWISS",
        "duration_minutes": 395,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best"
        ],
        "flight_numbers": [
          "LX 253",
          "LX 2818"
        ],
        "trip_total_eur": 1868.29,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 562.0,
        "airline": "El Al",
        "duration_minutes": 270,
        "stops": 0,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "LY 345"
        ],
        "trip_total_eur": 2175.94,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Résidence & Spa Le Machu Pichu",
        "price_eur_per_night": 254.0,
        "per_person_eur": 762.0,
        "is_cheapest": true,
        "rating": 2.9,
        "distance_to_lifts_km": 0.12,
        "trip_total_eur": 1844.14,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20R%C3%A9sidence%20%26%20Spa%20Le%20Machu%20Pichu%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWgo8EjgyADo0UsOpc2lkZW5jZSAmIFNwYSBMZSBNYWNodSBQaWNodSwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYDxIHCOsPEAEYFRgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Residence Le Chalet du Mont Vallon",
        "price_eur_per_night": 268.0,
        "per_person_eur": 804.0,
        "is_cheapest": false,
        "rating": 4.3,
        "distance_to_lifts_km": 2.29,
        "trip_total_eur": 1888.24,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Residence%20Le%20Chalet%20du%20Mont%20Vallon%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaXQo_EjsyADo3UmVzaWRlbmNlIExlIENoYWxldCBkdSBNb250IFZhbGxvbiwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYDxIHCOsPEAEYFRgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Duplex apartment on the top floor, ski-in ski-out, right in the center of town.",
        "price_eur_per_night": 280.0,
        "per_person_eur": 840.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1926.04,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Duplex%20apartment%20on%20the%20top%20floor%2C%20ski-in%20ski-out%2C%20right%20in%20the%20center%20of%20town.%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaigEKbBJoMgA6ZER1cGxleCBhcGFydG1lbnQgb24gdGhlIHRvcCBmbG9vciwgc2tpLWluIHNraS1vdXQsIHJpZ2h0IGluIHRoZSBjZW50ZXIgb2YgdG93bi4sIFZhbCBUaG9yZW5zLCBGcmFuY2UaABIaEhQKBwjrDxABGA8SBwjrDxABGBUYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Village Club MMV Les Arolles",
        "price_eur_per_night": 354.0,
        "per_person_eur": 1062.0,
        "is_cheapest": false,
        "rating": 3.8,
        "distance_to_lifts_km": 0.01,
        "trip_total_eur": 2159.14,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Village%20Club%20MMV%20Les%20Arolles%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVwo5EjUyADoxVmlsbGFnZSBDbHViIE1NViBMZXMgQXJvbGxlcywgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYDxIHCOsPEAEYFRgGMgIIASoJCgU6A0VVUhoA"
      }
    ],
    "total_eur_with_fastest_flight": 2175.94,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-1&to=resort-80&date=2027-01-15&time=18%3A05&adults=2&currency=EUR&return_date=2027-01-21&return_time=18%3A05&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 423.5,
      "duration_minutes": 200.0,
      "distance_km": 155.2,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/val-thorens",
    "ski_pass_search_url": "https://www.les3vallees.com/en/skipass",
    "weather": {
      "days": [
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": -1.7,
          "temp_min_c": -9.6,
          "snowfall_cm": 2.8,
          "snow_depth_cm": 130.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-16",
          "is_live_forecast": false,
          "temp_max_c": -4.2,
          "temp_min_c": -14.9,
          "snowfall_cm": 1.4,
          "snow_depth_cm": 131.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-17",
          "is_live_forecast": false,
          "temp_max_c": -2.6,
          "temp_min_c": -10.3,
          "snowfall_cm": 3.4,
          "snow_depth_cm": 133.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-18",
          "is_live_forecast": false,
          "temp_max_c": -3.3,
          "temp_min_c": -9.3,
          "snowfall_cm": 5.2,
          "snow_depth_cm": 136.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-19",
          "is_live_forecast": false,
          "temp_max_c": -5.3,
          "temp_min_c": -13.9,
          "snowfall_cm": 0.9,
          "snow_depth_cm": 136.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-20",
          "is_live_forecast": false,
          "temp_max_c": -7.5,
          "temp_min_c": -14.9,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 135.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-21",
          "is_live_forecast": false,
          "temp_max_c": -4.7,
          "temp_min_c": -17.4,
          "snowfall_cm": 0.0,
          "snow_depth_cm": 133.6,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": -4.2,
      "avg_temp_min_c": -12.9,
      "avg_snowfall_cm": 2.0,
      "avg_snow_depth_cm": 133.7
    }
  },
  {
    "resort": {
      "name": "Val Thorens",
      "country": "France",
      "region": "Les Trois Vallées",
      "piste_km": 150.0,
      "off_piste_rating": 4,
      "snow_reliability": 5,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Geneva (GVA) / Chambéry (CMF)",
      "transfer_time_minutes": 151.0,
      "terrain": {
        "beginner": 0.29,
        "intermediate": 0.61,
        "advanced": 0.1,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-14",
    "end_date": "2027-01-20",
    "season": "high",
    "cost": {
      "flight_eur": 267.0,
      "transfer_eur": 108.25,
      "accommodation_eur": 762.0,
      "ski_pass_eur": 330.32,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 93.28,
      "total_eur": 1958.85,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 108.25,
        "duration_minutes": 240,
        "carrier": "AlpyBus",
        "departure": "2027-01-14T10:00:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAwODMiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTQiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIxMDowMCIsImFycml2YWxUaW1lIjoiMTQ6MDAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0yMCIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjE0OjAwIiwiYXJyaXZhbFBvc2l0aW9uIjo0NDA0NzAsImRlcGFydHVyZVBvc2l0aW9uIjozMTQ1MjAsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.ufSw7pLXGlw1UDjoMRi9hZODjpHvyLDPDG2Xs9sXA0s",
        "is_round_trip": true,
        "roles": [
          "cheapest"
        ],
        "is_indicative": false,
        "price_high_eur_per_person": null
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 114.5,
        "duration_minutes": 195,
        "carrier": "Alpine Fleet",
        "departure": "2027-01-14T09:45:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTQiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIwOTo0NSIsImFycml2YWxUaW1lIjoiMTM6MDAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0yMCIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjEzOjAwIiwiYXJyaXZhbFBvc2l0aW9uIjo0NDA0NzAsImRlcGFydHVyZVBvc2l0aW9uIjozMTQ1MjAsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.S7GlVmJshLuiG-I9WxaCtVtiweHOgqhiL3Ha2Z84wRU",
        "is_round_trip": true,
        "roles": [
          "fastest"
        ],
        "is_indicative": false,
        "price_high_eur_per_person": null
      }
    ],
    "score": 0.6169,
    "score_components": {
      "ski_quality": 0.681,
      "price": 0.121,
      "snow": 1.0,
      "nightlife": 0.8,
      "convenience": 0.417,
      "accommodation": 0.767,
      "family": 0.8
    },
    "explanation": "Why: reliable snow, good nightlife, family-friendly. Terrain: 61% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMTRqBRIDVExWcgUSA0dWQRoaEgoyMDI3LTAxLTIwagUSA0dWQXIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20R%C3%A9sidence%20%26%20Spa%20Le%20Machu%20Pichu%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWgo8EjgyADo0UsOpc2lkZW5jZSAmIFNwYSBMZSBNYWNodSBQaWNodSwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYDhIHCOsPEAEYFBgGMgIIASoJCgU6A0VVUhoA",
    "accommodation_property_name": "Résidence & Spa Le Machu Pichu",
    "flight_options": [
      {
        "price_eur": 267.0,
        "airline": "Aegean",
        "duration_minutes": 1390,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "A3 927",
          "A3 856"
        ],
        "trip_total_eur": 1958.85,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 279.0,
        "airline": "Lufthansa",
        "duration_minutes": 415,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best"
        ],
        "flight_numbers": [
          "LH 687",
          "LH 1222"
        ],
        "trip_total_eur": 1971.45,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 427.0,
        "airline": "ITA",
        "duration_minutes": 390,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "AZ 809",
          "AZ 576"
        ],
        "trip_total_eur": 2126.85,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Résidence & Spa Le Machu Pichu",
        "price_eur_per_night": 254.0,
        "per_person_eur": 762.0,
        "is_cheapest": true,
        "rating": 2.9,
        "distance_to_lifts_km": 0.12,
        "trip_total_eur": 1958.85,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20R%C3%A9sidence%20%26%20Spa%20Le%20Machu%20Pichu%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWgo8EjgyADo0UsOpc2lkZW5jZSAmIFNwYSBMZSBNYWNodSBQaWNodSwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYDhIHCOsPEAEYFBgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Residence Le Chalet du Mont Vallon",
        "price_eur_per_night": 268.0,
        "per_person_eur": 804.0,
        "is_cheapest": false,
        "rating": 4.3,
        "distance_to_lifts_km": 2.29,
        "trip_total_eur": 2002.95,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Residence%20Le%20Chalet%20du%20Mont%20Vallon%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaXQo_EjsyADo3UmVzaWRlbmNlIExlIENoYWxldCBkdSBNb250IFZhbGxvbiwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYDhIHCOsPEAEYFBgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Duplex apartment on the top floor, ski-in ski-out, right in the center of town.",
        "price_eur_per_night": 280.0,
        "per_person_eur": 840.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 2040.75,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Duplex%20apartment%20on%20the%20top%20floor%2C%20ski-in%20ski-out%2C%20right%20in%20the%20center%20of%20town.%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaigEKbBJoMgA6ZER1cGxleCBhcGFydG1lbnQgb24gdGhlIHRvcCBmbG9vciwgc2tpLWluIHNraS1vdXQsIHJpZ2h0IGluIHRoZSBjZW50ZXIgb2YgdG93bi4sIFZhbCBUaG9yZW5zLCBGcmFuY2UaABIaEhQKBwjrDxABGA4SBwjrDxABGBQYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "FAHRENHEIT SEVEN VAL THORENS",
        "price_eur_per_night": 425.0,
        "per_person_eur": 1275.0,
        "is_cheapest": false,
        "rating": 4.4,
        "distance_to_lifts_km": 0.14,
        "trip_total_eur": 2497.5,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20FAHRENHEIT%20SEVEN%20VAL%20THORENS%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVwo5EjUyADoxRkFIUkVOSEVJVCBTRVZFTiBWQUwgVEhPUkVOUywgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYDhIHCOsPEAEYFBgGMgIIASoJCgU6A0VVUhoA"
      }
    ],
    "total_eur_with_fastest_flight": 2126.85,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-1&to=resort-80&date=2027-01-14&time=18%3A05&adults=2&currency=EUR&return_date=2027-01-20&return_time=18%3A05&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 423.5,
      "duration_minutes": 200.0,
      "distance_km": 155.2,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/val-thorens",
    "ski_pass_search_url": "https://www.les3vallees.com/en/skipass",
    "weather": {
      "days": [
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 0.3,
          "temp_min_c": -9.9,
          "snowfall_cm": 0.0,
          "snow_depth_cm": 130.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": -1.7,
          "temp_min_c": -9.6,
          "snowfall_cm": 2.8,
          "snow_depth_cm": 130.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-16",
          "is_live_forecast": false,
          "temp_max_c": -4.2,
          "temp_min_c": -14.9,
          "snowfall_cm": 1.4,
          "snow_depth_cm": 131.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-17",
          "is_live_forecast": false,
          "temp_max_c": -2.6,
          "temp_min_c": -10.3,
          "snowfall_cm": 3.4,
          "snow_depth_cm": 133.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-18",
          "is_live_forecast": false,
          "temp_max_c": -3.3,
          "temp_min_c": -9.3,
          "snowfall_cm": 5.2,
          "snow_depth_cm": 136.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-19",
          "is_live_forecast": false,
          "temp_max_c": -5.3,
          "temp_min_c": -13.9,
          "snowfall_cm": 0.9,
          "snow_depth_cm": 136.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-20",
          "is_live_forecast": false,
          "temp_max_c": -7.5,
          "temp_min_c": -14.9,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 135.2,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": -3.5,
      "avg_temp_min_c": -11.8,
      "avg_snowfall_cm": 2.0,
      "avg_snow_depth_cm": 133.2
    }
  },
  {
    "resort": {
      "name": "Val Thorens",
      "country": "France",
      "region": "Les Trois Vallées",
      "piste_km": 150.0,
      "off_piste_rating": 4,
      "snow_reliability": 5,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Geneva (GVA) / Chambéry (CMF)",
      "transfer_time_minutes": 151.0,
      "terrain": {
        "beginner": 0.29,
        "intermediate": 0.61,
        "advanced": 0.1,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-12",
    "end_date": "2027-01-18",
    "season": "high",
    "cost": {
      "flight_eur": 269.0,
      "transfer_eur": 108.25,
      "accommodation_eur": 762.0,
      "ski_pass_eur": 330.32,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 93.38,
      "total_eur": 1960.9499999999998,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 108.25,
        "duration_minutes": 195,
        "carrier": "Alpine Fleet",
        "departure": "2027-01-12T10:30:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTIiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIxMDozMCIsImFycml2YWxUaW1lIjoiMTM6NDUiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xOCIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjEzOjQ1IiwiYXJyaXZhbFBvc2l0aW9uIjo0NDA0NzAsImRlcGFydHVyZVBvc2l0aW9uIjozMTQ1MjAsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.kWHVoITFWIL9lHfzUl5Cd2AeMm_Qtmd_GeENuOW44V0",
        "is_round_trip": true,
        "roles": [
          "cheapest",
          "fastest"
        ],
        "is_indicative": false,
        "price_high_eur_per_person": null
      }
    ],
    "score": 0.6167,
    "score_components": {
      "ski_quality": 0.681,
      "price": 0.12,
      "snow": 1.0,
      "nightlife": 0.8,
      "convenience": 0.417,
      "accommodation": 0.767,
      "family": 0.8
    },
    "explanation": "Why: reliable snow, good nightlife, family-friendly. Terrain: 61% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMTJqBRIDVExWcgUSA0dWQRoaEgoyMDI3LTAxLTE4agUSA0dWQXIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20R%C3%A9sidence%20%26%20Spa%20Le%20Machu%20Pichu%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWgo8EjgyADo0UsOpc2lkZW5jZSAmIFNwYSBMZSBNYWNodSBQaWNodSwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYDBIHCOsPEAEYEhgGMgIIASoJCgU6A0VVUhoA",
    "accommodation_property_name": "Résidence & Spa Le Machu Pichu",
    "flight_options": [
      {
        "price_eur": 269.0,
        "airline": "Brussels Airlines + SWISS",
        "duration_minutes": 440,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest",
          "best"
        ],
        "flight_numbers": [
          "SN 3290",
          "LX 799"
        ],
        "trip_total_eur": 1960.95,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 427.0,
        "airline": "ITA",
        "duration_minutes": 390,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "AZ 809",
          "AZ 576"
        ],
        "trip_total_eur": 2126.85,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Résidence & Spa Le Machu Pichu",
        "price_eur_per_night": 254.0,
        "per_person_eur": 762.0,
        "is_cheapest": true,
        "rating": 2.9,
        "distance_to_lifts_km": 0.12,
        "trip_total_eur": 1960.95,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20R%C3%A9sidence%20%26%20Spa%20Le%20Machu%20Pichu%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWgo8EjgyADo0UsOpc2lkZW5jZSAmIFNwYSBMZSBNYWNodSBQaWNodSwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYDBIHCOsPEAEYEhgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Residence Le Chalet du Mont Vallon",
        "price_eur_per_night": 277.0,
        "per_person_eur": 831.0,
        "is_cheapest": false,
        "rating": 4.3,
        "distance_to_lifts_km": 2.29,
        "trip_total_eur": 2033.4,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Residence%20Le%20Chalet%20du%20Mont%20Vallon%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaXQo_EjsyADo3UmVzaWRlbmNlIExlIENoYWxldCBkdSBNb250IFZhbGxvbiwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYDBIHCOsPEAEYEhgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Duplex apartment on the top floor, ski-in ski-out, right in the center of town.",
        "price_eur_per_night": 280.0,
        "per_person_eur": 840.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 2042.85,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Duplex%20apartment%20on%20the%20top%20floor%2C%20ski-in%20ski-out%2C%20right%20in%20the%20center%20of%20town.%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaigEKbBJoMgA6ZER1cGxleCBhcGFydG1lbnQgb24gdGhlIHRvcCBmbG9vciwgc2tpLWluIHNraS1vdXQsIHJpZ2h0IGluIHRoZSBjZW50ZXIgb2YgdG93bi4sIFZhbCBUaG9yZW5zLCBGcmFuY2UaABIaEhQKBwjrDxABGAwSBwjrDxABGBIYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "FAHRENHEIT SEVEN VAL THORENS",
        "price_eur_per_night": 425.0,
        "per_person_eur": 1275.0,
        "is_cheapest": false,
        "rating": 4.4,
        "distance_to_lifts_km": 0.14,
        "trip_total_eur": 2499.6,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20FAHRENHEIT%20SEVEN%20VAL%20THORENS%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVwo5EjUyADoxRkFIUkVOSEVJVCBTRVZFTiBWQUwgVEhPUkVOUywgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYDBIHCOsPEAEYEhgGMgIIASoJCgU6A0VVUhoA"
      }
    ],
    "total_eur_with_fastest_flight": 2126.85,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-1&to=resort-80&date=2027-01-12&time=23%3A15&adults=2&currency=EUR&return_date=2027-01-18&return_time=23%3A15&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 423.5,
      "duration_minutes": 200.0,
      "distance_km": 155.2,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/val-thorens",
    "ski_pass_search_url": "https://www.les3vallees.com/en/skipass",
    "weather": {
      "days": [
        {
          "date": "2027-01-12",
          "is_live_forecast": false,
          "temp_max_c": -2.6,
          "temp_min_c": -10.1,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 134.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": -2.1,
          "temp_min_c": -8.7,
          "snowfall_cm": 0.6,
          "snow_depth_cm": 132.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 0.3,
          "temp_min_c": -9.9,
          "snowfall_cm": 0.0,
          "snow_depth_cm": 130.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": -1.7,
          "temp_min_c": -9.6,
          "snowfall_cm": 2.8,
          "snow_depth_cm": 130.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-16",
          "is_live_forecast": false,
          "temp_max_c": -4.2,
          "temp_min_c": -14.9,
          "snowfall_cm": 1.4,
          "snow_depth_cm": 131.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-17",
          "is_live_forecast": false,
          "temp_max_c": -2.6,
          "temp_min_c": -10.3,
          "snowfall_cm": 3.4,
          "snow_depth_cm": 133.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-18",
          "is_live_forecast": false,
          "temp_max_c": -3.3,
          "temp_min_c": -9.3,
          "snowfall_cm": 5.2,
          "snow_depth_cm": 136.6,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": -2.3,
      "avg_temp_min_c": -10.4,
      "avg_snowfall_cm": 1.9,
      "avg_snow_depth_cm": 132.5
    }
  },
  {
    "resort": {
      "name": "Val Thorens",
      "country": "France",
      "region": "Les Trois Vallées",
      "piste_km": 150.0,
      "off_piste_rating": 4,
      "snow_reliability": 5,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Geneva (GVA) / Chambéry (CMF)",
      "transfer_time_minutes": 151.0,
      "terrain": {
        "beginner": 0.29,
        "intermediate": 0.61,
        "advanced": 0.1,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-13",
    "end_date": "2027-01-19",
    "season": "high",
    "cost": {
      "flight_eur": 269.0,
      "transfer_eur": 114.5,
      "accommodation_eur": 762.0,
      "ski_pass_eur": 330.32,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 93.69,
      "total_eur": 1967.51,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 114.5,
        "duration_minutes": 195,
        "carrier": "Alpine Fleet",
        "departure": "2027-01-13T10:30:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTMiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIxMDozMCIsImFycml2YWxUaW1lIjoiMTM6NDUiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xOSIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjEzOjQ1IiwiYXJyaXZhbFBvc2l0aW9uIjo0NDA0NzAsImRlcGFydHVyZVBvc2l0aW9uIjozMTQ1MjAsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.8zzAwk3KE_vU8PeoZkjThaYrnzFA-dyWKGb3Who2CmE",
        "is_round_trip": true,
        "roles": [
          "cheapest",
          "fastest"
        ],
        "is_indicative": false,
        "price_high_eur_per_person": null
      }
    ],
    "score": 0.6167,
    "score_components": {
      "ski_quality": 0.681,
      "price": 0.12,
      "snow": 1.0,
      "nightlife": 0.8,
      "convenience": 0.417,
      "accommodation": 0.767,
      "family": 0.8
    },
    "explanation": "Why: reliable snow, good nightlife, family-friendly. Terrain: 61% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMTNqBRIDVExWcgUSA0dWQRoaEgoyMDI3LTAxLTE5agUSA0dWQXIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20R%C3%A9sidence%20%26%20Spa%20Le%20Machu%20Pichu%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWgo8EjgyADo0UsOpc2lkZW5jZSAmIFNwYSBMZSBNYWNodSBQaWNodSwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYDRIHCOsPEAEYExgGMgIIASoJCgU6A0VVUhoA",
    "accommodation_property_name": "Résidence & Spa Le Machu Pichu",
    "flight_options": [
      {
        "price_eur": 269.0,
        "airline": "SWISS",
        "duration_minutes": 930,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "LX 253",
          "LX 2802"
        ],
        "trip_total_eur": 1967.51,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 279.0,
        "airline": "Lufthansa",
        "duration_minutes": 415,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best"
        ],
        "flight_numbers": [
          "LH 687",
          "LH 1222"
        ],
        "trip_total_eur": 1978.01,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 492.0,
        "airline": "El Al + SWISS",
        "duration_minutes": 385,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "LY 347",
          "LX 2824"
        ],
        "trip_total_eur": 2201.66,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Résidence & Spa Le Machu Pichu",
        "price_eur_per_night": 254.0,
        "per_person_eur": 762.0,
        "is_cheapest": true,
        "rating": 2.9,
        "distance_to_lifts_km": 0.12,
        "trip_total_eur": 1967.51,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20R%C3%A9sidence%20%26%20Spa%20Le%20Machu%20Pichu%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWgo8EjgyADo0UsOpc2lkZW5jZSAmIFNwYSBMZSBNYWNodSBQaWNodSwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYDRIHCOsPEAEYExgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Residence Le Chalet du Mont Vallon",
        "price_eur_per_night": 277.0,
        "per_person_eur": 831.0,
        "is_cheapest": false,
        "rating": 4.3,
        "distance_to_lifts_km": 2.29,
        "trip_total_eur": 2039.96,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Residence%20Le%20Chalet%20du%20Mont%20Vallon%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaXQo_EjsyADo3UmVzaWRlbmNlIExlIENoYWxldCBkdSBNb250IFZhbGxvbiwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYDRIHCOsPEAEYExgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Duplex apartment on the top floor, ski-in ski-out, right in the center of town.",
        "price_eur_per_night": 280.0,
        "per_person_eur": 840.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 2049.41,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Duplex%20apartment%20on%20the%20top%20floor%2C%20ski-in%20ski-out%2C%20right%20in%20the%20center%20of%20town.%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaigEKbBJoMgA6ZER1cGxleCBhcGFydG1lbnQgb24gdGhlIHRvcCBmbG9vciwgc2tpLWluIHNraS1vdXQsIHJpZ2h0IGluIHRoZSBjZW50ZXIgb2YgdG93bi4sIFZhbCBUaG9yZW5zLCBGcmFuY2UaABIaEhQKBwjrDxABGA0SBwjrDxABGBMYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "FAHRENHEIT SEVEN VAL THORENS",
        "price_eur_per_night": 425.0,
        "per_person_eur": 1275.0,
        "is_cheapest": false,
        "rating": 4.4,
        "distance_to_lifts_km": 0.14,
        "trip_total_eur": 2506.16,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20FAHRENHEIT%20SEVEN%20VAL%20THORENS%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVwo5EjUyADoxRkFIUkVOSEVJVCBTRVZFTiBWQUwgVEhPUkVOUywgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYDRIHCOsPEAEYExgGMgIIASoJCgU6A0VVUhoA"
      }
    ],
    "total_eur_with_fastest_flight": 2201.66,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-1&to=resort-80&date=2027-01-13&time=09%3A15&adults=2&currency=EUR&return_date=2027-01-19&return_time=09%3A15&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 423.5,
      "duration_minutes": 200.0,
      "distance_km": 155.2,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/val-thorens",
    "ski_pass_search_url": "https://www.les3vallees.com/en/skipass",
    "weather": {
      "days": [
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": -2.1,
          "temp_min_c": -8.7,
          "snowfall_cm": 0.6,
          "snow_depth_cm": 132.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 0.3,
          "temp_min_c": -9.9,
          "snowfall_cm": 0.0,
          "snow_depth_cm": 130.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": -1.7,
          "temp_min_c": -9.6,
          "snowfall_cm": 2.8,
          "snow_depth_cm": 130.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-16",
          "is_live_forecast": false,
          "temp_max_c": -4.2,
          "temp_min_c": -14.9,
          "snowfall_cm": 1.4,
          "snow_depth_cm": 131.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-17",
          "is_live_forecast": false,
          "temp_max_c": -2.6,
          "temp_min_c": -10.3,
          "snowfall_cm": 3.4,
          "snow_depth_cm": 133.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-18",
          "is_live_forecast": false,
          "temp_max_c": -3.3,
          "temp_min_c": -9.3,
          "snowfall_cm": 5.2,
          "snow_depth_cm": 136.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-19",
          "is_live_forecast": false,
          "temp_max_c": -5.3,
          "temp_min_c": -13.9,
          "snowfall_cm": 0.9,
          "snow_depth_cm": 136.4,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": -2.7,
      "avg_temp_min_c": -10.9,
      "avg_snowfall_cm": 2.0,
      "avg_snow_depth_cm": 132.7
    }
  },
  {
    "resort": {
      "name": "Val Thorens",
      "country": "France",
      "region": "Les Trois Vallées",
      "piste_km": 150.0,
      "off_piste_rating": 4,
      "snow_reliability": 5,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Geneva (GVA) / Chambéry (CMF)",
      "transfer_time_minutes": 151.0,
      "terrain": {
        "beginner": 0.29,
        "intermediate": 0.61,
        "advanced": 0.1,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-18",
    "end_date": "2027-01-24",
    "season": "high",
    "cost": {
      "flight_eur": 269.0,
      "transfer_eur": 102.5,
      "accommodation_eur": 762.0,
      "ski_pass_eur": 330.32,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 93.09,
      "total_eur": 1954.9099999999999,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 102.5,
        "duration_minutes": 240,
        "carrier": "AlpyBus",
        "departure": "2027-01-18T10:00:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAwODMiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTgiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIxMDowMCIsImFycml2YWxUaW1lIjoiMTQ6MDAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0yNCIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjE0OjAwIiwiYXJyaXZhbFBvc2l0aW9uIjo0NDA0NzAsImRlcGFydHVyZVBvc2l0aW9uIjozMTQ1MjAsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.2o_EQbQWE_pUOOdC5sI1iSBNVmlMY8nDaRZsFhRUEkE",
        "is_round_trip": true,
        "roles": [
          "cheapest"
        ],
        "is_indicative": false,
        "price_high_eur_per_person": null
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 108.75,
        "duration_minutes": 195,
        "carrier": "Alpine Fleet",
        "departure": "2027-01-18T10:30:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTgiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIxMDozMCIsImFycml2YWxUaW1lIjoiMTM6NDUiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0yNCIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjEzOjQ1IiwiYXJyaXZhbFBvc2l0aW9uIjo0NDA0NzAsImRlcGFydHVyZVBvc2l0aW9uIjozMTQ1MjAsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.gVOhSM_f5iMA5NkBG2n1DmGr6XwK2RkBT_GtsaalFI4",
        "is_round_trip": true,
        "roles": [
          "fastest"
        ],
        "is_indicative": false,
        "price_high_eur_per_person": null
      }
    ],
    "score": 0.6167,
    "score_components": {
      "ski_quality": 0.681,
      "price": 0.12,
      "snow": 1.0,
      "nightlife": 0.8,
      "convenience": 0.417,
      "accommodation": 0.767,
      "family": 0.8
    },
    "explanation": "Why: reliable snow, good nightlife, family-friendly. Terrain: 61% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMThqBRIDVExWcgUSA0dWQRoaEgoyMDI3LTAxLTI0agUSA0dWQXIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20R%C3%A9sidence%20%26%20Spa%20Le%20Machu%20Pichu%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWgo8EjgyADo0UsOpc2lkZW5jZSAmIFNwYSBMZSBNYWNodSBQaWNodSwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYEhIHCOsPEAEYGBgGMgIIASoJCgU6A0VVUhoA",
    "accommodation_property_name": "Résidence & Spa Le Machu Pichu",
    "flight_options": [
      {
        "price_eur": 269.0,
        "airline": "Brussels Airlines + SWISS",
        "duration_minutes": 440,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "SN 3290",
          "LX 799"
        ],
        "trip_total_eur": 1954.91,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 279.0,
        "airline": "Lufthansa",
        "duration_minutes": 415,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best"
        ],
        "flight_numbers": [
          "LH 687",
          "LH 1222"
        ],
        "trip_total_eur": 1965.41,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 727.0,
        "airline": "El Al",
        "duration_minutes": 275,
        "stops": 0,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "LY 345"
        ],
        "trip_total_eur": 2435.81,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Résidence & Spa Le Machu Pichu",
        "price_eur_per_night": 254.0,
        "per_person_eur": 762.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1954.91,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20R%C3%A9sidence%20%26%20Spa%20Le%20Machu%20Pichu%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWgo8EjgyADo0UsOpc2lkZW5jZSAmIFNwYSBMZSBNYWNodSBQaWNodSwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYEhIHCOsPEAEYGBgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Residence Le Chalet du Mont Vallon",
        "price_eur_per_night": 263.0,
        "per_person_eur": 789.0,
        "is_cheapest": false,
        "rating": 4.3,
        "distance_to_lifts_km": 2.29,
        "trip_total_eur": 1983.26,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Residence%20Le%20Chalet%20du%20Mont%20Vallon%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaXQo_EjsyADo3UmVzaWRlbmNlIExlIENoYWxldCBkdSBNb250IFZhbGxvbiwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYEhIHCOsPEAEYGBgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Village Club MMV Les Arolles",
        "price_eur_per_night": 362.0,
        "per_person_eur": 1086.0,
        "is_cheapest": false,
        "rating": 3.8,
        "distance_to_lifts_km": 0.01,
        "trip_total_eur": 2295.11,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Village%20Club%20MMV%20Les%20Arolles%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVwo5EjUyADoxVmlsbGFnZSBDbHViIE1NViBMZXMgQXJvbGxlcywgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYEhIHCOsPEAEYGBgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Hôtel et Résidence Le Portillo",
        "price_eur_per_night": 431.0,
        "per_person_eur": 1293.0,
        "is_cheapest": false,
        "rating": 4.2,
        "distance_to_lifts_km": 0.14,
        "trip_total_eur": 2512.46,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20H%C3%B4tel%20et%20R%C3%A9sidence%20Le%20Portillo%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWwo9EjkyADo1SMO0dGVsIGV0IFLDqXNpZGVuY2UgTGUgUG9ydGlsbG8sIFZhbCBUaG9yZW5zLCBGcmFuY2UaABIaEhQKBwjrDxABGBISBwjrDxABGBgYBjICCAEqCQoFOgNFVVIaAA"
      }
    ],
    "total_eur_with_fastest_flight": 2435.81,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-1&to=resort-80&date=2027-01-18&time=23%3A15&adults=2&currency=EUR&return_date=2027-01-24&return_time=23%3A15&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 423.5,
      "duration_minutes": 200.0,
      "distance_km": 155.2,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/val-thorens",
    "ski_pass_search_url": "https://www.les3vallees.com/en/skipass",
    "weather": {
      "days": [
        {
          "date": "2027-01-18",
          "is_live_forecast": false,
          "temp_max_c": -3.3,
          "temp_min_c": -9.3,
          "snowfall_cm": 5.2,
          "snow_depth_cm": 136.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-19",
          "is_live_forecast": false,
          "temp_max_c": -5.3,
          "temp_min_c": -13.9,
          "snowfall_cm": 0.9,
          "snow_depth_cm": 136.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-20",
          "is_live_forecast": false,
          "temp_max_c": -7.5,
          "temp_min_c": -14.9,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 135.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-21",
          "is_live_forecast": false,
          "temp_max_c": -4.7,
          "temp_min_c": -17.4,
          "snowfall_cm": 0.0,
          "snow_depth_cm": 133.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-22",
          "is_live_forecast": false,
          "temp_max_c": -3.2,
          "temp_min_c": -10.8,
          "snowfall_cm": 2.9,
          "snow_depth_cm": 133.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-23",
          "is_live_forecast": false,
          "temp_max_c": -3.2,
          "temp_min_c": -9.6,
          "snowfall_cm": 2.5,
          "snow_depth_cm": 135.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-24",
          "is_live_forecast": false,
          "temp_max_c": -1.4,
          "temp_min_c": -10.5,
          "snowfall_cm": 1.9,
          "snow_depth_cm": 137.8,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": -4.1,
      "avg_temp_min_c": -12.3,
      "avg_snowfall_cm": 1.9,
      "avg_snow_depth_cm": 135.5
    }
  },
  {
    "resort": {
      "name": "Val Thorens",
      "country": "France",
      "region": "Les Trois Vallées",
      "piste_km": 150.0,
      "off_piste_rating": 4,
      "snow_reliability": 5,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Geneva (GVA) / Chambéry (CMF)",
      "transfer_time_minutes": 151.0,
      "terrain": {
        "beginner": 0.29,
        "intermediate": 0.61,
        "advanced": 0.1,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-19",
    "end_date": "2027-01-25",
    "season": "high",
    "cost": {
      "flight_eur": 269.0,
      "transfer_eur": 108.75,
      "accommodation_eur": 762.0,
      "ski_pass_eur": 330.32,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 93.41,
      "total_eur": 1961.48,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 108.75,
        "duration_minutes": 195,
        "carrier": "Alpine Fleet",
        "departure": "2027-01-19T10:30:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTkiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIxMDozMCIsImFycml2YWxUaW1lIjoiMTM6NDUiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0yNSIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjEzOjQ1IiwiYXJyaXZhbFBvc2l0aW9uIjo0NDA0NzAsImRlcGFydHVyZVBvc2l0aW9uIjozMTQ1MjAsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.bWZutZzSCvTasmprEC6COZr4sbZpEH2U-cImGg5zVUY",
        "is_round_trip": true,
        "roles": [
          "cheapest",
          "fastest"
        ],
        "is_indicative": false,
        "price_high_eur_per_person": null
      }
    ],
    "score": 0.6167,
    "score_components": {
      "ski_quality": 0.681,
      "price": 0.12,
      "snow": 1.0,
      "nightlife": 0.8,
      "convenience": 0.417,
      "accommodation": 0.767,
      "family": 0.8
    },
    "explanation": "Why: reliable snow, good nightlife, family-friendly. Terrain: 61% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMTlqBRIDVExWcgUSA0dWQRoaEgoyMDI3LTAxLTI1agUSA0dWQXIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20R%C3%A9sidence%20%26%20Spa%20Le%20Machu%20Pichu%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWgo8EjgyADo0UsOpc2lkZW5jZSAmIFNwYSBMZSBNYWNodSBQaWNodSwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYExIHCOsPEAEYGRgGMgIIASoJCgU6A0VVUhoA",
    "accommodation_property_name": "Résidence & Spa Le Machu Pichu",
    "flight_options": [
      {
        "price_eur": 269.0,
        "airline": "Brussels Airlines + SWISS",
        "duration_minutes": 440,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest",
          "best"
        ],
        "flight_numbers": [
          "SN 3290",
          "LX 799"
        ],
        "trip_total_eur": 1961.48,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 315.0,
        "airline": "ITA",
        "duration_minutes": 390,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "AZ 809",
          "AZ 576"
        ],
        "trip_total_eur": 2009.78,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Résidence & Spa Le Machu Pichu",
        "price_eur_per_night": 254.0,
        "per_person_eur": 762.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1961.48,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20R%C3%A9sidence%20%26%20Spa%20Le%20Machu%20Pichu%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWgo8EjgyADo0UsOpc2lkZW5jZSAmIFNwYSBMZSBNYWNodSBQaWNodSwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYExIHCOsPEAEYGRgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Residence Le Chalet du Mont Vallon",
        "price_eur_per_night": 276.0,
        "per_person_eur": 828.0,
        "is_cheapest": false,
        "rating": 4.3,
        "distance_to_lifts_km": 2.29,
        "trip_total_eur": 2030.78,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Residence%20Le%20Chalet%20du%20Mont%20Vallon%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaXQo_EjsyADo3UmVzaWRlbmNlIExlIENoYWxldCBkdSBNb250IFZhbGxvbiwgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYExIHCOsPEAEYGRgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Duplex apartment on the top floor, ski-in ski-out, right in the center of town.",
        "price_eur_per_night": 280.0,
        "per_person_eur": 840.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 2043.38,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Duplex%20apartment%20on%20the%20top%20floor%2C%20ski-in%20ski-out%2C%20right%20in%20the%20center%20of%20town.%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaigEKbBJoMgA6ZER1cGxleCBhcGFydG1lbnQgb24gdGhlIHRvcCBmbG9vciwgc2tpLWluIHNraS1vdXQsIHJpZ2h0IGluIHRoZSBjZW50ZXIgb2YgdG93bi4sIFZhbCBUaG9yZW5zLCBGcmFuY2UaABIaEhQKBwjrDxABGBMSBwjrDxABGBkYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Village Club MMV Les Arolles",
        "price_eur_per_night": 366.0,
        "per_person_eur": 1098.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 2314.28,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Village%20Club%20MMV%20Les%20Arolles%2C%20Val%20Thorens%2C%20France&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVwo5EjUyADoxVmlsbGFnZSBDbHViIE1NViBMZXMgQXJvbGxlcywgVmFsIFRob3JlbnMsIEZyYW5jZRoAEhoSFAoHCOsPEAEYExIHCOsPEAEYGRgGMgIIASoJCgU6A0VVUhoA"
      }
    ],
    "total_eur_with_fastest_flight": 2009.78,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-1&to=resort-80&date=2027-01-19&time=23%3A15&adults=2&currency=EUR&return_date=2027-01-25&return_time=23%3A15&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 423.5,
      "duration_minutes": 200.0,
      "distance_km": 155.2,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/val-thorens",
    "ski_pass_search_url": "https://www.les3vallees.com/en/skipass",
    "weather": {
      "days": [
        {
          "date": "2027-01-19",
          "is_live_forecast": false,
          "temp_max_c": -5.3,
          "temp_min_c": -13.9,
          "snowfall_cm": 0.9,
          "snow_depth_cm": 136.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-20",
          "is_live_forecast": false,
          "temp_max_c": -7.5,
          "temp_min_c": -14.9,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 135.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-21",
          "is_live_forecast": false,
          "temp_max_c": -4.7,
          "temp_min_c": -17.4,
          "snowfall_cm": 0.0,
          "snow_depth_cm": 133.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-22",
          "is_live_forecast": false,
          "temp_max_c": -3.2,
          "temp_min_c": -10.8,
          "snowfall_cm": 2.9,
          "snow_depth_cm": 133.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-23",
          "is_live_forecast": false,
          "temp_max_c": -3.2,
          "temp_min_c": -9.6,
          "snowfall_cm": 2.5,
          "snow_depth_cm": 135.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-24",
          "is_live_forecast": false,
          "temp_max_c": -1.4,
          "temp_min_c": -10.5,
          "snowfall_cm": 1.9,
          "snow_depth_cm": 137.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-25",
          "is_live_forecast": false,
          "temp_max_c": -0.9,
          "temp_min_c": -8.9,
          "snowfall_cm": 0.7,
          "snow_depth_cm": 136.0,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": -3.7,
      "avg_temp_min_c": -12.3,
      "avg_snowfall_cm": 1.3,
      "avg_snow_depth_cm": 135.4
    }
  },
  {
    "resort": {
      "name": "Kitzbühel",
      "country": "Austria",
      "region": "Kitzbüheler Alpen (KitzSki)",
      "piste_km": 233.0,
      "off_piste_rating": 3,
      "snow_reliability": 3,
      "nightlife_rating": 5,
      "family_friendliness": 4,
      "nearest_airport": "Innsbruck (INN) / Salzburg (SZG) / Munich (MUC)",
      "transfer_time_minutes": 85.0,
      "terrain": {
        "beginner": 0.2,
        "intermediate": 0.65,
        "advanced": 0.15,
        "quality": "estimated"
      },
      "needs_verification": true
    },
    "start_date": "2027-01-30",
    "end_date": "2027-02-05",
    "season": "high",
    "cost": {
      "flight_eur": 266.0,
      "transfer_eur": 15.0,
      "accommodation_eur": 435.0,
      "ski_pass_eur": 329.09,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 72.16,
      "total_eur": 1515.25,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 15.0,
        "duration_minutes": 154,
        "carrier": "Train, line 860 bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Innsbruck-Airport/Kitzb%C3%BChel",
        "is_round_trip": false,
        "roles": [
          "cheapest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 75.0
      },
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 18.0,
        "duration_minutes": 136,
        "carrier": "Train",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Innsbruck-Airport/Kitzb%C3%BChel",
        "is_round_trip": false,
        "roles": [
          "fastest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 35.0
      }
    ],
    "score": 0.6416,
    "score_components": {
      "ski_quality": 0.621,
      "price": 0.275,
      "snow": 0.6,
      "nightlife": 1.0,
      "convenience": 0.77,
      "accommodation": 0.833,
      "family": 0.8
    },
    "explanation": "Why: good nightlife, accommodation matching your comfort level, family-friendly. Terrain: 65% graded for intermediates (estimated, not a published figure). (NOTE: some data for this resort is flagged NEEDS VERIFICATION in the seed DB) Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMzBqBRIDVExWcgUSA0lOThoaEgoyMDI3LTAyLTA1agUSA0lOTnIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Aurach%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaRwopEiUyADohSG90ZWwgQXVyYWNoLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgeEgcI6w8QAhgFGAYyAggBKgkKBToDRVVSGgA",
    "accommodation_property_name": "Hotel Aurach",
    "flight_options": [
      {
        "price_eur": 266.0,
        "airline": "SKY express",
        "duration_minutes": 810,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "GQ 721",
          "GQ 870"
        ],
        "trip_total_eur": 1515.25,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 320.0,
        "airline": "SWISS + Lufthansa",
        "duration_minutes": 580,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best"
        ],
        "flight_numbers": [
          "LX 257",
          "LH 2369"
        ],
        "trip_total_eur": 1571.95,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 391.0,
        "airline": "Austrian",
        "duration_minutes": 335,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "OS 84",
          "OS 103"
        ],
        "trip_total_eur": 1646.5,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Hotel Aurach",
        "price_eur_per_night": 145.0,
        "per_person_eur": 435.0,
        "is_cheapest": true,
        "rating": 4.3,
        "distance_to_lifts_km": 1.36,
        "trip_total_eur": 1515.25,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Aurach%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaRwopEiUyADohSG90ZWwgQXVyYWNoLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgeEgcI6w8QAhgFGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "Ferienhotel Alpenhof",
        "price_eur_per_night": 146.0,
        "per_person_eur": 438.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1518.4,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Ferienhotel%20Alpenhof%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaTwoxEi0yADopRmVyaWVuaG90ZWwgQWxwZW5ob2YsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGB4SBwjrDxACGAUYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Safestay Kitzbühel Centre",
        "price_eur_per_night": 178.0,
        "per_person_eur": 534.0,
        "is_cheapest": false,
        "rating": 4.8,
        "distance_to_lifts_km": 0.32,
        "trip_total_eur": 1619.2,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Safestay%20Kitzb%C3%BChel%20Centre%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVQo3EjMyADovU2FmZXN0YXkgS2l0emLDvGhlbCBDZW50cmUsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGB4SBwjrDxACGAUYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Biohotel in Österreich - Bruggerhof Tirol",
        "price_eur_per_night": 225.0,
        "per_person_eur": 675.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1767.25,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Biohotel%20in%20%C3%96sterreich%20-%20Bruggerhof%20Tirol%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaZQpHEkMyADo_QmlvaG90ZWwgaW4gw5ZzdGVycmVpY2ggLSBCcnVnZ2VyaG9mIFRpcm9sLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgeEgcI6w8QAhgFGAYyAggBKgkKBToDRVVSGgA"
      }
    ],
    "total_eur_with_fastest_flight": 1646.5,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-19&to=resort-169&date=2027-01-30&time=12%3A45&adults=2&currency=EUR&return_date=2027-02-05&return_time=12%3A45&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 306.0,
      "duration_minutes": 145.0,
      "distance_km": 97.8,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.intersportrent.com/skirent-kitzbuehel~12413",
    "ski_pass_search_url": "https://www.kitzski.at/en/ticket-shop-kitzski.html",
    "weather": {
      "days": [
        {
          "date": "2027-01-30",
          "is_live_forecast": false,
          "temp_max_c": 6.6,
          "temp_min_c": -7.0,
          "snowfall_cm": 1.4,
          "snow_depth_cm": 77.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-31",
          "is_live_forecast": false,
          "temp_max_c": 4.5,
          "temp_min_c": -4.5,
          "snowfall_cm": 2.5,
          "snow_depth_cm": 78.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-02-01",
          "is_live_forecast": false,
          "temp_max_c": 3.4,
          "temp_min_c": -2.8,
          "snowfall_cm": 4.4,
          "snow_depth_cm": 82.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-02-02",
          "is_live_forecast": false,
          "temp_max_c": 4.6,
          "temp_min_c": -2.9,
          "snowfall_cm": 8.5,
          "snow_depth_cm": 88.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-02-03",
          "is_live_forecast": false,
          "temp_max_c": 8.0,
          "temp_min_c": -2.1,
          "snowfall_cm": 2.1,
          "snow_depth_cm": 88.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-02-04",
          "is_live_forecast": false,
          "temp_max_c": 6.9,
          "temp_min_c": -4.1,
          "snowfall_cm": 2.3,
          "snow_depth_cm": 87.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-02-05",
          "is_live_forecast": false,
          "temp_max_c": 6.3,
          "temp_min_c": -3.0,
          "snowfall_cm": 0.6,
          "snow_depth_cm": 85.8,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": 5.8,
      "avg_temp_min_c": -3.8,
      "avg_snowfall_cm": 3.1,
      "avg_snow_depth_cm": 84.1
    }
  },
  {
    "resort": {
      "name": "Kitzbühel",
      "country": "Austria",
      "region": "Kitzbüheler Alpen (KitzSki)",
      "piste_km": 233.0,
      "off_piste_rating": 3,
      "snow_reliability": 3,
      "nightlife_rating": 5,
      "family_friendliness": 4,
      "nearest_airport": "Innsbruck (INN) / Salzburg (SZG) / Munich (MUC)",
      "transfer_time_minutes": 85.0,
      "terrain": {
        "beginner": 0.2,
        "intermediate": 0.65,
        "advanced": 0.15,
        "quality": "estimated"
      },
      "needs_verification": true
    },
    "start_date": "2027-01-12",
    "end_date": "2027-01-18",
    "season": "high",
    "cost": {
      "flight_eur": 334.0,
      "transfer_eur": 15.0,
      "accommodation_eur": 369.0,
      "ski_pass_eur": 329.09,
      "equipment_eur": 110.0,
      "food_eur": 288.0,
      "misc_eur": 72.26,
      "total_eur": 1517.35,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 15.0,
        "duration_minutes": 154,
        "carrier": "Train, line 860 bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Innsbruck-Airport/Kitzb%C3%BChel",
        "is_round_trip": false,
        "roles": [
          "cheapest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 75.0
      },
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 18.0,
        "duration_minutes": 136,
        "carrier": "Train",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Innsbruck-Airport/Kitzb%C3%BChel",
        "is_round_trip": false,
        "roles": [
          "fastest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 35.0
      }
    ],
    "score": 0.6416,
    "score_components": {
      "ski_quality": 0.621,
      "price": 0.275,
      "snow": 0.6,
      "nightlife": 1.0,
      "convenience": 0.77,
      "accommodation": 0.833,
      "family": 0.8
    },
    "explanation": "Why: good nightlife, accommodation matching your comfort level, family-friendly. Terrain: 65% graded for intermediates (estimated, not a published figure). (NOTE: some data for this resort is flagged NEEDS VERIFICATION in the seed DB) Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMTJqBRIDVExWcgUSA0lOThoaEgoyMDI3LTAxLTE4agUSA0lOTnIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Aurach%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaRwopEiUyADohSG90ZWwgQXVyYWNoLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgMEgcI6w8QARgSGAYyAggBKgkKBToDRVVSGgA",
    "accommodation_property_name": "Hotel Aurach",
    "flight_options": [
      {
        "price_eur": 334.0,
        "airline": "Lufthansa",
        "duration_minutes": 250,
        "stops": 0,
        "is_cheapest": true,
        "roles": [
          "cheapest",
          "best",
          "fastest"
        ],
        "flight_numbers": [
          "LH 681"
        ],
        "trip_total_eur": 1517.35,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Hotel Aurach",
        "price_eur_per_night": 123.0,
        "per_person_eur": 369.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1517.35,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Aurach%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaRwopEiUyADohSG90ZWwgQXVyYWNoLCBLaXR6YsO8aGVsLCBBdXN0cmlhGgASGhIUCgcI6w8QARgMEgcI6w8QARgSGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "Safestay Kitzbühel Centre",
        "price_eur_per_night": 178.0,
        "per_person_eur": 534.0,
        "is_cheapest": false,
        "rating": 4.8,
        "distance_to_lifts_km": 0.32,
        "trip_total_eur": 1690.6,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Safestay%20Kitzb%C3%BChel%20Centre%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVQo3EjMyADovU2FmZXN0YXkgS2l0emLDvGhlbCBDZW50cmUsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGAwSBwjrDxABGBIYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Hotel Neuwirt Kaiserhotels",
        "price_eur_per_night": 205.0,
        "per_person_eur": 615.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1775.65,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Neuwirt%20Kaiserhotels%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaVQo3EjMyADovSG90ZWwgTmV1d2lydCBLYWlzZXJob3RlbHMsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGAwSBwjrDxABGBIYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Hotel Garni Entstrasser",
        "price_eur_per_night": 237.0,
        "per_person_eur": 711.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1876.45,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Hotel%20Garni%20Entstrasser%2C%20Kitzb%C3%BChel%2C%20Austria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaUgo0EjAyADosSG90ZWwgR2FybmkgRW50c3RyYXNzZXIsIEtpdHpiw7xoZWwsIEF1c3RyaWEaABIaEhQKBwjrDxABGAwSBwjrDxABGBIYBjICCAEqCQoFOgNFVVIaAA"
      }
    ],
    "total_eur_with_fastest_flight": 1517.35,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-19&to=resort-169&date=2027-01-12&time=21%3A05&adults=2&currency=EUR&return_date=2027-01-18&return_time=21%3A05&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 306.0,
      "duration_minutes": 145.0,
      "distance_km": 97.8,
      "vehicles_offered": 3,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.intersportrent.com/skirent-kitzbuehel~12413",
    "ski_pass_search_url": "https://www.kitzski.at/en/ticket-shop-kitzski.html",
    "weather": {
      "days": [
        {
          "date": "2027-01-12",
          "is_live_forecast": false,
          "temp_max_c": 2.2,
          "temp_min_c": -10.0,
          "snowfall_cm": 0.9,
          "snow_depth_cm": 66.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": 4.7,
          "temp_min_c": -11.2,
          "snowfall_cm": 0.3,
          "snow_depth_cm": 65.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 6.3,
          "temp_min_c": -10.2,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 64.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": 4.6,
          "temp_min_c": -5.7,
          "snowfall_cm": 1.9,
          "snow_depth_cm": 63.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-16",
          "is_live_forecast": false,
          "temp_max_c": 4.8,
          "temp_min_c": -8.4,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 65.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-17",
          "is_live_forecast": false,
          "temp_max_c": 5.1,
          "temp_min_c": -9.2,
          "snowfall_cm": 0.7,
          "snow_depth_cm": 65.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-18",
          "is_live_forecast": false,
          "temp_max_c": 5.7,
          "temp_min_c": -5.4,
          "snowfall_cm": 1.6,
          "snow_depth_cm": 69.0,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": 4.8,
      "avg_temp_min_c": -8.6,
      "avg_snowfall_cm": 0.8,
      "avg_snow_depth_cm": 65.7
    }
  },
  {
    "resort": {
      "name": "Bansko",
      "country": "Bulgaria",
      "region": "Pirin Mountains",
      "piste_km": 75.0,
      "off_piste_rating": 2,
      "snow_reliability": 3,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Sofia (SOF)",
      "transfer_time_minutes": 125.0,
      "terrain": {
        "beginner": 0.4,
        "intermediate": 0.4,
        "advanced": 0.2,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-11",
    "end_date": "2027-01-17",
    "season": "high",
    "cost": {
      "flight_eur": 186.0,
      "transfer_eur": 4.0,
      "accommodation_eur": 132.0,
      "ski_pass_eur": 256.33,
      "equipment_eur": 110.0,
      "food_eur": 180.0,
      "misc_eur": 43.42,
      "total_eur": 911.7499999999999,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 4.0,
        "duration_minutes": 285,
        "carrier": "Bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Sofia-Airport-SOF/Bansko",
        "is_round_trip": false,
        "roles": [
          "cheapest",
          "fastest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 12.0
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 6.0,
        "duration_minutes": 287,
        "carrier": "Bus via Хотел Плиска",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Sofia-Airport-SOF/Bansko",
        "is_round_trip": false,
        "roles": [],
        "is_indicative": true,
        "price_high_eur_per_person": 10.0
      },
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 7.0,
        "duration_minutes": 317,
        "carrier": "Train, bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Sofia-Airport-SOF/Bansko",
        "is_round_trip": false,
        "roles": [],
        "is_indicative": true,
        "price_high_eur_per_person": 14.0
      }
    ],
    "score": 0.5835,
    "score_components": {
      "ski_quality": 0.482,
      "price": 0.55,
      "snow": 0.6,
      "nightlife": 0.8,
      "convenience": 0.556,
      "accommodation": 0.633,
      "family": 0.8
    },
    "explanation": "Why: good nightlife, family-friendly, accommodation matching your comfort level. Terrain: 40% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMTFqBRIDVExWcgUSA1NPRhoaEgoyMDI3LTAxLTE3agUSA1NPRnIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Zigen%20House%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaQwolEiEyADodWmlnZW4gSG91c2UsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjrDxABGAsSBwjrDxABGBEYBjICCAEqCQoFOgNFVVIaAA",
    "accommodation_property_name": "Zigen House",
    "flight_options": [
      {
        "price_eur": 186.0,
        "airline": "Aegean",
        "duration_minutes": 485,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest",
          "best"
        ],
        "flight_numbers": [
          "A3 925",
          "A3 982"
        ],
        "trip_total_eur": 911.75,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 292.0,
        "airline": "Austrian",
        "duration_minutes": 355,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "OS 84",
          "OS 771"
        ],
        "trip_total_eur": 1023.05,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Zigen House",
        "price_eur_per_night": 44.0,
        "per_person_eur": 132.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 911.75,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Zigen%20House%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaQwolEiEyADodWmlnZW4gSG91c2UsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjrDxABGAsSBwjrDxABGBEYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Trinity Bansko Spa Hotel",
        "price_eur_per_night": 45.0,
        "per_person_eur": 135.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 914.9,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Trinity%20Bansko%20Spa%20Hotel%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaUAoyEi4yADoqVHJpbml0eSBCYW5za28gU3BhIEhvdGVsLCBCYW5za28sIEJ1bGdhcmlhGgASGhIUCgcI6w8QARgLEgcI6w8QARgRGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "Family House Oreha - Suite (3 Adults)",
        "price_eur_per_night": 47.0,
        "per_person_eur": 141.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 921.2,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Family%20House%20Oreha%20-%20Suite%20%283%20Adults%29%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaXQo_EjsyADo3RmFtaWx5IEhvdXNlIE9yZWhhIC0gU3VpdGUgKDMgQWR1bHRzKSwgQmFuc2tvLCBCdWxnYXJpYRoAEhoSFAoHCOsPEAEYCxIHCOsPEAEYERgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Cozy nature stay , Great view, free Parking",
        "price_eur_per_night": 64.0,
        "per_person_eur": 192.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 974.75,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Cozy%20nature%20stay%20%2C%20Great%20view%2C%20free%20Parking%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaYwpFEkEyADo9Q296eSBuYXR1cmUgc3RheSAsIEdyZWF0IHZpZXcsIGZyZWUgUGFya2luZywgQmFuc2tvLCBCdWxnYXJpYRoAEhoSFAoHCOsPEAEYCxIHCOsPEAEYERgGMgIIASoJCgU6A0VVUhoA"
      }
    ],
    "total_eur_with_fastest_flight": 1023.05,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-44&to=resort-632&date=2027-01-11&time=21%3A10&adults=2&currency=EUR&return_date=2027-01-17&return_time=21%3A10&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 222.0,
      "duration_minutes": 180.0,
      "distance_km": 159.5,
      "vehicles_offered": 2,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/bansko",
    "ski_pass_search_url": "https://www.banskoski.com/en",
    "weather": {
      "days": [
        {
          "date": "2027-01-11",
          "is_live_forecast": false,
          "temp_max_c": 3.7,
          "temp_min_c": -2.6,
          "snowfall_cm": 0.5,
          "snow_depth_cm": 9.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-12",
          "is_live_forecast": false,
          "temp_max_c": 1.8,
          "temp_min_c": -7.1,
          "snowfall_cm": 2.9,
          "snow_depth_cm": 9.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": 2.1,
          "temp_min_c": -7.8,
          "snowfall_cm": 0.3,
          "snow_depth_cm": 8.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 5.7,
          "temp_min_c": -5.4,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 8.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": 5.7,
          "temp_min_c": -4.9,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 7.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-16",
          "is_live_forecast": false,
          "temp_max_c": 5.9,
          "temp_min_c": -3.5,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 16.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-17",
          "is_live_forecast": false,
          "temp_max_c": 7.1,
          "temp_min_c": -2.6,
          "snowfall_cm": 0.0,
          "snow_depth_cm": 15.8,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": 4.6,
      "avg_temp_min_c": -4.8,
      "avg_snowfall_cm": 0.6,
      "avg_snow_depth_cm": 10.8
    }
  },
  {
    "resort": {
      "name": "Bansko",
      "country": "Bulgaria",
      "region": "Pirin Mountains",
      "piste_km": 75.0,
      "off_piste_rating": 2,
      "snow_reliability": 3,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Sofia (SOF)",
      "transfer_time_minutes": 125.0,
      "terrain": {
        "beginner": 0.4,
        "intermediate": 0.4,
        "advanced": 0.2,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-12",
    "end_date": "2027-01-18",
    "season": "high",
    "cost": {
      "flight_eur": 186.0,
      "transfer_eur": 4.0,
      "accommodation_eur": 132.0,
      "ski_pass_eur": 256.33,
      "equipment_eur": 110.0,
      "food_eur": 180.0,
      "misc_eur": 43.42,
      "total_eur": 911.7499999999999,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 4.0,
        "duration_minutes": 285,
        "carrier": "Bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Sofia-Airport-SOF/Bansko",
        "is_round_trip": false,
        "roles": [
          "cheapest",
          "fastest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 12.0
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 6.0,
        "duration_minutes": 287,
        "carrier": "Bus via Хотел Плиска",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Sofia-Airport-SOF/Bansko",
        "is_round_trip": false,
        "roles": [],
        "is_indicative": true,
        "price_high_eur_per_person": 10.0
      },
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 7.0,
        "duration_minutes": 317,
        "carrier": "Train, bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Sofia-Airport-SOF/Bansko",
        "is_round_trip": false,
        "roles": [],
        "is_indicative": true,
        "price_high_eur_per_person": 14.0
      }
    ],
    "score": 0.5835,
    "score_components": {
      "ski_quality": 0.482,
      "price": 0.55,
      "snow": 0.6,
      "nightlife": 0.8,
      "convenience": 0.556,
      "accommodation": 0.633,
      "family": 0.8
    },
    "explanation": "Why: good nightlife, family-friendly, accommodation matching your comfort level. Terrain: 40% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMTJqBRIDVExWcgUSA1NPRhoaEgoyMDI3LTAxLTE4agUSA1NPRnIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Zigen%20House%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaQwolEiEyADodWmlnZW4gSG91c2UsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjrDxABGAwSBwjrDxABGBIYBjICCAEqCQoFOgNFVVIaAA",
    "accommodation_property_name": "Zigen House",
    "flight_options": [
      {
        "price_eur": 186.0,
        "airline": "Aegean",
        "duration_minutes": 890,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "A3 929",
          "A3 982"
        ],
        "trip_total_eur": 911.75,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 243.0,
        "airline": "TAROM",
        "duration_minutes": 630,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best"
        ],
        "flight_numbers": [
          "RO 156",
          "RO 291"
        ],
        "trip_total_eur": 971.6,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 362.0,
        "airline": "Austrian",
        "duration_minutes": 355,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "OS 84",
          "OS 771"
        ],
        "trip_total_eur": 1096.55,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Zigen House",
        "price_eur_per_night": 44.0,
        "per_person_eur": 132.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 911.75,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Zigen%20House%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaQwolEiEyADodWmlnZW4gSG91c2UsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjrDxABGAwSBwjrDxABGBIYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Trinity Bansko Spa Hotel",
        "price_eur_per_night": 45.0,
        "per_person_eur": 135.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 914.9,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Trinity%20Bansko%20Spa%20Hotel%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaUAoyEi4yADoqVHJpbml0eSBCYW5za28gU3BhIEhvdGVsLCBCYW5za28sIEJ1bGdhcmlhGgASGhIUCgcI6w8QARgMEgcI6w8QARgSGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "BanskoVilla Zlateva House, Bansko",
        "price_eur_per_night": 63.0,
        "per_person_eur": 189.0,
        "is_cheapest": false,
        "rating": 4.6,
        "distance_to_lifts_km": 0.67,
        "trip_total_eur": 971.6,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20BanskoVilla%20Zlateva%20House%2C%20Bansko%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWQo7EjcyADozQmFuc2tvVmlsbGEgWmxhdGV2YSBIb3VzZSwgQmFuc2tvLCBCYW5za28sIEJ1bGdhcmlhGgASGhIUCgcI6w8QARgMEgcI6w8QARgSGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "Cozy nature stay , Great view, free Parking",
        "price_eur_per_night": 64.0,
        "per_person_eur": 192.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 974.75,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Cozy%20nature%20stay%20%2C%20Great%20view%2C%20free%20Parking%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaYwpFEkEyADo9Q296eSBuYXR1cmUgc3RheSAsIEdyZWF0IHZpZXcsIGZyZWUgUGFya2luZywgQmFuc2tvLCBCdWxnYXJpYRoAEhoSFAoHCOsPEAEYDBIHCOsPEAEYEhgGMgIIASoJCgU6A0VVUhoA"
      }
    ],
    "total_eur_with_fastest_flight": 1096.55,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-44&to=resort-632&date=2027-01-12&time=20%3A55&adults=2&currency=EUR&return_date=2027-01-18&return_time=20%3A55&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 222.0,
      "duration_minutes": 180.0,
      "distance_km": 159.5,
      "vehicles_offered": 2,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/bansko",
    "ski_pass_search_url": "https://www.banskoski.com/en",
    "weather": {
      "days": [
        {
          "date": "2027-01-12",
          "is_live_forecast": false,
          "temp_max_c": 1.8,
          "temp_min_c": -7.1,
          "snowfall_cm": 2.9,
          "snow_depth_cm": 9.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": 2.1,
          "temp_min_c": -7.8,
          "snowfall_cm": 0.3,
          "snow_depth_cm": 8.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 5.7,
          "temp_min_c": -5.4,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 8.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": 5.7,
          "temp_min_c": -4.9,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 7.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-16",
          "is_live_forecast": false,
          "temp_max_c": 5.9,
          "temp_min_c": -3.5,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 16.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-17",
          "is_live_forecast": false,
          "temp_max_c": 7.1,
          "temp_min_c": -2.6,
          "snowfall_cm": 0.0,
          "snow_depth_cm": 15.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-18",
          "is_live_forecast": false,
          "temp_max_c": 7.6,
          "temp_min_c": -2.6,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 14.4,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": 5.1,
      "avg_temp_min_c": -4.8,
      "avg_snowfall_cm": 0.5,
      "avg_snow_depth_cm": 11.5
    }
  },
  {
    "resort": {
      "name": "Bansko",
      "country": "Bulgaria",
      "region": "Pirin Mountains",
      "piste_km": 75.0,
      "off_piste_rating": 2,
      "snow_reliability": 3,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Sofia (SOF)",
      "transfer_time_minutes": 125.0,
      "terrain": {
        "beginner": 0.4,
        "intermediate": 0.4,
        "advanced": 0.2,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-30",
    "end_date": "2027-02-05",
    "season": "high",
    "cost": {
      "flight_eur": 198.0,
      "transfer_eur": 44.93,
      "accommodation_eur": 132.0,
      "ski_pass_eur": 256.33,
      "equipment_eur": 110.0,
      "food_eur": 180.0,
      "misc_eur": 46.07,
      "total_eur": 967.33,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 44.93,
        "duration_minutes": 115,
        "carrier": "Infobus",
        "departure": "2027-01-30T22:25:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMzAiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIyMjoyNSIsImFycml2YWxUaW1lIjoiMDA6MjAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMi0wNSIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjAwOjIwIiwiYXJyaXZhbFBvc2l0aW9uIjozNjk3MDcsImRlcGFydHVyZVBvc2l0aW9uIjozMTQwNjcsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.sURitvKy4U1kSgwr90LATMNcD69f04kL6mPUFOyH5p4",
        "is_round_trip": true,
        "roles": [
          "cheapest",
          "fastest"
        ],
        "is_indicative": false,
        "price_high_eur_per_person": null
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 45.53,
        "duration_minutes": 155,
        "carrier": "Infobus",
        "departure": "2027-01-30T22:15:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMzAiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIyMjoxNSIsImFycml2YWxUaW1lIjoiMDA6NTAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMi0wNSIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjAwOjUwIiwiYXJyaXZhbFBvc2l0aW9uIjozNjk3MDcsImRlcGFydHVyZVBvc2l0aW9uIjozMTQwNjcsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.RvQZMuoKb18LI6Rh5S7A7UAOtHvMH8WCefvBRwaGOYo",
        "is_round_trip": true,
        "roles": [],
        "is_indicative": false,
        "price_high_eur_per_person": null
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 46.64,
        "duration_minutes": 145,
        "carrier": "Infobus",
        "departure": "2027-01-30T22:25:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMzAiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIyMjoyNSIsImFycml2YWxUaW1lIjoiMDA6NTAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMi0wNSIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjAwOjUwIiwiYXJyaXZhbFBvc2l0aW9uIjozNjk3MDcsImRlcGFydHVyZVBvc2l0aW9uIjozMTQwNjcsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.KmORv293DNzDFYOEwfAADLz5ysPp7Rkr-f-kzJWNHNQ",
        "is_round_trip": true,
        "roles": [],
        "is_indicative": false,
        "price_high_eur_per_person": null
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 49.98,
        "duration_minutes": 135,
        "carrier": "Infobus",
        "departure": "2027-01-30T22:25:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMzAiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIyMjoyNSIsImFycml2YWxUaW1lIjoiMDA6NDAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMi0wNSIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjAwOjQwIiwiYXJyaXZhbFBvc2l0aW9uIjozNjk3MDcsImRlcGFydHVyZVBvc2l0aW9uIjozMTQwNjcsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.2rgwcNQJOx9ZJDPq-byMOYXxo1ZTHiYm4-rmrz-h6IM",
        "is_round_trip": true,
        "roles": [],
        "is_indicative": false,
        "price_high_eur_per_person": null
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 61.09,
        "duration_minutes": 155,
        "carrier": "Infobus",
        "departure": "2027-01-30T22:25:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMzAiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIyMjoyNSIsImFycml2YWxUaW1lIjoiMDE6MDAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMi0wNSIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjAxOjAwIiwiYXJyaXZhbFBvc2l0aW9uIjozNjk3MDcsImRlcGFydHVyZVBvc2l0aW9uIjozMTQwNjcsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.i3sbWLoPwQVY6Rb7fDJWrY5s9Apl9hMWQZUoCE3lMuM",
        "is_round_trip": true,
        "roles": [],
        "is_indicative": false,
        "price_high_eur_per_person": null
      }
    ],
    "score": 0.5823,
    "score_components": {
      "ski_quality": 0.482,
      "price": 0.544,
      "snow": 0.6,
      "nightlife": 0.8,
      "convenience": 0.556,
      "accommodation": 0.633,
      "family": 0.8
    },
    "explanation": "Why: good nightlife, family-friendly, accommodation matching your comfort level. Terrain: 40% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMzBqBRIDVExWcgUSA1NPRhoaEgoyMDI3LTAyLTA1agUSA1NPRnIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Zigen%20House%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaQwolEiEyADodWmlnZW4gSG91c2UsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjrDxABGB4SBwjrDxACGAUYBjICCAEqCQoFOgNFVVIaAA",
    "accommodation_property_name": "Zigen House",
    "flight_options": [
      {
        "price_eur": 198.0,
        "airline": "Aegean",
        "duration_minutes": 305,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "A3 929",
          "A3 980"
        ],
        "trip_total_eur": 967.33,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 240.0,
        "airline": "Wizz Air",
        "duration_minutes": 170,
        "stops": 0,
        "is_cheapest": false,
        "roles": [
          "best",
          "fastest"
        ],
        "flight_numbers": [
          "W6 4428"
        ],
        "trip_total_eur": 1011.43,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Zigen House",
        "price_eur_per_night": 44.0,
        "per_person_eur": 132.0,
        "is_cheapest": true,
        "rating": 4.8,
        "distance_to_lifts_km": 1.14,
        "trip_total_eur": 967.33,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Zigen%20House%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaQwolEiEyADodWmlnZW4gSG91c2UsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjrDxABGB4SBwjrDxACGAUYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Стаята на Ив",
        "price_eur_per_night": 57.0,
        "per_person_eur": 171.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1008.28,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20%D0%A1%D1%82%D0%B0%D1%8F%D1%82%D0%B0%20%D0%BD%D0%B0%20%D0%98%D0%B2%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaTgowEiwyADoo0KHRgtCw0Y_RgtCwINC90LAg0JjQsiwgQmFuc2tvLCBCdWxnYXJpYRoAEhoSFAoHCOsPEAEYHhIHCOsPEAIYBRgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Borealis Apartment",
        "price_eur_per_night": 70.0,
        "per_person_eur": 210.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1049.23,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Borealis%20Apartment%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaSgosEigyADokQm9yZWFsaXMgQXBhcnRtZW50LCBCYW5za28sIEJ1bGdhcmlhGgASGhIUCgcI6w8QARgeEgcI6w8QAhgFGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "BanskoVilla Zlateva House, Bansko",
        "price_eur_per_night": 74.0,
        "per_person_eur": 222.0,
        "is_cheapest": false,
        "rating": 4.6,
        "distance_to_lifts_km": 0.67,
        "trip_total_eur": 1061.83,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20BanskoVilla%20Zlateva%20House%2C%20Bansko%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWQo7EjcyADozQmFuc2tvVmlsbGEgWmxhdGV2YSBIb3VzZSwgQmFuc2tvLCBCYW5za28sIEJ1bGdhcmlhGgASGhIUCgcI6w8QARgeEgcI6w8QAhgFGAYyAggBKgkKBToDRVVSGgA"
      }
    ],
    "total_eur_with_fastest_flight": 1011.43,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-44&to=resort-632&date=2027-01-30&time=11%3A10&adults=2&currency=EUR&return_date=2027-02-05&return_time=11%3A10&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 222.0,
      "duration_minutes": 180.0,
      "distance_km": 159.5,
      "vehicles_offered": 2,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/bansko",
    "ski_pass_search_url": "https://www.banskoski.com/en",
    "weather": {
      "days": [
        {
          "date": "2027-01-30",
          "is_live_forecast": false,
          "temp_max_c": 5.7,
          "temp_min_c": -2.9,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 15.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-31",
          "is_live_forecast": false,
          "temp_max_c": 7.1,
          "temp_min_c": -3.5,
          "snowfall_cm": 0.4,
          "snow_depth_cm": 14.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-02-01",
          "is_live_forecast": false,
          "temp_max_c": 6.2,
          "temp_min_c": -3.9,
          "snowfall_cm": 3.2,
          "snow_depth_cm": 17.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-02-02",
          "is_live_forecast": false,
          "temp_max_c": 4.7,
          "temp_min_c": -3.9,
          "snowfall_cm": 1.5,
          "snow_depth_cm": 18.0,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-02-03",
          "is_live_forecast": false,
          "temp_max_c": 6.4,
          "temp_min_c": -4.1,
          "snowfall_cm": 0.6,
          "snow_depth_cm": 16.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-02-04",
          "is_live_forecast": false,
          "temp_max_c": 5.1,
          "temp_min_c": -3.8,
          "snowfall_cm": 0.3,
          "snow_depth_cm": 15.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-02-05",
          "is_live_forecast": false,
          "temp_max_c": 6.6,
          "temp_min_c": -3.6,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 15.0,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": 6.0,
      "avg_temp_min_c": -3.7,
      "avg_snowfall_cm": 0.9,
      "avg_snow_depth_cm": 16.0
    }
  },
  {
    "resort": {
      "name": "Bansko",
      "country": "Bulgaria",
      "region": "Pirin Mountains",
      "piste_km": 75.0,
      "off_piste_rating": 2,
      "snow_reliability": 3,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Sofia (SOF)",
      "transfer_time_minutes": 125.0,
      "terrain": {
        "beginner": 0.4,
        "intermediate": 0.4,
        "advanced": 0.2,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-13",
    "end_date": "2027-01-19",
    "season": "high",
    "cost": {
      "flight_eur": 198.0,
      "transfer_eur": 4.0,
      "accommodation_eur": 132.0,
      "ski_pass_eur": 256.33,
      "equipment_eur": 110.0,
      "food_eur": 180.0,
      "misc_eur": 44.02,
      "total_eur": 924.3499999999999,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 4.0,
        "duration_minutes": 285,
        "carrier": "Bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Sofia-Airport-SOF/Bansko",
        "is_round_trip": false,
        "roles": [
          "cheapest",
          "fastest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 12.0
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 6.0,
        "duration_minutes": 287,
        "carrier": "Bus via Хотел Плиска",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Sofia-Airport-SOF/Bansko",
        "is_round_trip": false,
        "roles": [],
        "is_indicative": true,
        "price_high_eur_per_person": 10.0
      },
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 7.0,
        "duration_minutes": 317,
        "carrier": "Train, bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Sofia-Airport-SOF/Bansko",
        "is_round_trip": false,
        "roles": [],
        "is_indicative": true,
        "price_high_eur_per_person": 14.0
      }
    ],
    "score": 0.5823,
    "score_components": {
      "ski_quality": 0.482,
      "price": 0.544,
      "snow": 0.6,
      "nightlife": 0.8,
      "convenience": 0.556,
      "accommodation": 0.633,
      "family": 0.8
    },
    "explanation": "Why: good nightlife, family-friendly, accommodation matching your comfort level. Terrain: 40% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMTNqBRIDVExWcgUSA1NPRhoaEgoyMDI3LTAxLTE5agUSA1NPRnIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Trinity%20Bansko%20Spa%20Hotel%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaUAoyEi4yADoqVHJpbml0eSBCYW5za28gU3BhIEhvdGVsLCBCYW5za28sIEJ1bGdhcmlhGgASGhIUCgcI6w8QARgNEgcI6w8QARgTGAYyAggBKgkKBToDRVVSGgA",
    "accommodation_property_name": "Trinity Bansko Spa Hotel",
    "flight_options": [
      {
        "price_eur": 198.0,
        "airline": "Aegean",
        "duration_minutes": 305,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest",
          "best"
        ],
        "flight_numbers": [
          "A3 929",
          "A3 980"
        ],
        "trip_total_eur": 924.35,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 293.0,
        "airline": "El Al",
        "duration_minutes": 165,
        "stops": 0,
        "is_cheapest": false,
        "roles": [
          "fastest"
        ],
        "flight_numbers": [
          "LY 551"
        ],
        "trip_total_eur": 1024.1,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Trinity Bansko Spa Hotel",
        "price_eur_per_night": 44.0,
        "per_person_eur": 132.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 924.35,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Trinity%20Bansko%20Spa%20Hotel%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaUAoyEi4yADoqVHJpbml0eSBCYW5za28gU3BhIEhvdGVsLCBCYW5za28sIEJ1bGdhcmlhGgASGhIUCgcI6w8QARgNEgcI6w8QARgTGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "Zigen House",
        "price_eur_per_night": 44.0,
        "per_person_eur": 132.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 924.35,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Zigen%20House%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaQwolEiEyADodWmlnZW4gSG91c2UsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjrDxABGA0SBwjrDxABGBMYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "BanskoVilla Zlateva House, Bansko",
        "price_eur_per_night": 63.0,
        "per_person_eur": 189.0,
        "is_cheapest": false,
        "rating": 4.6,
        "distance_to_lifts_km": 0.67,
        "trip_total_eur": 984.2,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20BanskoVilla%20Zlateva%20House%2C%20Bansko%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWQo7EjcyADozQmFuc2tvVmlsbGEgWmxhdGV2YSBIb3VzZSwgQmFuc2tvLCBCYW5za28sIEJ1bGdhcmlhGgASGhIUCgcI6w8QARgNEgcI6w8QARgTGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "Molerite Wine & Dine",
        "price_eur_per_night": 68.0,
        "per_person_eur": 204.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 999.95,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Molerite%20Wine%20%26%20Dine%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaTAouEioyADomTW9sZXJpdGUgV2luZSAmIERpbmUsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjrDxABGA0SBwjrDxABGBMYBjICCAEqCQoFOgNFVVIaAA"
      }
    ],
    "total_eur_with_fastest_flight": 1024.1,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-44&to=resort-632&date=2027-01-13&time=11%3A10&adults=2&currency=EUR&return_date=2027-01-19&return_time=11%3A10&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 222.0,
      "duration_minutes": 180.0,
      "distance_km": 159.5,
      "vehicles_offered": 2,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/bansko",
    "ski_pass_search_url": "https://www.banskoski.com/en",
    "weather": {
      "days": [
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": 2.1,
          "temp_min_c": -7.8,
          "snowfall_cm": 0.3,
          "snow_depth_cm": 8.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 5.7,
          "temp_min_c": -5.4,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 8.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": 5.7,
          "temp_min_c": -4.9,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 7.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-16",
          "is_live_forecast": false,
          "temp_max_c": 5.9,
          "temp_min_c": -3.5,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 16.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-17",
          "is_live_forecast": false,
          "temp_max_c": 7.1,
          "temp_min_c": -2.6,
          "snowfall_cm": 0.0,
          "snow_depth_cm": 15.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-18",
          "is_live_forecast": false,
          "temp_max_c": 7.6,
          "temp_min_c": -2.6,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 14.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-19",
          "is_live_forecast": false,
          "temp_max_c": 7.4,
          "temp_min_c": -2.8,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 13.0,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": 5.9,
      "avg_temp_min_c": -4.2,
      "avg_snowfall_cm": 0.1,
      "avg_snow_depth_cm": 12.0
    }
  },
  {
    "resort": {
      "name": "Bansko",
      "country": "Bulgaria",
      "region": "Pirin Mountains",
      "piste_km": 75.0,
      "off_piste_rating": 2,
      "snow_reliability": 3,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Sofia (SOF)",
      "transfer_time_minutes": 125.0,
      "terrain": {
        "beginner": 0.4,
        "intermediate": 0.4,
        "advanced": 0.2,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-08",
    "end_date": "2027-01-14",
    "season": "high",
    "cost": {
      "flight_eur": 201.0,
      "transfer_eur": 44.93,
      "accommodation_eur": 132.0,
      "ski_pass_eur": 256.33,
      "equipment_eur": 110.0,
      "food_eur": 180.0,
      "misc_eur": 46.22,
      "total_eur": 970.48,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 44.93,
        "duration_minutes": 115,
        "carrier": "Infobus",
        "departure": "2027-01-11T22:25:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTEiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIyMjoyNSIsImFycml2YWxUaW1lIjoiMDA6MjAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xNyIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjAwOjIwIiwiYXJyaXZhbFBvc2l0aW9uIjozNjk3MDcsImRlcGFydHVyZVBvc2l0aW9uIjozMTQwNjcsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.y4sdkPRqT27gn4qQ1BKeY1qm31Prm0uIdHH1ujjuw1k",
        "is_round_trip": true,
        "roles": [
          "cheapest",
          "fastest"
        ],
        "is_indicative": false,
        "price_high_eur_per_person": null
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 45.53,
        "duration_minutes": 155,
        "carrier": "Infobus",
        "departure": "2027-01-11T22:15:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTEiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIyMjoxNSIsImFycml2YWxUaW1lIjoiMDA6NTAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xNyIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjAwOjUwIiwiYXJyaXZhbFBvc2l0aW9uIjozNjk3MDcsImRlcGFydHVyZVBvc2l0aW9uIjozMTQwNjcsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.laVqP8uBm3XgK5e_Iuh5skMnpuizXECXoAK1A2FzdN8",
        "is_round_trip": true,
        "roles": [],
        "is_indicative": false,
        "price_high_eur_per_person": null
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 46.64,
        "duration_minutes": 145,
        "carrier": "Infobus",
        "departure": "2027-01-11T22:25:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTEiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIyMjoyNSIsImFycml2YWxUaW1lIjoiMDA6NTAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xNyIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjAwOjUwIiwiYXJyaXZhbFBvc2l0aW9uIjozNjk3MDcsImRlcGFydHVyZVBvc2l0aW9uIjozMTQwNjcsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.QXCUwif-ta1A9nedpbuMfOwLDNLmaYyCiUUB3qOLVkE",
        "is_round_trip": true,
        "roles": [],
        "is_indicative": false,
        "price_high_eur_per_person": null
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 49.98,
        "duration_minutes": 135,
        "carrier": "Infobus",
        "departure": "2027-01-11T22:25:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTEiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIyMjoyNSIsImFycml2YWxUaW1lIjoiMDA6NDAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xNyIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjAwOjQwIiwiYXJyaXZhbFBvc2l0aW9uIjozNjk3MDcsImRlcGFydHVyZVBvc2l0aW9uIjozMTQwNjcsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.5vOtyvMqf3VIgtnaOSac_9HBRhJdwRKs8UuTv6_XYno",
        "is_round_trip": true,
        "roles": [],
        "is_indicative": false,
        "price_high_eur_per_person": null
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 61.09,
        "duration_minutes": 155,
        "carrier": "Infobus",
        "departure": "2027-01-11T22:25:00+01:00",
        "booking_url": "https://www.omio.com/links/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXJ0bmVyIjp7ImlkIjoib21pb2FpIn0sImVuYWJsZWQiOnRydWUsImxhbmRUbyI6IlNFQVJDSF9KT1VSTkVZX1BBR0UiLCJza2lwVHJhbnNmZXJQYWdlIjp0cnVlLCJsYW5kaW5nRG9tYWluIjoiIiwicGFydG5lckxvZ29VcmwiOiIiLCJwcm92aWRlcklkcyI6WyIxMDAxMjAiXSwiZGVwYXJ0dXJlRGF0ZSI6IjIwMjctMDEtMTEiLCJlYXJsaWVzdERlcGFydHVyZVRpbWUiOiIyMjoyNSIsImFycml2YWxUaW1lIjoiMDE6MDAiLCJyZXR1cm5EYXRlIjoiMjAyNy0wMS0xNyIsImVhcmxpZXN0UmV0dXJuRGVwYXJ0dXJlVGltZSI6IjAxOjAwIiwiYXJyaXZhbFBvc2l0aW9uIjozNjk3MDcsImRlcGFydHVyZVBvc2l0aW9uIjozMTQwNjcsImFkdWx0c0NvdW50IjoyLCJzb3VyY2VTeXN0ZW0iOiJiMmItZGlzY292ZXJ5LWFwaSIsImxvY2FsZSI6ImVuIiwiY3VycmVuY3kiOiJFVVIiLCJ0cmF2ZWxNb2RlIjoiYnVzIn0.8Tj8ztkSH7gwKCQB6MrdQYDtFAYWZrm-1R3c77d0AUQ",
        "is_round_trip": true,
        "roles": [],
        "is_indicative": false,
        "price_high_eur_per_person": null
      }
    ],
    "score": 0.5819,
    "score_components": {
      "ski_quality": 0.482,
      "price": 0.542,
      "snow": 0.6,
      "nightlife": 0.8,
      "convenience": 0.556,
      "accommodation": 0.633,
      "family": 0.8
    },
    "explanation": "Why: good nightlife, family-friendly, accommodation matching your comfort level. Terrain: 40% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMDhqBRIDVExWcgUSA1NPRhoaEgoyMDI3LTAxLTE0agUSA1NPRnIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Zigen%20House%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaQwolEiEyADodWmlnZW4gSG91c2UsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjrDxABGAgSBwjrDxABGA4YBjICCAEqCQoFOgNFVVIaAA",
    "accommodation_property_name": "Zigen House",
    "flight_options": [
      {
        "price_eur": 201.0,
        "airline": "Aegean",
        "duration_minutes": 470,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest"
        ],
        "flight_numbers": [
          "A3 925",
          "A3 982"
        ],
        "trip_total_eur": 970.48,
        "return_duration_minutes": null,
        "booking_url": null
      },
      {
        "price_eur": 274.0,
        "airline": "Austrian",
        "duration_minutes": 355,
        "stops": 1,
        "is_cheapest": false,
        "roles": [
          "best",
          "fastest"
        ],
        "flight_numbers": [
          "OS 84",
          "OS 771"
        ],
        "trip_total_eur": 1047.13,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Zigen House",
        "price_eur_per_night": 44.0,
        "per_person_eur": 132.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 970.48,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Zigen%20House%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaQwolEiEyADodWmlnZW4gSG91c2UsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjrDxABGAgSBwjrDxABGA4YBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Family House Oreha - Suite (3 Adults)",
        "price_eur_per_night": 47.0,
        "per_person_eur": 141.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 979.93,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Family%20House%20Oreha%20-%20Suite%20%283%20Adults%29%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaXQo_EjsyADo3RmFtaWx5IEhvdXNlIE9yZWhhIC0gU3VpdGUgKDMgQWR1bHRzKSwgQmFuc2tvLCBCdWxnYXJpYRoAEhoSFAoHCOsPEAEYCBIHCOsPEAEYDhgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "Cozy nature stay , Great view, free Parking",
        "price_eur_per_night": 62.0,
        "per_person_eur": 186.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1027.18,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Cozy%20nature%20stay%20%2C%20Great%20view%2C%20free%20Parking%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaYwpFEkEyADo9Q296eSBuYXR1cmUgc3RheSAsIEdyZWF0IHZpZXcsIGZyZWUgUGFya2luZywgQmFuc2tvLCBCdWxnYXJpYRoAEhoSFAoHCOsPEAEYCBIHCOsPEAEYDhgGMgIIASoJCgU6A0VVUhoA"
      },
      {
        "property_name": "BanskoVilla Zlateva House, Bansko",
        "price_eur_per_night": 63.0,
        "per_person_eur": 189.0,
        "is_cheapest": false,
        "rating": 4.6,
        "distance_to_lifts_km": 0.67,
        "trip_total_eur": 1030.33,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20BanskoVilla%20Zlateva%20House%2C%20Bansko%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWQo7EjcyADozQmFuc2tvVmlsbGEgWmxhdGV2YSBIb3VzZSwgQmFuc2tvLCBCYW5za28sIEJ1bGdhcmlhGgASGhIUCgcI6w8QARgIEgcI6w8QARgOGAYyAggBKgkKBToDRVVSGgA"
      }
    ],
    "total_eur_with_fastest_flight": 1047.13,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-44&to=resort-632&date=2027-01-08&time=20%3A55&adults=2&currency=EUR&return_date=2027-01-14&return_time=20%3A55&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 222.0,
      "duration_minutes": 180.0,
      "distance_km": 159.5,
      "vehicles_offered": 2,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/bansko",
    "ski_pass_search_url": "https://www.banskoski.com/en",
    "weather": {
      "days": [
        {
          "date": "2027-01-08",
          "is_live_forecast": false,
          "temp_max_c": 8.0,
          "temp_min_c": -0.6,
          "snowfall_cm": 2.2,
          "snow_depth_cm": 10.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-09",
          "is_live_forecast": false,
          "temp_max_c": 6.1,
          "temp_min_c": -3.0,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 9.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-10",
          "is_live_forecast": false,
          "temp_max_c": 5.7,
          "temp_min_c": -0.6,
          "snowfall_cm": 1.9,
          "snow_depth_cm": 9.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-11",
          "is_live_forecast": false,
          "temp_max_c": 3.7,
          "temp_min_c": -2.6,
          "snowfall_cm": 0.5,
          "snow_depth_cm": 9.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-12",
          "is_live_forecast": false,
          "temp_max_c": 1.8,
          "temp_min_c": -7.1,
          "snowfall_cm": 2.9,
          "snow_depth_cm": 9.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": 2.1,
          "temp_min_c": -7.8,
          "snowfall_cm": 0.3,
          "snow_depth_cm": 8.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 5.7,
          "temp_min_c": -5.4,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 8.2,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": 4.7,
      "avg_temp_min_c": -3.9,
      "avg_snowfall_cm": 1.1,
      "avg_snow_depth_cm": 9.4
    }
  },
  {
    "resort": {
      "name": "Bansko",
      "country": "Bulgaria",
      "region": "Pirin Mountains",
      "piste_km": 75.0,
      "off_piste_rating": 2,
      "snow_reliability": 3,
      "nightlife_rating": 4,
      "family_friendliness": 4,
      "nearest_airport": "Sofia (SOF)",
      "transfer_time_minutes": 125.0,
      "terrain": {
        "beginner": 0.4,
        "intermediate": 0.4,
        "advanced": 0.2,
        "quality": "sourced"
      },
      "needs_verification": false
    },
    "start_date": "2027-01-10",
    "end_date": "2027-01-16",
    "season": "high",
    "cost": {
      "flight_eur": 238.0,
      "transfer_eur": 4.0,
      "accommodation_eur": 132.0,
      "ski_pass_eur": 256.33,
      "equipment_eur": 110.0,
      "food_eur": 180.0,
      "misc_eur": 46.02,
      "total_eur": 966.3499999999999,
      "flight_price_is_live": true,
      "accommodation_price_is_live": true,
      "transfer_price_is_live": true,
      "ski_pass_price_is_researched": true
    },
    "transfer_options": [
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 4.0,
        "duration_minutes": 285,
        "carrier": "Bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Sofia-Airport-SOF/Bansko",
        "is_round_trip": false,
        "roles": [
          "cheapest",
          "fastest"
        ],
        "is_indicative": true,
        "price_high_eur_per_person": 12.0
      },
      {
        "kind": "scheduled",
        "mode": "bus",
        "price_eur_per_person": 6.0,
        "duration_minutes": 287,
        "carrier": "Bus via Хотел Плиска",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Sofia-Airport-SOF/Bansko",
        "is_round_trip": false,
        "roles": [],
        "is_indicative": true,
        "price_high_eur_per_person": 10.0
      },
      {
        "kind": "scheduled",
        "mode": "train",
        "price_eur_per_person": 7.0,
        "duration_minutes": 317,
        "carrier": "Train, bus",
        "departure": null,
        "booking_url": "https://www.rome2rio.com/map/Sofia-Airport-SOF/Bansko",
        "is_round_trip": false,
        "roles": [],
        "is_indicative": true,
        "price_high_eur_per_person": 14.0
      }
    ],
    "score": 0.5785,
    "score_components": {
      "ski_quality": 0.482,
      "price": 0.525,
      "snow": 0.6,
      "nightlife": 0.8,
      "convenience": 0.556,
      "accommodation": 0.633,
      "family": 0.8
    },
    "explanation": "Why: good nightlife, family-friendly, accommodation matching your comfort level. Terrain: 40% graded for intermediates. Flight price is live, checked just now. Accommodation price is live, checked just now.",
    "within_budget": true,
    "alternative_dates": [],
    "flight_search_url": "https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDEtMTBqBRIDVExWcgUSA1NPRhoaEgoyMDI3LTAxLTE2agUSA1NPRnIFEgNUTFZCAQFIAZgBAQ==&hl=en&curr=EUR",
    "accommodation_search_url": "https://www.google.com/travel/search?q=Hotels%20in%20Zigen%20House%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaQwolEiEyADodWmlnZW4gSG91c2UsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjrDxABGAoSBwjrDxABGBAYBjICCAEqCQoFOgNFVVIaAA",
    "accommodation_property_name": "Zigen House",
    "flight_options": [
      {
        "price_eur": 238.0,
        "airline": "Aegean",
        "duration_minutes": 470,
        "stops": 1,
        "is_cheapest": true,
        "roles": [
          "cheapest",
          "best",
          "fastest"
        ],
        "flight_numbers": [
          "A3 925",
          "A3 982"
        ],
        "trip_total_eur": 966.35,
        "return_duration_minutes": null,
        "booking_url": null
      }
    ],
    "accommodation_options": [
      {
        "property_name": "Zigen House",
        "price_eur_per_night": 44.0,
        "per_person_eur": 132.0,
        "is_cheapest": true,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 966.35,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Zigen%20House%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaQwolEiEyADodWmlnZW4gSG91c2UsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjrDxABGAoSBwjrDxABGBAYBjICCAEqCQoFOgNFVVIaAA"
      },
      {
        "property_name": "Trinity Bansko Spa Hotel",
        "price_eur_per_night": 45.0,
        "per_person_eur": 135.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 969.5,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Trinity%20Bansko%20Spa%20Hotel%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaUAoyEi4yADoqVHJpbml0eSBCYW5za28gU3BhIEhvdGVsLCBCYW5za28sIEJ1bGdhcmlhGgASGhIUCgcI6w8QARgKEgcI6w8QARgQGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "BanskoVilla Zlateva House, Bansko",
        "price_eur_per_night": 63.0,
        "per_person_eur": 189.0,
        "is_cheapest": false,
        "rating": 4.6,
        "distance_to_lifts_km": 0.67,
        "trip_total_eur": 1026.2,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20BanskoVilla%20Zlateva%20House%2C%20Bansko%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaWQo7EjcyADozQmFuc2tvVmlsbGEgWmxhdGV2YSBIb3VzZSwgQmFuc2tvLCBCYW5za28sIEJ1bGdhcmlhGgASGhIUCgcI6w8QARgKEgcI6w8QARgQGAYyAggBKgkKBToDRVVSGgA"
      },
      {
        "property_name": "Molerite Wine & Dine",
        "price_eur_per_night": 68.0,
        "per_person_eur": 204.0,
        "is_cheapest": false,
        "rating": null,
        "distance_to_lifts_km": null,
        "trip_total_eur": 1041.95,
        "url": "https://www.google.com/travel/search?q=Hotels%20in%20Molerite%20Wine%20%26%20Dine%2C%20Bansko%2C%20Bulgaria&hl=en&curr=EUR&gl=us&ts=CAESCgoCCAMKAggDEAAaTAouEioyADomTW9sZXJpdGUgV2luZSAmIERpbmUsIEJhbnNrbywgQnVsZ2FyaWEaABIaEhQKBwjrDxABGAoSBwjrDxABGBAYBjICCAEqCQoFOgNFVVIaAA"
      }
    ],
    "total_eur_with_fastest_flight": 966.35,
    "transfer_search_url": "https://booking.alps2alps.com/booking/quick-checkout?from=airport-44&to=resort-632&date=2027-01-10&time=20%3A55&adults=2&currency=EUR&return_date=2027-01-16&return_time=20%3A55&ski_bags=2&ski=1",
    "transfer_info": {
      "source": "alps2alps",
      "price_eur": 222.0,
      "duration_minutes": 180.0,
      "distance_km": 159.5,
      "vehicles_offered": 2,
      "unavailable_reason": null,
      "vehicle_name": null,
      "pickup_time": null,
      "return_pickup_time": null,
      "is_private": null,
      "public_price_eur_per_person": null,
      "public_mode": null,
      "public_options_count": null,
      "public_booking_url": null,
      "public_carrier": null
    },
    "equipment_search_url": "https://www.skiset.co.uk/ski-resort/bansko",
    "ski_pass_search_url": "https://www.banskoski.com/en",
    "weather": {
      "days": [
        {
          "date": "2027-01-10",
          "is_live_forecast": false,
          "temp_max_c": 5.7,
          "temp_min_c": -0.6,
          "snowfall_cm": 1.9,
          "snow_depth_cm": 9.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-11",
          "is_live_forecast": false,
          "temp_max_c": 3.7,
          "temp_min_c": -2.6,
          "snowfall_cm": 0.5,
          "snow_depth_cm": 9.8,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-12",
          "is_live_forecast": false,
          "temp_max_c": 1.8,
          "temp_min_c": -7.1,
          "snowfall_cm": 2.9,
          "snow_depth_cm": 9.4,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-13",
          "is_live_forecast": false,
          "temp_max_c": 2.1,
          "temp_min_c": -7.8,
          "snowfall_cm": 0.3,
          "snow_depth_cm": 8.6,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-14",
          "is_live_forecast": false,
          "temp_max_c": 5.7,
          "temp_min_c": -5.4,
          "snowfall_cm": 0.1,
          "snow_depth_cm": 8.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-15",
          "is_live_forecast": false,
          "temp_max_c": 5.7,
          "temp_min_c": -4.9,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 7.2,
          "description": null,
          "years_sampled": 5
        },
        {
          "date": "2027-01-16",
          "is_live_forecast": false,
          "temp_max_c": 5.9,
          "temp_min_c": -3.5,
          "snowfall_cm": 0.2,
          "snow_depth_cm": 16.8,
          "description": null,
          "years_sampled": 5
        }
      ],
      "avg_temp_max_c": 4.4,
      "avg_temp_min_c": -4.6,
      "avg_snowfall_cm": 0.9,
      "avg_snow_depth_cm": 9.9
    }
  }
] as unknown as TripResult[];
