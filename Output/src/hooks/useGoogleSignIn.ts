/**
 * hooks/useGoogleSignIn.ts
 * Loads the Google Identity Services script once, initializes it with
 * NEXT_PUBLIC_GOOGLE_CLIENT_ID, and renders Google's own sign-in button
 * into the given ref. Calls onCredential(idToken) when the user signs in.
 */

"use client";

import { useEffect, useRef } from "react";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
          }) => void;
          renderButton: (
            parent: HTMLElement,
            options: Record<string, string | number>
          ) => void;
        };
      };
    };
  }
}

const GSI_SCRIPT_SRC = "https://accounts.google.com/gsi/client";

function loadGsiScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();

  const existing = document.querySelector<HTMLScriptElement>(
    `script[src="${GSI_SCRIPT_SRC}"]`
  );
  if (existing) {
    return new Promise((resolve) => existing.addEventListener("load", () => resolve()));
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = GSI_SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Google Identity Services script"));
    document.head.appendChild(script);
  });
}

export function useGoogleSignIn(onCredential: (idToken: string) => void) {
  const buttonRef = useRef<HTMLDivElement>(null);
  const onCredentialRef = useRef(onCredential);
  onCredentialRef.current = onCredential;

  useEffect(() => {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    if (!clientId) {
      console.warn("NEXT_PUBLIC_GOOGLE_CLIENT_ID is not set — Google Sign-In disabled.");
      return;
    }

    let cancelled = false;
    let observer: ResizeObserver | null = null;
    let renderedWidth = 0;

    loadGsiScript()
      .then(() => {
        if (cancelled || !window.google || !buttonRef.current) return;
        const container = buttonRef.current;
        const gsi = window.google.accounts.id;

        gsi.initialize({
          client_id: clientId,
          callback: (response) => onCredentialRef.current(response.credential),
        });

        // GIS only accepts a pixel width (200–400) — never "100%". The container
        // is fluid (phone widths go under 300px), so measure it, clamp, and
        // re-render on resize (rotation, breakpoint crossings) so the iframe
        // never overflows its card.
        const render = () => {
          const available = Math.floor(container.getBoundingClientRect().width);
          if (!available) return;
          const width = Math.min(400, Math.max(200, available));
          if (width === renderedWidth) return;
          renderedWidth = width;
          container.innerHTML = "";
          gsi.renderButton(container, {
            type: "standard",
            theme: "outline",
            size: "large",
            width,
            text: "continue_with",
          });
        };

        render();

        if ("ResizeObserver" in window) {
          observer = new ResizeObserver(render);
          observer.observe(container);
        }
      })
      .catch((err) => console.error(err));

    return () => {
      cancelled = true;
      observer?.disconnect();
    };
  }, []);

  return buttonRef;
}
