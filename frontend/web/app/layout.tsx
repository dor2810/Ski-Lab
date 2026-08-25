import type { Metadata } from "next";
import { Montserrat, Rubik } from "next/font/google";
import { LanguageProvider } from "@/lib/i18n/context";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { AuthProvider } from "@/lib/auth/context";
import { AuthWidget } from "@/components/AuthWidget";
import "./globals.css";

const montserrat = Montserrat({
  variable: "--font-montserrat",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

// Montserrat has no Hebrew glyphs at all -- without a fallback, Hebrew
// text would silently drop to whatever generic sans-serif the browser
// picks, breaking the branded typography the moment someone switches
// language. Rubik is a geometric sans with full Hebrew + Latin coverage
// that pairs cleanly with Montserrat's style; globals.css switches to
// it specifically when `dir="rtl"` is set (see lib/i18n/context.tsx).
const rubik = Rubik({
  variable: "--font-rubik",
  subsets: ["hebrew", "latin"],
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "Ski Lab — Find the perfect line",
  description:
    "Ski Lab prices complete ski trips end to end -- flights, transfers, lodging, lift pass -- across 30 European resorts, and ranks them for real, not a guess.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${montserrat.variable} ${rubik.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-navy text-white">
        <LanguageProvider>
          <AuthProvider>
            <div className="fixed top-4 end-4 z-50 flex items-center gap-3">
              <AuthWidget />
              <LanguageSwitcher />
            </div>
            {children}
          </AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
