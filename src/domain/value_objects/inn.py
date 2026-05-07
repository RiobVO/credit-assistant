"""ИНН Узбекистана: 9 цифр для юрлиц, 14 — для ИП/физлиц."""

from dataclasses import dataclass


class InvalidInnError(ValueError):
    """ИНН не прошёл базовую валидацию (длина или формат)."""


VALID_LENGTHS = (9, 14)


@dataclass(frozen=True, slots=True)
class INN:
    value: str

    def __post_init__(self) -> None:
        cleaned = self.value.strip()
        object.__setattr__(self, "value", cleaned)
        if len(cleaned) not in VALID_LENGTHS:
            raise InvalidInnError(
                f"INN length must be 9 or 14, got {len(cleaned)}",
            )
        if not cleaned.isdigit():
            raise InvalidInnError("INN must contain only digits")

    @property
    def masked(self) -> str:
        # Section 8 security: в логах показываем только последние 4 цифры
        return "X" * (len(self.value) - 4) + self.value[-4:]
