/**
 * lib/queryClient.ts
 * TanStack Query client — single instance, shared across the app.
 * Configuration per architecture ruleset §9.4.
 */

import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,      // 5 minutes — data is considered fresh
      gcTime: 10 * 60 * 1000,         // 10 minutes — cache retention after unmount
      retry: 1,                        // One retry on failure
      refetchOnWindowFocus: false,     // Don't refetch on tab switch
    },
    mutations: {
      retry: 0,                        // No automatic retry on mutations
    },
  },
});
