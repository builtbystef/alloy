import { expect, test } from "vite-plus/test";

import { chatErrorMessage } from "./errors";

test("the API's detail is shown when the transport hands over the body", () => {
  expect(chatErrorMessage(new Error('{"detail":"Too many messages. Try again later."}'))).toBe(
    "Too many messages. Try again later.",
  );
});

test("anything else falls back to the message, then to a generic line", () => {
  expect(chatErrorMessage(new Error('{"detail":[{"msg":"x"}]}'))).toBe('{"detail":[{"msg":"x"}]}');
  expect(chatErrorMessage(new Error('{"error":"x"}'))).toBe('{"error":"x"}');
  expect(chatErrorMessage(new Error("Failed to fetch"))).toBe("Failed to fetch");
  expect(chatErrorMessage(new Error(""))).toBe("Something went wrong.");
  expect(chatErrorMessage(new Error("null"))).toBe("null");
});
