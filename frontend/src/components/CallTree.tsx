import { useEffect, useMemo, useRef, useState } from "react";
import { callState, callStats, hasReturned, layoutCallTree, NODE_HEIGHT } from "../lib/callTreeLayout";
import type { CallNode } from "../types";

const PAD = 16;

interface Props {
  calls: CallNode[];
  stepIndex: number;
  currentFrame: string;
  stackDepth: number;
  onJump: (step: number) => void;
}

export function CallTree({ calls, stepIndex, currentFrame, stackDepth, onJump }: Props) {
  const layout = useMemo(() => layoutCallTree(calls), [calls]);
  const stats = useMemo(() => callStats(calls), [calls]);
  const [zoom, setZoom] = useState(1);
  const [showFuture, setShowFuture] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  const visibleCount = calls.filter((c) => c.call_step <= stepIndex).length;
  const current = layout.byId.get(currentFrame);

  // Keep the current call in view while stepping.
  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap || !current) return;
    const cx = (current.x + current.width / 2 + PAD) * zoom;
    const cy = (current.y + PAD) * zoom;
    if (cx < wrap.scrollLeft + 40 || cx > wrap.scrollLeft + wrap.clientWidth - 40) {
      wrap.scrollLeft = cx - wrap.clientWidth / 2;
    }
    if (cy < wrap.scrollTop + 20 || cy > wrap.scrollTop + wrap.clientHeight - 60) {
      wrap.scrollTop = cy - wrap.clientHeight / 2;
    }
  }, [current, zoom]);

  if (calls.length === 0) {
    return (
      <div className="empty-state">
        这段程序没有调用任何函数。
        <br />
        在代码末尾加上一次调用（例如 <code>fact(4)</code>），或在“可视化调用”输入框里填写，再点击可视化。
      </div>
    );
  }

  const width = (layout.width + PAD * 2) * zoom;
  const height = (layout.height + PAD * 2) * zoom;

  return (
    <div className="call-tree" data-testid="call-tree">
      <div className="stats">
        <span className="stat">
          已发生调用 <b>{visibleCount}</b> / {stats.total}
        </span>
        <span className="stat">
          当前栈深度 <b>{Math.max(0, stackDepth)}</b>
        </span>
        <span className="stat">
          最大深度 <b>{stats.maxDepth}</b>
        </span>
        {stats.duplicates.size > 0 && (
          <span className="stat" title="同样的参数被重复计算——可以考虑记忆化（memoization）">
            重复子问题 <b>{stats.duplicates.size}</b> 种
          </span>
        )}
        <span className="header-spacer" />
        <label className="row" style={{ gap: 4 }}>
          <input type="checkbox" checked={showFuture} onChange={(e) => setShowFuture(e.target.checked)} />
          显示尚未发生的调用
        </label>
        <button className="small" onClick={() => setZoom((z) => Math.max(0.4, z - 0.15))} aria-label="缩小">
          −
        </button>
        <span className="mono">{Math.round(zoom * 100)}%</span>
        <button className="small" onClick={() => setZoom((z) => Math.min(1.8, z + 0.15))} aria-label="放大">
          +
        </button>
      </div>
      {stats.duplicates.size > 0 && (
        <div className="stats dup-list">
          <span className="muted">重复计算：</span>
          {[...stats.duplicates]
            .sort((a, b) => b[1] - a[1])
            .slice(0, 8)
            .map(([label, n]) => (
              <span key={label} className="badge warn mono">
                {label} ×{n}
              </span>
            ))}
        </div>
      )}
      <div className="call-tree-wrap" ref={wrapRef}>
        <svg width={width} height={height} viewBox={`0 0 ${layout.width + PAD * 2} ${layout.height + PAD * 2}`}>
          <g transform={`translate(${PAD},${PAD})`}>
            {layout.nodes.map(({ node, x, width: w, y }) => {
              const parent = node.parent ? layout.byId.get(node.parent) : undefined;
              if (!parent) return null;
              const visible = node.call_step <= stepIndex;
              if (!visible && !showFuture) return null;
              const px = parent.x + parent.width / 2;
              const py = parent.y + NODE_HEIGHT;
              const cx = x + w / 2;
              const midY = (py + y) / 2;
              return (
                <path
                  key={`e-${node.id}`}
                  className={`call-edge ${visible ? "visible" : ""}`}
                  d={`M${px},${py} C${px},${midY} ${cx},${midY} ${cx},${y}`}
                />
              );
            })}
            {layout.nodes.map(({ node, x, y, width: w }) => {
              const state = callState(node, stepIndex, currentFrame);
              if (state === "hidden" && !showFuture) return null;
              const dup = stats.duplicates.get(node.label);
              const showRet = hasReturned(node, stepIndex);
              const cls = ["call-node", state === "hidden" ? "future" : state].join(" ");
              return (
                <g
                  key={node.id}
                  className={cls}
                  transform={`translate(${x},${y})`}
                  onClick={() => onJump(node.call_step)}
                  data-testid="call-node"
                >
                  <title>
                    {`${node.id}: ${node.label}${showRet ? ` → ${node.ret}` : ""}${dup ? `\n这个调用共出现 ${dup} 次` : ""}\n点击跳转到这次调用`}
                  </title>
                  <rect width={w} height={NODE_HEIGHT} />
                  <text x={w / 2} y={showRet ? 18 : 27} textAnchor="middle">
                    {node.label}
                  </text>
                  {dup && (
                    <g className="dup-badge" transform={`translate(${w - 6},-6)`}>
                      <circle r={10} />
                      <text textAnchor="middle" y={4}>
                        ×{dup}
                      </text>
                    </g>
                  )}
                  {showRet && (
                    <text className="ret" x={w / 2} y={36} textAnchor="middle">
                      {node.status === "error" ? "⚠ 异常" : `→ ${node.ret}`}
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        </svg>
      </div>
    </div>
  );
}
