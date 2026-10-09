import { describe, expect, it } from "vitest";
import { firstDoctestCall, hasTopLevelStatements, withTraceCall } from "./code";

describe("code helpers", () => {
  const fact = 'def fact(n):\n    """\n    >>> fact(4)\n    24\n    """\n    return 1\n';

  it("finds the first doctest call", () => {
    expect(firstDoctestCall(fact)).toBe("fact(4)");
    expect(firstDoctestCall("x = 1")).toBeNull();
  });

  it("detects module-level statements", () => {
    expect(hasTopLevelStatements(fact)).toBe(false);
    expect(hasTopLevelStatements(fact + "fact(3)\n")).toBe(true);
    expect(hasTopLevelStatements("import math\n# comment\n@decorator\ndef f():\n    pass\n")).toBe(false);
    expect(hasTopLevelStatements('"""module docstring\nwith lines\n"""\ndef f():\n    pass\n')).toBe(false);
  });

  it("appends the trace call", () => {
    expect(withTraceCall("x = 1\n\n\n", "f(2)")).toBe("x = 1\n\nf(2)\n");
    expect(withTraceCall("x = 1\n", "  ")).toBe("x = 1\n");
  });
});
