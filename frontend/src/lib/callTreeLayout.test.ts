import { describe, expect, it } from "vitest";
import type { CallNode } from "../types";
import { callState, callStats, layoutCallTree, NODE_HEIGHT } from "./callTreeLayout";

function call(id: string, label: string, parent: string | null, depth: number, call_step: number, return_step: number | null): CallNode {
  return { id, name: label.split("(")[0], label, parent, depth, call_step, return_step, ret: "1", status: "returned" };
}

// fib(3) -> fib(2) -> fib(1), fib(0); fib(3) -> fib(1)
const calls = [
  call("f1", "fib(3)", null, 1, 0, 20),
  call("f2", "fib(2)", "f1", 2, 2, 12),
  call("f3", "fib(1)", "f2", 3, 4, 6),
  call("f4", "fib(0)", "f2", 3, 8, 10),
  call("f5", "fib(1)", "f1", 2, 14, 17),
];

describe("layoutCallTree", () => {
  const layout = layoutCallTree(calls);
  const pos = (id: string) => layout.byId.get(id)!;
  const center = (id: string) => pos(id).x + pos(id).width / 2;

  it("puts each depth on its own row", () => {
    expect(pos("f1").y).toBe(0);
    expect(pos("f2").y).toBe(pos("f5").y);
    expect(pos("f3").y).toBeGreaterThan(pos("f2").y + NODE_HEIGHT);
  });

  it("centers parents over their children", () => {
    expect(center("f2")).toBeCloseTo((center("f3") + center("f4")) / 2);
    expect(center("f1")).toBeCloseTo((center("f2") + center("f5")) / 2);
  });

  it("never overlaps nodes on the same row", () => {
    const rows = new Map<number, { x: number; width: number }[]>();
    for (const n of layout.nodes) rows.set(n.y, [...(rows.get(n.y) ?? []), n]);
    for (const row of rows.values()) {
      row.sort((a, b) => a.x - b.x);
      for (let i = 1; i < row.length; i++) expect(row[i].x).toBeGreaterThanOrEqual(row[i - 1].x + row[i - 1].width);
    }
    expect(layout.width).toBeGreaterThan(0);
  });
});

describe("callState", () => {
  it("tracks a call through its lifetime", () => {
    const node = calls[2]; // f3: steps 4..6
    expect(callState(node, 3, "f2")).toBe("hidden");
    expect(callState(node, 4, "f3")).toBe("current");
    expect(callState(node, 5, "f2")).toBe("active");
    expect(callState(node, 7, "f2")).toBe("returned");
    expect(callState({ ...node, status: "error" }, 7, "f2")).toBe("error");
  });
});

describe("callStats", () => {
  it("counts calls, depth and repeated subproblems", () => {
    const stats = callStats(calls);
    expect(stats.total).toBe(5);
    expect(stats.maxDepth).toBe(3);
    expect([...stats.duplicates]).toEqual([["fib(1)", 2]]);
  });
});
