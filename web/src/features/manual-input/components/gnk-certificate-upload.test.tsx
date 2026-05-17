// T0.3.1 RTL — GnkCertificateUpload: 3 critical paths.
//   - innValid=false → подсказка «введите ИНН», форма не показана
//   - innValid=true + GET 404 → форма видна, можно загружать
//   - innValid=true + GET 200 → summary справки, форма скрыта

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ru from "../../../i18n/ru.json";
import { GnkCertificateUpload } from "./gnk-certificate-upload";

function renderWithIntl(ui: React.ReactNode) {
  return render(
    <NextIntlClientProvider locale="ru" messages={ru}>
      {ui}
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("GnkCertificateUpload", () => {
  it("показывает подсказку и не рендерит форму при невалидном ИНН", () => {
    renderWithIntl(<GnkCertificateUpload inn="123" innValid={false} />);
    expect(
      screen.getByText(/Введите ИНН \(9 цифр\)/),
    ).toBeInTheDocument();
    expect(screen.queryByRole("form")).not.toBeInTheDocument();
  });

  it("рендерит форму загрузки когда ИНН валиден и справки ещё нет (404)", async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response("", { status: 404 }),
    );
    renderWithIntl(<GnkCertificateUpload inn="305002665" innValid />);
    await waitFor(() => {
      expect(
        screen.getByRole("form", { name: /Форма загрузки/ }),
      ).toBeInTheDocument();
    });
    expect(screen.getByText(/ГНК-справка/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Загрузить/ }),
    ).toBeDisabled(); // без файла и full_name
  });

  it("показывает summary существующей справки и скрывает форму", async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          file_id: "11111111-2222-3333-4444-555555555555",
          borrower_inn: "305002665",
          full_name: '"ZAMIN NOZ NEMATLARI" MCHJ',
          status: "active",
          okveds: ["47.11", "47.19"],
          source: "uploaded",
          cert_id: "GNK-2026-1",
          uploaded_at: "2026-05-18T10:00:00Z",
          uploaded_by_analyst_id: null,
        }),
        { status: 200 },
      ),
    );
    renderWithIntl(<GnkCertificateUpload inn="305002665" innValid />);
    await waitFor(() => {
      expect(screen.getByTestId("gnk-cert-summary")).toBeInTheDocument();
    });
    expect(screen.getByText('"ZAMIN NOZ NEMATLARI" MCHJ')).toBeInTheDocument();
    expect(screen.getByText(/активный плательщик/)).toBeInTheDocument();
    expect(screen.getByText(/47.11, 47.19/)).toBeInTheDocument();
    expect(screen.getByText("GNK-2026-1")).toBeInTheDocument();
    // Кнопка «Загрузить заново» переводит в режим формы.
    fireEvent.click(screen.getByRole("button", { name: /Загрузить заново/ }));
    await waitFor(() => {
      expect(screen.queryByTestId("gnk-cert-summary")).not.toBeInTheDocument();
    });
    expect(
      screen.getByRole("form", { name: /Форма загрузки/ }),
    ).toBeInTheDocument();
  });

  it("отвергает файл с неподдерживаемым mime-type на клиенте", async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response("", { status: 404 }),
    );
    renderWithIntl(<GnkCertificateUpload inn="305002665" innValid />);
    await waitFor(() => {
      expect(screen.getByRole("form", { name: /Форма загрузки/ })).toBeInTheDocument();
    });
    const fileInput = screen.getByLabelText(/Файл справки/) as HTMLInputElement;
    const badFile = new File([new Uint8Array([1, 2])], "x.docx", {
      type: "application/vnd.docx",
    });
    fireEvent.change(fileInput, { target: { files: [badFile] } });
    expect(screen.getByText(/Формат не поддерживается/)).toBeInTheDocument();
  });
});
