import CodeMirror, { type ViewUpdate } from "@uiw/react-codemirror";
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
  /** Called with the selected lines (expanded to whole lines), or null. */
  onSelectionChange?: (selection: { text: string; line: number; lines: number } | null) => void;
}

export function CodeEditor({ value, onChange, height = "420px", onDropFile, running = false, onSelectionChange }: Props) {
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
        onUpdate={(update: ViewUpdate) => {
          if (!onSelectionChange || !(update.selectionSet || update.docChanged)) return;
          const { state } = update;
          const range = state.selection.main;
          if (range.empty) {
            onSelectionChange(null);
            return;
          }
          const first = state.doc.lineAt(range.from);
          // A selection ending at the start of a line does not include that line.
          const lastPos = range.to > range.from && state.doc.lineAt(range.to).from === range.to ? range.to - 1 : range.to;
          const last = state.doc.lineAt(lastPos);
          onSelectionChange({
            text: state.sliceDoc(first.from, last.to),
            line: first.number,
            lines: last.number - first.number + 1,
          });
        }}
        basicSetup={{ tabSize: 4, foldGutter: false }}
        indentWithTab
      />
    </div>
  );
}
