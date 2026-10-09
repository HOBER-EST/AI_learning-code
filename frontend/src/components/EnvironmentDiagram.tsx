import { useMemo } from "react";
import { layoutHeap } from "../lib/heapLayout";
import type { Frame, Step, Value } from "../types";
import { Arrows } from "./Arrows";
import { ObjectView, ValueView } from "./HeapView";

interface FrameBoxProps {
  title: string;
  parent?: string;
  vars: [string, Value][];
  ret?: Value;
  raised?: boolean;
  status: "current" | "on-stack" | "exited" | "idle";
}

function FrameBox({ title, parent, vars, ret, raised, status }: FrameBoxProps) {
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
              <tr key={name}>
                <td className="name">{name}</td>
                <td className="val">
                  <ValueView value={value} highlight={highlight} />
                </td>
              </tr>
            ))}
            {ret !== undefined && (
              <tr className="ret">
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

export function EnvironmentDiagram({ step, showExited = true }: { step: Step; showExited?: boolean }) {
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
    <div className="env-diagram" data-testid="env-diagram">
      <div>
        <div className="env-column-title">帧 Frames</div>
        <div className="frames">
          <FrameBox title="Global frame" vars={step.globals} status={step.frame === "Global" ? "current" : "on-stack"} />
          {frames.map((f) => (
            <FrameBox
              key={f.id}
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
