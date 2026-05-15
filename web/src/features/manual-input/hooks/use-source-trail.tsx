// CA-035: React Context для source_trail из CA-027 multi-file dropzone.
//
// ParsedFilesDropzone (Шаг 2) push'ит source_trail после successful response,
// Checklist (Шаг 3) читает для запроса POST /api/manual-input/readiness.
// Form state не используется: source_trail — UI-only memory, не «контракт
// формы» и не передаётся в финальный POST /api/manual-input.
//
// CA-DS21: parsedValues — параллельный map form-path → normalized digits.
// Используется useFieldSourceState чтобы отличать `auto` (значение совпадает
// с тем, что положил парсер) от `auto-edited` (парсер заполнил, потом
// пользователь поправил). sourceTrail остаётся «откуда оно пришло»,
// parsedValues — «что именно положил парсер», чтобы сравнивать с current.

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
type ParsedValues = Record<string, string>;

type SourceTrailContextValue = {
  sourceTrail: SourceTrail;
  setSourceTrail: (next: SourceTrail) => void;
  mergeSourceTrail: (patch: SourceTrail) => void;
  resetSourceTrail: () => void;
  parsedValues: ParsedValues;
  mergeParsedValues: (patch: ParsedValues) => void;
  resetParsedValues: () => void;
};

const SourceTrailContext = createContext<SourceTrailContextValue | null>(null);

export function SourceTrailProvider({ children }: { children: ReactNode }) {
  const [sourceTrail, setSourceTrailState] = useState<SourceTrail>({});
  const [parsedValues, setParsedValuesState] = useState<ParsedValues>({});

  const setSourceTrail = useCallback((next: SourceTrail) => {
    setSourceTrailState(next);
  }, []);

  const mergeSourceTrail = useCallback((patch: SourceTrail) => {
    setSourceTrailState((prev) => ({ ...prev, ...patch }));
  }, []);

  const resetSourceTrail = useCallback(() => {
    setSourceTrailState({});
  }, []);

  const mergeParsedValues = useCallback((patch: ParsedValues) => {
    setParsedValuesState((prev) => ({ ...prev, ...patch }));
  }, []);

  const resetParsedValues = useCallback(() => {
    setParsedValuesState({});
  }, []);

  const value = useMemo(
    () => ({
      sourceTrail,
      setSourceTrail,
      mergeSourceTrail,
      resetSourceTrail,
      parsedValues,
      mergeParsedValues,
      resetParsedValues,
    }),
    [
      sourceTrail,
      setSourceTrail,
      mergeSourceTrail,
      resetSourceTrail,
      parsedValues,
      mergeParsedValues,
      resetParsedValues,
    ],
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
