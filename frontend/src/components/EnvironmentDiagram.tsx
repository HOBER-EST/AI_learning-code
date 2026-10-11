import { useLayoutEffect, useMemo, useRef } from "react";
import { layoutHeap } from "../lib/heapLayout";
import { EMPTY_DIFF, RETURN_NAME, varKey, type StepDiff } from "../lib/stepDiff";
import type { Frame, Step, Value } from "../types";
import { Arrows } from "./Arrows";
import { ObjectView, ValueView } from "./HeapView";

interface FrameBoxProps {
  id: string;
  title: string;
  parent?: string;
  vars: [string, Value][];
  ret?: Value;
  raised?: boolean;
  status: "current" | "on-stack" | "exited" | "idle";
}

function FrameBox({ id, title, parent, vars, ret, raised, status }: FrameBoxProps) {
  const highlight = status === "current";
  return (
    <div className={`frame ${status}`} data-testid="frame">
      <div className="frame-title">
        {title} {parent && <span className="parent">[parent={parent}]</span>}
      </div>
      {vars.length === 0 && ret === undefined && !raised ? (
        <div className="empty-note">（还没有绑定任何名字）</div>
      ) : (
        <table>
          <tbody>
            {vars.map(([name, value]) => (
              <tr key={name} data-var={varKey(id, name)}>
                <td className="name">{name}</td>
                <td className="val">
                  <ValueView value={value} highlight={highlight} />
                </td>
              </tr>
            ))}
            {ret !== undefined && (
              <tr className="ret" data-var={varKey(id, RETURN_NAME)}>
                <td className="name">Return value</td>
                <td className="val">
                  <ValueView value={ret} highlight={highlight} />
                </td>
              </tr>
            )}
            {raised && (
              <tr className="ret">
                <td className="name">抛出异常</td>
                <td className="val">⚠</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

const reduceMotion = () =>
  typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/** Briefly highlights what changed in this step (works even if it also changed in the last one). */
function useFlashChanges(root: React.RefObject<HTMLDivElement | null>, diff: StepDiff, step: Step) {
  useLayoutEffect(() => {
    const el = root.current;
    if (!el || reduceMotion()) return;
    const flash = getComputedStyle(document.documentElement).getPropertyValue("--flash").trim() || "#ffd84d";
    const animate = (target: Element, frames: Keyframe[]) => {
      if (typeof (target as HTMLElement).animate === "function") {
        (target as HTMLElement).animate(frames, { duration: 1100, easing: "ease-out" });
      }
    };
    el.querySelectorAll<HTMLElement>("[data-var]").forEach((row) => {
      if (!diff.vars.has(row.dataset.var!)) return;
      row.querySelectorAll("td").forEach((cell) =>
        animate(cell, [{ backgroundColor: flash }, { backgroundColor: "transparent" }]),
      );
    });
    el.querySelectorAll<HTMLElement>("[data-obj-id]").forEach((obj) => {
      if (diff.objects.has(obj.dataset.objId!)) {
        animate(obj, [{ boxShadow: `0 0 0 4px ${flash}` }, { boxShadow: "0 0 0 0 transparent" }]);
      }
    });
  }, [root, diff, step]);
}

export function EnvironmentDiagram({
  step,
  showExited = true,
  diff = EMPTY_DIFF,
}: {
  step: Step;
  showExited?: boolean;
  diff?: StepDiff;
}) {
  const rootRef = useRef<HTMLDivElement>(null);
  useFlashChanges(rootRef, diff, step);
  const layout = useMemo(() => layoutHeap(step, showExited), [step, showExited]);
  const ctx = useMemo(() => ({ heap: step.heap, claimedBy: layout.claimedBy }), [step.heap, layout]);
  // A new object per (step, option) tells the arrows to re-measure.
  const version = useMemo(() => ({ step, showExited }), [step, showExited]);
  const onStack = new Set(step.stack);
  const frames: Frame[] = showExited ? step.frames : step.frames.filter((f) => f.live);
  const statusOf = (id: string, live: boolean): FrameBoxProps["status"] => {
    if (id === step.frame) return "current";
    if (onStack.has(id)) return "on-stack";
    return live ? "idle" : "exited";
  };

  return (
    <div className="env-diagram" data-testid="env-diagram" ref={rootRef}>
      <div>
        <div className="env-column-title">帧 Frames</div>
        <div className="frames">
          <FrameBox id="Global" title="Global frame" vars={step.globals} status={step.frame === "Global" ? "current" : "on-stack"} />
          {frames.map((f) => (
            <FrameBox
              key={f.id}
              id={f.id}
              title={f.label}
              parent={f.parent}
              vars={f.vars}
              ret={f.ret}
              raised={f.raised}
              status={statusOf(f.id, f.live)}
            />
          ))}
        </div>
      </div>
      <div>
        <div className="env-column-title">对象 Objects</div>
        <div className="objects">
          {layout.roots.map((id) => (
            <ObjectView key={id} id={id} ctx={ctx} />
          ))}
          {layout.roots.length === 0 && <div className="muted">（暂无对象）</div>}
          {step.heap_truncated && <div className="muted">对象太多，只显示了一部分。</div>}
        </div>
      </div>
      <Arrows version={version} />
    </div>
  );
}
