import test from "node:test";
import assert from "node:assert/strict";

import { getConsolePrinter } from "./console-safe";

test("getConsolePrinter keeps console method invocation safe", () => {
  const calls: Array<{ level: string; args: unknown[] }> = [];
  const consoleLike = {
    tag: "console-like",
    info(this: { tag: string }, ...args: unknown[]) {
      if (this.tag !== "console-like") {
        throw new TypeError("illegal invocation");
      }
      calls.push({ level: "info", args });
    },
    error(this: { tag: string }, ...args: unknown[]) {
      if (this.tag !== "console-like") {
        throw new TypeError("illegal invocation");
      }
      calls.push({ level: "error", args });
    },
  };

  const infoPrinter = getConsolePrinter(consoleLike, "request.success");
  const errorPrinter = getConsolePrinter(consoleLike, "request.error");

  assert.doesNotThrow(() => infoPrinter("ok", { request_id: "1" }));
  assert.doesNotThrow(() => errorPrinter("bad", { request_id: "2" }));
  assert.deepEqual(calls, [
    { level: "info", args: ["ok", { request_id: "1" }] },
    { level: "error", args: ["bad", { request_id: "2" }] },
  ]);
});

test("request.error logs structured payload without empty details", async () => {
  const originalEnv = process.env.NEXT_PUBLIC_DEV_LOG_FRONTEND;
  const originalFetch = globalThis.fetch;
  const globalWithWindow = globalThis as typeof globalThis & { window?: unknown };
  const originalWindow = globalWithWindow.window;
  const originalInfo = console.info;
  const originalError = console.error;
  const calls: Array<{ level: string; args: unknown[] }> = [];

  process.env.NEXT_PUBLIC_DEV_LOG_FRONTEND = "true";
  globalWithWindow.window = {} as unknown as Window & typeof globalThis;
  console.info = (...args: unknown[]) => calls.push({ level: "info", args });
  console.error = (...args: unknown[]) => calls.push({ level: "error", args });
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        detail: "bad request",
        error: {
          code: "bad.request",
          message: "bad request",
          details: {},
          correlation_id: "cid-1",
          status_code: 400,
        },
      }),
      {
        status: 400,
        headers: new Headers({
          "Content-Type": "application/json",
          "x-request-id": "req-1",
          "x-correlation-id": "corr-1",
        }),
      },
    );

  try {
    const { login } = await import("./api/core");
    await assert.rejects(() => login("demo@example.com", "pw"));
    const errorCall = calls.find((call) => call.level === "error");
    assert.ok(errorCall, "expected request.error log");
    const payload = errorCall.args[1] as Record<string, unknown>;
    assert.equal(typeof payload, "object");
    const errorPayload = payload.error as Record<string, unknown>;
    assert.equal(typeof errorPayload, "object");
    assert.equal(errorPayload.code, "bad.request");
    assert.equal(errorPayload.message, "bad request");
    assert.equal(errorPayload.status_code, 400);
    assert.equal(errorPayload.correlation_id, "corr-1");
    assert.equal(errorPayload.details, undefined);
  } finally {
    process.env.NEXT_PUBLIC_DEV_LOG_FRONTEND = originalEnv;
    globalThis.fetch = originalFetch;
    globalWithWindow.window = originalWindow;
    console.info = originalInfo;
    console.error = originalError;
  }
});
