"""SHELL_COMPANY_PARTNERS: юр-лица-контрагенты с ИНН моложе 6 месяцев."""

from datetime import date

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.counterparty import Counterparty
from domain.rules.counterparty.shell_company_partners import shell_company_partners
from domain.value_objects.inn import INN


def _snapshot(
    buyers: list[Counterparty] | None = None,
    suppliers: list[Counterparty] | None = None,
) -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=Borrower(
            inn=INN("123456789"),
            name="ООО",
            legal_form=LegalForm.LLC,
            registration_date=date(2020, 1, 1),
            director_name="Иванов",
            director_appointed_at=date(2020, 1, 1),
            okved_main="62.01",
            registered_address="Ташкент",
        ),
        as_of=date(2026, 5, 8),
        counterparties_buyers=buyers or [],
        counterparties_suppliers=suppliers or [],
    )


def _cp(
    inn_value: str,
    registered: date,
    *,
    opf: LegalForm | None = None,
) -> Counterparty:
    return Counterparty(
        inn=INN(inn_value),
        name=f"Контрагент {inn_value}",
        registration_date=registered,
        opf=opf,
    )


class TestShellCompanyPartners:
    def test_fires_when_buyer_younger_than_6_months(self) -> None:
        # ООО зарегистрирован 3 мес назад — fires.
        shell = _cp("111111111", date(2026, 2, 1), opf=LegalForm.LLC)
        ev = shell_company_partners(_snapshot(buyers=[shell]))
        assert ev is not None

    def test_fires_when_supplier_younger_than_6_months(self) -> None:
        shell = _cp("111111111", date(2026, 2, 1), opf=LegalForm.LLC)
        ev = shell_company_partners(_snapshot(suppliers=[shell]))
        assert ev is not None

    def test_silent_when_all_older_than_6_months(self) -> None:
        old = _cp("111111111", date(2024, 1, 1), opf=LegalForm.LLC)
        assert shell_company_partners(_snapshot(buyers=[old], suppliers=[old])) is None

    def test_silent_with_no_counterparties(self) -> None:
        assert shell_company_partners(_snapshot()) is None

    def test_lists_all_shell_inns_in_evidence(self) -> None:
        shell1 = _cp("111111111", date(2026, 2, 1), opf=LegalForm.LLC)
        shell2 = _cp("222222222", date(2026, 3, 1), opf=LegalForm.JSC)
        old = _cp("333333333", date(2020, 1, 1), opf=LegalForm.LLC)
        ev = shell_company_partners(_snapshot(buyers=[shell1, old], suppliers=[shell2]))
        assert ev is not None
        assert ev.evidence["shell_count"] == 2


class TestShellCompanyPartnersIeExclusion:
    """ADR-0024 Session 3: ИП исключаются — регистрация 1-2 дня, молодой ИП = норма."""

    def test_silent_when_young_counterparty_is_individual_entrepreneur(self) -> None:
        # ИП зарегистрирован 1 мес назад — silent.
        young_ie = _cp("111111111", date(2026, 4, 1), opf=LegalForm.IE)
        ev = shell_company_partners(_snapshot(buyers=[young_ie]))
        assert ev is None

    def test_fires_when_young_counterparty_is_llc(self) -> None:
        # Молодой ООО — fires (старая логика).
        young_llc = _cp("111111111", date(2026, 4, 1), opf=LegalForm.LLC)
        ev = shell_company_partners(_snapshot(buyers=[young_llc]))
        assert ev is not None

    def test_fires_conservative_when_opf_unknown(self) -> None:
        # opf=None (legacy / data source без поля) — conservative read,
        # fires как старая логика.
        young_unknown = _cp("111111111", date(2026, 4, 1), opf=None)
        ev = shell_company_partners(_snapshot(buyers=[young_unknown]))
        assert ev is not None
