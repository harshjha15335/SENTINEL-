import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  api,
  type CaseDetail,
  type CasePage,
  type CasePriority,
  type CaseResolution,
  type CaseStatus,
  type DataOrigin,
} from "@/lib/api";

export type CaseFilters = {
  status?: CaseStatus | "";
  priority?: CasePriority | "";
  origin?: DataOrigin | "";
  mine?: boolean;
  transactionId?: string;
  page: number;
  pageSize: number;
};

export function useCases(f: CaseFilters) {
  const params = new URLSearchParams({ limit: String(f.pageSize), offset: String(f.page * f.pageSize) });
  if (f.status) params.set("status", f.status);
  if (f.priority) params.set("priority", f.priority);
  if (f.origin) params.set("data_origin", f.origin);
  if (f.mine) params.set("mine", "true");
  if (f.transactionId) params.set("transaction_id", f.transactionId);
  return useQuery({
    queryKey: ["cases", params.toString()],
    queryFn: () => api<CasePage>(`/cases?${params}`),
    placeholderData: keepPreviousData,
  });
}

export function useCase(id: string) {
  return useQuery({ queryKey: ["case", id], queryFn: () => api<CaseDetail>(`/cases/${id}`) });
}

function useCaseMutation<V>(fn: (v: V) => Promise<CaseDetail>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (c) => {
      qc.setQueryData(["case", c.id], c);
      void qc.invalidateQueries({ queryKey: ["cases"] });
      void qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useOpenCase() {
  return useCaseMutation((v: { transactionId: string; reason: string }) =>
    api<CaseDetail>("/cases", { method: "POST", body: { transaction_id: v.transactionId, reason: v.reason } }),
  );
}

export function useClaimCase(id: string) {
  return useCaseMutation(() => api<CaseDetail>(`/cases/${id}/claim`, { method: "POST" }));
}

export function useResolveCase(id: string) {
  return useCaseMutation((v: { resolution: CaseResolution; note: string }) =>
    api<CaseDetail>(`/cases/${id}/resolve`, { method: "POST", body: v }),
  );
}

export function useAddNote(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => api(`/cases/${id}/notes`, { method: "POST", body: { body } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["case", id] }),
  });
}
