import { expect, test } from "vite-plus/test";

import { ApiError, errorMessage, tooManyAttempts } from "./api-error";

function result(status: number, body: unknown, headers: Record<string, string> = {}) {
  const response = new Response(null, { status, headers });
  return { error: body, response };
}

test("a detail string becomes the message", () => {
  const error = ApiError.fromResult(result(401, { detail: "Not authenticated" }));
  expect(error.status).toBe(401);
  expect(errorMessage(error)).toBe("Not authenticated");
  expect(error.retryAfter).toBeNull();
});

test("a 500 quotes the request ID from the header", () => {
  const error = ApiError.fromResult(
    result(
      500,
      {
        detail: "Something went wrong. Quote the request ID when reporting it.",
        request_id: "abc123",
      },
      { "x-request-id": "abc123" },
    ),
  );
  expect(error.requestId).toBe("abc123");
  expect(errorMessage(error)).toBe(
    "Something went wrong. Quote the request ID when reporting it. (request abc123)",
  );
});

test("a 4xx keeps the request ID without showing it", () => {
  const error = ApiError.fromResult(
    result(404, { detail: "Contact not found" }, { "x-request-id": "abc123" }),
  );
  expect(error.requestId).toBe("abc123");
  expect(errorMessage(error)).toBe("Contact not found");
});

test("a 429 says how long to wait, from Retry-After", () => {
  const error = ApiError.fromResult(
    result(429, { detail: "Too many attempts. Try again later." }, { "retry-after": "540" }),
  );
  expect(error.retryAfter).toBe(540);
  expect(errorMessage(error)).toBe("Too many attempts. Try again in 9 minutes.");
});

test("a 429 without Retry-After keeps the plain message", () => {
  const error = ApiError.fromResult(result(429, { detail: "Too many attempts. Try again later." }));
  expect(error.retryAfter).toBeNull();
  expect(errorMessage(error)).toBe("Too many attempts. Try again later.");
});

test("the wait is worded in seconds under a minute, minutes rounded up above", () => {
  expect(tooManyAttempts(1)).toBe("Too many attempts. Try again in 1 second.");
  expect(tooManyAttempts(45)).toBe("Too many attempts. Try again in 45 seconds.");
  expect(tooManyAttempts(60)).toBe("Too many attempts. Try again in 1 minute.");
  expect(tooManyAttempts(61)).toBe("Too many attempts. Try again in 2 minutes.");
});
