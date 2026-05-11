// CA-055: «откуда я пришёл» для досье back-button.
//
// Проблема: router.back() слеп — если предыдущая entry в browser history
// `/manual-input?draft=X`, аналитик попадает на пустую форму после
// submit (draft удалён в БД).
//
// Решение: «список»-страницы (`/search`, `/history`) при mount пишут себя
// в sessionStorage. ActionBar читает оттуда; если нет — fallback по
// APP_MODE. Это даёт predictable back:
//   /search   → dossier → Назад → /search    (запомнено)
//   /history  → dossier → Назад → /history   (запомнено)
//   /manual-input → dossier → Назад → /history (fallback, потому что
//                                              manual-input не сохраняется
//                                              как back target)
//   direct URL → Назад → /history (fallback)
//
// Per-tab (sessionStorage, не localStorage) — каждая вкладка независима.

const KEY = "ca:dossier-back-target";

export function rememberBackTarget(path: string): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(KEY, path);
  } catch {
    // Приватный режим / quota — игнорируем, ActionBar упадёт на fallback.
  }
}

export function consumeBackTarget(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}
