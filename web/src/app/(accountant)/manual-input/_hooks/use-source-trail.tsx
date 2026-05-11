// CA-035: React Context для source_trail из CA-027 multi-file dropzone.
//
// ParsedFilesDropzone (Шаг 2) push'ит source_trail после successful response,
// Checklist (Шаг 3) читает для запроса POST /api/manual-input/readiness.
// Form state не используется: source_trail — UI-only memory, не «контракт
// формы» и не передаётся в финальный POST /api/manual-input.

"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

type SourceTrail = Record<string, string>;

type SourceTrailContextValue = {
  sourceTrail: SourceTrail;
  setSourceTrail: (next: SourceTrail) => void;
  mergeSourceTrail: (patch: SourceTrail) => void;
  resetSourceTrail: () => void;
};

const SourceTrailContext = createContext<SourceTrailContextValue | null>(null);

export function SourceTrailProvider({ children }: { children: ReactNode }) {
  const [sourceTrail, setSourceTrailState] = useState<SourceTrail>({});

  const setSourceTrail = useCallback((next: SourceTrail) => {
    setSourceTrailState(next);
  }, []);

  const mergeSourceTrail = useCallback((patch: SourceTrail) => {
    setSourceTrailState((prev) => ({ ...prev, ...patch }));
  }, []);

  const resetSourceTrail = useCallback(() => {
    setSourceTrailState({});
  }, []);

  const value = useMemo(
    () => ({ sourceTrail, setSourceTrail, mergeSourceTrail, resetSourceTrail }),
    [sourceTrail, setSourceTrail, mergeSourceTrail, resetSourceTrail],
  );

  return (
    <SourceTrailContext.Provider value={value}>
      {children}
    </SourceTrailContext.Provider>
  );
}

export function useSourceTrail(): SourceTrailContextValue {
  const ctx = useContext(SourceTrailContext);
  if (ctx === null) {
    throw new Error(
      "useSourceTrail must be used within <SourceTrailProvider />",
    );
  }
  return ctx;
}
