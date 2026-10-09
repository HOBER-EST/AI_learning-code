/** Helpers that work on Python source text in the browser. */

/** The first doctest example (``>>> expr``) in the code, if any. */
export function firstDoctestCall(code: string): string | null {
  const match = code.match(/^\s*>>> (.+)$/m);
  return match ? match[1].trim() : null;
}

/** True if the code runs something at module level besides definitions. */
export function hasTopLevelStatements(code: string): boolean {
  let inString = false;
  for (const raw of code.split("\n")) {
    const tripleCount = (raw.match(/"""|'''/g) ?? []).length;
    const wasInString = inString;
    if (tripleCount % 2 === 1) inString = !inString;
    if (wasInString || /^\s/.test(raw) || raw.trim() === "") continue;
    if (/^(def |class |import |from |@|#|"""|''')/.test(raw)) continue;
    return true;
  }
  return false;
}

/** The code to trace: the program plus an optional extra call line. */
export function withTraceCall(code: string, call: string): string {
  const extra = call.trim();
  if (!extra) return code;
  return code.replace(/\s*$/, "") + "\n\n" + extra + "\n";
}
