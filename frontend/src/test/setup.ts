import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// Browser APIs Radix UI relies on that jsdom does not implement.
Element.prototype.hasPointerCapture ??= () => false;
Element.prototype.setPointerCapture ??= () => {};
Element.prototype.releasePointerCapture ??= () => {};
Element.prototype.scrollIntoView ??= () => {};
// Used by the toast library to follow the system colour scheme.
window.matchMedia ??= (query: string) =>
  ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }) as MediaQueryList;
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock the auth context for all tests
vi.mock("../contexts/AuthContext", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual as any,
    useAuth: () => ({
      user: { id: "123", email: "admin@rotpunkt.de", role: "admin", is_active: true },
      token: "fake-token",
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
  };
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  localStorage.clear();
});
