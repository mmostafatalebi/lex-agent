import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  AnalysisStatusResponse,
  HumanDecision,
  UploadContractResponse,
} from "./api-types";
import { getClient } from "./api-client";

const POLL_INTERVAL_MS = 3000;

export function useUploadContract() {
  return useMutation<UploadContractResponse, Error, File>({
    mutationFn: (file) => getClient().uploadContract(file),
  });
}

export function useStartAnalysis() {
  return useMutation<AnalysisStatusResponse, Error, string>({
    mutationFn: (contractId) => getClient().startAnalysis(contractId),
  });
}

export function useAnalysisStatus(threadId: string | null) {
  return useQuery<AnalysisStatusResponse>({
    queryKey: ["analysis", threadId],
    queryFn: () => getClient().getAnalysis(threadId as string),
    enabled: !!threadId,
    retry: false,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "complete" || status === "failed") return false;
      return POLL_INTERVAL_MS;
    },
  });
}

export function useSubmitDecisions(threadId: string) {
  const queryClient = useQueryClient();
  return useMutation<AnalysisStatusResponse, Error, HumanDecision[]>({
    mutationFn: (decisions) => getClient().submitDecisions(threadId, decisions),
    onSuccess: (data) => {
      queryClient.setQueryData(["analysis", threadId], data);
    },
  });
}
