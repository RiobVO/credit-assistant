"""DataSourcePort: контракт для адаптеров, читающих файловые источники.

Каждый файловый адаптер (ESF CSV, Soliq Excel) реализует этот protocol.
Manual input не файловый — он строит ``ManualChunk`` напрямую в API-слое
из Pydantic-схемы запроса, без порта.

Принцип:
- Парсер возвращает ровно один ``ParsedDataChunk``, никакой накопительной
  state, никаких side-effects. Чистый ``bytes-in → DTO-out``.
- ``borrower_inn`` приходит сверху (от пользователя через UI / API),
  адаптер использует его, чтобы определить направление в ЭСФ
  (продавец vs покупатель) и проверить, что файл соответствует заёмщику.
"""

from typing import BinaryIO, Protocol

from application.dto.parsed_data_chunk import ParsedDataChunk
from domain.value_objects.inn import INN


class DataSourcePort(Protocol):
    def parse(self, source: BinaryIO, borrower_inn: INN) -> ParsedDataChunk:
        """Прочитать файл и вернуть chunk; ошибки источника — типизированные."""
        ...
