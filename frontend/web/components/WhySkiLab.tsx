import { LiftPassIcon, TrendIcon, WeatherIcon, PriceIcon, ConfidenceIcon } from "./icons";

const POINTS = [
  { icon: LiftPassIcon, text: "Real deals from real sources" },
  { icon: TrendIcon, text: "Live prices and availability" },
  { icon: WeatherIcon, text: "Snow and weather intelligence" },
  { icon: PriceIcon, text: "Complete trips, total costs" },
  { icon: ConfidenceIcon, text: "Book with confidence" },
];

export function WhySkiLab() {
  return (
    <section className="mx-auto max-w-5xl px-6 py-20">
      <h2 className="text-center font-semibold text-2xl sm:text-3xl mb-12">Why Ski Lab</h2>
      <div className="grid gap-8 sm:grid-cols-5">
        {POINTS.map(({ icon: Icon, text }) => (
          <div key={text} className="text-center">
            <Icon size={26} className="mx-auto mb-3 text-sky" />
            <p className="text-sm text-ice/80">{text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
