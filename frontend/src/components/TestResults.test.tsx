import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { TestResult } from "../types";
import { TestResults } from "./TestResults";

const result: TestResult = {
  ok: false,
  summary: { passed: 1, failed: 1, total: 2 },
  results: [
    { name: "fact", origin: "doctest", source: "fact(3)", want: "6", got: "6", status: "passed", line: 3 },
    { name: "fact", origin: "doctest", source: "fact(4)", want: "24", got: "", status: "failed", line: 5 },
  ],
};

describe("TestResults", () => {
  it("summarizes and lists failing cases first", () => {
    render(<TestResults result={result} />);
    expect(screen.getByTestId("test-summary")).toHaveTextContent("1 / 2 通过");
    const cases = screen.getAllByTestId("test-case");
    expect(cases[0]).toHaveTextContent("fact(4)");
    expect(cases[0]).toHaveTextContent("函数可能返回了 None");
  });

  it("offers to visualize a failing example", async () => {
    const onVisualize = vi.fn();
    render(<TestResults result={result} onVisualize={onVisualize} />);
    await userEvent.click(screen.getByRole("button", { name: /可视化/ }));
    expect(onVisualize).toHaveBeenCalledWith("fact(4)");
  });

  it("shows load errors", () => {
    render(<TestResults result={{ ok: false, load_error: { type: "SyntaxError", message: "invalid syntax", line: 2 } }} />);
    expect(screen.getByTestId("load-error")).toHaveTextContent("SyntaxError");
    expect(screen.getByTestId("load-error")).toHaveTextContent("第 2 行");
  });
});
