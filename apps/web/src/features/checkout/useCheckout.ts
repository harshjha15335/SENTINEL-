import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type OrderCreated, type Product, type Transaction } from "@/lib/api";

export function useProducts() {
  return useQuery({ queryKey: ["products"], queryFn: () => api<Product[]>("/products") });
}

export function useCreateOrder() {
  return useMutation({
    mutationFn: ({ productId, quantity, key }: { productId: string; quantity: number; key: string }) =>
      api<OrderCreated>("/paypal/orders", {
        method: "POST",
        body: { product_id: productId, quantity },
        headers: { "Idempotency-Key": key },
      }),
  });
}

export function useCaptureOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (orderId: string) => api<Transaction>(`/paypal/orders/${encodeURIComponent(orderId)}/capture`, { method: "POST" }),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ["transactions"] });
      void qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
