import { useEffect, useState } from "react";
import { api } from "../api";
import { Skeleton } from "../components/Skeleton";
import { useToast } from "../components/Toast";
import type { SettingsInfo } from "../types";

/** Tells the header to refresh its "AI 导师" badge. */
export const SETTINGS_CHANGED = "learn61a:settings-changed";

export function Settings() {
  const [info, setInfo] = useState<SettingsInfo | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [key, setKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [model, setModel] = useState("");
  const [busy, setBusy] = useState<null | "save" | "test" | "clear">(null);
  const [check, setCheck] = useState<{ ok: boolean; message: string } | null>(null);
  const notify = useToast();

  useEffect(() => {
    api
      .settings()
      .then((s) => {
        setInfo(s);
        setModel(s.model);
      })
      .catch((e) => setLoadError((e as Error).message));
  }, []);

  if (loadError)
    return (
      <div className="page">
        <div className="alert err">{loadError}</div>
      </div>
    );
  if (!info)
    return (
      <div className="page">
        <div className="settings">
          <Skeleton lines={4} card />
          <Skeleton lines={6} card />
        </div>
      </div>
    );

  const changed = () => window.dispatchEvent(new Event(SETTINGS_CHANGED));

  const save = async () => {
    setBusy("save");
    setCheck(null);
    try {
      const next = await api.saveSettings({ api_key: key.trim() || undefined, model });
      setInfo(next);
      setKey("");
      changed();
      notify(next.has_key ? "已保存，AI 导师现在使用 Claude" : "已保存", "success");
    } catch (e) {
      notify((e as Error).message, "error");
    } finally {
      setBusy(null);
    }
  };

  const test = async () => {
    setBusy("test");
    setCheck(null);
    try {
      const result = await api.testSettings({ api_key: key.trim() || undefined, model });
      setCheck(result);
      notify(result.message, result.ok ? "success" : "error");
    } catch (e) {
      setCheck({ ok: false, message: (e as Error).message });
    } finally {
      setBusy(null);
    }
  };

  const clear = async () => {
    if (!window.confirm("删除保存在这台电脑上的 API key？AI 导师会回到离线规则模式。")) return;
    setBusy("clear");
    try {
      setInfo(await api.saveSettings({ clear_key: true }));
      setCheck(null);
      changed();
      notify("已删除 API key", "info");
    } finally {
      setBusy(null);
    }
  };

  const dirty = key.trim() !== "" || model !== info.model;

  return (
    <div className="page">
      <div className="settings">
        <div>
          <h1>设置</h1>
          <p className="muted" style={{ margin: 0 }}>
            填写 Anthropic API key 后，AI 导师和“讲解代码”会使用 Claude；不填写时使用离线规则，同样可以使用。
          </p>
        </div>

        <div className="card card-body" data-testid="settings-status">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <b>当前状态</b>
            <span className={`badge ${info.has_key ? "ok" : ""}`}>{info.has_key ? "Claude 已启用" : "离线规则模式"}</span>
          </div>
          <div className="section-gap" style={{ fontSize: 14 }}>
            {info.has_key ? (
              <>
                API key：<code>{info.key_hint}</code>（{info.key_source === "settings" ? "保存在本机设置中" : "来自环境变量 ANTHROPIC_API_KEY"}）
                <br />
                模型：<code>{info.model}</code>
              </>
            ) : (
              "还没有设置 API key。"
            )}
          </div>
        </div>

        <div className="card card-body">
          <label htmlFor="api-key">
            <b>Anthropic API key</b>
          </label>
          <div className="key-input section-gap">
            <input
              id="api-key"
              type={showKey ? "text" : "password"}
              value={key}
              onChange={(e) => {
                setKey(e.target.value);
                setCheck(null);
              }}
              placeholder={info.has_key ? `已设置 ${info.key_hint}，留空表示不修改` : "sk-ant-..."}
              autoComplete="off"
              spellCheck={false}
            />
            <button type="button" onClick={() => setShowKey((v) => !v)}>
              {showKey ? "隐藏" : "显示"}
            </button>
          </div>

          <div className="section-gap">
            <b>模型</b>
            <div className="model-options section-gap" role="radiogroup" aria-label="模型">
              {info.models.map((m) => (
                <label key={m.id} className={`model-option ${model === m.id ? "selected" : ""}`}>
                  <input type="radio" name="model" value={m.id} checked={model === m.id} onChange={() => setModel(m.id)} />
                  <b>{m.label}</b>
                  <span className="muted" style={{ fontSize: 13 }}>
                    {m.note}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="row section-gap">
            <button className="primary" onClick={save} disabled={busy !== null || !dirty}>
              {busy === "save" && <span className="spinner" />}
              保存
            </button>
            <button onClick={test} disabled={busy !== null || (!key.trim() && !info.has_key)}>
              {busy === "test" && <span className="spinner" />}
              {busy === "test" ? "测试中…" : "测试连接"}
            </button>
            {info.key_source === "settings" && (
              <button className="ghost" onClick={clear} disabled={busy !== null}>
                删除已保存的 key
              </button>
            )}
          </div>
          {check && (
            <div className={`alert ${check.ok ? "ok" : "err"} section-gap`} data-testid="settings-check">
              {check.message}
            </div>
          )}
        </div>

        <div className="card card-body">
          <b>如何获取 API key</b>
          <ol className="steps">
            <li>
              打开{" "}
              <a href="https://console.anthropic.com" target="_blank" rel="noreferrer">
                console.anthropic.com
              </a>{" "}
              注册并登录；
            </li>
            <li>在 Billing 页面充值（按用量计费）；</li>
            <li>在 API Keys 页面点 Create Key，复制以 sk-ant- 开头的 key，粘贴到上面后点“测试连接”，再点“保存”。</li>
          </ol>
          <div className="section-gap muted" style={{ fontSize: 13 }}>
            · key 只保存在这台电脑的 <code>{info.settings_file}</code>，页面不会再显示完整的 key。
            <br />· 使用 Claude 时，你的代码和问题会发送给 Anthropic 处理；其他功能都在本机运行。
            <br />· 每次提问 / 讲解都会产生少量费用；Sonnet、Haiku 比 Opus 更便宜。
          </div>
        </div>
      </div>
    </div>
  );
}
