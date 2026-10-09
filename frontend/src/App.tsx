import { useEffect, useState } from "react";
import { api } from "./api";
import { load, save } from "./lib/storage";
import { ExerciseWorkspace } from "./pages/ExerciseWorkspace";
import { Exercises } from "./pages/Exercises";
import { Guide } from "./pages/Guide";
import { Lab } from "./pages/Lab";
import { Quiz } from "./pages/Quiz";

function useHashRoute(): string {
  const [hash, setHash] = useState(() => window.location.hash || "#/lab");
  useEffect(() => {
    const onChange = () => setHash(window.location.hash || "#/lab");
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash.replace(/^#/, "");
}

const NAV = [
  { path: "/lab", label: "代码实验室" },
  { path: "/exercises", label: "练习" },
  { path: "/quiz", label: "WWPD 测验" },
  { path: "/guide", label: "使用说明" },
];

type Theme = "auto" | "light" | "dark";

function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(() => load<Theme>("learn61a:theme", "auto"));
  useEffect(() => {
    if (theme === "auto") delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = theme;
    save("learn61a:theme", theme);
  }, [theme]);
  const cycle = () => setTheme((t) => (t === "auto" ? "dark" : t === "dark" ? "light" : "auto"));
  return [theme, cycle];
}

export function App() {
  const route = useHashRoute();
  const [theme, cycleTheme] = useTheme();
  const [tutor, setTutor] = useState<"claude" | "rules" | "offline" | null>(null);

  useEffect(() => {
    api
      .health()
      .then((h) => setTutor(h.tutor))
      .catch(() => setTutor("offline"));
  }, []);

  const exerciseMatch = route.match(/^\/exercises\/([\w-]+)$/);
  let page;
  if (exerciseMatch) page = <ExerciseWorkspace key={exerciseMatch[1]} id={exerciseMatch[1]} />;
  else if (route.startsWith("/exercises")) page = <Exercises />;
  else if (route.startsWith("/quiz")) page = <Quiz />;
  else if (route.startsWith("/guide")) page = <Guide />;
  else page = <Lab />;

  return (
    <>
      <header className="app-header">
        <a className="brand" href="#/lab">
          <img src="/favicon.svg" alt="" />
          <span>61A 递归实验室</span>
        </a>
        <nav className="nav">
          {NAV.map((item) => (
            <a key={item.path} href={`#${item.path}`} className={route.startsWith(item.path) ? "active" : ""}>
              {item.label}
            </a>
          ))}
        </nav>
        <span className="header-spacer" />
        <span className="tutor-badge" title="AI 导师模式">
          {tutor === "claude" && "AI 导师：Claude"}
          {tutor === "rules" && "AI 导师：离线规则"}
        </span>
        <button className="small ghost" onClick={cycleTheme} title="切换主题（自动 / 深色 / 浅色）" aria-label="切换主题">
          {theme === "auto" ? "🌓" : theme === "dark" ? "🌙" : "☀️"}
        </button>
      </header>
      {tutor === "offline" && (
        <div className="page" style={{ paddingBottom: 0 }}>
          <div className="alert err">
            无法连接后端服务。请先启动后端：<code>cd backend &amp;&amp; uvicorn app.main:app --port 8000</code>
          </div>
        </div>
      )}
      <main>{page}</main>
    </>
  );
}
