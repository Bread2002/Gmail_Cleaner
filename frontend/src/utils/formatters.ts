// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: Contains utility functions for formatting numbers, dates, and strings in the Gmail Cleaner frontend application.

/** Format a number with commas: 1234 → "1,234" */
export function fmtNumber(n: number): string {
  return new Intl.NumberFormat().format(n);
}

/** Format an ISO date string to a readable short date */
export function fmtDate(iso?: string): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

/** Truncate a string to maxLen chars */
export function truncate(str: string | undefined, maxLen = 120): string {
  if (!str) return "";
  return str.length > maxLen ? str.slice(0, maxLen) + "…" : str;
}
