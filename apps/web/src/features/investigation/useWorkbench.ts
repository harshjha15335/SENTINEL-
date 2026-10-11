import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  api,
  apiUpload,
  type AIStatus,
  type ApprovalActionType,
  type ApprovalRequest,
  type Evidence,
  type EvidenceCategory,
  type EvidenceList,
  type EvidencePacket,
  type InvestigationRun,
} from "@/lib/api";

const ACTIVE = new Set(["QUEUED", "RUNNING"]);

export const isActive = (r: InvestigationRun | undefined) => r != null && ACTIVE.has(r.status);

export function useAIStatus() {
  return useQuery({ queryKey: ["ai-status"], queryFn: () => api<AIStatus>("/ai/status"), staleTime: 60_000 });
}

export function useInvestigations(caseId: string) {
  return useQuery({
    queryKey: ["investigations", caseId],
    queryFn: () => api<InvestigationRun[]>(`/cases/${caseId}/investigations`),
    // Poll only while a run is queued or running.
    refetchInterval: (q) => (q.state.data?.some((r) => ACTIVE.has(r.status)) ? 1500 : false),
  });
}

/** Refresh everything on the workbench that a mutation may have changed (incl. the timeline). */
function useRefresh(caseId: string) {
  const qc = useQueryClient();
  return (...keys: string[]) => {
    for (const k of keys) void qc.invalidateQueries({ queryKey: [k, caseId] });
    void qc.invalidateQueries({ queryKey: ["case", caseId] });
  };
}

export function useStartInvestigation(caseId: string) {
  const refresh = useRefresh(caseId);
  return useMutation({
    mutationFn: (mode: "auto" | "deterministic") =>
      api<InvestigationRun>(`/cases/${caseId}/investigations`, { method: "POST", body: { mode } }),
    onSettled: () => refresh("investigations"),
  });
}

export function useEvidence(caseId: string) {
  return useQuery({ queryKey: ["evidence", caseId], queryFn: () => api<EvidenceList>(`/cases/${caseId}/evidence`) });
}

export function useUploadEvidence(caseId: string) {
  const refresh = useRefresh(caseId);
  return useMutation({
    mutationFn: (v: { file: File; category: EvidenceCategory; description: string }) => {
      const form = new FormData();
      form.append("file", v.file);
      form.append("category", v.category);
      form.append("description", v.description);
      return apiUpload<Evidence>(`/cases/${caseId}/evidence`, form);
    },
    onSuccess: () => refresh("evidence"),
  });
}

export function usePackets(caseId: string) {
  return useQuery({ queryKey: ["packets", caseId], queryFn: () => api<EvidencePacket[]>(`/cases/${caseId}/packets`) });
}

export function useGeneratePacket(caseId: string) {
  const refresh = useRefresh(caseId);
  return useMutation({
    mutationFn: () => api<EvidencePacket>(`/cases/${caseId}/packets`, { method: "POST" }),
    onSuccess: () => refresh("packets"),
  });
}

export function useApprovals(caseId: string) {
  return useQuery({ queryKey: ["approvals", caseId], queryFn: () => api<ApprovalRequest[]>(`/cases/${caseId}/approvals`) });
}

export function useCreateApproval(caseId: string) {
  const refresh = useRefresh(caseId);
  return useMutation({
    mutationFn: (v: { action_type: ApprovalActionType; justification: string; packet_id?: string }) =>
      api<ApprovalRequest>(`/cases/${caseId}/approvals`, { method: "POST", body: v }),
    onSuccess: () => refresh("approvals"),
  });
}

export function useDecideApproval(caseId: string) {
  const refresh = useRefresh(caseId);
  return useMutation({
    mutationFn: (v: { id: string; verb: "approve" | "reject"; comment: string }) =>
      api<ApprovalRequest>(`/cases/${caseId}/approvals/${v.id}/${v.verb}`, { method: "POST", body: { comment: v.comment } }),
    onSettled: () => refresh("approvals"),
  });
}
