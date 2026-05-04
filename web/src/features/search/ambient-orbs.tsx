"use client";

import { useEffect, useRef } from "react";

// Phase 2 (DS-PHASE-2): два ambient orb (brand-soft + cool-tint) с медленным
// CSS-drift'ом + mouse-параллакс (±14px) на внешнем shell. Two-layer wrap:
// внешний — JS-параллакс, внутренний — CSS-keyframe drift. Без вложения они
// конфликтуют (одно transform на элементе).
export function AmbientOrbs() {
  const aRef = useRef<HTMLDivElement>(null);
  const bRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let mx = 0;
    let my = 0;
    let cx = 0;
    let cy = 0;
    let raf = 0;

    const onMove = (e: MouseEvent): void => {
      mx = (e.clientX / window.innerWidth - 0.5) * 2;
      my = (e.clientY / window.innerHeight - 0.5) * 2;
    };

    const tick = (): void => {
      cx += (mx - cx) * 0.04;
      cy += (my - cy) * 0.04;
      const a = aRef.current;
      const b = bRef.current;
      if (a) a.style.transform = `translate3d(${cx * -14}px, ${cy * -10}px, 0)`;
      if (b) b.style.transform = `translate3d(${cx * 14}px, ${cy * 10}px, 0)`;
      raf = requestAnimationFrame(tick);
    };

    window.addEventListener("mousemove", onMove);
    raf = requestAnimationFrame(tick);
    return () => {
      window.removeEventListener("mousemove", onMove);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <>
      <div
        ref={aRef}
        aria-hidden
        className="pointer-events-none fixed top-[-180px] right-[-80px] z-0 will-change-transform"
      >
        <div className="will-change-transform [animation:ds-orb-drift-a_36s_ease-in-out_infinite]">
          <div
            className="size-[620px] rounded-full opacity-45"
            style={{
              background:
                "radial-gradient(closest-side, color-mix(in oklab, var(--brand-primary) 40%, transparent) 0%, transparent 70%)",
              filter: "blur(120px)",
            }}
          />
        </div>
      </div>
      <div
        ref={bRef}
        aria-hidden
        className="pointer-events-none fixed bottom-[-240px] left-[8%] z-0 will-change-transform"
      >
        <div className="will-change-transform [animation:ds-orb-drift-b_48s_ease-in-out_infinite]">
          <div
            className="size-[480px] rounded-full opacity-55"
            style={{
              background:
                "radial-gradient(closest-side, color-mix(in oklab, var(--ink-1) 8%, transparent) 0%, transparent 72%)",
              filter: "blur(120px)",
            }}
          />
        </div>
      </div>
    </>
  );
}
