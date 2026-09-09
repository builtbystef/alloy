import { afterEach, expect, test, vi } from "vite-plus/test";

import { clientAddress, getClientIpHeader } from "./client-address";

afterEach(() => {
  vi.unstubAllEnvs();
});

const headers = new Headers({
  "cf-connecting-ip": "203.0.113.1",
  "x-real-ip": "203.0.113.2",
  "x-forwarded-for": "198.51.100.9, 203.0.113.3",
});

test("no configured header sends no address, whatever the request carries", () => {
  vi.stubEnv("CLIENT_IP_HEADER", undefined);
  expect(getClientIpHeader()).toBeNull();
  expect(clientAddress(headers)).toBeNull();
});

test("an empty value reads as unset", () => {
  vi.stubEnv("CLIENT_IP_HEADER", "  ");
  expect(getClientIpHeader()).toBeNull();
});

test("an unknown header name fails loudly", () => {
  vi.stubEnv("CLIENT_IP_HEADER", "x-client-ip");
  expect(() => getClientIpHeader()).toThrow(/CLIENT_IP_HEADER is "x-client-ip"/);
});

test("CF-Connecting-IP is read and the other headers ignored", () => {
  vi.stubEnv("CLIENT_IP_HEADER", "CF-Connecting-IP");
  expect(getClientIpHeader()).toBe("cf-connecting-ip");
  expect(clientAddress(headers)).toBe("203.0.113.1");
});

test("X-Real-IP is read and the other headers ignored", () => {
  vi.stubEnv("CLIENT_IP_HEADER", "x-real-ip");
  expect(clientAddress(headers)).toBe("203.0.113.2");
});

test("X-Forwarded-For takes the last entry, the one the nearest proxy appended", () => {
  vi.stubEnv("CLIENT_IP_HEADER", "x-forwarded-for");
  expect(clientAddress(headers)).toBe("203.0.113.3");
  expect(clientAddress(new Headers({ "x-forwarded-for": "203.0.113.4" }))).toBe("203.0.113.4");
});

test("a configured header the request lacks yields no address", () => {
  vi.stubEnv("CLIENT_IP_HEADER", "cf-connecting-ip");
  expect(clientAddress(new Headers({ "x-forwarded-for": "203.0.113.3" }))).toBeNull();
  expect(clientAddress(new Headers({ "cf-connecting-ip": "  " }))).toBeNull();
});
