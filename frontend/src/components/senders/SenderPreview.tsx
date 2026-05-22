import { useState, useEffect } from 'react';
import { sendersApi } from '../../api/senders';
import type { PreviewResponse } from '../../types';
import { truncate, fmtDate } from '../../utils/formatters';

interface Props {
  senderId: string;
  initialSnippet?: string;
  initialSubject?: string;
}

export function SenderPreview({ senderId, initialSnippet, initialSubject }: Props) {
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    sendersApi.preview(senderId)
      .then(setPreview)
      .catch(() => setPreview(null))
      .finally(() => setLoading(false));
  }, [senderId]);

  if (loading) {
    return (
      <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-400 animate-pulse">
        Loading preview…
      </div>
    );
  }

  const subject = preview?.subject ?? initialSubject ?? '(no subject)';
  const snippet = preview?.snippet ?? initialSnippet ?? '';

  return (
    <div className="bg-gray-50 rounded-lg p-3 text-sm border border-gray-100">
      <p className="font-medium text-gray-700 mb-1">{subject}</p>
      <p className="text-gray-500 italic">{truncate(snippet, 200)}</p>
      {preview?.date && (
        <p className="text-xs text-gray-400 mt-1">Received {fmtDate(preview.date)}</p>
      )}
    </div>
  );
}
