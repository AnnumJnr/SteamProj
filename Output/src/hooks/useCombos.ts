/**
 * hooks/useCombos.ts
 * Responsibility: fetch and cache combo data via TanStack Query.
 * Forbidden: store writes, navigation, analytics.
 * TanStack Query hooks for combo data fetching and mutations.
 */
 
"use client";
 
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/constants/queryKeys";
import * as comboService from "@/services/comboService";
import type { ComboFilters, CreateComboPayload, UpdateComboPayload } from "@/types/combo";
 
export function useCombos(filters: ComboFilters = {}) {
  return useQuery({
    queryKey: queryKeys.combos.list(filters),
    queryFn: () => comboService.getCombos(filters),
  });
}
 
export function useCombo(id: string) {
  return useQuery({
    queryKey: queryKeys.combos.detail(id),
    queryFn: () => comboService.getCombo(id),
    enabled: Boolean(id),
  });
}
 
export function useMyCombos() {
  return useQuery({
    queryKey: queryKeys.combos.mine,
    queryFn: comboService.getMyCombos,
  });
}
 
export function useComboProgress(id: string) {
  return useQuery({
    queryKey: queryKeys.combos.progress(id),
    queryFn: () => comboService.getComboProgress(id),
    enabled: Boolean(id),
    // Don't error if user is not authenticated — returns 401 which is expected
    retry: false,
  });
}
 
export function useCreateCombo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateComboPayload) => comboService.createCombo(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.combos.all });
      qc.invalidateQueries({ queryKey: queryKeys.combos.mine });
    },
  });
}
 
export function useUpdateCombo(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: UpdateComboPayload) => comboService.updateCombo(id, payload),
    onSuccess: (updatedCombo) => {
      // Update the cache directly with the returned data — no need for a refetch
      qc.setQueryData(queryKeys.combos.detail(id), updatedCombo);
      // Also invalidate the list and mine so counts/visibility update
      qc.invalidateQueries({ queryKey: queryKeys.combos.list({}) });
      qc.invalidateQueries({ queryKey: queryKeys.combos.mine });
    },
  });
}
 
export function useDeleteCombo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => comboService.deleteCombo(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.combos.all });
      qc.invalidateQueries({ queryKey: queryKeys.combos.mine });
    },
  });
}
 
export function useRateCombo(comboId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (rating: number) => comboService.rateCombo(comboId, rating),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.combos.detail(comboId) });
      qc.invalidateQueries({ queryKey: queryKeys.combos.ratings(comboId) });
    },
  });
}