import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError, type Me, type Role, type Session } from "@/lib/api";

export const meKey = ["me"] as const;

export function useMe() {
  return useQuery({
    queryKey: meKey,
    queryFn: async () => {
      try {
        return await api<Me>("/me");
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
    staleTime: 60_000,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; password: string }) => api<Session>("/auth/login", { method: "POST", body }),
    onSuccess: (session) => {
      qc.clear();
      qc.setQueryData(meKey, session.user);
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<undefined>("/auth/logout", { method: "POST" }),
    onSettled: () => {
      qc.clear();
      qc.setQueryData(meKey, null);
    },
  });
}

/** UI hint only. The API enforces roles; hiding a control is never the authorization. */
export function canOperate(role: Role | undefined): boolean {
  return role === "ADMIN" || role === "ANALYST";
}
