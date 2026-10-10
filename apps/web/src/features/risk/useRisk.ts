import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError, type ModelCard, type RiskAssessment } from "@/lib/api";

export function useAssessment(transactionId: string) {
  return useQuery({
    queryKey: ["risk", transactionId],
    queryFn: async () => {
      try {
        return await api<RiskAssessment>(`/transactions/${transactionId}/risk`);
      } catch (e) {
        if (e instanceof ApiError && e.status === 404 && e.code === "not_found") return null;
        throw e;
      }
    },
  });
}

export function useRescore(transactionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<RiskAssessment>(`/transactions/${transactionId}/risk`, { method: "POST" }),
    onSuccess: (a) => {
      qc.setQueryData(["risk", transactionId], a);
      void qc.invalidateQueries({ queryKey: ["transaction", transactionId] });
      void qc.invalidateQueries({ queryKey: ["cases"] });
    },
  });
}

export function useModelCard() {
  return useQuery({ queryKey: ["risk-model"], queryFn: () => api<ModelCard>("/risk/model"), staleTime: Infinity });
}
