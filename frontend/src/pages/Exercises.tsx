import { useEffect, useState } from "react";
import { api } from "../api";
import { solvedExercises } from "../lib/storage";
import type { ExerciseSummary, Topic, TopicInfo } from "../types";

export const TOPIC_ORDER: Topic[] = ["recursion", "link", "tree"];
export const TOPIC_ICON: Record<Topic, string> = { recursion: "🔁", link: "🔗", tree: "🌳" };

export function Difficulty({ level }: { level: number }) {
  return (
    <span className="difficulty" title={["", "简单", "中等", "困难"][level]}>
      {"★".repeat(level)}
      <span style={{ opacity: 0.25 }}>{"★".repeat(3 - level)}</span>
    </span>
  );
}

export function Exercises() {
  const [items, setItems] = useState<ExerciseSummary[] | null>(null);
  const [topics, setTopics] = useState<Record<string, TopicInfo>>({});
  const [error, setError] = useState<string | null>(null);
  const solved = solvedExercises();

  useEffect(() => {
    Promise.all([api.exercises(), api.topics()])
      .then(([ex, t]) => {
        setItems(ex);
        setTopics(t);
      })
      .catch((e) => setError((e as Error).message));
  }, []);

  if (error) return <div className="page"><div className="alert err">{error}</div></div>;
  if (!items) return <div className="page"><div className="empty-state">加载中…</div></div>;

  const done = items.filter((e) => solved.has(e.id)).length;

  return (
    <div className="page">
      <div className="hero">
        <div>
          <h1>交互式练习</h1>
          <p className="muted">CS61A 风格的 Recursion、Linked List 和 Tree 练习：写代码、跑测试、可视化、找 AI 导师要提示。</p>
        </div>
      </div>
      <div className="overall-progress">
        <span className="badge ok">
          已完成 {done} / {items.length}
        </span>
        <div className="progress-bar" style={{ maxWidth: 360, background: "var(--surface-2)" }}>
          <div style={{ width: `${(done / items.length) * 100}%` }} />
        </div>
      </div>
      {TOPIC_ORDER.map((topic) => {
        const list = items.filter((e) => e.topic === topic);
        const info = topics[topic];
        return (
          <section className="topic-section" key={topic} data-testid={`topic-${topic}`}>
            <div className="topic-head">
              <h2>
                {TOPIC_ICON[topic]} {info?.title ?? topic}
              </h2>
              <span className="muted">
                {list.filter((e) => solved.has(e.id)).length} / {list.length} 完成
              </span>
            </div>
            {info && <p className="muted" style={{ margin: 0 }}>{info.description}</p>}
            <div className="exercise-grid">
              {list.map((ex) => (
                <a className="card exercise-card" href={`#/exercises/${ex.id}`} key={ex.id}>
                  <div className="row" style={{ justifyContent: "space-between" }}>
                    <span className="title">{ex.title}</span>
                    {solved.has(ex.id) && <span className="badge ok">✓ 已完成</span>}
                  </div>
                  <Difficulty level={ex.difficulty} />
                  <div className="row" style={{ gap: 4 }}>
                    {ex.concepts.map((c) => (
                      <span className="badge" key={c}>
                        {c}
                      </span>
                    ))}
                  </div>
                </a>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
