/**
 * stores/uiStore.ts
 * UI state — sidebar open/closed, active filter panel, persistent UI preferences.
 * Per architecture ruleset §9.1: no server data stored here.
 */

"use client";

import { create } from "zustand";

interface UIState {
  // ─── State ───────────────────────────────────────────────────────────────
  isSidebarOpen: boolean;
  isFilterPanelOpen: boolean;

  // ─── Actions ─────────────────────────────────────────────────────────────
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setFilterPanelOpen: (open: boolean) => void;
  toggleFilterPanel: () => void;
}

export const useUIStore = create<UIState>()((set) => ({
  // ─── Initial State ────────────────────────────────────────────────────────
  isSidebarOpen: false,
  isFilterPanelOpen: false,

  // ─── Actions ──────────────────────────────────────────────────────────────
  setSidebarOpen: (open) => set({ isSidebarOpen: open }),
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setFilterPanelOpen: (open) => set({ isFilterPanelOpen: open }),
  toggleFilterPanel: () =>
    set((state) => ({ isFilterPanelOpen: !state.isFilterPanelOpen })),
}));
