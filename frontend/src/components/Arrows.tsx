import { useLayoutEffect, useRef, useState } from "react";

interface ArrowPath {
  key: string;
  d: string;
  highlight: boolean;
}

/**
 * Draws pointer arrows over its parent element (which must be positioned).
 * Any element with ``data-ref="<id>"`` is an arrow source; the element with
 * ``data-obj-id="<id>"`` is its target. Positions are measured after layout,
 * and re-measured on resize. ``version`` must change whenever content changes.
 */
export function Arrows({ version }: { version: unknown }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [paths, setPaths] = useState<ArrowPath[]>([]);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useLayoutEffect(() => {
    // The svg's own ref is attached before this effect runs; a ref on the
    // parent element would not be on first mount.
    const el = svgRef.current?.parentElement;
    if (!el) return;
    const compute = () => {
      const base = el.getBoundingClientRect();
      const ox = base.left - el.scrollLeft;
      const oy = base.top - el.scrollTop;
      const next: ArrowPath[] = [];
      el.querySelectorAll<HTMLElement>("[data-ref]").forEach((src, i) => {
        const target = el.querySelector<HTMLElement>(`[data-obj-id="${src.dataset.ref}"]`);
        if (!target) return;
        const a = src.getBoundingClientRect();
        const b = target.getBoundingClientRect();
        const x1 = a.left + a.width / 2 - ox;
        const y1 = a.top + a.height / 2 - oy;
        let d: string;
        if (b.left - ox >= x1 + 8) {
          const x2 = b.left - ox;
          const y2 = b.top - oy + (b.height < 60 ? b.height / 2 : 14);
          const dx = Math.max(24, (x2 - x1) / 2);
          d = `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`;
        } else {
          // Target is to the left (or overlapping): enter from the top.
          const x2 = b.left - ox + Math.min(18, b.width / 2);
          const y2 = b.top - oy;
          d = `M${x1},${y1} C${x1 + 50},${y1 - 10} ${x2},${y2 - 50} ${x2},${y2}`;
        }
        next.push({ key: `${i}-${src.dataset.ref}`, d, highlight: src.dataset.hl === "1" });
      });
      setPaths(next);
      setSize({ width: el.scrollWidth, height: el.scrollHeight });
    };
    compute();
    const observer = new ResizeObserver(compute);
    observer.observe(el);
    for (const child of Array.from(el.children)) observer.observe(child);
    return () => observer.disconnect();
  }, [version]);

  return (
    <svg ref={svgRef} className="arrows" width={size.width} height={size.height} aria-hidden="true">
      <defs>
        <marker id="arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" />
        </marker>
        <marker id="arrowhead-hl" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" style={{ fill: "var(--line-next)" }} />
        </marker>
      </defs>
      {paths.map((p) => (
        <path
          key={p.key}
          d={p.d}
          className={p.highlight ? "highlight" : undefined}
          markerEnd={p.highlight ? "url(#arrowhead-hl)" : "url(#arrowhead)"}
        />
      ))}
    </svg>
  );
}
