import type en from "./en";

/**
 * Hebrew translations. Typed against en's exact key set (Record<keyof
 * typeof en, string>) -- TypeScript fails the build if a key is
 * missing here, added here but not in en.ts, or misspelled. That
 * compile-time guarantee is the point: it's what keeps "generic" from
 * silently rotting into "half-translated" as the app grows.
 */
const he: Record<keyof typeof en, string> = {
  // --- Hero ---
  heroHeadline1: "מצאו את המסלול המושלם.",
  heroHeadline2: "אנחנו עושים את החשבון.",
  heroSubhead:
    "טיולי סקי מלאים, מתומחרים מקצה לקצה. טיסות, הסעות, לינה, כרטיס סקי — מספר אמיתי אחד. בחרו תאריכים מדויקים או חודש שלם ואנחנו נמצא לכם את השבוע הכי טוב.",
  heroCta: "תכננו את הטיול שלי",

  // --- Problem section ---
  problem1Title: "חמישה אתרים, ניחוש אחד",
  problem1Body: "טיסות כאן, מלונות שם, הסעות במקום אחר — אתם מרכיבים הכול לבד ומקווים לטוב.",
  problem2Title: "עלויות נסתרות בכל שלב",
  problem2Body: "הטיסה נראתה זולה. אחר כך ההסעה, הכרטיס ודמי האתר התווספו.",
  problem3Title: "אין לכם מושג אם אתם משלמים יותר מדי",
  problem3Body: "האם זה היה שבוע טוב לנסוע? שום דבר לא אומר לכם — עד שכבר הזמנתם.",

  // --- How it works ---
  howItWorksTitle: "איך זה עובד",
  step1Label: "חיפוש",
  step1Body: "ספרו לנו על התקציב, התאריכים ורמת הסקי שלכם",
  step2Label: "אופטימיזציה",
  step2Body: "אנחנו מתמחרים אלפי שילובי טיולים",
  step3Label: "ניתוח",
  step3Body: "אנחנו מדרגים אותם ומציגים את הסכום האמיתי",
  step4Label: "תיהנו",
  step4Body: "הזמינו בביטחון",

  // --- Search form ---
  departureCity: "עיר יציאה",
  earliestDate: "תאריך מוקדם ביותר",
  latestReturn: "חזרה מאוחרת ביותר",
  skiDaysLabel: "ימי סקי",
  skiDaysHint: "= {nights} לילות בחוץ (הגעה בערב שלפני, טיסה חזרה יום אחרי)",
  startDayOfWeek: "יום התחלה בשבוע",
  anyDay: "כל יום",
  weekdayMonday: "יום שני",
  weekdayTuesday: "יום שלישי",
  weekdayWednesday: "יום רביעי",
  weekdayThursday: "יום חמישי",
  weekdayFriday: "יום שישי",
  weekdaySaturday: "שבת",
  weekdaySunday: "יום ראשון",
  rangeHint:
    "תנו טווח תאריכים רחב יותר מאורך הטיול ואנחנו נחפש בכל תאריך התחלה אפשרי בטווח (למשל, רק ימי שבת, אם נבחר למעלה) כדי למצוא את העסקה הטובה ביותר.",
  travellers: "נוסעים",
  skillLevel: "רמת סקי",
  skillBeginner: "מתחיל",
  skillIntermediate: "בינוני",
  skillAdvanced: "מתקדם",
  skillExpert: "מומחה",
  budgetPerPerson: "תקציב לאדם (יורו)",
  priorities: "עדיפויות",
  priorityShiQuality: "איכות סקי",
  priorityPrice: "מחיר",
  prioritySnow: "אמינות שלג",
  priorityNightlife: "חיי לילה",
  priorityConvenience: "נוחות",
  priorityAccommodation: "נוחות הלינה",
  optionalPreferences: "העדפות נוספות",
  hideOptionalPreferences: "הסתירו העדפות נוספות",
  accommodationTier: "רמת לינה",
  tierBudget: "חסכוני",
  tierStandard: "רגיל",
  tierLuxury: "יוקרתי",
  foodStyle: "סגנון אוכל",
  foodBudget: "חסכוני",
  foodNormal: "רגיל",
  foodLuxury: "יוקרתי",
  transferTypesAccept: "סוגי הסעות שתקבלו",
  transferSharedShuttle: "שאטל משותף",
  transferPrivateTransfer: "הסעה פרטית",
  transferTrain: "רכבת",
  transferBus: "אוטובוס",
  transferNonePreference: "לא נבחר כלום = אין העדפה.",
  maxFlightConnections: "מקסימום עצירות בטיסה",
  connectionsNoPreference: "אין העדפה",
  connectionsNonstop: "ישירה בלבד",
  connectionsUpTo1: "עד עצירה אחת",
  connectionsUpTo2: "עד שתי עצירות",
  errorTripLength: "מספר ימי הסקי חייב להיות לפחות 1.",
  errorRangeTooShort: "טווח התאריכים חייב להיות לפחות באורך הטיול.",
  errorGeneric: "משהו השתבש. נסו שוב.",
  searching: "מחפשים…",
  findMyTrip: "מצאו לי טיול",

  // --- Resort picker ---
  resortsLabel: "אתרי סקי",
  resortsOnlyThese: "רק אלה",
  resortsExceptThese: "חוץ מאלה",
  resortsNoneSelectedHint: 'לא נבחר כלום = חיפוש בכל האתרים. בחרו כמה כדי לחפש רק בהם, או עברו ל"חוץ מאלה" כדי להוציא אותם.',
  resortsFilterPlaceholder: "סננו אתרים…",
  resortsLoading: "טוען אתרים…",
  resortsNoMatch: 'אין אתרים שתואמים ל"{filter}".',

  // --- Result card ---
  overBudgetBanner: "מעל התקציב שלכם — הטיול הזול ביותר שמצאנו. שום דבר לא התאים לתקציב שציינתם.",
  perPersonTotal: "לאדם, סה״כ",
  matchScoreTitle: "ציון התאמה",
  lineFlight: "טיסה",
  lineTransfer: "הסעה",
  lineAccommodation: "לינה",
  lineLiftPass: "כרטיס סקי",
  lineEquipment: "ציוד",
  lineFood: "אוכל",
  liveBadge: "לייב",
  estBadge: "מוערך",
  liveTooltip: "מתומחר ממקור חי, נבדק הרגע",
  estTooltip: "מוערך לפי תעריפים מפורסמים — יש לוודא לפני הזמנה",
  kmPiste: "{km} ק״מ מסלולים",
  minFromAirport: "{min} דק׳ מ-{airport}",
  offPisteRating: "אוף-פיסט {n}/5",
  snowRating: "שלג {n}/5",
  nightlifeRating: "חיי לילה {n}/5",
  viewTripDetails: "צפו בפרטי הטיול",
  hideTripDetails: "הסתירו פרטי טיול",
  viewFlights: "צפייה בטיסות",
  viewAccommodation: "צפייה במלונות",
  viewTransfer: "צפייה בהסעה",
  accommodationPropertyNamePrefix: "המחיר עבור:",
  searchLinkDisclaimer: "פותח את תוצאות החיפוש החיות של Google — התוצאה המובילה מקשרת ישירות לטיסה/לינה המתומחרת הזו כשניתן.",
  needsVerificationNote: "חלק מהנתונים עבור אתר זה מסומנים כטעונים אימות.",
  terrainNotAvailable: "פילוח שטח אינו זמין עבור אתר זה.",
  terrainBreakdown: "{beginner}% מתחילים · {intermediate}% בינוני · {advanced}% מתקדמים",
  estimatedSuffix: " (מוערך)",

  // --- Weather (result card) ---
  weatherTitle: "מזג האוויר השבוע",
  weatherAvgHigh: "מקסימום ממוצע",
  weatherAvgLow: "מינימום ממוצע",
  weatherAvgSnow: "שלג ממוצע",
  weatherSnowBase: "בסיס שלג",
  weatherSnowBaseTooltip: "עומק שלג בפועל על הקרקע, לא שלג חדש",
  weatherShowDaily: "הצג יום אחר יום",
  weatherHideDaily: "הסתר יום אחר יום",
  weatherLiveForecast: "תחזית חיה",
  weatherHistoricalAvg: "ממוצע {years} שנים",
  weatherNoData: "אין נתוני מזג אוויר זמינים עבור אתר זה.",

  // --- Price calendar ---
  priceByStartDate: "מחיר לפי תאריך התחלה",
  savesLine: "נסיעה בשבוע של {date1} חוסכת {amount} לאדם לעומת {date2}.",

  // --- Why Ski Lab ---
  whySkiLabTitle: "למה Ski Lab",
  why1: "עסקאות אמיתיות ממקורות אמיתיים",
  why2: "מחירים וזמינות בזמן אמת",
  why3: "מודיעין שלג ומזג אוויר",
  why4: "טיולים מלאים, עלויות כוללות",
  why5: "הזמינו בביטחון",

  // --- Footer ---
  footerTagline: "נתונים. שלג. הרפתקה.",
  footerCopyright: "© {year} Ski Lab. המחירים הם הערכות או מחירים בזמן אמת כפי שמסומן — יש לוודא תמיד לפני הזמנה.",

  // --- Page-level results section ---
  findingRealTrips: "מוצאים טיולים אמיתיים…",
  previewErrorApi: "מנוע החיפוש מתחמם או אינו זמין ({message}). נסו לחפש למטה.",
  previewErrorGeneric: "לא הצלחנו להתחבר למנוע החיפוש עדיין. השרת בגרסה החינמית עשוי עדיין לעלות — נסו לחפש למטה בעוד רגע.",
  bestTripsForSearch: "הטיולים הטובים ביותר לחיפוש שלכם",
  exampleTripsRightNow: "טיולים לדוגמה כרגע",
  livePricingActive: "תמחור בזמן אמת פעיל",
  estimatedPricing: "תמחור משוער",
  noTripsFound: "לא נמצאו טיולים עבור ההגדרות האלה — נסו תקציב או טווח תאריכים רחב יותר.",

  // --- Seasons (mirrors backend season_band values) ---
  seasonPeak: "שיא",
  seasonHigh: "גבוה",
  seasonShoulder: "ביניים",

  // --- Language switcher ---
  languageLabel: "שפה",

  // --- Auth ---
  signIn: "התחברות",
  signOut: "התנתקות",
  createAccount: "יצירת חשבון",
  continueWithGoogle: "המשך עם Google",
  orDivider: "או",
  emailLabel: "אימייל",
  passwordLabel: "סיסמה",
  authSwitchToRegister: "אין לכם חשבון? צרו אחד",
  authSwitchToLogin: "כבר יש לכם חשבון? התחברו",
  authWorking: "טוען…",
  authPasswordTooShort: "הסיסמה חייבת להכיל לפחות 12 תווים.",
  authErrorGeneric: "משהו השתבש. נסו שוב.",
  googleSignInFailed: "ההתחברות עם Google לא הושלמה -- ייתכן שביטלתם אותה, או שהחיבור פג. נסו שוב.",
  signInToSearch: "התחברו כדי לחפש טיולים.",
  signInToSeeExamples: "התחברו כדי לראות טיולים לדוגמה.",
  backToHome: "→ חזרה ל-Ski Lab",
};

export default he;
