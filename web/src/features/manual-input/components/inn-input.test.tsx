// CA-DS20a: RTL-тесты на InnInput state machine.
//
// Покрываем переходы:
//   idle → checking (на blur с 9 цифрами, debounce 700ms) → verified
//   any value change → idle (через setTimeout 0)
//   blur empty → idle
//   blur с <9 цифр → invalid (border red, без pill)
//   verified + blur без правки → НЕ flash checking повторно

import { fireEvent, render, screen, act } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ru from "../../../i18n/ru.json";
import { InnInput } from "./step-1-borrower";

const CHECK_DELAY_MS = 700;

function renderInn(initial = "") {
  let lastValue = initial;
  let lastBlurCount = 0;
  function Harness() {
    const [value, setValue] = useState(initial);
    const [invalid, setInvalid] = useState(false);
    return (
      <NextIntlClientProvider locale="ru" messages={ru}>
        <InnInput
          value={value}
          onChange={(v) => {
            setValue(v);
            lastValue = v;
            // Внешний invalid снимаем при правке — mirror real wrapper.
            setInvalid(false);
          }}
          onBlur={() => {
            lastBlurCount += 1;
          }}
          invalid={invalid}
        />
      </NextIntlClientProvider>
    );
  }
  const utils = render(<Harness />);
  return {
    ...utils,
    input: utils.container.querySelector("input")!,
    getValue: () => lastValue,
    getBlurCount: () => lastBlurCount,
  };
}

describe("InnInput state machine (CA-DS20a)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("initial render → idle pill", async () => {
    renderInn();
    // useEffect [value] делает setTimeout 0 → state становится idle асинхронно.
    await act(async () => {
      vi.advanceTimersByTime(0);
    });
    expect(screen.getByText(ru.accountant.manual_input.s1_inn_state_idle))
      .toBeInTheDocument();
  });

  it("ввод 9 цифр + blur → checking → verified через 700ms", async () => {
    const { input } = renderInn();
    await act(async () => {
      vi.advanceTimersByTime(0);
    });

    fireEvent.change(input, { target: { value: "123456789" } });
    await act(async () => {
      vi.advanceTimersByTime(0);
    });

    fireEvent.blur(input);
    // Сразу после blur должен быть checking pill (без advance таймера 700).
    expect(
      screen.getByText(ru.accountant.manual_input.s1_inn_state_checking),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(ru.accountant.manual_input.s1_inn_state_verified),
    ).not.toBeInTheDocument();

    // Прошло 700ms → verified.
    await act(async () => {
      vi.advanceTimersByTime(CHECK_DELAY_MS);
    });
    expect(
      screen.getByText(ru.accountant.manual_input.s1_inn_state_verified),
    ).toBeInTheDocument();
    // Резюме mock-фирмы рядом с verified pill.
    expect(
      screen.getByText(ru.accountant.manual_input.s1_inn_summary_mock),
    ).toBeInTheDocument();
  });

  it("ввод не-цифр фильтруется + макс 9 символов", async () => {
    const { input, getValue } = renderInn();
    await act(async () => {
      vi.advanceTimersByTime(0);
    });

    fireEvent.change(input, { target: { value: "abc12345" } });
    await act(async () => {
      vi.advanceTimersByTime(0);
    });
    expect(getValue()).toBe("12345");

    fireEvent.change(input, { target: { value: "1234567890123" } });
    await act(async () => {
      vi.advanceTimersByTime(0);
    });
    expect(getValue()).toBe("123456789");
  });

  it("blur с <9 цифр → invalid (без pill, без verified)", async () => {
    const { input } = renderInn();
    await act(async () => {
      vi.advanceTimersByTime(0);
    });

    fireEvent.change(input, { target: { value: "12345" } });
    await act(async () => {
      vi.advanceTimersByTime(0);
    });

    fireEvent.blur(input);
    await act(async () => {
      vi.advanceTimersByTime(CHECK_DELAY_MS);
    });

    // Invalid state не показывает pill (только border) — checking/verified отсутствуют.
    expect(
      screen.queryByText(ru.accountant.manual_input.s1_inn_state_checking),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(ru.accountant.manual_input.s1_inn_state_verified),
    ).not.toBeInTheDocument();
    // Idle pill тоже НЕ показывается — invalid имеет свою пустую UI ветку.
    expect(
      screen.queryByText(ru.accountant.manual_input.s1_inn_state_idle),
    ).not.toBeInTheDocument();
  });

  it("blur с пустым value → idle", async () => {
    const { input } = renderInn();
    await act(async () => {
      vi.advanceTimersByTime(0);
    });

    fireEvent.blur(input);
    await act(async () => {
      vi.advanceTimersByTime(CHECK_DELAY_MS);
    });
    expect(
      screen.getByText(ru.accountant.manual_input.s1_inn_state_idle),
    ).toBeInTheDocument();
  });

  it("повторный blur после verified — НЕ flashит checking", async () => {
    const { input } = renderInn();
    await act(async () => {
      vi.advanceTimersByTime(0);
    });

    fireEvent.change(input, { target: { value: "987654321" } });
    await act(async () => {
      vi.advanceTimersByTime(0);
    });
    fireEvent.blur(input);
    await act(async () => {
      vi.advanceTimersByTime(CHECK_DELAY_MS);
    });
    // Verified.
    expect(
      screen.getByText(ru.accountant.manual_input.s1_inn_state_verified),
    ).toBeInTheDocument();

    // Повторный blur без изменения value: state остаётся verified, без
    // визуального flash «checking».
    fireEvent.blur(input);
    expect(
      screen.queryByText(ru.accountant.manual_input.s1_inn_state_checking),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(ru.accountant.manual_input.s1_inn_state_verified),
    ).toBeInTheDocument();
  });

  it("правка value после verified возвращает в idle", async () => {
    const { input } = renderInn();
    await act(async () => {
      vi.advanceTimersByTime(0);
    });

    fireEvent.change(input, { target: { value: "111111111" } });
    await act(async () => {
      vi.advanceTimersByTime(0);
    });
    fireEvent.blur(input);
    await act(async () => {
      vi.advanceTimersByTime(CHECK_DELAY_MS);
    });
    expect(
      screen.getByText(ru.accountant.manual_input.s1_inn_state_verified),
    ).toBeInTheDocument();

    // Меняем последнюю цифру → setTimeout 0 → state сбрасывается в idle.
    fireEvent.change(input, { target: { value: "111111112" } });
    await act(async () => {
      vi.advanceTimersByTime(0);
    });
    expect(
      screen.getByText(ru.accountant.manual_input.s1_inn_state_idle),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(ru.accountant.manual_input.s1_inn_state_verified),
    ).not.toBeInTheDocument();
  });

  it("onBlur prop callback дёргается на каждый blur", async () => {
    const { input, getBlurCount } = renderInn();
    await act(async () => {
      vi.advanceTimersByTime(0);
    });

    fireEvent.blur(input);
    fireEvent.blur(input);
    expect(getBlurCount()).toBe(2);
  });
});
