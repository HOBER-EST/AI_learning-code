import { useEffect, useState } from "react";
import type { TestCase, TestResult } from "../types";

/** Grows from 0 to `pct` after mounting, so each new result visibly fills up. */
export function ProgressBar({ pct, style }: { pct: number; style?: React.CSSProperties }) {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const frame = requestAnimationFrame(() => setWidth(pct));
    return () => cancelAnimationFrame(frame);
  }, [pct]);
  return (
    <div className="progress-bar" aria-hidden="true" style={style}>
      <div style={{ width: `${width}%` }} />
    </div>
  );
}

const STATUS: Record<TestCase["status"], { text: string; cls: string }> = {
  passed: { text: "通过", cls: "ok" },
  failed: { text: "未通过", cls: "err" },
  error: { text: "出错", cls: "err" },
  timeout: { text: "超时", cls: "err" },
};

const ORIGIN: Record<TestCase["origin"], string> = {
  doctest: "文档测试",
  exercise: "练习测试",
  test_function: "test_ 函数",
  constraint: "代码要求",
};

interface Props {
  result: TestResult | null;
  onVisualize?: (source: string) => void;
}

export function TestResults({ result, onVisualize }: Props) {
  if (!result) {
    return <div className="empty-state">还没有运行测试。点击“运行测试”自动执行代码中的 doctest 和 test_ 函数。</div>;
  }
  if (result.sandbox_error) {
    return (
      <div className="alert err">
        <b>{result.sandbox_error.type}</b>：{result.sandbox_error.message}
      </div>
    );
  }
  if (result.load_error) {
    const e = result.load_error;
    return (
      <div className="alert err" data-testid="load-error">
        <div>
          代码无法加载：<b>{e.type}</b> {e.message}
          {e.line ? `（第 ${e.line} 行）` : ""}
        </div>
        {e.traceback && <pre style={{ marginTop: 8 }}>{e.traceback}</pre>}
      </div>
    );
  }
  const cases = result.results ?? [];
  const summary = result.summary ?? { passed: 0, failed: 0, total: 0 };
  if (cases.length === 0) {
    return (
      <div className="empty-state">
        没有找到测试。在函数的文档字符串里写 doctest（<code>&gt;&gt;&gt; f(1)</code> 下一行写期望输出），或定义 <code>test_</code> 开头的函数。
      </div>
    );
  }
  const pct = summary.total ? (summary.passed / summary.total) * 100 : 0;
  // Failing cases first, so the most useful information is on top.
  const ordered = [...cases].sort((a, b) => Number(a.status === "passed") - Number(b.status === "passed"));
  return (
    <div data-testid="test-results">
      <div className="results-summary">
        <span className={`badge ${summary.failed ? "err" : "ok"}`} data-testid="test-summary">
          {summary.passed} / {summary.total} 通过
        </span>
        <ProgressBar pct={pct} />
      </div>
      {result.solved && <div className="alert ok celebrate" style={{ marginBottom: 10 }}>🎉 全部测试通过，练习完成！</div>}
      {ordered.map((c, i) => (
        <div
          className={`test-case ${c.status}`}
          key={i}
          data-testid="test-case"
          style={{ animationDelay: `${Math.min(i, 12) * 45}ms` }}
        >
          <div className="head">
            <span className="source">
              {c.origin === "constraint" ? c.source : <>&gt;&gt;&gt; {c.source.split("\n").join("\n... ")}</>}
            </span>
            <span className="row" style={{ gap: 6 }}>
              <span className="muted" style={{ fontSize: 12 }}>
                {ORIGIN[c.origin]}
                {c.origin !== "exercise" && c.origin !== "constraint" ? ` · ${c.name}` : ""}
                {c.line ? ` · 第 ${c.line} 行` : ""}
              </span>
              <span className={`badge ${STATUS[c.status].cls}`}>{STATUS[c.status].text}</span>
              {onVisualize && c.status !== "passed" && c.origin !== "constraint" && c.origin !== "test_function" && (
                <button className="small" onClick={() => onVisualize(c.source)} title="把这个调用放到代码末尾并可视化">
                  🔍 可视化
                </button>
              )}
            </span>
          </div>
          {c.status !== "passed" && (
            <div className="diff">
              {c.origin !== "test_function" && (
                <>
                  <span className="label">期望</span>
                  <pre>{c.want || "（无输出）"}</pre>
                </>
              )}
              <span className="label">实际</span>
              <pre>{c.got || "（无输出，函数可能返回了 None）"}</pre>
            </div>
          )}
        </div>
      ))}
      {result.stdout && (
        <details className="section-gap">
          <summary className="muted">加载代码时的输出</summary>
          <pre className="stdout">{result.stdout}</pre>
        </details>
      )}
    </div>
  );
}
