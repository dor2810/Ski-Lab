/**
 * Canonical English dictionary -- the source of truth for every
 * translation key that exists in the app. Every other language file
 * (he.ts, and any future one) is typed as Record<keyof typeof en,
 * string>, so TypeScript itself fails the build if a new key gets
 * added here without a matching translation everywhere else. This is
 * the mechanism that makes the system "generic" rather than just
 * "has two languages": adding language #3 is copy this file, translate
 * every value, register it in languages.ts -- nothing else changes.
 *
 * {placeholder} tokens are substituted by lib/i18n/context.tsx's t()
 * via simple string replacement -- see its own comment for why that's
 * enough here and a full ICU/plural-rules library isn't.
 */
const en = {
  // --- Hero ---
  heroHeadline1: "Find the perfect line.",
  heroHeadline2: "We do the math.",
  heroSubhead:
    "Complete ski trips, priced end to end. Flights, transfers, lodging, lift pass — one real number. Pick exact dates or a whole month and we'll find the best week for you.",
  heroTrustLive: "Live flight & hotel prices",
  heroTrustTotal: "Real total, not a headline fare",
  heroTrustFree: "Free, no booking required",
  heroCta: "Plan my trip",

  // --- Problem section ---
  problem1Title: "Five websites, one guess",
  problem1Body: "Flights here, hotels there, transfers somewhere else — you piece it together and hope.",
  problem2Title: "Hidden costs at every step",
  problem2Body: "The flight looked cheap. Then the transfer, the pass, the resort fees added up.",
  problem3Title: "No idea if you're overpaying",
  problem3Body: "Was that a good week to go? Nothing tells you — until you've already booked.",

  // --- How it works ---
  howItWorksTitle: "How it works",
  step1Label: "FIND",
  step1Body: "Tell us your budget, dates and how you ski",
  step2Label: "OPTIMIZE",
  step2Body: "We price thousands of trip combinations",
  step3Label: "ANALYZE",
  step3Body: "We rank them and show the real total",
  step4Label: "ENJOY",
  step4Body: "Book with confidence",

  // --- Search form ---
  departureCity: "Departure city",
  earliestDate: "Earliest date",
  latestReturn: "Latest return",
  skiDaysLabel: "Ski days",
  skiDaysHint: "= {nights} nights away (arrive the evening before, fly home the day after)",
  startDayOfWeek: "Start day of week",
  anyDay: "Any day",
  weekdayMonday: "Monday",
  weekdayTuesday: "Tuesday",
  weekdayWednesday: "Wednesday",
  weekdayThursday: "Thursday",
  weekdayFriday: "Friday",
  weekdaySaturday: "Saturday",
  weekdaySunday: "Sunday",
  rangeHint:
    "Give a wider date range than your trip needs and we'll search every valid start date in it (e.g. only Saturdays, if set above) for the best deal.",
  travellers: "Travellers",
  skillLevel: "Skill level",
  skillBeginner: "Beginner",
  skillIntermediate: "Intermediate",
  skillAdvanced: "Advanced",
  skillExpert: "Expert",
  budgetPerPerson: "Budget per person (EUR)",
  priorities: "Priorities",
  priorityShiQuality: "Ski quality",
  priorityPrice: "Price",
  prioritySnow: "Snow reliability",
  priorityNightlife: "Nightlife",
  priorityConvenience: "Convenience",
  priorityAccommodation: "Accommodation comfort",
  priorityFamily: "Good for kids",
  optionalPreferences: "Optional preferences",
  hideOptionalPreferences: "Hide optional preferences",
  accommodationTier: "Accommodation tier",
  tierBudget: "Budget",
  tierStandard: "Standard",
  tierLuxury: "Luxury",
  foodStyle: "Food style",
  foodBudget: "Budget",
  foodNormal: "Normal",
  foodLuxury: "Luxury",
  transferTypesAccept: "Transfer types you'll accept",
  transferSharedShuttle: "Shared shuttle",
  transferPrivateTransfer: "Private transfer",
  transferTrain: "Train",
  transferBus: "Bus",
  transferNonePreference: "None selected = no preference.",
  maxFlightConnections: "Maximum flight connections",
  connectionsNoPreference: "No preference",
  connectionsNonstop: "Nonstop only",
  connectionsUpTo1: "Up to 1 stop",
  connectionsUpTo2: "Up to 2 stops",
  errorTripLength: "Ski days must be at least 1.",
  errorRangeTooShort: "The date range must be at least as long as the trip.",
  sessionExpired: "Your session expired. Please sign in again.",
  errorGeneric: "Something went wrong. Please try again.",
  searching: "Searching…",
  findMyTrip: "Find my trip",

  // --- Trip style presets ---
  styleQuestion: "What kind of trip do you want?",
  styleHint: "Pick one and we'll set everything sensibly. You can fine-tune after.",
  styleBalanced: "A bit of everything",
  styleBalancedBlurb: "Good all-round trip",
  styleValue: "Cheapest",
  styleValueBlurb: "Lowest total, stopovers OK",
  styleSnow: "Best snow",
  styleSnowBlurb: "Most reliable conditions",
  styleEasy: "Easy & relaxed",
  styleEasyBlurb: "Short transfers, few stopovers",
  styleFamily: "With kids",
  styleFamilyBlurb: "Kid-friendly, easy journey",
  styleLively: "Lively",
  styleLivelyBlurb: "Good bars and après-ski",
  styleComfort: "Luxury",
  styleComfortBlurb: "Best hotels, nonstop flights only",
  fineTune: "Fine-tune priorities",
  hideFineTune: "Hide priorities",
  fineTuneHint: "Only if you want to. The style above already set these.",
  styleCustom: "Custom",

  creditsLabel: "Search credits",
  creditsRemaining: "{remaining} of {allowance} left today",
  creditsThisSearch: "This search costs {cost} credit(s) — a wider date range costs more.",
  creditsNotEnough: "This search costs {cost} credit(s) — more than you have left today. Try a narrower date range.",

  // --- Resort picker ---
  resortsLabel: "Resorts",
  resortsOnlyThese: "Only these",
  resortsExceptThese: "Except these",
  resortsNoneSelectedHint: 'None selected = search all resorts. Pick some to search only those, or flip to "Except these" to exclude them.',
  resortsFilterPlaceholder: "Filter resorts…",
  resortsSignInFirst: "Sign in to pick specific resorts — or just search all of them.",
  resortsLoading: "Loading resorts…",
  resortsNoMatch: 'No resorts match "{filter}".',

  // --- Result card ---
  overBudgetBanner: "Over your budget — the cheapest trip we could find. Nothing fit your stated budget.",
  perPersonTotal: "per person, total",
  matchScoreTitle: "Match score",
  lineFlight: "Flight",
  lineTransfer: "Transfer",
  lineAccommodation: "Accommodation",
  lineLiftPass: "Lift pass",
  lineEquipment: "Equipment",
  lineFood: "Food",
  liveBadge: "LIVE",
  estBadge: "EST.",
  researchedBadge: "REAL",
  researchedTooltip: "A real published price from the resort's own ticketing page — not a per-request quote, but sourced rather than estimated",
  liveTooltip: "Priced from a live source, checked just now",
  estTooltip: "Estimated from published rates — verify before booking",
  kmPiste: "{km} km piste",
  minFromAirport: "{min} min from {airport}",
  offPisteRating: "Off-piste {n}/5",
  snowRating: "Snow {n}/5",
  nightlifeRating: "Nightlife {n}/5",
  viewTripDetails: "View trip details",
  hideTripDetails: "Hide trip details",
  viewFlights: "View flights",
  viewAccommodation: "View accommodation",
  viewTransfer: "View transfer",
  viewEquipment: "Rent equipment",
  viewSkiPass: "Buy lift pass",
  accommodationPropertyNamePrefix: "Priced for:",
  searchLinkDisclaimer: "Opens Google's own live results — the top match links straight to this priced flight/stay when available.",
  needsVerificationNote: "Some data for this resort is flagged as needing verification.",
  terrainNotAvailable: "Terrain breakdown not available for this resort.",
  terrainBreakdown: "{beginner}% beginner · {intermediate}% intermediate · {advanced}% advanced",
  estimatedSuffix: " (estimated)",

  // --- What's included / not included ---
  whatsIncludedTitle: "What this price includes",
  includedHeading: "Included",
  notIncludedHeading: "Not included",
  inclFlight: "Return flight from Tel Aviv",
  inclTransfer: "Airport ↔ resort transfer, both ways",
  inclAccommodation: "Accommodation for the whole stay",
  inclLiftPass: "Lift pass for your ski days",
  inclEquipment: "Ski or snowboard rental",
  inclFood: "Everyday food and drink",
  exclLessons: "Ski school / lessons (roughly €100–414 per week)",
  exclSkiBaggage: "Flying your own skis (free on most full-fare airlines, ~€45 per flight on low-cost)",
  exclInsurance: "Travel and ski insurance",
  exclResortTax: "Resort / tourist tax, paid at the property",
  exclOnMountainLunch: "Mountain restaurant lunches (our food figure assumes mostly off-mountain)",

  // --- Weather (result card) ---
  weatherTitle: "Weather this week",
  weatherAvgHigh: "Avg high",
  weatherAvgLow: "Avg low",
  weatherAvgSnow: "Avg snowfall",
  weatherSnowBase: "Snow base",
  weatherSnowBaseTooltip: "Actual ground snow depth, not new snowfall",
  weatherShowDaily: "Show day by day",
  weatherHideDaily: "Hide day by day",
  weatherLiveForecast: "Live forecast",
  weatherHistoricalAvg: "{years}-yr average",
  weatherNoData: "No weather data available for this resort.",

  // --- Price calendar ---
  priceByStartDate: "Price by start date",
  savesLine: "Travelling the week of {date1} saves {amount} per person versus {date2}.",

  // --- Why Ski Lab ---
  whySkiLabTitle: "Why Ski Lab",
  why1: "Real deals from real sources",
  why2: "Live prices and availability",
  why3: "Snow and weather intelligence",
  why4: "Complete trips, total costs",
  why5: "Book with confidence",

  // --- Footer ---
  footerTagline: "DATA. SNOW. ADVENTURE.",
  footerCopyright: "© {year} Ski Lab. Prices are estimates or live quotes as labeled — always verify before booking.",

  // --- Page-level results section ---
  findingRealTrips: "Finding real trips…",
  previewErrorApi: "The search engine is warming up or unavailable ({message}). Try a search below.",
  previewErrorGeneric: "Couldn't reach the search engine yet. The free-tier backend may still be starting up — try a search below in a moment.",
  bestTripsForSearch: "Best trips for your search",
  exampleTripsRightNow: "Example trips right now",
  livePricingActive: "Live pricing active",
  estimatedPricing: "Estimated pricing",
  noTripsFound: "No trips found for those settings — try a wider budget or date range.",

  // --- Seasons (mirrors backend season_band values) ---
  seasonPeak: "Peak",
  seasonHigh: "High",
  seasonShoulder: "Shoulder",

  // --- Language switcher ---
  languageLabel: "Language",

  // --- Auth ---
  signIn: "Sign in",
  signOut: "Sign out",
  createAccount: "Create account",
  continueWithGoogle: "Continue with Google",
  orDivider: "or",
  emailLabel: "Email",
  passwordLabel: "Password",
  authSwitchToRegister: "Need an account? Create one",
  authSwitchToLogin: "Already have an account? Sign in",
  authWorking: "Working…",
  authPasswordTooShort: "Password must be at least 12 characters.",
  authErrorGeneric: "Something went wrong. Please try again.",
  googleSignInFailed: "Google sign-in didn't complete -- you may have canceled it, or the session expired. Try again.",
  signInToSearch: "Sign in to search for trips.",
  signInToSeeExamples: "Sign in to see example trips.",
  backToHome: "← Back to Ski Lab",
} as const;

export default en;
