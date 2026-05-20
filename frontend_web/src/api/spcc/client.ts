import apiClient from '@/api/apiClient';
import type {
  CallDetail,
  CallSummary,
  DashboardStats,
  OperatorReport,
  OperatorSummary,
  UploadResponse,
} from './types';

const PREFIX = '/v1/spcc';

export async function uploadFiles(
  callsFile: File,
  utterancesFile: File,
  onProgress?: (percent: number) => void
): Promise<UploadResponse> {
  const form = new FormData();
  form.append('calls_file', callsFile);
  form.append('utterances_file', utterancesFile);
  const res = await apiClient.post<UploadResponse>(`${PREFIX}/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 5 * 60 * 1000,
    onUploadProgress: e => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded * 100) / e.total));
      }
    },
  });
  return res.data;
}

export async function getDashboard(sessionId: string): Promise<DashboardStats> {
  const res = await apiClient.get<DashboardStats>(
    `${PREFIX}/session/${sessionId}/dashboard`
  );
  return res.data;
}

export async function getOperators(sessionId: string): Promise<OperatorSummary[]> {
  const res = await apiClient.get<OperatorSummary[]>(
    `${PREFIX}/session/${sessionId}/operators`
  );
  return res.data;
}

export async function getCalls(
  sessionId: string,
  filters: {
    operatorName?: string;
    skill?: string;
    minDuration?: number;
    flagOnly?: boolean;
    limit?: number;
  } = {}
): Promise<CallSummary[]> {
  const res = await apiClient.get<CallSummary[]>(
    `${PREFIX}/session/${sessionId}/calls`,
    {
      params: {
        operator_name: filters.operatorName,
        skill: filters.skill,
        min_duration: filters.minDuration,
        flag_only: filters.flagOnly,
        limit: filters.limit ?? 200,
      },
    }
  );
  return res.data;
}

export async function getCallDetail(
  sessionId: string,
  callId: string
): Promise<CallDetail> {
  const res = await apiClient.get<CallDetail>(
    `${PREFIX}/session/${sessionId}/call/${encodeURIComponent(callId)}`,
    { timeout: 3 * 60 * 1000 }
  );
  return res.data;
}

export async function getOperatorReport(
  sessionId: string,
  operatorName: string
): Promise<OperatorReport> {
  const res = await apiClient.get<OperatorReport>(
    `${PREFIX}/session/${sessionId}/operator/${encodeURIComponent(operatorName)}`,
    { timeout: 3 * 60 * 1000 }
  );
  return res.data;
}
