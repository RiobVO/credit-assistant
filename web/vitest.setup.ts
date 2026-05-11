// CA-040: подключает кастомные матчеры jest-dom (toBeInTheDocument, toHaveTextContent, ...)
// к expect через автоматический expect.extend.
import "@testing-library/jest-dom/vitest";

// RTL auto-cleanup полагается на глобальный afterEach. С vitest globals=false
// глобалов нет → DOM протекает между тестами. Регистрируем cleanup явно.
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
