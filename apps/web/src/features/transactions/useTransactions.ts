import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api, type DataOrigin, type TransactionDetail, type TransactionPage, type TransactionStatus } from "@/lib/api";

export type TransactionFilters = {
  status?: TransactionStatus | "";
  origin?: DataOrigin | "";
  q?: string;
  page: number;
  pageSize: number;
};

export function useTransactions(f: TransactionFilters) {
  const params = new URLSearchParams({ limit: String(f.pageSize), offset: String(f.page * f.pageSize) });
  if (f.status) params.set("status", f.status);
  if (f.origin) params.set("data_origin", f.origin);
  if (f.q?.trim()) params.set("q", f.q.trim());
  return useQuery({
    queryKey: ["transactions", params.toString()],
    queryFn: () => api<TransactionPage>(`/transactions?${params}`),
    placeholderData: keepPreviousData,
  });
}

export function useTransaction(id: string) {
  return useQuery({ queryKey: ["transaction", id], queryFn: () => api<TransactionDetail>(`/transactions/${id}`) });
}
