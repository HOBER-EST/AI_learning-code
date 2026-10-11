import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { CodeEditor } from "../components/CodeEditor";
import { Confetti } from "../components/Confetti";
import { ExplainPanel, selectionLabel, type Selection } from "../components/ExplainPanel";
import { Skeleton } from "../components/Skeleton";
import { useToast } from "../components/Toast";
import { Markdown } from "../components/Markdown";
import { TestResults } from "../components/TestResults";
import { TutorPanel } from "../components/TutorPanel";
import { Visualizer } from "../components/Visualizer";
import { withTraceCall } from "../lib/code";
import { formatDuration, MOD, testToast, timed, useRunShortcuts } from "../lib/feedback";
import { load, markSolved, save, solvedExercises } from "../lib/storage";
import type { ExerciseDetail, TestResult, TraceResult } from "../types";
import { Difficulty, TOPIC_ICON } from "./Exercises";

const CONSTRAINT_TEXT: Record<string, string> = {
  recursive: "必须使用递归",
  no_loops: "不能使用 for / while 循环",
};

type Busy = null | "test" | "submit" | "trace";

export function ExerciseWorkspace({ id }: { id: string }) {
  const [ex, setEx] = useState<ExerciseDetail | null>(null);
  const [code, setCode] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<Busy>(null);
  const [result, setResult] = useState<TestResult | null>(null);
  const [tab, setTab] = useState<"tests" | "explain" | "tutor">("tests");
  const [selection, setSelection] = useState<Selection | null>(null);
  const [explainToken, setExplainToken] = useState(0);
  const [hints, setHints] = useState(0);
  const [solution, setSolution] = useState<string | null>(null);
  const [traceCall, setTraceCall] = useState("");
  const [trace, setTrace] = useState<{ result: TraceResult; code: string } | null>(null);
  const [mode, setMode] = useState<"edit" | "viz">("edit");
  const [version, setVersion] = useState(0);
  const [celebrate, setCelebrate] = useState(0);
  const notify = useToast();
  const draftKey = `learn61a:exercise:${id}`;
  // Keyboard shortcuts are registered before the early returns below (hook
  // order), and call whatever the latest actions are.
  const actions = useRef({ submit: () => {}, visualize: () => {} });
  useRunShortcuts(
    () => actions.current.submit(),
    () => actions.current.visualize(),
    mode === "edit",
  );

  useEffect(() => {
    if (!celebrate) return;
    const timer = setTimeout(() => setCelebrate(0), 1800);
    return () => clearTimeout(timer);
  }, [celebrate]);

  useEffect(() => {
    setEx(null);
    setResult(null);
    setHints(0);
    setSolution(null);
    setMode("edit");
    api
      .exercise(id)
      .then((detail) => {
        setEx(detail);
        setCode(load(draftKey, detail.starter));
        setTraceCall(detail.trace);
      })
      .catch((e) => setLoadError((e as Error).message));
  }, [id, draftKey]);

  useEffect(() => {
    if (ex?.id === id) save(draftKey, code);
  }, [code, ex, id, draftKey]);

  if (loadError) return <div className="page"><div className="alert err">{loadError}</div></div>;
  if (!ex)
    return (
      <div className="page">
        <div className="workspace">
          <Skeleton lines={8} card />
          <Skeleton lines={12} card />
        </div>
      </div>
    );

  const guard = async (kind: Busy, fn: () => Promise<void>) => {
    setBusy(kind);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
      notify((e as Error).message, "error");
    } finally {
      setBusy(null);
    }
  };

  const runVisible = () =>
    busy === null &&
    guard("test", async () => {
      const [res, ms] = await timed(() => api.test(code));
      setResult(res);
      setVersion((v) => v + 1);
      setTab("tests");
      notify(...testToast(res, ms));
    });

  const submit = () =>
    busy === null &&
    guard("submit", async () => {
      const firstSolve = !solvedExercises().has(ex.id);
      const [res, ms] = await timed(() => api.submit(ex.id, code));
      setResult(res);
      setVersion((v) => v + 1);
      setTab("tests");
      if (res.solved) {
        markSolved(ex.id);
        setCelebrate((c) => c + 1);
        notify(firstSolve ? `🎉 练习完成：${ex.title}` : "再次全部通过 ✓", "success");
      } else {
        notify(...testToast(res, ms));
      }
    });

  const visualize = (call: string) =>
    busy === null &&
    guard("trace", async () => {
      const traced = withTraceCall(code, call);
      const [res, ms] = await timed(() => api.trace(traced));
      if (res.sandbox_error) {
        setError(res.sandbox_error.message);
        notify(res.sandbox_error.message, "error");
        return;
      }
      notify(`已记录 ${res.steps.length} 步、${res.calls.length} 次调用 · ${formatDuration(ms)}`, "success");
      setTrace({ result: res, code: traced });
      setMode("viz");
      window.scrollTo({ top: 0 });
    });

  actions.current = { submit, visualize: () => visualize(traceCall) };

  if (mode === "viz" && trace) {
    return (
      <div className="page">
        <div className="row" style={{ marginBottom: 12 }}>
          <a href="#/exercises">练习</a>
          <span className="muted">/</span>
          <b>{ex.title}</b>
          <span className="muted">· 可视化</span>
        </div>
        <Visualizer trace={trace.result} code={trace.code} onClose={() => setMode("edit")} />
      </div>
    );
  }

  return (
    <div className="page">
      {celebrate > 0 && <Confetti key={celebrate} />}
      <div className="row" style={{ marginBottom: 12 }}>
        <a href="#/exercises">← 全部练习</a>
      </div>
      <div className="workspace">
        <div className="card card-body" data-testid="exercise-description">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <h1 style={{ margin: 0 }}>
              {TOPIC_ICON[ex.topic]} {ex.title}
            </h1>
            <Difficulty level={ex.difficulty} />
          </div>
          <div className="row section-gap">
            {ex.concepts.map((c) => (
              <span className="badge" key={c}>
                {c}
              </span>
            ))}
            <span className="badge accent">隐藏测试 {ex.hidden_test_count} 组</span>
          </div>
          <div className="section-gap">
            <Markdown>{ex.description}</Markdown>
          </div>
          {ex.constraints.length > 0 && (
            <div className="alert info section-gap">
              <b>代码要求：</b>
              {ex.constraints.map((c) => CONSTRAINT_TEXT[c.type] ?? c.type).join("；")}
            </div>
          )}

          <div className="section-gap">
            <div className="row" style={{ justifyContent: "space-between", marginBottom: 6 }}>
              <b>提示</b>
              <button className="small" onClick={() => setHints((h) => Math.min(ex.hints.length, h + 1))} disabled={hints >= ex.hints.length}>
                💡 {hints === 0 ? "给我一个提示" : hints < ex.hints.length ? "下一个提示" : "没有更多提示了"}（{hints}/{ex.hints.length}）
              </button>
            </div>
            {ex.hints.slice(0, hints).map((h, i) => (
              <div className="hint" key={i}>
                提示 {i + 1}：{h}
              </div>
            ))}
          </div>

          <div className="section-gap">
            {solution ? (
              <>
                <b>参考答案</b>
                <pre className="quiz-code section-gap">{solution}</pre>
              </>
            ) : (
              <button
                className="small ghost"
                onClick={async () => {
                  if (!window.confirm("确定要查看参考答案吗？建议先尝试提示和可视化。")) return;
                  try {
                    setSolution((await api.solution(ex.id)).solution);
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                🔑 查看参考答案
              </button>
            )}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16, minWidth: 0 }}>
          <div className="card card-body">
            <div className="toolbar">
              <button onClick={runVisible} disabled={busy !== null} className={busy === "test" ? "busy" : ""}>
                {busy === "test" && <span className="spinner" />}
                {busy === "test" ? "测试中…" : "✓ 运行示例测试"}
              </button>
              <button
                className={`primary ${busy === "submit" ? "busy" : ""}`}
                onClick={submit}
                disabled={busy !== null}
                data-testid="submit"
                title={`提交（${MOD}+Enter）`}
              >
                {busy === "submit" && <span className="spinner" />}
                {busy === "submit" ? "评测中…" : "🚀 提交（含隐藏测试）"}
              </button>
              <span className="grow" />
              <button
                className="ghost"
                onClick={() => {
                  if (window.confirm("重置为初始代码？你当前的代码会丢失。")) setCode(ex.starter);
                }}
              >
                ↺ 重置
              </button>
            </div>
            <CodeEditor value={code} onChange={setCode} height="380px" running={busy !== null} onSelectionChange={setSelection} />
            <div className="toolbar section-gap">
              <label className="trace-call" style={{ flex: 1 }}>
                <span className="muted">可视化调用</span>
                <input type="text" value={traceCall} onChange={(e) => setTraceCall(e.target.value)} style={{ flex: 1 }} aria-label="可视化调用" />
              </label>
              <button
                onClick={() => {
                  setTab("explain");
                  setExplainToken((t) => t + 1);
                }}
                title="讲解代码；在编辑器里选中几行则只讲解选中部分"
              >
                {selectionLabel(selection)}
              </button>
              <button
                onClick={() => visualize(traceCall)}
                disabled={busy !== null}
                className={busy === "trace" ? "busy" : ""}
                title={`可视化（${MOD}+Shift+Enter）`}
              >
                {busy === "trace" && <span className="spinner" />}
                {busy === "trace" ? "正在追踪…" : "🔍 可视化"}
              </button>
            </div>
            {error && <div className="alert err">{error}</div>}
            <div className="status-line">
              <span className={`status-dot ${busy ? "busy" : result ? (result.ok ? "ok" : "err") : ""}`} />
              <span>
                {busy
                  ? "正在运行…"
                  : result?.summary
                    ? `上次结果：${result.summary.passed} / ${result.summary.total} 通过`
                    : "还没有运行过测试"}
              </span>
              <span className="header-spacer" />
              <span>
                <kbd>{MOD}</kbd>+<kbd>Enter</kbd> 提交 · <kbd>{MOD}</kbd>+<kbd>Shift</kbd>+<kbd>Enter</kbd> 可视化
              </span>
            </div>
          </div>

          <div className="card">
            <div className="tabs">
              <button className={tab === "tests" ? "active" : ""} onClick={() => setTab("tests")}>
                测试结果
                {result?.summary && (
                  <span className={`badge ${result.summary.failed ? "err" : "ok"}`} style={{ marginLeft: 6 }}>
                    {result.summary.passed}/{result.summary.total}
                  </span>
                )}
              </button>
              <button className={tab === "explain" ? "active" : ""} onClick={() => setTab("explain")}>
                讲解
              </button>
              <button className={tab === "tutor" ? "active" : ""} onClick={() => setTab("tutor")}>
                AI 导师
              </button>
            </div>
            <div className="card-body panel-enter" key={tab} hidden={tab === "explain"}>
              {tab === "tests" && <TestResults key={version} result={result} onVisualize={(src) => visualize(src)} />}
              {tab === "tutor" && <TutorPanel code={code} testResults={result} exerciseId={ex.id} />}
            </div>
            {/* Always mounted: keeps the explanation while other tabs are open. */}
            <div className="card-body" hidden={tab !== "explain"}>
              <ExplainPanel code={code} selection={selection} call={traceCall} exerciseId={ex.id} startToken={explainToken} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
