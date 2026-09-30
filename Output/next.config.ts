import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["192.168.43.5"],

  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          // Next.js' default COOP (same-origin) blocks the cross-origin
          // window.postMessage calls Google Identity Services relies on.
          { key: "Cross-Origin-Opener-Policy", value: "same-origin-allow-popups" },
        ],
      },
    ];
  },

  images: {
    // Disable server-side image optimization for external URLs.
    // YouTube thumbnails (i.ytimg.com) are fetched client-side in the browser,
    // not by the Next.js server process — avoids ENOTFOUND errors in dev.
    unoptimized: true,
    remotePatterns: [
      { protocol: "https", hostname: "img.youtube.com" },
      { protocol: "https", hostname: "i.ytimg.com" },
      { protocol: "https", hostname: "lh3.googleusercontent.com" },
      { protocol: "https", hostname: "ocw.mit.edu" },
      { protocol: "https", hostname: "openstax.org" },
    ],
  },
};

export default nextConfig;