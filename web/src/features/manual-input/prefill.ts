// CA-058: pre-fill Шага 1 при «Пересобрать с дополнениями» из досье.
//
// ActionBar на досье запоминает borrower-карточку в sessionStorage перед
// переходом на /manual-input?inn=X. manual-input-view при mount читает
// (только если нет draft) и через form.reset наполняет Шаг 1. Затем
// чистит ключ — повторный mount не подхватит stale data.
//
// Семантика: borrower-данные (ОПФ, ОКВЭД, директор, адрес, даты) реально
// не меняются между submit'ами, аналитик не должен переписывать их при
// каждой пересборке. Финансы (Шаг 2) и кредит (Шаг 3) — заново, потому
// что они меняются, и именно для них аналитик пересобирает досье.
//
// Per-tab (sessionStorage). LocalStorage был бы опасен — pre-fill утёк бы
// в другие вкладки.

const KEY = "ca:manual-input-prefill-step1";

export type Step1Prefill = {
  inn: string;
  name: string;
  legal_form: string;
  registration_date: string;
  director_name: string;
  director_appointed_at: string;
  okved_main: string;
  registered_address: string;
};

export function rememberStep1Prefill(data: Step1Prefill): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify(data));
  } catch {
    // Приватный режим / quota — игнорируем, аналитик заполнит руками.
  }
}

export function consumeStep1Prefill(): Step1Prefill | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(KEY);
    if (raw === null) return null;
    window.sessionStorage.removeItem(KEY);
    return JSON.parse(raw) as Step1Prefill;
  } catch {
    return null;
  }
}
