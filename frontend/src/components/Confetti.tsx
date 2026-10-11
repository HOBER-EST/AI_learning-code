import { useMemo } from "react";

const COLORS = ["#2b5bd7", "#18804a", "#e0a422", "#d64545", "#8a5cd6", "#1aa3b8"];

/** A short, dependency-free burst of confetti. Remount (change `key`) to replay. */
export function Confetti({ pieces = 36 }: { pieces?: number }) {
  const bits = useMemo(
    () =>
      Array.from({ length: pieces }, (_, i) => ({
        left: 10 + Math.random() * 80,
        dx: (Math.random() - 0.5) * 260,
        delay: Math.random() * 0.25,
        rotate: Math.random() * 720 - 360,
        color: COLORS[i % COLORS.length],
        wide: Math.random() > 0.5,
      })),
    [pieces],
  );
  return (
    <div className="confetti" aria-hidden="true">
      {bits.map((b, i) => (
        <span
          key={i}
          style={
            {
              left: `${b.left}%`,
              background: b.color,
              width: b.wide ? 10 : 6,
              animationDelay: `${b.delay}s`,
              "--dx": `${b.dx}px`,
              "--rot": `${b.rotate}deg`,
            } as React.CSSProperties
          }
        />
      ))}
    </div>
  );
}
