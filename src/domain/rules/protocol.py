"""Контракт правила: pure-функция от снапшота к флагу либо None."""

from collections.abc import Callable

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.red_flag import RedFlag

type RuleFn = Callable[[BorrowerSnapshot], RedFlag | None]
