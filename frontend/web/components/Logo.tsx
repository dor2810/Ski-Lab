import Image from "next/image";

/**
 * The provided logo.jpg has a WHITE background, which is why it used to
 * be wrapped in a white card on the old dark-navy theme (the flask's
 * outline otherwise vanished into the background). On the light theme
 * the white square now blends into the surface naturally, so the card
 * is gone -- just a rounded clip to keep the jpg's hard edges from
 * showing against tinted surfaces.
 */
export function Logo({ size = 40, className = "" }: { size?: number; className?: string }) {
  return (
    <span
      className={`inline-flex items-center justify-center overflow-hidden rounded-lg ${className}`}
      style={{ width: size, height: size }}
    >
      <Image
        src="/images/logo.jpg"
        alt="Ski Lab"
        width={size}
        height={size}
        className="h-full w-full object-contain"
        priority
      />
    </span>
  );
}

export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`font-extrabold tracking-wide text-ink ${className}`}>
      SKI <span className="text-signal">LAB</span>
    </span>
  );
}
