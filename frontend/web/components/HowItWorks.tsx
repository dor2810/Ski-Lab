import { PinIcon, TrendIcon, ChartIcon, SnowMountainIcon } from "./icons";

const STEPS = [
  { label: "FIND", icon: PinIcon, body: "Tell us your budget, dates and how you ski" },
  { label: "OPTIMIZE", icon: TrendIcon, body: "We price thousands of trip combinations" },
  { label: "ANALYZE", icon: ChartIcon, body: "We rank them and show the real total" },
  { label: "ENJOY", icon: SnowMountainIcon, body: "Book with confidence" },
];

export function HowItWorks() {
  return (
    <section className="mx-auto max-w-5xl px-6 py-20">
      <h2 className="text-center font-semibold text-2xl sm:text-3xl mb-14">How it works</h2>
      <div className="grid gap-10 sm:grid-cols-4">
        {STEPS.map(({ label, icon: Icon, body }, i) => (
          <div key={label} className="relative text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-midnight border border-white/10">
              <Icon size={24} className="text-sky" />
            </div>
            <div className="text-xs font-bold tracking-widest text-sky mb-1">
              {String(i + 1).padStart(2, "0")} · {label}
            </div>
            <p className="text-ice/70 text-sm leading-relaxed">{body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
