/**
 * The API's default `ALLOY_ATTACHMENT_MAX_BYTES`. Checked here before an
 * upload starts, so the user hears about it at once; the API is the authority.
 */
export const ATTACHMENT_MAX_BYTES = 25 * 1024 * 1024;

const UNITS = ["B", "KB", "MB", "GB"] as const;

/** "12 B", "3.4 KB", "25 MB": one decimal above bytes, none when it would be ".0". */
export function formatBytes(bytes: number): string {
  let value = Math.max(bytes, 0);
  let unit = 0;
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024;
    unit++;
  }
  const rounded = unit === 0 ? value : Math.round(value * 10) / 10;
  return `${rounded} ${UNITS[unit]}`;
}
