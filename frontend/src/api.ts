import type {
  Analysis,
  ExerciseDetail,
  ExerciseSummary,
  Quiz,
  QuizCheck,
  RunResult,
  TestResult,
  TopicInfo,
  TraceResult,
  TutorReply,
  UploadResult,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

/** A human-readable reason for a failed response. Exported for tests. */
export async function describeFailure(response: Response): Promise<string> {
  const base = `请求失败（${response.status}）`;
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    // Not our backend's JSON: the request never reached it (dev proxy with the
    // backend stopped, or a proxy/VPN app intercepting 127.0.0.1).
    return (
      `${base}：后端没有正常响应。请确认后端已启动；如果开着代理或 VPN 软件（如 Clash），` +
      "请把 127.0.0.1 / localhost 加入直连（绕过代理）列表后重试。"
    );
  }
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return `${base}：提交的数据格式不正确。`;
  return base;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError("无法连接后端服务，请确认后端已启动（默认 http://127.0.0.1:8000）。", 0);
  }
  if (!response.ok) {
    throw new ApiError(await describeFailure(response), response.status);
  }
  return response.json() as Promise<T>;
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const api = {
  health: () => request<{ status: string; tutor: "claude" | "rules"; window_error?: string }>("/api/health"),
  run: (code: string) => post<RunResult>("/api/run", { code }),
  test: (code: string, tests?: string) => post<TestResult>("/api/test", { code, tests }),
  trace: (code: string, maxSteps?: number) => post<TraceResult>("/api/trace", { code, max_steps: maxSteps }),
  analyze: (code: string, testResults?: TestResult | null) =>
    post<Analysis>("/api/analyze", { code, test_results: testResults ?? null }),
  upload: (file: File, autoTest = true) => {
    const form = new FormData();
    form.append("file", file);
    form.append("auto_test", String(autoTest));
    return request<UploadResult>("/api/upload", { method: "POST", body: form });
  },
  topics: () => request<Record<string, TopicInfo>>("/api/topics"),
  exercises: () => request<ExerciseSummary[]>("/api/exercises"),
  exercise: (id: string) => request<ExerciseDetail>(`/api/exercises/${encodeURIComponent(id)}`),
  submit: (id: string, code: string) => post<TestResult>(`/api/exercises/${encodeURIComponent(id)}/submit`, { code }),
  solution: (id: string) => request<{ solution: string }>(`/api/exercises/${encodeURIComponent(id)}/solution`),
  quizzes: () => request<Quiz[]>("/api/quizzes"),
  checkQuiz: (id: string, answer: string) => post<QuizCheck>(`/api/quizzes/${encodeURIComponent(id)}/check`, { answer }),
  tutor: (body: { code: string; question: string; test_results?: TestResult | null; exercise_id?: string }) =>
    post<TutorReply>("/api/tutor", body),
};
