import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["192.168.43.5"],

  // Pin the workspace root. Without this, Next.js/Turbopack infers the root
  // by walking up for lockfiles — a stray package-lock.json in the parent
  // folder makes it pick the WRONG directory and mis-resolve font modules.
  turbopack: {
    root: __dirname,
  },

  async headers() {
    return [
      {
        // Apply X-Frame-Options everywhere EXCEPT course detail pages.
        // Course detail pages embed YouTube iframes — X-Frame-Options: SAMEORIGIN
        // blocks cross-origin iframes including the YouTube player itself.
        source: "/((?!courses/).*)",
        headers: [
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
        ],
      },
      {
        // All pages: CSP and COOP headers.
        // frame-src permits YouTube embed player.
        // Cross-Origin-Opener-Policy permits Google Sign-In popups.
        source: "/(.*)",
        headers: [
          {
            key: "Cross-Origin-Opener-Policy",
            value: "same-origin-allow-popups",
          },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com",
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
              "font-src 'self' https://fonts.gstatic.com",
              "img-src 'self' data: https: blob:",
              "frame-src 'self' https://www.youtube.com https://youtube.com https://accounts.google.com",
              "connect-src 'self' https://stempath-api.onrender.com https://app.posthog.com http://localhost:8000",
              "media-src 'self' https://www.youtube.com https://youtube.com",
            ].join("; "),
          },
        ],
      },
    ];
  },

  images: {
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