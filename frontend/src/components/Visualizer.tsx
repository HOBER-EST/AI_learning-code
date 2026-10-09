import { useCallback, useEffect, useMemo, useState } from "react";
import type { TraceResult } from "../types";
import { CallTree } from "./CallTree";
import { CodeView } from "./CodeView";
import { EnvironmentDiagram } from "./EnvironmentDiagram";

interface Props {
  trace: TraceResult;
  code: string;
  onClose?: () => void;
}

const SPEEDS = [
  { label: "慢", ms: 1100 },
  { label: "中", ms: 550 },
  { label: "快", ms: 200 },
];

function describe(trace: TraceResult, index: number): { event: string; detail: string } {
  const step = trace.steps[index];
  const call = trace.calls.find((c) => c.id === step.frame);
  if (step.exception) return { event: "⚠ 异常", detail: step.exception };
  switch (step.event) {
    case "call":
      return { event: "调用", detail: `${call?.label ?? step.frame}，创建新帧 ${step.frame}` };
    case "return": {
      if (step.frame === "Global") return { event: "结束", detail: "程序执行完毕" };
      const frame = step.frames.find((f) => f.id === step.frame);
      const ret = frame?.ret;
      const shown = ret?.t === "prim" ? ret.v : ret ? "一个对象（见箭头）" : "None";
      return { event: "返回", detail: `${call?.label ?? step.frame} 返回 ${shown}` };
    }
    default:
      return { event: "执行", detail: `即将执行第 ${step.line} 行${step.frame !== "Global" ? `（在 ${step.frame} 中）` : ""}` };
  }
}

export function Visualizer({ trace, code, onClose }: Props) {
  const total = trace.steps.length;
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [tab, setTab] = useState<"env" | "tree">(trace.calls.length > 1 ? "tree" : "env");
  const [showExited, setShowExited] = useState(true);

  useEffect(() => {
    setIndex(0);
    setPlaying(false);
  }, [trace]);

  const go = useCallback((i: number) => setIndex(Math.max(0, Math.min(total - 1, i))), [total]);

  useEffect(() => {
    if (!playing) return;
    if (index >= total - 1) {
      setPlaying(false);
      return;
    }
    const timer = setTimeout(() => setIndex((i) => i + 1), SPEEDS[speed].ms);
    return () => clearTimeout(timer);
  }, [playing, index, total, speed]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof Element && e.target.closest("input, textarea, select, .cm-editor")) return;
      if (e.key === "ArrowRight") {
        e.preventDefault();
        go(index + 1);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        go(index - 1);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, index]);

  const step = trace.steps[index];
  const prev = index > 0 ? trace.steps[index - 1] : undefined;
  const info = useMemo(() => (step ? describe(trace, index) : null), [trace, index, step]);

  if (!step) {
    return (
      <div className="card card-body">
        {trace.error ? (
          <div className="alert err">
            <b>{trace.error.type}</b>：{trace.error.message}
            {trace.error.line ? `（第 ${trace.error.line} 行）` : ""}
          </div>
        ) : (
          <div className="alert info">没有可以显示的执行步骤。</div>
        )}
        {onClose && (
          <button className="section-gap" onClick={onClose}>
            ← 返回编辑
          </button>
        )}
      </div>
    );
  }

  const atEnd = index === total - 1;

  return (
    <div className="viz" data-testid="visualizer">
      <div className="viz-left">
        <div className="card">
          <div className="row" style={{ padding: "10px 12px", borderBottom: "1px solid var(--border)" }}>
            <b>代码</b>
            <span className="legend">
              <span>
                <span className="marker-prev">➜</span> 刚执行的行
              </span>
              <span>
                <span className="marker-next">➜</span> 下一步要执行的行
              </span>
            </span>
            <span className="header-spacer" />
            {onClose && (
              <button className="small" onClick={onClose}>
                ← 返回编辑
              </button>
            )}
          </div>
          <CodeView
            code={code}
            nextLine={step.line}
            prevLine={prev?.line}
            errorLine={atEnd && trace.error ? trace.error.line : null}
          />
          <div className="step-controls" style={{ borderTop: "1px solid var(--border)" }}>
            <input
              type="range"
              min={0}
              max={total - 1}
              value={index}
              onChange={(e) => go(Number(e.target.value))}
              aria-label="执行步骤"
            />
            <div className="row">
              <button className="small" onClick={() => go(0)} disabled={index === 0} aria-label="第一步">
                ⏮
              </button>
              <button className="small" onClick={() => go(index - 1)} disabled={index === 0}>
                ◀ 上一步
              </button>
              <button className="small primary" onClick={() => go(index + 1)} disabled={atEnd}>
                下一步 ▶
              </button>
              <button className="small" onClick={() => go(total - 1)} disabled={atEnd} aria-label="最后一步">
                ⏭
              </button>
              <button
                className="small"
                onClick={() => {
                  if (atEnd) setIndex(0);
                  setPlaying((p) => !p);
                }}
              >
                {playing ? "⏸ 暂停" : "⏵ 自动播放"}
              </button>
              <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))} aria-label="播放速度">
                {SPEEDS.map((s, i) => (
                  <option key={s.label} value={i}>
                    {s.label}速
                  </option>
                ))}
              </select>
            </div>
            <div className="step-desc" data-testid="step-desc">
              <span className="badge accent">
                第 {index + 1} / {total} 步
              </span>{" "}
              <span className="event">{info?.event}</span> {info?.detail}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              提示：可以用键盘 ← → 逐步前进或后退。
            </div>
          </div>
        </div>
        <div className="card card-body">
          <b>程序输出</b>
          <div className="stdout" data-testid="stdout">
            {step.stdout || <span className="muted">（暂无输出）</span>}
          </div>
        </div>
        {atEnd && trace.truncated && (
          <div className="alert warn">
            已达到最大步数（{trace.max_steps}）。如果你的程序本应很快结束，很可能是<b>无限递归</b>：检查基本情况，以及每次递归参数是否在变小。
          </div>
        )}
        {atEnd && trace.error && (
          <div className="alert err">
            <b>{trace.error.type}</b>：{trace.error.message}
            {trace.error.line ? `（第 ${trace.error.line} 行）` : ""}
          </div>
        )}
      </div>

      <div className="card">
        <div className="tabs">
          <button className={tab === "env" ? "active" : ""} onClick={() => setTab("env")}>
            环境图 Environment Diagram
          </button>
          <button className={tab === "tree" ? "active" : ""} onClick={() => setTab("tree")}>
            递归调用树 ({trace.calls.length})
          </button>
        </div>
        {tab === "env" ? (
          <>
            <div className="diagram-options">
              <label>
                <input type="checkbox" checked={showExited} onChange={(e) => setShowExited(e.target.checked)} />
                显示已返回的帧（CS61A 风格）
              </label>
              <span>
                当前帧：<b className="mono">{step.frame === "Global" ? "Global" : step.frame}</b>
              </span>
              <span>
                调用栈：<span className="mono">{step.stack.join(" → ")}</span>
              </span>
            </div>
            <EnvironmentDiagram step={step} showExited={showExited} />
          </>
        ) : (
          <CallTree
            calls={trace.calls}
            stepIndex={index}
            currentFrame={step.frame}
            stackDepth={step.stack.length - 1}
            onJump={(i) => {
              setPlaying(false);
              go(i);
            }}
          />
        )}
      </div>
    </div>
  );
}
