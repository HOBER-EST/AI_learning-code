import "@testing-library/jest-dom/vitest";

// jsdom has no layout engine; the diagram only needs these to exist.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
