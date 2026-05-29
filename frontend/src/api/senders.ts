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
  BulkDeleteResponse,
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

  // Method to move all emails from a specific sender to Gmail Trash (recoverable for 30 days)
  moveToTrash: (senderId: string, dryRun = false) =>
    apiClient
      .post<TrashStartResponse>(`/senders/${senderId}/move-to-trash`, {
        dry_run: dryRun,
      })
      .then((r) => r.data),

  // Method to permanently delete all emails from a specific sender (irreversible)
  deleteForever: (senderId: string, dryRun = false) =>
    apiClient
      .post<TrashStartResponse>(`/senders/${senderId}/delete`, {
        dry_run: dryRun,
      })
      .then((r) => r.data),

  // Method to block a specific sender using the sender ID
  block: (senderId: string) =>
    apiClient
      .post<BlockResponse>(`/senders/${senderId}/block`)
      .then((r) => r.data),

  // Method to move multiple senders' emails to Gmail Trash at once (recoverable for 30 days)
  bulkMoveToTrash: (senderIds: string[], dryRun = false) =>
    apiClient
      .post<BulkDeleteResponse>("/senders/bulk/move-to-trash", {
        sender_ids: senderIds,
        dry_run: dryRun,
      })
      .then((r) => r.data),

  // Method to permanently delete multiple senders' emails at once (irreversible)
  bulkDeleteForever: (senderIds: string[], dryRun = false) =>
    apiClient
      .post<BulkDeleteResponse>("/senders/bulk/delete", {
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
