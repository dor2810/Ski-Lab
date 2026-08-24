import { PriceIcon, CalendarIcon, TrendIcon } from "./icons";

const PROBLEMS = [
  {
    icon: CalendarIcon,
    title: "Five websites, one guess",
    body: "Flights here, hotels there, transfers somewhere else — you piece it together and hope.",
  },
  {
    icon: PriceIcon,
    title: "Hidden costs at every step",
    body: "The flight looked cheap. Then the transfer, the pass, the resort fees added up.",
  },
  {
    icon: TrendIcon,
    title: "No idea if you're overpaying",
    body: "Was that a good week to go? Nothing tells you — until you've already booked.",
  },
];

export function ProblemSection() {
  return (
    <section className="mx-auto max-w-5xl px-6 py-20">
      <div className="grid gap-10 sm:grid-cols-3">
        {PROBLEMS.map(({ icon: Icon, title, body }) => (
          <div key={title} className="text-center sm:text-left">
            <Icon size={28} className="text-sky mb-4 mx-auto sm:mx-0" />
            <h3 className="font-semibold text-lg text-white mb-2">{title}</h3>
            <p className="text-ice/70 text-sm leading-relaxed">{body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
