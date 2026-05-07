# ADR 0003: Rules engine design

- **Status**: Accepted
- **Date**: 2026-05-08
- **Phase**: 1

## Context

Сердце продукта — 17 red-flag правил, которые читают досье заёмщика и помечают подозрительные паттерны. Требования:

1. Каждый банк-клиент попросит свою корректировку (пороги, severity, добавление правил) → конфигурация без правки кода.
2. Пилотирование = калибровка по реальным кейсам → severity и thresholds должны быть changeable отдельно от логики.
3. Каждое правило аудиториально проверяется → нужен явный источник (`RULE_SOURCE`) и след в evidence.
4. Правила тестируются изолированно от БД и API.

Альтернативы, которые рассмотрели:

- **DSL-движок** (например, JSON Logic, Drools): мощно, но требует обучения и DSL-компилятора. Pure-Python функции дают тот же expressiveness без overhead.
- **ML-скоринг (regression / GBDT)**: бриф (Section 11) запрещает до Phase 2 — на 17 правилах достаточно для v1.
- **Hardcoded правила без YAML**: severity и source повторно появляются в коде и в UI/отчётах → дубликат истины. YAML делает их edit-friendly.

## Decision

**Архитектура:** pure functions + YAML metadata + RuleRegistry + ScoringService.

```
config/rules/v1_uz_msb.yaml      ← severity / source / formula / rationale / version
        │
        ▼  yaml.safe_load + Pydantic-валидация
infrastructure/rules/yaml_schema.py
        │
        ▼  + CODE_RULES dict[id, fn]
infrastructure/rules/registry_factory.py  ← RuleConfigError при mismatch
        │
        ▼
domain/rules/rule.py · RuleRegistry      ← run_all(snapshot) → list[RedFlag]
                                              ▲
                                              │ упаковывает FiringEvidence
                                              │ + metadata из Rule в RedFlag
        ▼
domain/services/scoring_service.py        ← list[RedFlag] → RiskScore
```

Ключевые принципы:

1. **Pure rule = `(BorrowerSnapshot) → FiringEvidence | None`**. Без I/O, side-эффектов, состояния. Тестируется изолированно.
2. **Single source of truth для metadata = YAML.** id, name, severity, source, formula, rationale хранятся там. Код знает только id ↔ функция (через `CODE_RULES`).
3. **Mismatch fails at startup.** `load_registry()` падает с `RuleConfigError`, если YAML и code-registry не совпадают по id (в любом направлении). Регрессии ловим в boot-тесте.
4. **Severity weights калибруются.** Веса `LOW=1, MEDIUM=3, HIGH=7, CRITICAL=15` — эвристика выровненная по Базель III IRB intuition. Перекалибровка после Phase 2 на реальных кейсах.
5. **Recommendation thresholds:** `<15 APPROVE, 15-29 REVIEW, ≥30 REJECT`. Откалиброваны так, чтобы один CRITICAL + ~2 HIGH давал REJECT (реалистично для UZ-практики).
6. **Версия правил в RedFlag.** `rule_version` берётся из `RulesConfigYaml.version` — позволяет аудитировать прогон.

Скрытые инварианты:
- `domain/rules/` не зависит от `infrastructure/`. YAML loader живёт в `infrastructure/rules/`.
- BorrowerSnapshot — единственный вход правил. Адаптеры (Phase 2) формируют snapshot из источников; правила не знают форматов данных.
- `CIRCULAR_INVOICING` — упрощённый 2-cycle (TODO[CA-002] для full graph).

## Consequences

**Плюсы:**
- Новый банк → правка YAML без code change в 80% случаев.
- Правила покрываются unit-тестами без БД (coverage `src/domain/rules` = 99% на phase 1).
- Audit trail — `RedFlag.evidence` хранит конкретные числа, `rule_version` фиксирует версию правил.

**Минусы:**
- Дубликат: `id` правила и в YAML, и в `CODE_RULES`. Mitigated через mismatch-check на старте.
- YAML — eventually-consistent с кодом. Если кто-то добавил pure fn, но забыл YAML → fail at startup, не runtime. Это «фейлим рано, фейлим громко».
- Severity hardcoded в YAML, не в коде → код самого правила нельзя смотреть и понимать tier без YAML. Решено сознательно: это и есть смысл «metadata в YAML».

## Что сделать дальше (Phase 2)

- Реализовать адаптеры (SoliqExcelAdapter, EsfJsonAdapter, ManualInputAdapter), которые формируют BorrowerSnapshot.
- Прогнать engine на 5 папиных фирмах → собрать ground truth → откалибровать severity weights и thresholds.
- Полный graph cycle detection для `CIRCULAR_INVOICING` (`TODO[CA-002]`).
- Реализовать INN checksum по алгоритму ГНК РУз (`TODO[CA-001]`).

## References

- `PROJECT_BRIEF.md` Section 5 — каноническое описание 17 правил.
- `config/rules/v1_uz_msb.yaml` — текущий конфиг.
- `src/domain/rules/protocol.py` — контракт `RuleFn` и `FiringEvidence`.
- `src/domain/rules/rule.py` — RuleRegistry.run_all.
- `src/domain/services/scoring_service.py` — ScoringService с весами и thresholds.
- `src/infrastructure/rules/registry_factory.py` — связь YAML ↔ code.
