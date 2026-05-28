// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: Contains the useDeletion hook for managing the state and actions related to bulk deletion of emails in the Gmail Cleaner application.

// Import necessary modules and components
import { useState, useCallback, useRef } from "react";
import { sendersApi } from "../api/senders";
import { sseUrl } from "../api/client";
import { createSSE } from "../utils/sse";
import type { TrashProgressEvent, TrashCompleteEvent } from "../types";

// Define the possible phases of the deletion process and the structure of the deletion state
export type DeletionPhase = "idle" | "starting" | "deleting" | "done" | "error";

// Define the structure of the deletion state
interface DeletionState {
  phase: DeletionPhase;
  jobId: string | null;
  progress: TrashProgressEvent | null;
  result: TrashCompleteEvent | null;
  error: string | null;
}

// Define the initial state for the deletion process
const INITIAL: DeletionState = {
  phase: "idle",
  jobId: null,
  progress: null,
  result: null,
  error: null,
};

// Define the useDeletion hook that manages the state and actions related to bulk deletion of emails for a specific sender
export function useDeletion(senderId: string) {
  const [state, setState] = useState<DeletionState>(INITIAL);
  const sseRef = useRef<{ close: () => void } | null>(null);

  /** Open an SSE stream for an already-started job and wire up state transitions. */
  const _openSSE = useCallback(
    (jobId: string) => {
      const url = sseUrl(`/senders/${senderId}/trash/${jobId}/stream`);
      sseRef.current = createSSE(url, {
        onMessage: (type, data: any) => {
          if (type === "progress") {
            setState((s) => ({ ...s, progress: data as TrashProgressEvent }));
          } else if (type === "complete") {
            setState((s) => ({
              ...s,
              phase: "done",
              result: data as TrashCompleteEvent,
            }));
          } else if (type === "error") {
            setState((s) => ({
              ...s,
              phase: "error",
              error: data.detail ?? "Deletion failed",
            }));
          }
        },
        onDone: () => {
          setState((s) => (s.phase !== "done" ? { ...s, phase: "done" } : s));
        },
        onError: () => {
          setState((s) => ({
            ...s,
            phase: "error",
            error: "Connection lost during deletion",
          }));
        },
      });
    },
    [senderId],
  );

  const trash = useCallback(
    async (dryRun = false) => {
      sseRef.current?.close();
      setState({ ...INITIAL, phase: "starting" });

      try {
        const { job_id } = await sendersApi.trash(senderId, dryRun);
        setState((s) => ({ ...s, phase: "deleting", jobId: job_id }));
        _openSSE(job_id);
      } catch (e: any) {
        setState((s) => ({
          ...s,
          phase: "error",
          error: e.message ?? "Failed to start deletion",
        }));
      }
    },
    [senderId, _openSSE],
  );

  /**
   * Attach to a bulk-trash job that was already started by the backend.
   * Skips the POST and goes straight to SSE monitoring.
   */
  const startFromJobId = useCallback(
    (jobId: string) => {
      sseRef.current?.close();
      setState({ ...INITIAL, phase: "deleting", jobId });
      _openSSE(jobId);
    },
    [_openSSE],
  );

  const reset = useCallback(() => {
    sseRef.current?.close();
    setState(INITIAL);
  }, []);

  return { ...state, trash, startFromJobId, reset };
}
