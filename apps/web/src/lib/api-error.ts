import type { ValidationError } from "@alloy/api-client";

/** The shape openapi-fetch returns from every request. */
interface ApiResult<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

/** A non-2xx response from the API, with FastAPI's `detail` turned into a message. */
export class ApiError extends Error {
  override readonly name = "ApiError";

  constructor(
    readonly status: number,
    message: string,
    /** Per-field messages from a 422, keyed by the body field name. */
    readonly fields: Readonly<Record<string, string>> = {},
  ) {
    super(message);
  }

  static fromResult(result: ApiResult<unknown>): ApiError {
    const { response, error } = result;
    const detail = isRecord(error) ? error["detail"] : undefined;
    if (typeof detail === "string") {
      return new ApiError(response.status, detail);
    }
    if (Array.isArray(detail)) {
      // FastAPI request validation: [{ loc: ["body", "email"], msg, type }].
      const fields: Record<string, string> = {};
      const messages: string[] = [];
      for (const issue of detail as ValidationError[]) {
        const field = issue.loc
          .filter((part): part is string => typeof part === "string" && part !== "body")
          .join(".");
        if (field) fields[field] ??= issue.msg;
        messages.push(field ? `${field}: ${issue.msg}` : issue.msg);
      }
      return new ApiError(response.status, messages.join("; ") || "Validation error", fields);
    }
    return new ApiError(
      response.status,
      response.statusText || `Request failed with status ${response.status}`,
    );
  }
}

/** `data` from a successful result; throws `ApiError` otherwise. */
export function unwrap<T>(result: ApiResult<T>): T {
  if (result.response.ok) {
    return result.data as T;
  }
  throw ApiError.fromResult(result);
}

/** A message for the user from anything a query or mutation can reject with. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return "The API could not be reached.";
  if (error instanceof Error) return error.message;
  return String(error);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
