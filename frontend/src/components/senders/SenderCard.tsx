// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: Sender card component that displays sender information, preview, and action buttons for managing individual senders.

// Import necessary modules and components
import { useState, useEffect, useRef } from "react";
import type { FlaggedSender } from "../../types";
import { useDeletion } from "../../hooks/useDeletion";
import { SenderPreview } from "./SenderPreview";
import { ActionButtons } from "./ActionButtons";
import { DeletionProgress } from "../deletion/DeletionProgress";

// Define the props for the SenderCard component
interface Props {
  sender: FlaggedSender;
  dryRun: boolean;
  selected: boolean;
  onToggleSelect: (id: string) => void;
  /** Called when user skips, or on auto-dismiss after trash/block. */
  onDismiss: (id: string) => void;
  /** Called the first time this sender is trashed or blocked (deselects from bulk). */
  onActioned: (id: string) => void;
  /**
   * Called once when a real (non-dry-run) trash job finishes successfully.
   * Used by SenderList to track which senders have been permanently deleted
   * so the Bulk Trash button can be suppressed for already-trashed senders.
   */
  onTrashed?: (id: string) => void;
  /**
   * Set when this card is the *currently active* bulk-trash job.
   * The card attaches to this job's SSE stream and shows live progress.
   */
  bulkTrashJobId?: string | null;
  /**
   * Set when this card is *waiting* in the bulk-trash queue (not yet active).
   * Shows a "Queued…" indicator; no SSE is opened yet.
   */
  isBulkTrashQueued?: boolean;
  /**
   * Called immediately when this card's bulk-trash job completes (or errors),
   * so the next queued job can start. The card stays visible — the user must
   * then Block or Skip to remove it from the list.
   */
  onBulkTrashJobDone?: (id: string) => void;
}

// Define the SenderCard component that renders sender information, preview, and action buttons for managing individual senders
export function SenderCard({
  sender,
  dryRun,
  selected,
  onToggleSelect,
  onDismiss,
  onActioned,
  onTrashed,
  bulkTrashJobId,
  isBulkTrashQueued,
  onBulkTrashJobDone,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const deletion = useDeletion(sender.id);
  const actionedNotifiedRef = useRef(false);
  const trashedNotifiedRef = useRef(false);
  const prevBulkJobIdRef = useRef<string | null>(null);

  // Ref so the bulk-done effect can read the current bulkTrashJobId without
  // including it in the dep array (prevents cleanup from cancelling the dismiss timer).
  const bulkTrashJobIdRef = useRef<string | null | undefined>(null);
  bulkTrashJobIdRef.current = bulkTrashJobId;

  // Guard: fire onBulkTrashJobDone + schedule dismiss at most once per card.
  const bulkDoneRef = useRef(false);

  const { startFromJobId } = deletion;

  // A sender is "actioned" once trashed or blocked individually.
  const isActioned = deletion.phase === "done" || blocked;

  // Deselect from bulk once actioned individually.
  useEffect(() => {
    if (isActioned && !actionedNotifiedRef.current) {
      actionedNotifiedRef.current = true;
      onActioned(sender.id);
    }
  }, [isActioned, sender.id, onActioned]);

  // Notify parent that this sender's emails have been permanently deleted
  // (real run only — dry-run does not count as trashed).
  useEffect(() => {
    if (deletion.phase === "done" && !dryRun && !trashedNotifiedRef.current) {
      trashedNotifiedRef.current = true;
      onTrashed?.(sender.id);
    }
  }, [deletion.phase, dryRun, sender.id, onTrashed]);

  // When the active bulk-trash job ID arrives, attach to its SSE stream.
  useEffect(() => {
    if (bulkTrashJobId && bulkTrashJobId !== prevBulkJobIdRef.current) {
      prevBulkJobIdRef.current = bulkTrashJobId;
      startFromJobId(bulkTrashJobId);
    }
  }, [bulkTrashJobId, startFromJobId]);

  // When the bulk-trash SSE finishes (done or error):
  //   Notify the queue immediately so the next job can start.
  //   The card stays visible — the user must then Block or Skip to leave the list.
  //   The individual-action effect below handles auto-dismiss once trash + block are both done.
  // We read bulkTrashJobId via ref so that a prop change (queue advancing,
  // setting it to null) does NOT re-run this effect.
  useEffect(() => {
    const terminal = deletion.phase === "done" || deletion.phase === "error";
    if (!terminal || !bulkTrashJobIdRef.current || bulkDoneRef.current) return;
    bulkDoneRef.current = true;
    onBulkTrashJobDone?.(sender.id);
    // Do NOT auto-dismiss — card stays for the user to Block or Skip.
  }, [deletion.phase, sender.id, onBulkTrashJobDone]);

  // For individually trashed senders: auto-dismiss once trashed AND blocked.
  useEffect(() => {
    if (!bulkTrashJobId && deletion.phase === "done" && blocked) {
      const timer = setTimeout(() => onDismiss(sender.id), 1500);
      return () => clearTimeout(timer);
    }
  }, [bulkTrashJobId, deletion.phase, blocked, sender.id, onDismiss]);

  const avatarLetter = (sender.display_name ?? sender.email)
    .charAt(0)
    .toUpperCase();

  // Is this card locked because it's part of a bulk operation?
  const isBulkLocked = !!(bulkTrashJobId || isBulkTrashQueued);

  return (
    <div
      className={`bg-white rounded-xl border transition-all ${
        selected ? "border-blue-400 shadow-md" : "border-gray-200 shadow-sm"
      } ${deletion.phase === "done" ? "opacity-75" : ""} ${
        isBulkTrashQueued ? "opacity-60" : ""
      }`}
    >
      <div className="p-4">
        {/* Top row: checkbox, avatar, sender info, badge */}
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onToggleSelect(sender.id)}
            disabled={
              deletion.phase === "deleting" ||
              deletion.phase === "starting" ||
              isBulkLocked
            }
            className="mt-1 w-4 h-4 accent-blue-600 cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
          />

          {/* Avatar */}
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-semibold text-sm flex-shrink-0">
            {avatarLetter}
          </div>

          {/* Sender details */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                {sender.display_name && (
                  <p className="font-semibold text-gray-900 text-sm truncate">
                    {sender.display_name}
                  </p>
                )}
                <p
                  className={`text-sm truncate ${sender.display_name ? "text-gray-500" : "font-semibold text-gray-900"}`}
                >
                  {sender.email}
                </p>
              </div>

              {/* Badge: message count */}
              <div className="flex-shrink-0 text-right">
                <span className="bg-red-100 text-red-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                  {sender.consecutive_unread_count}+ consecutive unread
                </span>
              </div>
            </div>

            {/* Preview toggle — hide when queued */}
            {!isBulkTrashQueued && (
              <button
                onClick={() => setExpanded((e) => !e)}
                className="mt-1.5 text-xs text-blue-500 hover:text-blue-700 transition-colors"
              >
                {expanded ? "▲ Hide preview" : "▼ Show preview"}
              </button>
            )}
          </div>
        </div>

        {/* Expanded preview */}
        {expanded && !isBulkTrashQueued && (
          <div className="mt-3 ml-12">
            <SenderPreview
              senderId={sender.id}
              initialSnippet={sender.snippet}
              initialSubject={sender.subject}
            />
          </div>
        )}

        {/* Action area */}
        <div className="mt-3 ml-12">
          {isBulkTrashQueued ? (
            /* Waiting in queue — no SSE yet */
            <p className="text-xs text-gray-400 italic">⏳ Queued…</p>
          ) : (
            <>
              {/* Deletion progress — shown while running, on completion, or on error */}
              {(deletion.phase === "starting" ||
                deletion.phase === "deleting" ||
                deletion.phase === "done" ||
                deletion.phase === "error") && (
                <DeletionProgress
                  phase={deletion.phase}
                  progress={deletion.progress}
                  result={deletion.result}
                  dryRun={dryRun}
                />
              )}

              {/* Action buttons — only for individually-managed senders (not bulk-trash) */}
              {!bulkTrashJobId &&
                (deletion.phase === "idle" || deletion.phase === "done") && (
                  <ActionButtons
                    senderId={sender.id}
                    phase={deletion.phase}
                    dryRun={dryRun}
                    blocked={blocked}
                    onTrash={() => deletion.trash(dryRun)}
                    onSkip={() => onDismiss(sender.id)}
                    onBlockComplete={() => setBlocked(true)}
                  />
                )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
