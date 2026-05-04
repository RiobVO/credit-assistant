"use client";

import { useEffect, useState } from "react";

// MediaQuery `prefers-reduced-motion` через React-хук. Для accessibility:
// count-up / sparkline draw / ring sweep на /search отключаются, если у юзера
// в OS выставлен «reduce motion». Возвращает true когда motion должен быть
// уменьшен.
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    // eslint-disable-next-line react-hooks/set-state-in-effect -- subscribe-to-system: initial sync media-query value, обновления через mql.change
    setReduced(mql.matches);
    const onChange = (e: MediaQueryListEvent): void => setReduced(e.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  return reduced;
}
