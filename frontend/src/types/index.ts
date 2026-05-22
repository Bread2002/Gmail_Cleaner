// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface LoginResponse {
  auth_url: string;
}

export interface CallbackRequest {
  code: string;
  state: string;
}

export interface CallbackResponse {
  session_token: string;
  user_email: string;
  expires_at: string;
}

export interface MeResponse {
  email: string;
  authenticated: boolean;
}

// ---------------------------------------------------------------------------
// Senders / Scan
// ---------------------------------------------------------------------------

export type ScanStatus = "pending" | "running" | "complete" | "error";

export interface FlaggedSender {
  id: string;
  email: string;
  display_name?: string;
  message_count: number;
  consecutive_unread_count: number;
  snippet?: string;
  subject?: string;
  first_message_date?: string;
}

export interface ScanRequest {
  dry_run: boolean;
  consecutive_unread_threshold: number;
  max_senders: number;
  max_messages_per_sender: number;
}

export interface ScanStartResponse {
  scan_id: string;
}

export interface ScanResult {
  scan_id: string;
  status: ScanStatus;
  dry_run: boolean;
  senders: FlaggedSender[];
  error?: string;
}

export interface PreviewResponse {
  sender_id: string;
  email: string;
  subject?: string;
  snippet?: string;
  date?: string;
}

export interface TrashStartResponse {
  job_id: string;
  sender: string;
  estimated_count: number;
}

export interface BlockResponse {
  filter_id?: string;
  sender: string;
}

export interface BulkTrashJob {
  sender_id: string;
  job_id: string;
}

export interface BulkTrashResponse {
  jobs: BulkTrashJob[];
}

export interface BulkBlockResponse {
  blocked: string[];
  failed: string[];
}

export interface BulkSkipResponse {
  skipped: string[];
  failed: string[];
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

export interface UserSettings {
  consecutive_unread_threshold: number;
  max_senders: number;
  max_messages_per_sender: number;
  dry_run_by_default: boolean;
}

// ---------------------------------------------------------------------------
// SSE Events
// ---------------------------------------------------------------------------

export type ScanEventType =
  | "progress"
  | "sender_found"
  | "complete"
  | "error"
  | "heartbeat"
  | "done";
export type TrashEventType =
  | "progress"
  | "complete"
  | "error"
  | "heartbeat"
  | "done";

export interface ScanProgressEvent {
  phase: string;
  message?: string;
  sender?: string;
  current?: number;
  total?: number;
  total_unread?: number;
}

export interface ScanCompleteEvent {
  scan_id: string;
  senders_found: number;
  dry_run: boolean;
}

export interface TrashProgressEvent {
  trashed: number;
  total: number;
  batch?: number;
  total_batches?: number;
  message?: string;
}

export interface TrashCompleteEvent {
  trashed_count: number;
  sender: string;
  dry_run: boolean;
}
