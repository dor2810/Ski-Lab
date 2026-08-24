import { Logo } from "./Logo";

export function Footer() {
  return (
    <footer className="border-t border-white/10 py-10">
      <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 px-6 sm:flex-row">
        <div className="flex items-center gap-2.5">
          <Logo size={28} />
          <span className="text-sm font-bold tracking-wide">
            SKI <span className="text-sky">LAB</span>
          </span>
        </div>
        <p className="text-xs text-ice/40">
          © {new Date().getFullYear()} Ski Lab. Prices are estimates or live quotes as labeled —
          always verify before booking.
        </p>
      </div>
    </footer>
  );
}
