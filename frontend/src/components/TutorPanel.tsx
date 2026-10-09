import { useEffect, useState } from "react";
import { api } from "../api";
import type { Analysis, Finding, TestResult } from "../types";
import { Markdown } from "./Markdown";

interface Message {
  role: "user" | "tutor";
  text: string;
  source?: "claude" | "rules";
}

interface Props {
  code: string;
  testResults: TestResult | null;
  exerciseId?: string;
}

const LEVEL: Record<Finding["level"], string> = { error: "问题", warning: "注意", info: "提示" };

export function FindingList({ findings }: { findings: Finding[] }) {
  if (!findings.length) return <div className="alert ok">静态分析没有发现常见问题 👍</div>;
  return (
    <div data-testid="findings">
      {findings.map((f, i) => (
        <div className={`finding ${f.level}`} key={i}>
          <div className="title">
            {LEVEL[f.level]} · {f.title}
            {f.line ? <span className="muted" style={{ fontWeight: 400 }}>（第 {f.line} 行）</span> : null}
          </div>
          <div>{f.message}</div>
        </div>
      ))}
    </div>
  );
}

function FunctionSummary({ analysis }: { analysis: Analysis }) {
  const recursive = analysis.functions.filter((f) => f.recursive);
  if (!recursive.length) return null;
  return (
    <div className="row" style={{ marginBottom: 10 }}>
      {recursive.map((f) => (
        <span className="badge accent" key={`${f.name}-${f.line}`} title={f.has_base_case ? "检测到基本情况" : "没有检测到基本情况"}>
          {f.name}：{f.kind}
          {f.has_base_case ? " ✓ base case" : " ✗ base case"}
        </span>
      ))}
    </div>
  );
}

export function TutorPanel({ code, testResults, exerciseId }: Props) {
  const [analysis, setAnalysis] = useState<Analysis | null>(testResults?.analysis ?? null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (testResults?.analysis) setAnalysis(testResults.analysis);
  }, [testResults]);

  const refresh = async () => {
    setError(null);
    try {
      setAnalysis(await api.analyze(code, testResults));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const ask = async (q: string) => {
    setBusy(true);
    setError(null);
    setMessages((m) => [...m, { role: "user", text: q || "我的代码哪里有问题？" }]);
    setQuestion("");
    try {
      const reply = await api.tutor({ code, question: q, test_results: testResults, exercise_id: exerciseId });
      setMessages((m) => [...m, { role: "tutor", text: reply.notice ? `${reply.answer}\n\n> ${reply.notice}` : reply.answer, source: reply.source }]);
      setAnalysis({ functions: analysis?.functions ?? [], findings: reply.findings });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="tutor-panel">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
        <b>代码诊断</b>
        <button className="small" onClick={refresh}>
          重新分析当前代码
        </button>
      </div>
      {analysis ? (
        <>
          <FunctionSummary analysis={analysis} />
          <FindingList findings={analysis.findings} />
        </>
      ) : (
        <div className="muted" style={{ marginBottom: 10 }}>
          运行测试或点击“重新分析”后，这里会显示递归结构分析和常见错误提示。
        </div>
      )}

      <div className="section-gap">
        <b>向 AI 导师提问</b>
        <div className="chat section-gap">
          {messages.map((m, i) => (
            <div className={`chat-msg ${m.role}`} key={i}>
              <div className="who">{m.role === "user" ? "你" : m.source === "claude" ? "AI 导师（Claude）" : "AI 导师（离线规则）"}</div>
              {m.role === "tutor" ? <Markdown>{m.text}</Markdown> : <div>{m.text}</div>}
            </div>
          ))}
          {busy && (
            <div className="chat-msg tutor row">
              <span className="spinner" /> 导师正在思考…
            </div>
          )}
        </div>
        {error && <div className="alert err section-gap">{error}</div>}
        <form
          className="row section-gap"
          onSubmit={(e) => {
            e.preventDefault();
            void ask(question.trim());
          }}
        >
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="例如：为什么我的递归停不下来？"
            style={{ flex: 1, minWidth: 180 }}
            aria-label="向 AI 导师提问"
          />
          <button className="primary" type="submit" disabled={busy}>
            提问
          </button>
          <button type="button" disabled={busy} onClick={() => void ask("")}>
            帮我看看哪里错了
          </button>
        </form>
      </div>
    </div>
  );
}
