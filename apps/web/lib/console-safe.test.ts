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
