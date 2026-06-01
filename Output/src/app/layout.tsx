/**
 * app/layout.tsx
 * Root layout — wraps every page with Providers, Navbar, and Footer.
 * This is a Server Component. No hooks, no "use client".
 * All client-side logic is deferred to Providers and child components.
 */

import type { Metadata } from "next";
import { DM_Sans, DM_Serif_Display } from "next/font/google";
import { Providers } from "./providers";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import "@/styles/globals.css";
 
// DM Sans — primary body font
const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});
 
// DM Serif Display — hero headings only
const dmSerifDisplay = DM_Serif_Display({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
  display: "swap",
});
 
export const metadata: Metadata = {
  title: {
    default: "STEMPath — Guided STEM Learning Paths",
    template: "%s | STEMPath",
  },
  description:
    "Discover curated STEM courses and structured Combo learning paths from trusted sources. Learn at your pace, track your progress.",
  keywords: ["STEM", "learning", "courses", "coding", "mathematics", "science", "engineering"],
  openGraph: {
    title: "STEMPath — Guided STEM Learning Paths",
    description: "Curated STEM courses and structured learning paths for every level.",
    type: "website",
  },
};
 
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${dmSans.variable} ${dmSerifDisplay.variable}`}
    >
      <body>
        <Providers>
          <div className="flex flex-col min-h-dvh">
            <Navbar />
            <main className="flex-1">
              {children}
            </main>
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  );
}