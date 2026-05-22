import { useState } from "react";
import { sendersApi } from "../../api/senders";

interface Props {
  selectedIds: string[];
  totalCount: number;
  dryRun: boolean;
  /**
   * IDs of senders whose emails have already been permanently deleted.
   * The Bulk Trash button is suppressed when every selected sender is in this set.
   */
  trashedIds: Set<string>;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  /** Called after bulk skip/block completes with the IDs that were successfully actioned. */
  onBulkComplete: (ids: string[]) => void;
  /**
   * Called when a real (non-dry-run) bulk-trash request returns job IDs.
   * Senders stay visible; each SenderCard monitors its own SSE stream and
   * self-dismisses when the job finishes.
   */
  onBulkTrashStarted: (jobs: { sender_id: string; job_id: string }[]) => void;
}

export function BulkActionBar({
  selectedIds,
  totalCount,
  dryRun,
  trashedIds,
  onSelectAll,
  onDeselectAll,
  onBulkComplete,
  onBulkTrashStarted,
}: Props) {
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (totalCount === 0) return null;

  // Only operate on senders that haven't been trashed yet.
  const trashableIds = selectedIds.filter((id) => !trashedIds.has(id));
  const allSelectedTrashed = selectedIds.length > 0 && trashableIds.length === 0;

  const handleBulkTrash = async () => {
    // Only trash senders that haven't been deleted yet; skip already-trashed ones.
    const ids = trashableIds;
    if (ids.length === 0) return;
    setLoading(true);
    setStatus(null);
    try {
      const { jobs } = await sendersApi.bulkTrash(ids, dryRun);
      if (dryRun) {
        setStatus(`🧪 Would trash emails from ${jobs.length} sender(s)`);
        // Dry-run: no real work happening, dismiss immediately.
        onBulkComplete(jobs.map((j) => j.sender_id));
      } else {
        setStatus(`🗑️ Trashing ${jobs.length} sender(s)…`);
        // Real trash: hand off job IDs so each SenderCard can monitor SSE
        // progress and self-dismiss when its job completes.
        onBulkTrashStarted(jobs);
      }
    } catch (e: any) {
      setStatus(`❌ ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleBulkBlock = async () => {
    const ids = [...selectedIds];
    if (ids.length === 0) return;
    setLoading(true);
    setStatus(null);
    try {
      const { blocked, failed } = await sendersApi.bulkBlock(ids);
      setStatus(
        dryRun
          ? `🧪 Would block ${ids.length} sender(s)`
          : `🚫 Blocked ${blocked.length} sender(s)${failed.length ? `, ${failed.length} failed` : ""}`,
      );
      // Dismiss all selected — status message already reports any failures.
      onBulkComplete(ids);
    } catch (e: any) {
      setStatus(`❌ ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleBulkSkip = async () => {
    const ids = [...selectedIds];
    if (ids.length === 0) return;
    setLoading(true);
    setStatus(null);
    try {
      const { skipped, failed } = await sendersApi.bulkSkip(ids);
      setStatus(
        `⏭ Skipped ${skipped.length} sender(s)${failed.length ? `, ${failed.length} not found` : ""}`,
      );
      // Backend returns confirmed IDs — only dismiss those.
      onBulkComplete(skipped);
    } catch (e: any) {
      setStatus(`❌ ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-3 flex flex-wrap items-center gap-3 shadow-sm">
      {/* Select controls */}
      <div className="flex items-center gap-2 text-sm text-gray-600">
        <button
          onClick={onSelectAll}
          className="text-blue-600 hover:underline text-xs"
        >
          Select all
        </button>
        <span className="text-gray-300">|</span>
        <button
          onClick={onDeselectAll}
          className="text-gray-500 hover:underline text-xs"
        >
          None
        </button>
        <span className="font-medium text-gray-800">
          {selectedIds.length} / {totalCount} selected
        </span>
      </div>

      <div className="flex gap-2 ml-auto flex-wrap">
        <button
          onClick={handleBulkTrash}
          disabled={selectedIds.length === 0 || loading || allSelectedTrashed}
          title={allSelectedTrashed ? "All selected senders have already been trashed" : undefined}
          className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors
            ${
              dryRun
                ? "bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200"
                : "bg-red-50 hover:bg-red-100 text-red-700 border border-red-200"
            } disabled:opacity-40 disabled:cursor-not-allowed`}
        >
          {dryRun ? "🧪 Preview Trash" : "🗑️ Trash Selected"}
        </button>

        <button
          onClick={handleBulkBlock}
          disabled={selectedIds.length === 0 || loading}
          className="text-xs bg-orange-50 hover:bg-orange-100 text-orange-700 border border-orange-200 px-3 py-1.5 rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          🚫 Block Selected
        </button>

        <button
          onClick={handleBulkSkip}
          disabled={selectedIds.length === 0 || loading}
          className="text-xs bg-gray-50 hover:bg-gray-100 text-gray-500 border border-gray-200 px-3 py-1.5 rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          ⏭ Skip Selected
        </button>
      </div>

      {status && (
        <p className="w-full text-xs text-gray-600 bg-gray-50 rounded px-2 py-1">
          {status}
        </p>
      )}
    </div>
  );
}
