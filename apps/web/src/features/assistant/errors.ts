/**
 * The API answers errors as `{"detail": ...}`; the chat transport hands that
 * body over verbatim as the error's message.
 */
export function chatErrorMessage(error: Error): string {
  try {
    const parsed: unknown = JSON.parse(error.message);
    if (parsed && typeof parsed === "object" && "detail" in parsed) {
      const detail = (parsed as { detail: unknown }).detail;
      if (typeof detail === "string") return detail;
    }
  } catch {
    // Not JSON.
  }
  return error.message || "Something went wrong.";
}
