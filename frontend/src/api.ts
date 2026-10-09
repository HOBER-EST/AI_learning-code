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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError("无法连接后端服务，请确认后端已启动（默认 http://127.0.0.1:8000）。", 0);
  }
  if (!response.ok) {
    let message = `请求失败（${response.status}）`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      /* not JSON */
    }
    throw new ApiError(message, response.status);
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
  health: () => request<{ status: string; tutor: "claude" | "rules" }>("/api/health"),
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
