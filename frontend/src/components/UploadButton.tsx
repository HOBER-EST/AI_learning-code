import { useRef } from "react";

export function UploadButton({ onFile, disabled }: { onFile: (file: File) => void; disabled?: boolean }) {
  const input = useRef<HTMLInputElement>(null);
  return (
    <>
      <button onClick={() => input.current?.click()} disabled={disabled} title="上传 .py 文件（也可以直接拖到编辑器里）">
        📂 上传 .py
      </button>
      <input
        ref={input}
        type="file"
        accept=".py,text/x-python"
        hidden
        data-testid="upload-input"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
          e.target.value = "";
        }}
      />
    </>
  );
}
