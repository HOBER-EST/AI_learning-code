import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

export type ToastKind = "success" | "error" | "info";

interface ToastItem {
  id: number;
  kind: ToastKind;
  text: string;
  leaving?: boolean;
}

type Notify = (text: string, kind?: ToastKind) => void;

const ToastContext = createContext<Notify>(() => {});

const ICON: Record<ToastKind, string> = { success: "✓", error: "!", info: "i" };
const DURATION = 3600;
const EXIT_MS = 220;

/** Small transient messages in the corner: the result of every action. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(1);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: number) => {
    setToasts((list) => list.map((t) => (t.id === id ? { ...t, leaving: true } : t)));
    setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), EXIT_MS);
    const timer = timers.current.get(id);
    if (timer) clearTimeout(timer);
    timers.current.delete(id);
  }, []);

  const notify = useCallback<Notify>(
    (text, kind = "info") => {
      const id = nextId.current++;
      setToasts((list) => [...list.slice(-3), { id, kind, text }]);
      timers.current.set(id, setTimeout(() => dismiss(id), kind === "error" ? DURATION * 1.6 : DURATION));
    },
    [dismiss],
  );

  useEffect(() => {
    const all = timers.current;
    return () => all.forEach((t) => clearTimeout(t));
  }, []);

  return (
    <ToastContext.Provider value={notify}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.kind} ${t.leaving ? "leaving" : ""}`} data-testid="toast">
            <span className="toast-icon" aria-hidden="true">
              {ICON[t.kind]}
            </span>
            <span className="toast-text">{t.text}</span>
            <button className="toast-close" onClick={() => dismiss(t.id)} aria-label="关闭提示">
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): Notify {
  return useContext(ToastContext);
}
