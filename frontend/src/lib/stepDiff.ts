import type { Step, Value } from "../types";

/** What changed between two consecutive steps, so the diagram can flash it. */
export interface StepDiff {
  /** Keys like "Global:x", "f2:n" or "f2:#ret" (the return value). */
  vars: Set<string>;
  /** Heap object ids that are new or whose contents changed. */
  objects: Set<string>;
  /** Output printed during this step. */
  newOutput: string;
}

export const EMPTY_DIFF: StepDiff = { vars: new Set(), objects: new Set(), newOutput: "" };

export const varKey = (frame: string, name: string) => `${frame}:${name}`;
export const RETURN_NAME = "#ret";

function bindings(step: Step): Map<string, Value> {
  const map = new Map<string, Value>();
  for (const [name, value] of step.globals) map.set(varKey("Global", name), value);
  for (const frame of step.frames) {
    for (const [name, value] of frame.vars) map.set(varKey(frame.id, name), value);
    if (frame.ret) map.set(varKey(frame.id, RETURN_NAME), frame.ret);
  }
  return map;
}

export function diffSteps(prev: Step | undefined, cur: Step): StepDiff {
  if (!prev) return EMPTY_DIFF;
  const before = bindings(prev);
  const vars = new Set<string>();
  for (const [key, value] of bindings(cur)) {
    const old = before.get(key);
    if (!old || JSON.stringify(old) !== JSON.stringify(value)) vars.add(key);
  }
  const objects = new Set<string>();
  for (const [id, obj] of Object.entries(cur.heap)) {
    const old = prev.heap[id];
    if (!old || JSON.stringify(old) !== JSON.stringify(obj)) objects.add(id);
  }
  const newOutput = cur.stdout.startsWith(prev.stdout) ? cur.stdout.slice(prev.stdout.length) : "";
  return { vars, objects, newOutput };
}
