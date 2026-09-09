/**
 * The header that carries the visitor's address, and how to read it.
 *
 * Every platform in front of the web app overwrites exactly one header with
 * the address it saw, and only that header is safe to trust: any other is
 * whatever the visitor sent. Which one it is depends on the host, so it is
 * configured with `CLIENT_IP_HEADER` rather than guessed from what arrives.
 */
export const CLIENT_IP_HEADERS = ["cf-connecting-ip", "x-real-ip", "x-forwarded-for"] as const;

export type ClientIpHeader = (typeof CLIENT_IP_HEADERS)[number];

function isClientIpHeader(value: string): value is ClientIpHeader {
  return (CLIENT_IP_HEADERS as readonly string[]).includes(value);
}

/**
 * The header to trust, from the server-side environment (case-insensitive).
 * Null when unset, which is right for local `next dev` and the safe reading of
 * a deployment that forgot to set it. Throws on any other value so a typo
 * fails at startup instead of silently dropping the address.
 */
export function getClientIpHeader(): ClientIpHeader | null {
  const raw = process.env["CLIENT_IP_HEADER"]?.trim().toLowerCase();
  if (!raw) return null;
  if (isClientIpHeader(raw)) return raw;
  throw new Error(
    `CLIENT_IP_HEADER is "${raw}"; expected one of ${CLIENT_IP_HEADERS.join(", ")}, or unset`,
  );
}

/**
 * The visitor's address as the configured header reports it, or null when no
 * header is configured or the request lacks it. `X-Forwarded-For` is a list
 * to which each proxy appends, so the last entry is the one the nearest
 * proxy wrote and the one a visitor cannot forge.
 */
export function clientAddress(
  headers: Headers,
  header: ClientIpHeader | null = getClientIpHeader(),
): string | null {
  if (header === null) return null;
  const value = headers.get(header);
  if (value === null) return null;
  const address = header === "x-forwarded-for" ? value.split(",").at(-1) : value;
  return address?.trim() || null;
}
