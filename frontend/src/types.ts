// Shapes returned by the Python backend (see backend/app/runner/tracer.py).

export type Value =
  | { t: "prim"; v: string }
  | { t: "ref"; id: string }
  | { t: "empty" };

export type HeapObject =
  | { t: "list" | "tuple" | "set"; items: Value[]; len: number }
  | { t: "dict"; items: [Value, Value][]; len: number }
  | { t: "func"; name: string; params: string; parent?: string; line?: number | null; builtin?: boolean }
  | { t: "method"; func: Value; self: Value }
  | { t: "class"; name: string; bases: string[]; attrs: [string, Value][] }
  | { t: "instance"; cls: string; attrs: [string, Value][] }
  | { t: "link"; first: Value; rest: Value }
  | { t: "tree"; label: Value; branches: Value[] }
  | { t: "other"; repr: string };

export interface Frame {
  id: string;
  label: string;
  name: string;
  parent: string;
  vars: [string, Value][];
  live: boolean;
  ret?: Value;
  raised?: boolean;
}

export interface Step {
  event: "call" | "line" | "return" | "exception";
  line: number;
  frame: string;
  stack: string[];
  globals: [string, Value][];
  frames: Frame[];
  heap: Record<string, HeapObject>;
  stdout: string;
  exception?: string;
  uncaught?: boolean;
  heap_truncated?: boolean;
}

export interface CallNode {
  id: string;
  name: string;
  label: string;
  parent: string | null;
  depth: number;
  call_step: number;
  return_step: number | null;
  ret: string | null;
  status: "active" | "returned" | "error";
}

export interface ErrorInfo {
  type: string;
  message: string;
  line: number | null;
  traceback?: string;
}

export interface SandboxError {
  type: string;
  message: string;
  detail?: string;
}

export interface TraceResult {
  ok: boolean;
  steps: Step[];
  calls: CallNode[];
  error: ErrorInfo | null;
  truncated?: boolean;
  max_steps?: number;
  stdout?: string;
  sandbox_error?: SandboxError;
}

export interface TestCase {
  name: string;
  origin: "doctest" | "exercise" | "test_function" | "constraint";
  source: string;
  want: string;
  got: string;
  status: "passed" | "failed" | "error" | "timeout";
  line: number | null;
  error_type?: string;
}

export interface Finding {
  level: "error" | "warning" | "info";
  title: string;
  message: string;
  line: number | null;
  function?: string | null;
}

export interface FunctionInfo {
  name: string;
  line: number;
  params: string[];
  recursive: boolean;
  kind: string | null;
  recursive_calls: number[];
  has_base_case: boolean;
  has_loops: boolean;
}

export interface Analysis {
  functions: FunctionInfo[];
  findings: Finding[];
}

export interface TestResult {
  ok: boolean;
  load_error?: ErrorInfo | null;
  results?: TestCase[];
  summary?: { passed: number; failed: number; total: number };
  stdout?: string;
  analysis?: Analysis;
  sandbox_error?: SandboxError;
  solved?: boolean;
}

export interface RunResult {
  ok: boolean;
  stdout?: string;
  error?: ErrorInfo | null;
  sandbox_error?: SandboxError;
}

export interface UploadResult {
  filename: string;
  code: string;
  syntax: { ok: boolean; message: string | null; line: number | null };
  functions: string[];
  tests: TestResult | null;
  analysis?: Analysis;
}

export type Topic = "recursion" | "link" | "tree";

export interface ExerciseSummary {
  id: string;
  topic: Topic;
  title: string;
  difficulty: 1 | 2 | 3;
  function: string;
  concepts: string[];
}

export interface ExerciseDetail extends ExerciseSummary {
  description: string;
  starter: string;
  hints: string[];
  trace: string;
  constraints: { type: string }[];
  hidden_test_count: number;
}

export interface TopicInfo {
  title: string;
  description: string;
}

export interface Quiz {
  id: string;
  topic: Topic;
  setup: string;
  expression: string;
}

export interface QuizCheck {
  correct: boolean;
  answer: string;
  explanation: string;
}

export interface TutorReply {
  source: "claude" | "rules";
  answer: string;
  findings: Finding[];
  notice?: string;
}
