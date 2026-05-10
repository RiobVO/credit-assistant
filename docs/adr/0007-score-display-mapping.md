# ADR 0007: Score display mapping (domain ↔ banking)

- **Status**: Accepted
- **Date**: 2026-05-10
- **Phase**: 3 (подфаза 3.B)

## Context

`ScoringService` (см. ADR 0003) считает risk score по схеме «больше — хуже»:
веса severity суммируются, итоговое число клампается до 100. Калибровка v1:
`<15` → APPROVE, `15..29` → REVIEW, `≥30` → REJECT. То есть **0 — идеально,
100 — катастрофа**.

Дизайн экрана досье (Phase 3.A, файл `пдф.png`) построен на banking-style
gauge — полудуга с 4 цветными секторами слева направо
(red → orange → yellow → green) и подписью «73 / 100». Здесь интуиция
обратная: **100 — отлично, 0 — отказ**. Это привычная UX-конвенция в
кредитном скоринге (FICO, RBI, ЦБ РУз внутренние методики), от которой нет
смысла отказываться — она ложится на «больше — лучше» из мира credit cards
и risk-tolerance.

Прямое использование domain score на UI неудобно:
- инвертированная шкала «зелёный слева, красный справа» отпугнёт банкиров;
- подпись «12 / 100 — рекомендация одобрить» читается как «12 баллов из 100»,
  что вызывает противоречие.

## Decision

Backend в `RiskScoreOutput` отдаёт **оба** числа:

```python
class RiskScoreOutput(_StrictModel):
    score: int          # raw domain (lower=better), для аудита и логов
    display_score: int  # 100 − score (clamped 0..100), banking-style higher=better
    recommendation: RecommendationCode
    severity_breakdown: dict[SeverityCode, int]
```

Маппинг — pure function в `interfaces/api/shared/dossier_mapper.py`:

```python
def _to_display_score(domain_score: int) -> int:
    return max(0, min(100, 100 - domain_score))
```

Frontend (gauge / badge / любое user-facing место) использует
`display_score`. Domain-`score` остаётся в payload — для журнала аудита
и сравнения версий правил.

## Consequences

**Плюсы**
- Domain логика остаётся интуитивной для разработчика: `score=0` = чистый
  заёмщик, веса severity накапливают плохие новости.
- UI-конвенция совпадает с интуицией банкира; не нужно переучивать пользователя.
- В одном payload видны оба числа — аудитор не теряет связь между внутренней
  калибровкой и тем, что показано клиенту.

**Минусы**
- Дублирование информации в JSON (минорно: два int).
- Новые члены команды должны помнить, что в коде domain-числа «инвертированы»
  относительно UI. Снято комментариями в `RiskScoreOutput` и в gauge-компоненте.

**Возможные альтернативы (отклонены)**
- B — оставить только domain score, перевернуть gauge визуально (зелёный слева).
  Отклонено: ломает узнаваемость banking-UX, требует ручного перепроверивания
  оси при каждом изменении дизайна.
- C — заменить domain score на display, считать «больше — лучше» во всех слоях.
  Отклонено: расходится с интуицией экспоненциального суммирования severity
  (см. ADR 0003), требует переписать ScoringService.

## Notes

`ScoringService.MAX_SCORE = 100` уже клампит domain score; повторный clamp в
`_to_display_score` — страховка на случай будущих изменений калибровки
(если решим расширить шкалу до >100, mapping не выдаст отрицательные числа).

Когда в Phase 3.C появится PDF-отчёт, тот же display_score уйдёт в шапку
дашборда. Аудиторам банка в приложении к PDF удобнее видеть raw `score` и
recommendation — это уже отдельный контракт оформлять не надо, у нас оба
числа уже едут в одном объекте.
