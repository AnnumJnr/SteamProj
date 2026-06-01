/**
 * app/providers.tsx
 * All client-side providers in one wrapper component.
 * This file is the ONLY place providers are composed.
 * Keeps the root layout clean and server-component-friendly.
 *
 * Provider order (inside → out):
 *   QueryClientProvider → children
 *
 * Auth store wires itself into the API client on import (stores/authStore.ts).
 * No explicit provider needed for Zustand.
 */

"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { queryClient } from "@/lib/queryClient";
import type { ReactNode } from "react";

// Side-effect import: wires auth store into Axios interceptors on module load.
// Must be imported here so it runs on every client-side page, not just auth pages.
import "@/stores/authStore";

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {/* DevTools only visible in development — tree-shaken in production build */}
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
