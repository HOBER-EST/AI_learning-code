import type { CallNode } from "../types";

export const NODE_HEIGHT = 46;
export const LEVEL_GAP = 34;
export const SIBLING_GAP = 14;

export interface PositionedNode {
  node: CallNode;
  x: number; // left edge
  y: number; // top edge
  width: number;
}

export interface CallTreeLayout {
  nodes: PositionedNode[];
  byId: Map<string, PositionedNode>;
  width: number;
  height: number;
}

export function nodeWidth(node: CallNode): number {
  const longest = Math.max(node.label.length, (node.ret ?? "").length + 2);
  return Math.max(64, Math.min(220, longest * 7.4 + 22));
}

/**
 * Tidy top-down layout: each subtree gets a horizontal span wide enough for
 * its children side by side, and every parent is centered above its children.
 * The layout covers all calls (including future ones) so nodes never move
 * while stepping through the execution.
 */
export function layoutCallTree(calls: CallNode[]): CallTreeLayout {
  const ids = new Set(calls.map((c) => c.id));
  const children = new Map<string | null, CallNode[]>();
  for (const call of calls) {
    const key = call.parent && ids.has(call.parent) ? call.parent : null;
    if (!children.has(key)) children.set(key, []);
    children.get(key)!.push(call);
  }

  const span = new Map<string, number>();
  const measure = (node: CallNode): number => {
    const kids = children.get(node.id) ?? [];
    const kidsWidth = kids.reduce((sum, k) => sum + measure(k), 0) + SIBLING_GAP * Math.max(0, kids.length - 1);
    const w = Math.max(nodeWidth(node), kidsWidth);
    span.set(node.id, w);
    return w;
  };

  const nodes: PositionedNode[] = [];
  const place = (node: CallNode, left: number, depth: number): PositionedNode => {
    const total = span.get(node.id)!;
    const width = nodeWidth(node);
    const positioned: PositionedNode = { node, x: left + (total - width) / 2, y: depth * (NODE_HEIGHT + LEVEL_GAP), width };
    nodes.push(positioned);
    const kids = children.get(node.id) ?? [];
    const kidsWidth = kids.reduce((sum, k) => sum + span.get(k.id)!, 0) + SIBLING_GAP * Math.max(0, kids.length - 1);
    let x = left + (total - kidsWidth) / 2;
    const placed = kids.map((kid) => {
      const p = place(kid, x, depth + 1);
      x += span.get(kid.id)! + SIBLING_GAP;
      return p;
    });
    if (placed.length) {
      // Center the parent over its first and last child, within its span.
      const first = placed[0];
      const last = placed[placed.length - 1];
      const mid = (first.x + first.width / 2 + last.x + last.width / 2) / 2;
      positioned.x = Math.min(Math.max(mid - width / 2, left), left + total - width);
    }
    return positioned;
  };

  let left = 0;
  for (const root of children.get(null) ?? []) {
    const width = measure(root);
    place(root, left, 0);
    left += width + SIBLING_GAP * 2;
  }
  const byId = new Map(nodes.map((n) => [n.node.id, n]));
  const width = nodes.reduce((m, n) => Math.max(m, n.x + n.width), 0);
  const height = nodes.reduce((m, n) => Math.max(m, n.y + NODE_HEIGHT), 0);
  return { nodes, byId, width, height };
}

export type CallState = "hidden" | "active" | "current" | "returned" | "error";

export function callState(node: CallNode, stepIndex: number, currentFrame: string): CallState {
  if (node.call_step > stepIndex) return "hidden";
  if (node.id === currentFrame) return "current";
  if (node.return_step !== null && node.return_step <= stepIndex) {
    return node.status === "error" ? "error" : "returned";
  }
  return "active";
}

/** Whether the return value of a call is known at the given step. */
export function hasReturned(node: CallNode, stepIndex: number): boolean {
  return node.return_step !== null && node.return_step <= stepIndex;
}

export interface CallStats {
  total: number;
  maxDepth: number;
  duplicates: Map<string, number>; // label -> count, only labels seen more than once
}

export function callStats(calls: CallNode[]): CallStats {
  const counts = new Map<string, number>();
  let maxDepth = 0;
  for (const c of calls) {
    counts.set(c.label, (counts.get(c.label) ?? 0) + 1);
    maxDepth = Math.max(maxDepth, c.depth);
  }
  const duplicates = new Map([...counts].filter(([, n]) => n > 1));
  return { total: calls.length, maxDepth, duplicates };
}
