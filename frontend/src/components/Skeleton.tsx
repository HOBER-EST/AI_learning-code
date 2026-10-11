/** Placeholder blocks shown while data loads. */
export function Skeleton({ lines = 3, card = false }: { lines?: number; card?: boolean }) {
  return (
    <div className={card ? "card card-body" : undefined} aria-busy="true" aria-label="加载中">
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="skeleton" style={{ width: `${92 - ((i * 17) % 35)}%` }} />
      ))}
    </div>
  );
}

export function SkeletonGrid({ count = 6 }: { count?: number }) {
  return (
    <div className="exercise-grid">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="card card-body">
          <div className="skeleton" style={{ width: "70%", height: 16 }} />
          <div className="skeleton" style={{ width: "30%" }} />
          <div className="skeleton" style={{ width: "55%" }} />
        </div>
      ))}
    </div>
  );
}
