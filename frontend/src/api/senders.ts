// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: API module for sender-related endpoints in the Gmail Cleaner application.

// Import necessary modules and components
import { apiClient } from "./client";
import type {
  PreviewResponse,
  TrashStartResponse,
  BlockResponse,
  BulkTrashResponse,
  BulkBlockResponse,
  BulkSkipResponse,
} from "../types";

// Define the sendersApi object that contains methods for sender-related API calls
export const sendersApi = {
  // Method to retrieve a preview of emails from a specific sender using the sender ID
  preview: (senderId: string) =>
    apiClient
      .get<PreviewResponse>(`/senders/${senderId}/preview`)
      .then((r) => r.data),

  // Method to move all emails from a specific sender to trash, with an optional dry run mode
  trash: (senderId: string, dryRun = false) =>
    apiClient
      .post<TrashStartResponse>(`/senders/${senderId}/trash`, {
        dry_run: dryRun,
      })
      .then((r) => r.data),

  // Method to block a specific sender using the sender ID
  block: (senderId: string) =>
    apiClient
      .post<BlockResponse>(`/senders/${senderId}/block`)
      .then((r) => r.data),

  // Method to trash multiple senders at once using their sender IDs
  bulkTrash: (senderIds: string[], dryRun = false) =>
    apiClient
      .post<BulkTrashResponse>("/senders/bulk/trash", {
        sender_ids: senderIds,
        dry_run: dryRun,
      })
      .then((r) => r.data),

  // Method to block multiple senders at once using their sender IDs
  bulkBlock: (senderIds: string[]) =>
    apiClient
      .post<BulkBlockResponse>("/senders/bulk/block", { sender_ids: senderIds })
      .then((r) => r.data),

  // Method to skip multiple senders at once using their sender IDs
  bulkSkip: (senderIds: string[]) =>
    apiClient
      .post<BulkSkipResponse>("/senders/bulk/skip", { sender_ids: senderIds })
      .then((r) => r.data),
};
