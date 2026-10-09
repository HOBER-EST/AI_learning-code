import type { HeapObject, Step, Value } from "../types";

/**
 * Decides how heap objects are grouped for drawing.
 *
 * Linked lists are drawn as one horizontal chain and trees as one nested
 * structure, so a Link node "claims" the node in its ``rest`` and a Tree node
 * claims its branches. Claimed objects are rendered inside their claimer;
 * the remaining objects become top-level blocks, ordered by when they are
 * first reached from the frames (Global first), like Python Tutor.
 */
export interface HeapLayout {
  /** Top-level object ids, in display order. */
  roots: string[];
  /** child id -> id of the object that draws it inline. */
  claimedBy: Map<string, string>;
}

function refs(obj: HeapObject): Value[] {
  switch (obj.t) {
    case "list":
    case "tuple":
    case "set":
      return obj.items;
    case "dict":
      return obj.items.flat();
    case "method":
      return [obj.func, obj.self];
    case "class":
    case "instance":
      return obj.attrs.map(([, v]) => v);
    case "link":
      return [obj.first, obj.rest];
    case "tree":
      return [obj.label, ...obj.branches];
    default:
      return [];
  }
}

function inlineChildren(obj: HeapObject): string[] {
  if (obj.t === "link" && obj.rest.t === "ref") return [obj.rest.id];
  if (obj.t === "tree") return obj.branches.flatMap((b) => (b.t === "ref" ? [b.id] : []));
  return [];
}

export function visitOrder(step: Pick<Step, "globals" | "frames" | "heap">, showExited = true): string[] {
  const order: string[] = [];
  const seen = new Set<string>();
  const queue: string[] = [];
  const push = (v: Value | undefined) => {
    if (v && v.t === "ref" && !seen.has(v.id) && step.heap[v.id]) {
      seen.add(v.id);
      queue.push(v.id);
    }
  };
  step.globals.forEach(([, v]) => push(v));
  for (const frame of step.frames) {
    if (!showExited && !frame.live) continue;
    frame.vars.forEach(([, v]) => push(v));
    push(frame.ret);
  }
  while (queue.length) {
    const id = queue.shift()!;
    order.push(id);
    refs(step.heap[id]).forEach(push);
  }
  return order;
}

export function layoutHeap(step: Pick<Step, "globals" | "frames" | "heap">, showExited = true): HeapLayout {
  const order = visitOrder(step, showExited);
  const claimedBy = new Map<string, string>();
  const sameKind = (a: HeapObject, b: HeapObject | undefined) => !!b && a.t === b.t;
  const isAncestor = (candidate: string, of: string) => {
    let cur: string | undefined = of;
    while (cur !== undefined) {
      if (cur === candidate) return true;
      cur = claimedBy.get(cur);
    }
    return false;
  };
  for (const id of order) {
    const obj = step.heap[id];
    for (const child of inlineChildren(obj)) {
      if (child === id || claimedBy.has(child) || !sameKind(obj, step.heap[child])) continue;
      if (isAncestor(child, id)) continue; // cycle: draw an arrow instead
      claimedBy.set(child, id);
    }
  }
  return { roots: order.filter((id) => !claimedBy.has(id)), claimedBy };
}
