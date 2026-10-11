import { useEffect, useRef } from "react";
import type { ToastKind } from "../components/Toast";
import type { RunResult, TestResult } from "../types";

export function formatDuration(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} 毫秒` : `${(ms / 1000).toFixed(1)} 秒`;
}

/** Run an async action and report how long it took. */
export async function timed<T>(fn: () => Promise<T>): Promise<[T, number]> {
  const start = performance.now();
  const value = await fn();
  return [value, performance.now() - start];
}

/** One-line toast for a test run. */
export function testToast(result: TestResult, ms: number): [string, ToastKind] {
  const took = ` · ${formatDuration(ms)}`;
  if (result.sandbox_error) return [result.sandbox_error.message, "error"];
  if (result.load_error) return [`代码无法加载：${result.load_error.type}${took}`, "error"];
  const s = result.summary ?? { passed: 0, failed: 0, total: 0 };
  if (s.total === 0) return [`没有找到测试${took}`, "info"];
  if (s.failed === 0) return [`全部 ${s.total} 个测试通过${took}`, "success"];
  return [`${s.passed} / ${s.total} 个测试通过，${s.failed} 个未通过${took}`, "error"];
}

export function runToast(result: RunResult, ms: number): [string, ToastKind] {
  const took = ` · ${formatDuration(ms)}`;
  if (result.sandbox_error) return [result.sandbox_error.message, "error"];
  if (result.error) return [`运行出错：${result.error.type}${took}`, "error"];
  return [`运行完成${took}`, "success"];
}

export const IS_MAC = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);
export const MOD = IS_MAC ? "⌘" : "Ctrl";

/**
 * Ctrl/⌘+Enter → onRun, Ctrl/⌘+Shift+Enter → onVisualize. Listens in the
 * capture phase so the code editor does not swallow the keys first.
 */
export function useRunShortcuts(onRun: () => void, onVisualize: () => void, enabled = true): void {
  const handlers = useRef({ onRun, onVisualize });
  handlers.current = { onRun, onVisualize };
  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Enter" || !(e.ctrlKey || e.metaKey) || e.altKey) return;
      e.preventDefault();
      e.stopPropagation();
      if (e.shiftKey) handlers.current.onVisualize();
      else handlers.current.onRun();
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [enabled]);
}
