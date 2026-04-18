"""Типизированные ошибки парсера Soliq xltx-форм (my3.soliq.uz)."""


class SoliqXltxParseError(ValueError):
    """Базовый класс ошибок парсинга .xltx-выгрузок из my3.soliq.uz."""


class UnsupportedFormatError(SoliqXltxParseError):
    """Файл не распознан как одна из поддерживаемых форм. Несёт sheet-листинг
    для диагностики (что увидели вместо ожидаемых форм)."""

    def __init__(self, sheet_names: list[str], reason: str = "unknown form") -> None:
        super().__init__(f"{reason}; sheets={sheet_names}")
        self.sheet_names = sheet_names
        self.reason = reason


class MalformedXltxError(SoliqXltxParseError):
    """Файл правильного типа, но конкретная ячейка/строка невалидна.

    ``sheet`` и ``coord`` указывают на проблемное место (например ``list02!H15``).
    ``row_no`` опционален — для построчного парсинга реестра ЭСФ.
    """

    def __init__(
        self,
        *,
        sheet: str,
        coord: str,
        reason: str,
        row_no: int | None = None,
    ) -> None:
        location = f"{sheet}!{coord}" if row_no is None else f"{sheet}!{coord} (row {row_no})"
        super().__init__(f"{location}: {reason}")
        self.sheet = sheet
        self.coord = coord
        self.reason = reason
        self.row_no = row_no
