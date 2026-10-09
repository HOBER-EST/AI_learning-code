// Per-viewer conveniences (drafts, progress). Storage can be unavailable
// (private mode, blocked site data), so every access is guarded.

export function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw === null ? fallback : (JSON.parse(raw) as T);
  } catch {
    return fallback;
  }
}

export function save(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* ignore */
  }
}

export function remove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

const SOLVED_KEY = "learn61a:solved";

export function solvedExercises(): Set<string> {
  return new Set(load<string[]>(SOLVED_KEY, []));
}

export function markSolved(id: string): void {
  const solved = solvedExercises();
  solved.add(id);
  save(SOLVED_KEY, [...solved]);
}
