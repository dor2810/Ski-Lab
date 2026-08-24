import Image from "next/image";

/**
 * The provided logo.jpg has a white background, so on the dark navy
 * theme it needs a white card behind it -- otherwise the flask's dark
 * outline nearly disappears into --color-navy. On light surfaces the
 * plain variant is used instead.
 */
export function Logo({ size = 40, className = "" }: { size?: number; className?: string }) {
  return (
    <div
      className={`inline-flex items-center justify-center rounded-xl bg-white shadow-sm ${className}`}
      style={{ width: size, height: size, padding: size * 0.08 }}
    >
      <Image
        src="/images/logo.jpg"
        alt="Ski Lab"
        width={size}
        height={size}
        className="h-full w-full object-contain"
        priority
      />
    </div>
  );
}

export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`font-extrabold tracking-wide ${className}`}>
      SKI <span className="text-sky">LAB</span>
    </span>
  );
}
