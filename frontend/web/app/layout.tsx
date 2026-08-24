import type { Metadata } from "next";
import { Montserrat } from "next/font/google";
import "./globals.css";

const montserrat = Montserrat({
  variable: "--font-montserrat",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "Ski Lab — Find the perfect line",
  description:
    "Ski Lab prices complete ski trips end to end -- flights, transfers, lodging, lift pass -- across 30 European resorts, and ranks them for real, not a guess.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${montserrat.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-navy text-white">
        {children}
      </body>
    </html>
  );
}
