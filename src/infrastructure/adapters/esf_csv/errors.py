"""Типизированные ошибки парсера e-factura.uz CSV."""


class EsfParseError(ValueError):
    """Базовый класс ошибок парсинга ЭСФ-CSV."""


class MalformedFileError(EsfParseError):
    """Файл целиком невалидный: пустой, отсутствуют обязательные колонки,
    или ИНН заёмщика не встречается ни в одной строке."""


class MalformedRowError(EsfParseError):
    """Конкретная строка невалидна. Несёт ``row_no`` (1-индексированный, без
    учёта заголовка), чтобы пользователь мог открыть исходник и поправить."""

    def __init__(self, row_no: int, reason: str) -> None:
        super().__init__(f"row {row_no}: {reason}")
        self.row_no = row_no
        self.reason = reason
