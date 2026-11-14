"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";
import { toApiParams, type Filters } from "./filters";
import type {
  BandGroup,
  Country,
  Department,
  EmployeeProfile,
  EmployeeSummary,
  Exceptions,
  ExceptionType,
  HistoryEntry,
  Page,
  PayBandListing,
  PayGroup,
  Preview,
  RecentChange,
  Role,
  Summary,
} from "./types";

/** TanStack Query hooks: one per endpoint. Reference data barely changes, so it's cached. */

const REFERENCE = { staleTime: Infinity } as const;

export const keys = {
  me: ["me"] as const,
  employees: ["employees"] as const,
  employee: (id: number) => ["employees", id] as const,
  insights: ["insights"] as const,
};

export function useMe() {
  return useQuery({ queryKey: keys.me, queryFn: () => api.get<{ email: string }>("/auth/me") });
}

export function useLogout() {
  return useMutation({ mutationFn: () => api.post<void>("/auth/logout") });
}

export function useCountries() {
  return useQuery({
    queryKey: ["reference", "countries"],
    queryFn: () => api.get<Country[]>("/reference/countries"),
    ...REFERENCE,
  });
}

export function useDepartments() {
  return useQuery({
    queryKey: ["reference", "departments"],
    queryFn: () => api.get<Department[]>("/reference/departments"),
    ...REFERENCE,
  });
}

export function useRoles() {
  return useQuery({
    queryKey: ["reference", "roles"],
    queryFn: () => api.get<Role[]>("/reference/roles"),
    ...REFERENCE,
  });
}

export function usePayBands(roleId: number | null, country: string | null) {
  return useQuery({
    queryKey: ["reference", "pay-bands", roleId, country],
    queryFn: () =>
      api.get<PayBandListing[]>(`/reference/pay-bands?role_id=${roleId}&country=${country}`),
    enabled: roleId !== null && country !== null,
    ...REFERENCE,
  });
}

export function useEmployees(filters: Filters, pageSize?: number) {
  const params = toApiParams(filters, pageSize).toString();
  return useQuery({
    queryKey: [...keys.employees, "list", params],
    queryFn: () => api.get<Page<EmployeeSummary>>(`/employees?${params}`),
    placeholderData: keepPreviousData,
  });
}

export function useEmployee(id: number) {
  return useQuery({
    queryKey: keys.employee(id),
    queryFn: () => api.get<EmployeeProfile>(`/employees/${id}`),
  });
}

export function useHistory(id: number) {
  return useQuery({
    queryKey: [...keys.employee(id), "history"],
    queryFn: () => api.get<HistoryEntry[]>(`/employees/${id}/compensation`),
  });
}

export function useSummary() {
  return useQuery({
    queryKey: [...keys.insights, "summary"],
    queryFn: () => api.get<Summary>("/insights/summary"),
  });
}

export function useExceptions(type: ExceptionType, page = 1, pageSize = 25) {
  return useQuery({
    queryKey: [...keys.insights, "exceptions", type, page, pageSize],
    queryFn: () =>
      api.get<Exceptions>(`/insights/exceptions?type=${type}&page=${page}&page_size=${pageSize}`),
    placeholderData: keepPreviousData,
  });
}

export function useRecentChanges(limit = 5) {
  return useQuery({
    queryKey: [...keys.insights, "recent", limit],
    queryFn: () => api.get<RecentChange[]>(`/insights/recent-changes?limit=${limit}`),
  });
}

export function useBreakdown(groupBy: string, filters = "") {
  return useQuery({
    queryKey: [...keys.insights, "breakdown", groupBy, filters],
    queryFn: () =>
      api.get<PayGroup[]>(`/insights/breakdown?group_by=${groupBy}${filters ? `&${filters}` : ""}`),
    placeholderData: keepPreviousData,
  });
}

export function useBandDistribution(groupBy: string) {
  return useQuery({
    queryKey: [...keys.insights, "bands", groupBy],
    queryFn: () => api.get<BandGroup[]>(`/insights/band-distribution?group_by=${groupBy}`),
    placeholderData: keepPreviousData,
  });
}

export type RevisionBody = {
  effective_from: string;
  reason: string;
  base_annual_minor: number;
  role_id?: number;
  components?: unknown[];
  note?: string;
};

export function usePreview(employeeId: number, body: RevisionBody | null) {
  return useQuery({
    queryKey: [...keys.employee(employeeId), "preview", body],
    queryFn: () => api.post<Preview>(`/employees/${employeeId}/compensation/preview`, body),
    enabled: body !== null,
    placeholderData: keepPreviousData,
    retry: false,
  });
}

export function useRevise(employeeId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: RevisionBody) =>
      api.post<HistoryEntry>(`/employees/${employeeId}/compensation`, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.employees });
      void queryClient.invalidateQueries({ queryKey: keys.insights });
    },
  });
}

export function useHire() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post<EmployeeProfile>("/employees", body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.employees });
      void queryClient.invalidateQueries({ queryKey: keys.insights });
    },
  });
}
