import { expect, test, type Page } from "@playwright/test";

async function setEditor(page: Page, code: string) {
  const editor = page.locator(".cm-content").first();
  await editor.click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.press("Delete");
  await editor.fill(code);
}

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
});

test("visualizes tree recursion with a call tree and an environment diagram", async ({ page }) => {
  await page.goto("/#/lab");
  await page.getByLabel("载入示例").selectOption("fib");
  await page.getByRole("button", { name: /可视化执行/ }).click();
  await expect(page.getByTestId("visualizer")).toBeVisible();

  // The recursion tree grows as we step through the program.
  await page.getByRole("button", { name: /递归调用树/ }).click();
  await expect(page.getByTestId("call-node")).toHaveCount(0);
  await page.getByRole("button", { name: "最后一步" }).click();
  await expect(page.getByTestId("call-node")).toHaveCount(15);
  await expect(page.getByTestId("call-node").first()).toContainText("fib(5)");
  await expect(page.getByTestId("call-node").first()).toContainText("→ 5");
  await expect(page.getByText("fib(1) ×5")).toBeVisible();

  // Clicking a call jumps to that step; the environment diagram shows its frames.
  await page.getByTestId("call-node").nth(2).click();
  await expect(page.getByTestId("step-desc")).toContainText("调用 fib(3)");
  await page.getByRole("button", { name: /环境图/ }).click();
  await expect(page.locator(".frame-title", { hasText: "f3: fib" })).toBeVisible();
  await expect(page.locator(".arrows > path")).not.toHaveCount(0);
});

test("draws linked lists as box-and-pointer chains", async ({ page }) => {
  await page.goto("/#/lab");
  await page.getByLabel("载入示例").selectOption("link");
  await page.getByRole("button", { name: /可视化执行/ }).click();
  await page.getByRole("button", { name: /环境图/ }).click();
  await page.getByRole("button", { name: "最后一步" }).click();
  await expect(page.locator(".link-chain")).toHaveCount(2);
  await expect(page.locator(".link-node")).toHaveCount(6);
  await expect(page.getByTestId("stdout")).toHaveText("<1 99 3> <10 20 30>");
});

test("uploads a .py file and runs its tests automatically", async ({ page }) => {
  await page.goto("/#/lab");
  const code = 'def square(x):\n    """\n    >>> square(3)\n    9\n    >>> square(4)\n    15\n    """\n    return x * x\n';
  await page.getByTestId("upload-input").setInputFiles({ name: "hw01.py", mimeType: "text/x-python", buffer: Buffer.from(code) });
  await expect(page.getByTestId("upload-notice")).toContainText("hw01.py");
  await expect(page.getByTestId("test-summary")).toHaveText("1 / 2 通过");
  await expect(page.getByTestId("test-case").first()).toContainText("square(4)");

  // A failing example can be visualized directly.
  await page.getByTestId("test-case").first().getByRole("button", { name: /可视化/ }).click();
  await expect(page.getByTestId("visualizer")).toBeVisible();
  await expect(page.getByTestId("code-view")).toContainText("square(4)");
});

test("solves an exercise end to end", async ({ page }) => {
  await page.goto("/#/exercises/factorial");
  await expect(page.getByRole("heading", { name: /阶乘 factorial/ })).toBeVisible();

  await page.getByTestId("submit").click();
  await expect(page.getByTestId("test-summary")).toContainText("0 /");

  await page.getByRole("button", { name: /给我一个提示/ }).click();
  await expect(page.getByText(/提示 1：/)).toBeVisible();

  await setEditor(page, "def factorial(n):\n    if n == 0:\n        return 1\n    return n * factorial(n - 1)\n");
  await page.getByTestId("submit").click();
  await expect(page.getByText("全部测试通过，练习完成")).toBeVisible();

  // Jumping straight to another exercise must not carry this code over.
  await page.goto("/#/exercises/sum_digits");
  await expect(page.locator(".cm-content")).toContainText("def sum_digits");
  await page.goto("/#/exercises/factorial");
  await expect(page.locator(".cm-content")).toContainText("return n * factorial(n - 1)");

  await page.goto("/#/exercises");
  await expect(page.getByTestId("topic-recursion")).toContainText("1 / 8 完成");
});

test("a loop-based answer fails the recursion requirement", async ({ page }) => {
  await page.goto("/#/exercises/factorial");
  await expect(page.getByRole("heading", { name: /阶乘 factorial/ })).toBeVisible();
  await setEditor(page, "def factorial(n):\n    r = 1\n    for i in range(1, n + 1):\n        r *= i\n    return r\n");
  await page.getByTestId("submit").click();
  await expect(page.getByTestId("test-case").first()).toContainText("factorial 必须是递归函数");
});

test("the AI tutor explains a missing return", async ({ page }) => {
  await page.goto("/#/lab");
  await page.getByLabel("载入示例").selectOption("bug");
  await page.getByRole("button", { name: "✓ 运行测试" }).click();
  await expect(page.getByTestId("test-summary")).toHaveText("0 / 2 通过");
  await page.getByRole("button", { name: "AI 导师" }).click();
  await expect(page.getByTestId("findings")).toContainText("可能缺少基本情况");
  await page.getByRole("button", { name: "帮我看看哪里错了" }).click();
  await expect(page.locator(".chat-msg.tutor")).toContainText("第一个没通过的测试");
});

test("WWPD quiz checks answers", async ({ page }) => {
  await page.goto("/#/quiz");
  const card = page.getByTestId("quiz-card").filter({ hasText: "lnk.rest.first" });
  await card.getByLabel("你的答案").fill("3");
  await card.getByRole("button", { name: "检查答案" }).click();
  await expect(card.getByTestId("quiz-feedback")).toContainText("不对");
  await card.getByLabel("你的答案").fill("2");
  await card.getByRole("button", { name: "检查答案" }).click();
  await expect(card.getByTestId("quiz-feedback")).toContainText("正确");
});

test("the usage guide is available in the app", async ({ page }) => {
  await page.goto("/#/guide");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});

test("keyboard shortcuts run tests and visualize, with feedback", async ({ page }) => {
  await page.goto("/#/lab");
  await page.getByLabel("载入示例").selectOption("fact");
  await page.locator(".cm-content").click();
  await page.keyboard.press("ControlOrMeta+Enter");
  await expect(page.getByTestId("toast").first()).toContainText("全部 1 个测试通过");
  await expect(page.getByTestId("status-line")).toContainText("全部 1 个测试通过");

  await page.keyboard.press("ControlOrMeta+Shift+Enter");
  await expect(page.getByTestId("visualizer")).toBeVisible();
  await expect(page.getByTestId("toast").filter({ hasText: "已记录" })).toBeVisible();
});

test("explains the whole program or just the selected lines", async ({ page }) => {
  await page.goto("/#/lab");
  await page.getByLabel("载入示例").selectOption("fib");
  await page.getByTestId("explain-button").click();
  const output = page.getByTestId("explain-output");
  await expect(output).toContainText("逐行讲解");
  await expect(output).toContainText("树递归");
  await expect(output).toContainText("fib(5) → 5"); // grounded in a real run

  // Select lines 6-7 and explain only those.
  await page.locator(".cm-line").nth(5).click();
  await page.keyboard.press("Home");
  await page.keyboard.press("Shift+ArrowDown");
  await page.keyboard.press("Shift+End");
  await expect(page.getByTestId("explain-button")).toHaveText("📖 讲解选中的第 6–7 行");
  await page.getByTestId("explain-button").click();
  await expect(output).toContainText("选中的代码");
  await expect(output).toContainText("第 6 行");
  await expect(output).not.toContainText("第 10 行");
});

test("settings store an API key locally and switch the tutor mode", async ({ page }) => {
  await page.goto("/#/settings");
  await expect(page.getByTestId("settings-status")).toContainText("离线规则模式");
  await page.getByLabel("Anthropic API key").fill("sk-ant-api03-e2e-placeholder-wxyz");
  await page.locator(".model-option", { hasText: "Haiku" }).click();
  await page.getByRole("button", { name: "保存" }).click();
  await expect(page.getByTestId("tutor-badge")).toContainText("AI 导师：Claude");
  await expect(page.getByTestId("settings-status")).toContainText("sk-ant-…wxyz");
  await expect(page.getByTestId("settings-status")).toContainText("claude-haiku-5-5");
  await expect(page.getByLabel("Anthropic API key")).toHaveValue("");

  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "删除已保存的 key" }).click();
  await expect(page.getByTestId("tutor-badge")).toContainText("AI 导师：离线规则");
});
