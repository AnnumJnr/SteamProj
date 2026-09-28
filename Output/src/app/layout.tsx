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
 
/**
 * Runs before first paint, so the correct palette is on <html> by the time
 * anything renders. A React effect cannot do this — effects run after paint,
 * which is exactly what produces the white flash on a dark-mode reload.
 * The storage key must stay in sync with THEME_STORAGE_KEY in hooks/useTheme.ts.
 */
const themeScript = `
(function () {
  try {
    var stored = localStorage.getItem("stempath-theme");
    var resolved =
      stored === "light" || stored === "dark"
        ? stored
        : window.matchMedia("(prefers-color-scheme: light)").matches
          ? "light"
          : "dark";
    document.documentElement.dataset.theme = resolved;
    document.documentElement.style.colorScheme = resolved;
  } catch (e) {
    // Storage blocked — fall back to the dark palette already in the stylesheet.
  }
})();
`;

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
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
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