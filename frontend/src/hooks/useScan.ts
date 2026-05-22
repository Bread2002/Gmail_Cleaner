import { useState, useCallback, useRef } from "react";
import { scanApi } from "../api/scan";
import { sseUrl } from "../api/client";
import { createSSE } from "../utils/sse";
import type { FlaggedSender, ScanProgressEvent } from "../types";

export type ScanPhase = "idle" | "starting" | "scanning" | "done" | "error";

interface ScanState {
  phase: ScanPhase;
  scanId: string | null;
  senders: FlaggedSender[];
  progress: ScanProgressEvent | null;
  totalFound: number;
  error: string | null;
  /** Rolling log of activity messages shown in the progress panel */
  eventLog: string[];
}

const INITIAL: ScanState = {
  phase: "idle",
  scanId: null,
  senders: [],
  progress: null,
  totalFound: 0,
  error: null,
  eventLog: [],
};

function timestamp(): string {
  const d = new Date();
  return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
}

export function useScan() {
  const [state, setState] = useState<ScanState>(INITIAL);
  const sseRef = useRef<{ close: () => void } | null>(null);

  const appendLog = (msg: string) =>
    setState((s) => ({
      ...s,
      eventLog: [...s.eventLog, `[${timestamp()}] ${msg}`],
    }));

  const startScan = useCallback(
    async (opts: {
      dryRun: boolean;
      consecutiveUnreadThreshold: number;
      maxSenders: number;
      maxMessagesPerSender: number;
    }) => {
      sseRef.current?.close();
      setState({
        ...INITIAL,
        phase: "starting",
        eventLog: [`[${timestamp()}] Starting scan…`],
      });

      try {
        const { scan_id } = await scanApi.start({
          dry_run: opts.dryRun,
          consecutive_unread_threshold: opts.consecutiveUnreadThreshold,
          max_senders: opts.maxSenders,
          max_messages_per_sender: opts.maxMessagesPerSender,
        });

        setState((s) => ({ ...s, phase: "scanning", scanId: scan_id }));

        const url = sseUrl(`/scan/${scan_id}/stream`);
        sseRef.current = createSSE(url, {
          onMessage: (type, data: any) => {
            if (type === "progress") {
              const p = data as ScanProgressEvent;
              setState((s) => ({ ...s, progress: p }));

              if (p.phase === "listing_unread") {
                if (p.total_unread != null) {
                  // Final count after listing completes
                  appendLog(
                    `Found ${p.total_unread.toLocaleString()} unread messages — analysing senders…`,
                  );
                } else if (p.message) {
                  // First event: confirms SSE is working and scan has started
                  appendLog(p.message);
                }
              } else if (
                p.phase === "analyzing_senders" &&
                p.current != null &&
                p.total != null
              ) {
                // Only log every 500 messages to avoid flooding the log
                if (p.current === p.total || p.current % 500 === 0) {
                  appendLog(
                    `Analyzed ${p.current.toLocaleString()} of ${p.total.toLocaleString()} messages…`,
                  );
                }
              } else if (p.phase === "checking_sender" && p.sender) {
                appendLog(`Checking ${p.sender}`);
              }
            } else if (type === "sender_found") {
              const sender = data as FlaggedSender;
              setState((s) => ({
                ...s,
                senders: [...s.senders, sender],
                totalFound: s.totalFound + 1,
              }));
              appendLog(
                `⚑ Flagged: ${sender.email} (${sender.consecutive_unread_count}+ consecutive unread)`,
              );
            } else if (type === "complete") {
              const found = (data as any).senders_found ?? 0;
              appendLog(
                found === 0
                  ? `Scan complete — no senders met the threshold`
                  : `Scan complete — ${found} sender(s) flagged`,
              );
            } else if (type === "error") {
              appendLog(`❌ Error: ${(data as any).detail ?? "Unknown error"}`);
              setState((s) => ({
                ...s,
                phase: "error",
                error: (data as any).detail ?? "Scan failed",
              }));
            }
          },
          onDone: () => {
            setState((s) => ({ ...s, phase: "done" }));
          },
          onError: () => {
            appendLog("Connection error — check the backend terminal");
            setState((s) => ({ ...s, phase: "done" }));
          },
        });
      } catch (e: any) {
        appendLog(`❌ Failed to start scan: ${e.message}`);
        setState((s) => ({
          ...s,
          phase: "error",
          error: e.message ?? "Failed to start scan",
        }));
      }
    },
    [],
  ); // eslint-disable-line react-hooks/exhaustive-deps

  const reset = useCallback(() => {
    sseRef.current?.close();
    setState(INITIAL);
  }, []);

  return { ...state, startScan, reset };
}
