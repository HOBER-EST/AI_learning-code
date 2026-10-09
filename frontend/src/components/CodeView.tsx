import { useEffect, useRef } from "react";

interface Props {
  code: string;
  nextLine?: number | null;
  prevLine?: number | null;
  errorLine?: number | null;
}

/** Read-only code listing with Python Tutor style line markers. */
export function CodeView({ code, nextLine, prevLine, errorLine }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const lines = code.replace(/\n$/, "").split("\n");

  useEffect(() => {
    const el = ref.current?.querySelector<HTMLElement>(".code-line.next");
    const box = ref.current;
    if (!el || !box) return;
    const top = el.offsetTop;
    if (top < box.scrollTop || top > box.scrollTop + box.clientHeight - 30) {
      box.scrollTop = top - box.clientHeight / 3;
    }
  }, [nextLine]);

  return (
    <div className="code-view" ref={ref} data-testid="code-view">
      {lines.map((text, i) => {
        const n = i + 1;
        const isNext = n === nextLine;
        const isPrev = n === prevLine && !isNext;
        const cls = ["code-line", isNext ? "next" : "", isPrev ? "prev" : "", n === errorLine ? "error" : ""].join(" ");
        return (
          <div className={cls} key={n}>
            <span className="marker">{isNext ? "➜" : isPrev ? "➜" : ""}</span>
            <span className="ln">{n}</span>
            <span className="src">{text || " "}</span>
          </div>
        );
      })}
    </div>
  );
}
