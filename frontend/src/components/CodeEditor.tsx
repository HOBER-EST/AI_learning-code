import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { useEffect, useState, type DragEvent } from "react";

function useDarkMode(): boolean {
  const query = typeof window !== "undefined" && window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  const read = () => {
    const forced = document.documentElement.dataset.theme;
    if (forced) return forced === "dark";
    return !!query?.matches;
  };
  const [dark, setDark] = useState(read);
  useEffect(() => {
    const update = () => setDark(read());
    query?.addEventListener("change", update);
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => {
      query?.removeEventListener("change", update);
      observer.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return dark;
}

const extensions = [python()];

interface Props {
  value: string;
  onChange: (value: string) => void;
  height?: string;
  onDropFile?: (file: File) => void;
  /** Shows an animated bar while the code is being run. */
  running?: boolean;
}

export function CodeEditor({ value, onChange, height = "420px", onDropFile, running = false }: Props) {
  const dark = useDarkMode();
  const [dragging, setDragging] = useState(false);

  const onDrop = (e: DragEvent) => {
    if (!onDropFile) return;
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) onDropFile(file);
  };

  return (
    <div
      className={`editor-shell ${dragging ? "dragging" : ""} ${running ? "running" : ""}`}
      onDragOver={(e) => {
        if (!onDropFile || !e.dataTransfer.types.includes("Files")) return;
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      data-testid="code-editor"
    >
      <CodeMirror
        value={value}
        height={height}
        theme={dark ? "dark" : "light"}
        extensions={extensions}
        onChange={onChange}
        basicSetup={{ tabSize: 4, foldGutter: false }}
        indentWithTab
      />
    </div>
  );
}
