import { describe, expect, it } from "vitest";
import type { Step } from "../types";
import { diffSteps, varKey } from "./stepDiff";

function step(partial: Partial<Step>): Step {
  return { event: "line", line: 1, frame: "Global", stack: ["Global"], globals: [], frames: [], heap: {}, stdout: "", ...partial };
}

describe("diffSteps", () => {
  it("reports nothing for the first step", () => {
    const d = diffSteps(undefined, step({ globals: [["x", { t: "prim", v: "1" }]] }));
    expect(d.vars.size + d.objects.size).toBe(0);
  });

  it("finds new and changed bindings, return values and objects", () => {
    const prev = step({
      globals: [
        ["x", { t: "prim", v: "1" }],
        ["lst", { t: "ref", id: "o1" }],
      ],
      frames: [{ id: "f1", label: "f1: f", name: "f", parent: "Global", vars: [["n", { t: "prim", v: "3" }]], live: true }],
      heap: { o1: { t: "list", items: [{ t: "prim", v: "1" }], len: 1 } },
      stdout: "a\n",
    });
    const cur = step({
      globals: [
        ["x", { t: "prim", v: "1" }],
        ["lst", { t: "ref", id: "o1" }],
        ["y", { t: "prim", v: "2" }],
      ],
      frames: [
        { id: "f1", label: "f1: f", name: "f", parent: "Global", vars: [["n", { t: "prim", v: "3" }]], live: false, ret: { t: "prim", v: "6" } },
      ],
      heap: {
        o1: { t: "list", items: [{ t: "prim", v: "1" }, { t: "prim", v: "2" }], len: 2 },
        o2: { t: "func", name: "g", params: "()", parent: "Global" },
      },
      stdout: "a\nb\n",
    });
    const d = diffSteps(prev, cur);
    expect([...d.vars].sort()).toEqual([varKey("Global", "y"), varKey("f1", "#ret")].sort());
    expect([...d.objects].sort()).toEqual(["o1", "o2"]);
    expect(d.newOutput).toBe("b\n");
  });
});
