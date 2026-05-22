import { apiClient } from "./client";
import type { ScanRequest, ScanStartResponse, ScanResult } from "../types";

export const scanApi = {
  start: (body: ScanRequest) =>
    apiClient.post<ScanStartResponse>("/scan/start", body).then((r) => r.data),

  results: (scanId: string) =>
    apiClient.get<ScanResult>(`/scan/${scanId}/results`).then((r) => r.data),
};
