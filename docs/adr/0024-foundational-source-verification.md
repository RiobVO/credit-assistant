# ADR-0024 — Foundational source verification & replacement

* Status: accepted
* Date: 2026-05-19
* Tier: pre-demo polish (research debt closure)

## Context

В YAML rules engine (`config/rules/v1_uz_msb.yaml`) 9 из 19 правил ссылались
на 3 «foundational sources», достоверность которых не была проверена с момента
первичной авторизации (Phase 1, май 2025):

1. **«ЦБ РУз положение №27-п, п.4.5»** — упоминался как regulatory primary
   в 3 правилах (`REVENUE_DROP_MOM_30`, `REVENUE_DROP_YOY_50`,
   `NEGATIVE_PROFIT_3Q`).
2. **«НК РУз ст. 256»** — основа правила `VAT_ESF_MISMATCH`.
3. **«Group-IB Uzbekistan fraud report 2024-2025»** — единственный source
   для 5 AML-правил (`DIRECTOR_CHANGED_6M`, `OKVED_CHANGED_12M`,
   `NEW_COUNTERPARTY_LARGE_SHARE`, `SHELL_COMPANY_PARTNERS`,
   `CIRCULAR_INVOICING`).

При smoke-тесте обнаружен product gap (заявка `BR-2026-0050 TEST` получила
score 100 на partial data) — это запустило независимый research через 3 модели
(Claude Research, ChatGPT Deep Research, Qwen) с целью аудита всех 19 правил
и foundational sources. См. `docs/research/2026-05-19-3way-reconcile/`.

Research выявил **3 критичные ошибки атрибуции**:

### (1) «ЦБ РУз №27-п» — НЕ СУЩЕСТВУЕТ

Нумерация «XX-П» характерна для Банка России (ЦБ РФ), но не для ЦБ РУз.
Действующий нормативный акт ЦБ РУз по классификации активов:

**Положение «О порядке классификации качества активов и формирования
резервов на покрытие возможных потерь по активам, а также их использования
в коммерческих банках»** — рег. **№ 2696 от 14.07.2015** (Постановление
Правления ЦБ РУз №14/5 от 13.06.2015). URL: <https://lex.uz/ru/docs/2703056>.

Хронология редакций: 20.10.2015 → 11.10.2017 → 31.05.2018 → 28.07.2021 →
11.01.2022 (рег. №2696-3) → 12.06.2023 → 22.06.2024 → **последняя редакция
№2696-5 от 23.12.2025, в силе с 25.01.2026** (URL:
<https://lex.uz/ru/docs/7942786>).

При этом — **Положение №2696 НЕ содержит количественных порогов** типа
«−30% MoM выручки», «3 убыточных квартала подряд». Классификация
качественная по 4 категориям (стандартный / субстандартный / сомнительный /
безнадёжный). Конкретные количественные триггеры в наших правилах = внутренняя
методология + Basel III SREP, а не ЦБ РУз №27-п.

### (2) «НК РУз ст. 256» — АТРИБУЦИЯ ОШИБОЧНА

В действующей редакции НК РУз (Закон РУз № ЗРУ-599 от 30.12.2019,
<https://lex.uz/ru/docs/4674893>) **ст. 256 регулирует определение
налоговой базы налоговыми агентами при операциях с государственным
имуществом** — это НДС с продажи госактивов, не про ЭСФ.

Правильная атрибуция для правила `VAT_ESF_MISMATCH`:

* **НК РУз ст. 47** — счёт-фактура (форма, обязательность).
* **НК РУз ст. 257** — корректировка налоговой базы.
* **ПКМ РУз №489** — порядок выставления ЭСФ.
* **ст. 175-1 КоАО РУз** — административные штрафы 5-10 БРВ
  (2 060 000-4 120 000 UZS) за первое нарушение, 10-20 БРВ за повторное.
* **НК РУз ст. 223** — штраф 20% за сокрытие налоговой базы.

### (3) «Group-IB UZ fraud report 2024-2025» — LOW confidence

Group-IB **публикует** UZ-материалы на корпоративном блоге:

* «Choose Your Fighter: A New Stage in the Evolution of Android SMS
  Stealers in Uzbekistan» (group-ib.com/blog/mobile-malware-uzbekistan/,
  19.12.2025).
* «Fighting Credit Fraud in Uzbekistan: An Uphill Battle»
  (group-ib.com/blog/credit-fraud-in-uzbekistan/).

Однако **детальные corporate SME fraud schemes** (shell companies, circular
invoicing, INN_age метрики) в опубликованных материалах **не описаны** —
Group-IB фокусируется на retail/mobile fraud, не на SME loan / corporate-AML
fraud. Для правил уровня `SHELL_COMPANY_PARTNERS`, `CIRCULAR_INVOICING` это
LOW confidence source.

## Decision

Заменить атрибуцию во всех 9 правилах согласно следующей таблице:

| Rule ID | Старая ссылка | Новая ссылка |
|---|---|---|
| REVENUE_DROP_MOM_30 | ЦБ РУз №27-п, п.4.5 | ЦБ РУз №2696 (lex.uz/ru/docs/2703056) + Basel III SREP |
| REVENUE_DROP_YOY_50 | ЦБ РУз №27-п | ЦБ РУз №2696 + Altman Z-score |
| NEGATIVE_PROFIT_3Q | ЦБ РУз №27-п | ЦБ РУз №2696 + BCBS d424 §50 + Altman |
| VAT_ESF_MISMATCH | НК РУз ст. 256 | НК РУз ст. 47 + ст. 257 + ПКМ №489 + ст. 175-1 КоАО + ст. 223 |
| DIRECTOR_CHANGED_6M | Group-IB UZ | FATF R.24 + Закон РУз ЗРУ-660 + внутренние методики |
| OKVED_CHANGED_12M | Group-IB UZ + internal | ПКМ №275 (UZ-ОКЭД) + FATF R.10 + внутренние методики |
| NEW_COUNTERPARTY_LARGE_SHARE | Group-IB UZ | FATF R.10 + ЗРУ-660 + EAG typology |
| SHELL_COMPANY_PARTNERS | Group-IB UZ + AML | FATF R.10 + R.24 + ЗРУ-660 + EAG |
| CIRCULAR_INVOICING | Group-IB UZ | НК РУз гл. 17 + EAG VAT carousel typology + ЗРУ-660 + FATF R.21 |

## Alternatives considered

1. **Keep current attributions + add «pending verification» note** — отвергнут:
   подложная цитата на demo подорвёт trust банкира.
2. **DEPRECATE правил без verified sources до получения первичных** — отвергнут:
   правила сами по себе valid (логика верная), только attribution ошибочна.
3. **Add UZ-banking partner credit policy citations** — отвергнут (для текущей
   итерации): policies non-public, требует NDA с пилот-банком; добавляем после
   pilot trip.

## Consequences

**Positive:**

* Аудитор / banker открывает lex.uz / fatf-gafi.org и видит реальный документ.
* Compliance trail в PDF досье corretto: source citations кликаются и
  резолвятся.
* Foundation для post-pilot research debt closure (real fixtures, internal
  bank methodologies через NDA).

**Negative:**

* `RuleSpecYaml` schema strict-validation не сломалось (source = string,
  без structured validation URL). Будущий taking — schema upgrade (validated
  URL list per source, см. backlog).
* Foundational sources MUST быть валидированы повторно при следующей
  redacции ЦБ РУз №2696 (после 2026 — отслеживать lex.uz/ru/docs/2703056).

**Neutral:**

* score behavior на 49 существующих dossiers не меняется — source — это
  только metadata для отображения в PDF, не входит в score computation.
  Перегенерация PDF (`?lang=ru|uz`) подхватит новые sources автоматически.

## Verification

* Pytest YAML loader (`RuleSpecYaml.name_uz min_length=1`, `Rule.source`)
  должен пройти на обновлённой YAML.
* Ruff / mypy strict — no changes к Python.
* Manual smoke: regenerate PDF досье `BR-2026-0048`, проверить footer источников
  в разделе F.

## Research debt remaining

Не покрыто этим ADR (backlog):

* **Q0.B per-rule audit**: 16 правил с verdict ADJUST из Claude research —
  thresholds правки (LOAN_TO_REVENUE 0.50 → 0.40 unsecured / 0.70 secured,
  VAT_ESF_MISMATCH 15% → 10% retest, sezonniy filter для MoM/YoY правил,
  и т.д.). Покрыто Commit 5 этой же сессии.
* **Q0.C категориальные gaps**: FX exposure, DSCR, working capital adequacy,
  cash flow quality, related-party transactions, off-balance commitments,
  microfinance stacking. Top-3 critical (FX/DSCR/WC) — Commit 4 этой сессии.
* **Q1 Confidence Layer**: замена правила `INSUFFICIENT_DATA` на multi-tier
  partial-data scoring (per FRB SR 11-7 / SR 26-02). Commit 2 этой сессии.
* **Q3 OKED-UZ benchmark catalog**: classifier verification (UZ-ОКЭД ред.2 per
  ПКМ №275 от 24.08.2016), 7 buckets с null + honest notes (UZ net margin
  medians не публикуются в открытых источниках). Commit 3 этой сессии.

## References

* Research outputs: `docs/research/2026-05-19-3way-reconcile/` (Claude / ChatGPT
  / Qwen 3-way reconcile).
* ЦБ РУз Положение №2696: <https://lex.uz/ru/docs/2703056>; посл. редакция
  2696-5 от 23.12.2025: <https://lex.uz/ru/docs/7942786>.
* НК РУз: <https://lex.uz/ru/docs/4674893>.
* Basel III (BCBS d424): <https://www.bis.org/bcbs/publ/d424.pdf>.
* FRB SR 26-02 (revised SR 11-7, April 2026):
  <https://www.federalreserve.gov/supervisionreg/srletters/SR2602.pdf>.
* FATF Recommendations: <https://www.fatf-gafi.org>.
* IMF FSAP Uzbekistan 2025:
  <https://documents1.worldbank.org/curated/en/099072925165040123/>.
* Group-IB UZ credit fraud blog: <https://www.group-ib.com/blog/credit-fraud-in-uzbekistan/>.
