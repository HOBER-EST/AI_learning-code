import { useEffect, useState } from "react";
import { api } from "../api";
import { CodeEditor } from "../components/CodeEditor";
import { TestResults } from "../components/TestResults";
import { TutorPanel } from "../components/TutorPanel";
import { UploadButton } from "../components/UploadButton";
import { Visualizer } from "../components/Visualizer";
import { firstDoctestCall, hasTopLevelStatements, withTraceCall } from "../lib/code";
import { EXAMPLES } from "../lib/examples";
import { load, remove, save } from "../lib/storage";
import type { RunResult, TestResult, TraceResult } from "../types";

const CODE_KEY = "learn61a:lab-code";
export const INCOMING_KEY = "learn61a:lab-incoming";

type Busy = null | "run" | "test" | "trace" | "upload";
type Tab = "output" | "tests" | "tutor";

function Spinner({ on }: { on: boolean }) {
  return on ? <span className="spinner" /> : null;
}

export function Lab() {
  // Code sent from another page (e.g. a WWPD question) wins over the draft.
  const [code, setCode] = useState<string>(() => load<string | null>(INCOMING_KEY, null) ?? load(CODE_KEY, EXAMPLES[0].code));
  useEffect(() => remove(INCOMING_KEY), []);
  const [traceCall, setTraceCall] = useState("");
  const [busy, setBusy] = useState<Busy>(null);
  const [run, setRun] = useState<RunResult | null>(null);
  const [tests, setTests] = useState<TestResult | null>(null);
  const [trace, setTrace] = useState<{ result: TraceResult; code: string } | null>(null);
  const [tab, setTab] = useState<Tab>("output");
  const [mode, setMode] = useState<"edit" | "viz">("edit");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => save(CODE_KEY, code), [code]);

  const suggestion = firstDoctestCall(code);
  const autoCall = !hasTopLevelStatements(code) && suggestion ? suggestion : "";

  const guard = async (kind: Busy, fn: () => Promise<void>) => {
    setBusy(kind);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const doRun = () =>
    guard("run", async () => {
      setRun(await api.run(code));
      setTab("output");
    });

  const doTest = () =>
    guard("test", async () => {
      setTests(await api.test(code));
      setTab("tests");
    });

  const doTrace = (call: string) =>
    guard("trace", async () => {
      const traced = withTraceCall(code, call);
      const result = await api.trace(traced);
      if (result.sandbox_error) {
        setError(result.sandbox_error.message);
        return;
      }
      setTrace({ result, code: traced });
      setMode("viz");
      window.scrollTo({ top: 0 });
    });

  const doUpload = (file: File) =>
    guard("upload", async () => {
      const res = await api.upload(file);
      setCode(res.code);
      setTraceCall("");
      if (!res.syntax.ok) {
        setError(`语法错误（第 ${res.syntax.line} 行）：${res.syntax.message}`);
        setTests(null);
        return;
      }
      setNotice(
        `已上传 ${res.filename}` +
          (res.functions.length ? `，包含函数：${res.functions.join("、")}` : "") +
          (res.tests ? `。已自动运行测试：${res.tests.summary?.passed ?? 0} / ${res.tests.summary?.total ?? 0} 通过` : ""),
      );
      if (res.tests) {
        setTests(res.tests);
        setTab("tests");
      }
    });

  if (mode === "viz" && trace) {
    return (
      <div className="page">
        <Visualizer trace={trace.result} code={trace.code} onClose={() => setMode("edit")} />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="hero">
        <div>
          <h1>代码实验室</h1>
          <p className="muted">编写或上传 Python 代码，运行 doctest，并逐步可视化递归调用与环境图。Link、Tree 和 tree ADT 已内置可直接使用。</p>
        </div>
      </div>
      {error && (
        <div className="alert err" style={{ marginBottom: 12 }} role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="alert ok row" style={{ marginBottom: 12, justifyContent: "space-between" }}>
          <span data-testid="upload-notice">{notice}</span>
          <button className="small ghost" onClick={() => setNotice(null)} aria-label="关闭提示">
            ✕
          </button>
        </div>
      )}
      <div className="grid-2">
        <div className="card card-body">
          <div className="toolbar">
            <select
              aria-label="载入示例"
              value=""
              onChange={(e) => {
                const ex = EXAMPLES.find((x) => x.id === e.target.value);
                if (ex) {
                  setCode(ex.code);
                  setTraceCall("");
                  setTests(null);
                  setRun(null);
                }
              }}
            >
              <option value="">📚 载入示例…</option>
              {EXAMPLES.map((ex) => (
                <option key={ex.id} value={ex.id}>
                  {ex.title}
                </option>
              ))}
            </select>
            <UploadButton onFile={doUpload} disabled={busy !== null} />
            <span className="grow" />
            <button onClick={doRun} disabled={busy !== null}>
              <Spinner on={busy === "run"} />▶ 运行
            </button>
            <button onClick={doTest} disabled={busy !== null}>
              <Spinner on={busy === "test"} />✓ 运行测试
            </button>
          </div>
          <CodeEditor value={code} onChange={setCode} onDropFile={doUpload} height="460px" />
          <div className="toolbar section-gap">
            <label className="trace-call">
              <span className="muted">可视化调用</span>
              <input
                type="text"
                value={traceCall}
                onChange={(e) => setTraceCall(e.target.value)}
                placeholder={autoCall ? `${autoCall}（自动）` : "例如 fact(4)，可留空"}
                aria-label="可视化调用"
              />
            </label>
            <button className="primary" onClick={() => doTrace(traceCall || autoCall)} disabled={busy !== null}>
              <Spinner on={busy === "trace"} />
              🔍 可视化执行
            </button>
          </div>
          <div className="muted" style={{ fontSize: 13 }}>
            可视化会把“可视化调用”中的表达式追加到代码末尾执行；如果代码末尾已经有调用，可以留空。
          </div>
        </div>

        <div className="card">
          <div className="tabs">
            <button className={tab === "output" ? "active" : ""} onClick={() => setTab("output")}>
              输出
            </button>
            <button className={tab === "tests" ? "active" : ""} onClick={() => setTab("tests")}>
              测试结果
              {tests?.summary && (
                <span className={`badge ${tests.summary.failed ? "err" : "ok"}`} style={{ marginLeft: 6 }}>
                  {tests.summary.passed}/{tests.summary.total}
                </span>
              )}
            </button>
            <button className={tab === "tutor" ? "active" : ""} onClick={() => setTab("tutor")}>
              AI 导师
            </button>
          </div>
          <div className="card-body">
            {tab === "output" && <RunOutput run={run} />}
            {tab === "tests" && <TestResults result={tests} onVisualize={(src) => doTrace(src)} />}
            {tab === "tutor" && <TutorPanel code={code} testResults={tests} />}
          </div>
        </div>
      </div>
    </div>
  );
}

function RunOutput({ run }: { run: RunResult | null }) {
  if (!run) return <div className="empty-state">点击“运行”执行整个程序，输出会显示在这里。</div>;
  if (run.sandbox_error) return <div className="alert err">{run.sandbox_error.message}</div>;
  return (
    <div data-testid="run-output">
      <pre className="stdout">{run.stdout || "（程序没有输出）"}</pre>
      {run.error && (
        <div className="alert err section-gap">
          <pre>{run.error.traceback || `${run.error.type}: ${run.error.message}`}</pre>
        </div>
      )}
      {!run.error && <div className="muted section-gap">✓ 程序正常结束</div>}
    </div>
  );
}
