import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { ExplainEvent } from "../types";
import { Markdown } from "./Markdown";
import { useToast } from "./Toast";

export interface Selection {
  text: string;
  /** 1-based line number where the selection starts. */
  line: number;
  lines: number;
}

interface Props {
  code: string;
  selection: Selection | null;
  /** The example call to run so the explanation can describe real execution. */
  call?: string;
  exerciseId?: string;
  /** Changing this starts a new explanation (e.g. from a toolbar button). */
  startToken?: number;
}

const SUGGESTIONS = ["用一个具体例子一步步走一遍", "基本情况为什么这样写？", "这个函数的时间复杂度是多少？", "哪里可能出错？"];

type Status = "idle" | "streaming" | "done" | "error";

export function selectionLabel(selection: Selection | null): string {
  if (!selection) return "📖 讲解全部代码";
  const end = selection.line + selection.lines - 1;
  return selection.lines === 1 ? `📖 讲解第 ${selection.line} 行` : `📖 讲解选中的第 ${selection.line}–${end} 行`;
}

export function ExplainPanel({ code, selection, call, exerciseId, startToken = 0 }: Props) {
  const [text, setText] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [source, setSource] = useState<{ source: string; model?: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [asked, setAsked] = useState<{ question: string; scope: string } | null>(null);
  const abort = useRef<AbortController | null>(null);
  const notify = useToast();

  const start = async (q = "") => {
    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;
    setText("");
    setError(null);
    setSource(null);
    setStatus("streaming");
    setAsked({ question: q, scope: selectionLabel(selection).replace("📖 讲解", "") });
    const onEvent = (event: ExplainEvent) => {
      if (event.type === "meta") setSource({ source: event.source, model: event.model });
      else if (event.type === "delta") setText((t) => t + event.text);
      else if (event.type === "done") setStatus("done");
      else if (event.type === "error") {
        setError(event.message);
        setStatus("error");
        notify(event.message, "error");
      }
    };
    try {
      await api.explain(
        {
          code,
          selection: selection?.text ?? null,
          selection_line: selection?.line ?? 1,
          question: q,
          call: call || null,
          exercise_id: exerciseId,
        },
        onEvent,
        controller.signal,
      );
      setStatus((s) => (s === "streaming" ? "done" : s));
    } catch (e) {
      if ((e as Error).name === "AbortError") {
        setStatus("done");
        return;
      }
      setError((e as Error).message);
      setStatus("error");
      notify((e as Error).message, "error");
    }
  };

  // Started from outside (toolbar button / shortcut).
  const lastToken = useRef(startToken);
  useEffect(() => {
    if (startToken !== lastToken.current) {
      lastToken.current = startToken;
      void start();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startToken]);

  useEffect(() => () => abort.current?.abort(), []);

  const streaming = status === "streaming";
  const sourceLabel = source?.source === "claude" ? `Claude · ${source.model ?? ""}` : source ? "离线讲解" : null;

  return (
    <div data-testid="explain-panel">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
        <div className="row">
          <button className="primary" onClick={() => void start()} disabled={streaming}>
            {streaming && <span className="spinner" />}
            {streaming ? "讲解中…" : selectionLabel(selection)}
          </button>
          {streaming && (
            <button className="small" onClick={() => abort.current?.abort()}>
              ■ 停止
            </button>
          )}
        </div>
        {sourceLabel && <span className={`badge ${source?.source === "claude" ? "accent" : ""}`}>{sourceLabel}</span>}
      </div>
      {!selection && status === "idle" && (
        <div className="muted" style={{ fontSize: 13, marginBottom: 10 }}>
          提示：在编辑器里<b>选中几行代码</b>，就可以只讲解选中的部分。讲解会先真实运行一遍代码（使用“可视化调用”里的例子），再结合运行结果说明。
        </div>
      )}

      {asked && (
        <div className="muted" style={{ fontSize: 13, marginBottom: 6 }}>
          {asked.question ? `问题：${asked.question}（${asked.scope}）` : `讲解范围：${asked.scope}`}
        </div>
      )}

      {status === "idle" && !text ? (
        <div className="empty-state">点击上面的按钮，AI 导师会讲解代码在做什么、递归如何展开，并用实际运行结果走一遍例子。</div>
      ) : (
        <div className={`explain-output ${streaming ? "streaming" : ""}`} data-testid="explain-output">
          {text ? <Markdown>{text}</Markdown> : streaming && <div className="muted">正在运行代码并准备讲解…</div>}
          {streaming && <span className="typing-cursor" aria-hidden="true" />}
        </div>
      )}
      {error && <div className="alert err section-gap">{error}</div>}

      {(status === "done" || status === "error") && (
        <div className="section-gap">
          <div className="row" style={{ gap: 6, marginBottom: 8 }}>
            {SUGGESTIONS.map((s) => (
              <button key={s} className="small" onClick={() => void start(s)}>
                {s}
              </button>
            ))}
          </div>
          <form
            className="row"
            onSubmit={(e) => {
              e.preventDefault();
              if (question.trim()) {
                void start(question.trim());
                setQuestion("");
              }
            }}
          >
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="继续追问，例如：第 4 行为什么要 return？"
              style={{ flex: 1, minWidth: 180 }}
              aria-label="继续追问"
            />
            <button type="submit" disabled={!question.trim()}>
              追问
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
