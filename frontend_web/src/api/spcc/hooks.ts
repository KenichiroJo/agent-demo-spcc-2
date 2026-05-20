import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as client from './client';

export const spccKeys = {
  all: ['spcc'] as const,
  dashboard: (sessionId: string) => ['spcc', 'dashboard', sessionId] as const,
  operators: (sessionId: string) => ['spcc', 'operators', sessionId] as const,
  calls: (sessionId: string, filters: object) =>
    ['spcc', 'calls', sessionId, filters] as const,
  callDetail: (sessionId: string, callId: string) =>
    ['spcc', 'call', sessionId, callId] as const,
  operatorReport: (sessionId: string, name: string) =>
    ['spcc', 'operatorReport', sessionId, name] as const,
};

export function useUploadFiles() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      calls,
      utterances,
      onProgress,
    }: {
      calls: File;
      utterances: File;
      onProgress?: (p: number) => void;
    }) => client.uploadFiles(calls, utterances, onProgress),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: spccKeys.all });
    },
  });
}

export function useDashboard(sessionId: string | null) {
  return useQuery({
    queryKey: spccKeys.dashboard(sessionId ?? ''),
    queryFn: () => client.getDashboard(sessionId!),
    enabled: !!sessionId,
  });
}

export function useOperators(sessionId: string | null) {
  return useQuery({
    queryKey: spccKeys.operators(sessionId ?? ''),
    queryFn: () => client.getOperators(sessionId!),
    enabled: !!sessionId,
  });
}

export function useCalls(
  sessionId: string | null,
  filters: {
    operatorName?: string;
    skill?: string;
    minDuration?: number;
    flagOnly?: boolean;
    limit?: number;
  } = {}
) {
  return useQuery({
    queryKey: spccKeys.calls(sessionId ?? '', filters),
    queryFn: () => client.getCalls(sessionId!, filters),
    enabled: !!sessionId,
  });
}

export function useCallDetail(sessionId: string | null, callId: string | null) {
  return useQuery({
    queryKey: spccKeys.callDetail(sessionId ?? '', callId ?? ''),
    queryFn: () => client.getCallDetail(sessionId!, callId!),
    enabled: !!sessionId && !!callId,
    staleTime: 10 * 60 * 1000,
  });
}

export function useOperatorReport(sessionId: string | null, name: string | null) {
  return useQuery({
    queryKey: spccKeys.operatorReport(sessionId ?? '', name ?? ''),
    queryFn: () => client.getOperatorReport(sessionId!, name!),
    enabled: !!sessionId && !!name,
    staleTime: 10 * 60 * 1000,
  });
}
