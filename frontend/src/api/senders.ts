import { apiClient } from "./client";
import type {
  PreviewResponse,
  TrashStartResponse,
  BlockResponse,
  BulkTrashResponse,
  BulkBlockResponse,
  BulkSkipResponse,
} from "../types";

export const sendersApi = {
  preview: (senderId: string) =>
    apiClient
      .get<PreviewResponse>(`/senders/${senderId}/preview`)
      .then((r) => r.data),

  trash: (senderId: string, dryRun = false) =>
    apiClient
      .post<TrashStartResponse>(`/senders/${senderId}/trash`, {
        dry_run: dryRun,
      })
      .then((r) => r.data),

  block: (senderId: string) =>
    apiClient
      .post<BlockResponse>(`/senders/${senderId}/block`)
      .then((r) => r.data),

  bulkTrash: (senderIds: string[], dryRun = false) =>
    apiClient
      .post<BulkTrashResponse>("/senders/bulk/trash", {
        sender_ids: senderIds,
        dry_run: dryRun,
      })
      .then((r) => r.data),

  bulkBlock: (senderIds: string[]) =>
    apiClient
      .post<BulkBlockResponse>("/senders/bulk/block", { sender_ids: senderIds })
      .then((r) => r.data),

  bulkSkip: (senderIds: string[]) =>
    apiClient
      .post<BulkSkipResponse>("/senders/bulk/skip", { sender_ids: senderIds })
      .then((r) => r.data),
};
