import { describe, expect, it } from "vitest";
import { describeFailure } from "./api";

describe("describeFailure", () => {
  it("shows the backend's own explanation", async () => {
    const res = new Response(JSON.stringify({ detail: "服务器内部错误：OSError: boom" }), { status: 500 });
    expect(await describeFailure(res)).toBe("服务器内部错误：OSError: boom");
  });

  it("explains responses that did not come from the backend", async () => {
    const res = new Response("Bad Gateway", { status: 502 });
    const message = await describeFailure(res);
    expect(message).toContain("请求失败（502）");
    expect(message).toContain("代理");
  });

  it("summarizes validation errors", async () => {
    const res = new Response(JSON.stringify({ detail: [{ msg: "too long" }] }), { status: 422 });
    expect(await describeFailure(res)).toContain("数据格式不正确");
  });
});
