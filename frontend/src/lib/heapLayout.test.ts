import { describe, expect, it } from "vitest";
import type { HeapObject, Step, Value } from "../types";
import { layoutHeap, visitOrder } from "./heapLayout";

const ref = (id: string): Value => ({ t: "ref", id });
const prim = (v: string): Value => ({ t: "prim", v });

function step(globals: [string, Value][], heap: Record<string, HeapObject>): Pick<Step, "globals" | "frames" | "heap"> {
  return { globals, frames: [], heap };
}

describe("layoutHeap", () => {
  it("draws a linked list as one chain", () => {
    const s = step([["s", ref("a")]], {
      a: { t: "link", first: prim("1"), rest: ref("b") },
      b: { t: "link", first: prim("2"), rest: ref("c") },
      c: { t: "link", first: prim("3"), rest: { t: "empty" } },
    });
    const layout = layoutHeap(s);
    expect(layout.roots).toEqual(["a"]);
    expect(layout.claimedBy.get("b")).toBe("a");
    expect(layout.claimedBy.get("c")).toBe("b");
  });

  it("keeps a node inline even if a variable points into the middle of the chain", () => {
    const s = step(
      [
        ["mid", ref("b")],
        ["head", ref("a")],
      ],
      {
        a: { t: "link", first: prim("1"), rest: ref("b") },
        b: { t: "link", first: prim("2"), rest: { t: "empty" } },
      },
    );
    expect(layoutHeap(s).roots).toEqual(["a"]);
  });

  it("does not loop forever on cyclic links", () => {
    const s = step([["s", ref("a")]], {
      a: { t: "link", first: prim("1"), rest: ref("b") },
      b: { t: "link", first: prim("2"), rest: ref("a") },
    });
    const layout = layoutHeap(s);
    expect(layout.roots).toEqual(["a"]);
    expect(layout.claimedBy.has("a")).toBe(false);
  });

  it("nests tree branches under their parent", () => {
    const s = step([["t", ref("r")]], {
      r: { t: "tree", label: prim("1"), branches: [ref("x"), ref("y")] },
      x: { t: "tree", label: prim("2"), branches: [] },
      y: { t: "tree", label: prim("3"), branches: [] },
    });
    const layout = layoutHeap(s);
    expect(layout.roots).toEqual(["r"]);
    expect(layout.claimedBy.get("x")).toBe("r");
  });

  it("orders objects by first reach, globals first, then frames", () => {
    const s: Pick<Step, "globals" | "frames" | "heap"> = {
      globals: [["f", ref("fn")]],
      frames: [{ id: "f1", label: "f1: g", name: "g", parent: "Global", vars: [["xs", ref("lst")]], live: true }],
      heap: {
        fn: { t: "func", name: "g", params: "(xs)", parent: "Global" },
        lst: { t: "list", items: [ref("inner")], len: 1 },
        inner: { t: "list", items: [prim("1")], len: 1 },
      },
    };
    expect(visitOrder(s)).toEqual(["fn", "lst", "inner"]);
    expect(visitOrder(s, false)).toEqual(["fn", "lst", "inner"]);
    expect(visitOrder({ ...s, frames: [{ ...s.frames[0], live: false }] }, false)).toEqual(["fn"]);
  });
});
