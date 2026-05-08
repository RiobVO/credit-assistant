"""Классификация типа .xltx-выгрузки из my3.soliq.uz по содержимому workbook.

Каждая форма (Расчёт НДС, ilova-реестр ЭСФ, Форма №1 баланс, Форма №2 финрезультаты,
Расчёт налога на прибыль) имеет уникальную сигнатуру в первом листе ``list01``.
Детектор не парсит данные — только выбирает специализированный парсер.
"""

from enum import StrEnum

from openpyxl.workbook.workbook import Workbook


class SoliqXltxFormat(StrEnum):
    VAT_DECLARATION = "vat_declaration"
    VAT_REGISTRY_ILOVA = "vat_registry_ilova"
    FORM_2_INCOME_STATEMENT = "form_2_income_statement"
    FORM_1_BALANCE_SHEET = "form_1_balance_sheet"
    PROFIT_TAX = "profit_tax"
    UNKNOWN = "unknown"


# Sentinel-фразы (нормализованные substrings), по которым опознаём форму. Сравнение
# case-sensitive — формы Soliq стабильно используют одну и ту же редакцию текста.
_VAT_DECLARATION_SENTINEL = "СВЕДЕНИЯ о плательщике налога на добавленную стоимость"
_VAT_REGISTRY_SENTINEL = "Реестр счетов-фактур"
_FORM_2_SENTINEL = "Отчет о финансовых результатах"
_FORM_1_SENTINEL = "Бухгалтерский баланс"
_PROFIT_TAX_SENTINEL = "налога на прибыль"


def detect_format(wb: Workbook) -> SoliqXltxFormat:
    """Определить тип выгрузки по сигнатурным ячейкам list01.

    Возвращает ``UNKNOWN``, если list01 отсутствует или ни одна сигнатура не совпала.
    """
    if "list01" not in wb.sheetnames:
        return SoliqXltxFormat.UNKNOWN
    ws = wb["list01"]

    def text(coord: str) -> str:
        v = ws[coord].value
        return str(v) if v is not None else ""

    if _VAT_DECLARATION_SENTINEL in text("D8"):
        return SoliqXltxFormat.VAT_DECLARATION

    # Ilova-реестр: либо B9 (Таблица №1, закупки), либо list02 B9 (Таблица №2, продажи).
    # Для устойчивости проверяем оба возможных места (file может быть только Таблицей №2).
    if _VAT_REGISTRY_SENTINEL in text("B9") or _VAT_REGISTRY_SENTINEL in text("B8"):
        return SoliqXltxFormat.VAT_REGISTRY_ILOVA

    if _FORM_1_SENTINEL in text("B3"):
        return SoliqXltxFormat.FORM_1_BALANCE_SHEET

    if _FORM_2_SENTINEL in text("B3"):
        return SoliqXltxFormat.FORM_2_INCOME_STATEMENT

    if _PROFIT_TAX_SENTINEL in text("B2"):
        return SoliqXltxFormat.PROFIT_TAX

    return SoliqXltxFormat.UNKNOWN
