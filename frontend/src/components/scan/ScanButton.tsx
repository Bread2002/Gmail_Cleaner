import type { ScanPhase } from '../../hooks/useScan';

interface Props {
  phase: ScanPhase;
  dryRun: boolean;
  onScan: () => void;
  onReset: () => void;
}

export function ScanButton({ phase, dryRun, onScan, onReset }: Props) {
  const isScanning = phase === 'starting' || phase === 'scanning';

  if (phase === 'done' || phase === 'error') {
    return (
      <div className="flex gap-3">
        <button
          onClick={onScan}
          className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg font-medium transition-colors"
        >
          Scan Again
        </button>
        <button
          onClick={onReset}
          className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-5 py-2.5 rounded-lg font-medium transition-colors"
        >
          Clear Results
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={onScan}
      disabled={isScanning}
      className={`
        px-6 py-3 rounded-lg font-semibold text-white transition-all text-base
        ${isScanning
          ? 'bg-blue-400 cursor-not-allowed'
          : dryRun
            ? 'bg-amber-500 hover:bg-amber-600'
            : 'bg-blue-600 hover:bg-blue-700 shadow-sm hover:shadow-md'
        }
      `}
    >
      {isScanning
        ? '🔍 Scanning…'
        : dryRun
          ? '🧪 Preview Scan (Dry Run)'
          : '🔍 Scan My Inbox'}
    </button>
  );
}
