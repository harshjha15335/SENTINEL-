import { useQuery } from "@tanstack/react-query";

import { api, type PayPalStatus } from "@/lib/api";

export function usePayPalStatus() {
  return useQuery({ queryKey: ["paypal-status"], queryFn: () => api<PayPalStatus>("/paypal/status"), staleTime: 5 * 60_000 });
}
