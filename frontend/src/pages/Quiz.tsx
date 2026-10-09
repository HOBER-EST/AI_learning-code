import { useEffect, useState } from "react";
import { api } from "../api";
import { load, save } from "../lib/storage";
import type { Quiz as QuizItem, QuizCheck, Topic } from "../types";
import { TOPIC_ICON } from "./Exercises";
import { INCOMING_KEY } from "./Lab";

const FILTERS: { id: "all" | Topic; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "recursion", label: `${TOPIC_ICON.recursion} 递归` },
  { id: "link", label: `${TOPIC_ICON.link} 链表` },
  { id: "tree", label: `${TOPIC_ICON.tree} 树` },
];

const CORRECT_KEY = "learn61a:quiz-correct";

function QuizCard({ quiz, onCorrect }: { quiz: QuizItem; onCorrect: (id: string) => void }) {
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<QuizCheck | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const check = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await api.checkQuiz(quiz.id, answer);
      setResult(r);
      if (r.correct) onCorrect(quiz.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card quiz-card" data-testid="quiz-card">
      <div className="quiz-code">
        {quiz.setup}
        {"\n"}
        <b>&gt;&gt;&gt; {quiz.expression}</b>
      </div>
      <textarea
        rows={Math.max(1, answer.split("\n").length)}
        value={answer}
        onChange={(e) => {
          setAnswer(e.target.value);
          setResult(null);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) void check();
        }}
        placeholder="Python 会显示什么？（多行输出逐行填写；出错填 Error）"
        aria-label="你的答案"
      />
      <div className="row">
        <button className="primary small" onClick={check} disabled={busy || !answer.trim()}>
          检查答案
        </button>
        <button
          className="small ghost"
          onClick={() => {
            save(INCOMING_KEY, `${quiz.setup}\n${quiz.expression}\n`);
            window.location.hash = "#/lab";
          }}
        >
          在实验室中可视化
        </button>
      </div>
      {error && <div className="alert err">{error}</div>}
      {result && (
        <div className={`alert ${result.correct ? "ok" : "err"}`} data-testid="quiz-feedback">
          <b>{result.correct ? "✓ 正确！" : "✗ 不对哦"}</b>
          {!result.correct && (
            <div>
              正确答案：
              <pre className="mono">{result.answer}</pre>
            </div>
          )}
          <div style={{ color: "var(--text)", marginTop: 4 }}>{result.explanation}</div>
        </div>
      )}
    </div>
  );
}

export function Quiz() {
  const [items, setItems] = useState<QuizItem[] | null>(null);
  const [filter, setFilter] = useState<"all" | Topic>("all");
  const [correct, setCorrect] = useState<Set<string>>(() => new Set(load<string[]>(CORRECT_KEY, [])));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.quizzes().then(setItems).catch((e) => setError((e as Error).message));
  }, []);

  const onCorrect = (id: string) => {
    setCorrect((prev) => {
      const next = new Set(prev).add(id);
      save(CORRECT_KEY, [...next]);
      return next;
    });
  };

  if (error) return <div className="page"><div className="alert err">{error}</div></div>;
  if (!items) return <div className="page"><div className="empty-state">加载中…</div></div>;
  const shown = items.filter((q) => filter === "all" || q.topic === filter);

  return (
    <div className="page">
      <div className="hero">
        <div>
          <h1>What Would Python Display?</h1>
          <p className="muted">
            CS61A 经典题型：预测交互式解释器的输出。出错填 <code>Error</code>，函数值填 <code>Function</code>，多行输出逐行填写。
          </p>
        </div>
        <span className="badge ok">
          已答对 {correct.size} / {items.length}
        </span>
      </div>
      <div className="row" style={{ marginBottom: 14 }}>
        {FILTERS.map((f) => (
          <button key={f.id} className={`small ${filter === f.id ? "primary" : ""}`} onClick={() => setFilter(f.id)}>
            {f.label}
          </button>
        ))}
      </div>
      <div className="quiz-grid">
        {shown.map((q) => (
          <QuizCard key={q.id} quiz={q} onCorrect={onCorrect} />
        ))}
      </div>
    </div>
  );
}
