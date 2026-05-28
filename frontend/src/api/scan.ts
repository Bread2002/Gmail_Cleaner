// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 26th, 2026
// Description: API module for scan-related operations in the Gmail Cleaner frontend application.

// Import necessary modules and components
import { apiClient } from "./client";
import type { ScanRequest, ScanStartResponse, ScanResult } from "../types";

// Define the scanApi object that contains methods for scan-related API calls
export const scanApi = {
  // Method to start a new scan with the given request body
  start: (body: ScanRequest) =>
    apiClient.post<ScanStartResponse>("/scan/start", body).then((r) => r.data),

  // Method to retrieve the results of a scan using the scan ID
  results: (scanId: string) =>
    apiClient.get<ScanResult>(`/scan/${scanId}/results`).then((r) => r.data),
};
