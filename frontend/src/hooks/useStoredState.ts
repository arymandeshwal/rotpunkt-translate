import { useEffect, useState } from "react";

/** useState that persists to localStorage. Falls back to the default on bad data. */
export function useStoredState<T>(
  key: string,
  defaultValue: T,
  isValid: (value: unknown) => value is T,
) {
  const [value, setValue] = useState<T>(() => {
    try {
      const stored: unknown = JSON.parse(localStorage.getItem(key) ?? "null");
      return isValid(stored) ? stored : defaultValue;
    } catch {
      return defaultValue;
    }
  });

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);

  return [value, setValue] as const;
}
