import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import fixture from "../test/fixtures/trace.json";
import type { TraceResult } from "../types";
import { Visualizer } from "./Visualizer";

const trace = fixture.trace as unknown as TraceResult;

describe("Visualizer", () => {
  it("steps forward and backward with buttons and keys", async () => {
    render(<Visualizer trace={trace} code={fixture.code} />);
    expect(screen.getByTestId("step-desc")).toHaveTextContent(`第 1 / ${trace.steps.length} 步`);
    await userEvent.click(screen.getByRole("button", { name: "下一步 ▶" }));
    expect(screen.getByTestId("step-desc")).toHaveTextContent("第 2 /");
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(screen.getByTestId("step-desc")).toHaveTextContent("第 3 /");
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(screen.getByTestId("step-desc")).toHaveTextContent("第 2 /");
    await userEvent.click(screen.getByRole("button", { name: "最后一步" }));
    expect(screen.getByTestId("step-desc")).toHaveTextContent("程序执行完毕");
  });

  it("shows CS61A frames, linked lists and trees in the environment diagram", async () => {
    render(<Visualizer trace={trace} code={fixture.code} />);
    await userEvent.click(screen.getByRole("button", { name: /环境图/ }));
    await userEvent.click(screen.getByRole("button", { name: "最后一步" }));
    const titles = screen.getAllByTestId("frame").map((f) => f.querySelector(".frame-title")!.textContent);
    expect(titles).toEqual([
      "Global frame ",
      "f1: fact [parent=Global]",
      "f2: fact [parent=Global]",
      "f3: fact [parent=Global]",
    ]);
    expect(screen.getAllByText("Return value")).toHaveLength(3);
    const diagram = screen.getByTestId("env-diagram");
    expect(diagram.querySelectorAll(".link-node")).toHaveLength(3);
    expect(diagram.querySelectorAll(".tree-node")).toHaveLength(3);
    expect(diagram.querySelectorAll(".link-chain")).toHaveLength(1);

    // Hiding exited frames leaves only the Global frame at the end.
    await userEvent.click(screen.getByLabelText(/显示已返回的帧/));
    expect(screen.getAllByTestId("frame")).toHaveLength(1);
  });

  it("reveals the recursion tree as the program runs and jumps on click", async () => {
    render(<Visualizer trace={trace} code={fixture.code} />);
    await userEvent.click(screen.getByRole("button", { name: /递归调用树/ }));
    expect(screen.queryAllByTestId("call-node")).toHaveLength(0);
    await userEvent.click(screen.getByRole("button", { name: "最后一步" }));
    const nodes = screen.getAllByTestId("call-node");
    expect(nodes.map((n) => n.querySelector("text")!.textContent)).toEqual(["fact(2)", "fact(1)", "fact(0)"]);
    expect(nodes[0]).toHaveTextContent("→ 2");
    fireEvent.click(nodes[2]);
    expect(screen.getByTestId("step-desc")).toHaveTextContent("调用 fact(0)");
  });

  it("explains truncated traces", async () => {
    const truncated: TraceResult = { ...trace, truncated: true, max_steps: trace.steps.length };
    render(<Visualizer trace={truncated} code={fixture.code} />);
    await userEvent.click(screen.getByRole("button", { name: "最后一步" }));
    expect(screen.getByText(/无限递归/)).toBeInTheDocument();
  });
});
