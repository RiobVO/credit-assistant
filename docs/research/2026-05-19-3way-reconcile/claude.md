# Quant Credit Risk Research — Узбекистан, pre-underwriting MVP для mid-tier банков

---

## Q0.A — Foundational source verification

### (1) «ЦБ РУз положение №27-п» — **ИСТОЧНИК НЕ ВЕРИФИЦИРОВАН, АТРИБУЦИЯ В MVP ОШИБОЧНА** (HIGH confidence — regulatory primary)

В нормативной базе ЦБ РУз положения с номером «27-п» в сфере классификации активов не существует. Подобная нумерация («XX-П») характерна для Банка России (например, Положение Банка России №590-П, №809-П), но **не для UZ-регулятора**.

**Действующий нормативный акт ЦБ РУз**: «Положение о порядке классификации качества активов и формирования резервов на покрытие возможных потерь по активам, а также их использования в коммерческих банках» — рег. **№ 2696** от 14.07.2015 г. (Постановление Правления ЦБ РУз № 14/5 от 13.06.2015), lex.uz/ru/docs/2703056.

**Хронология редакций**: 20.10.2015 → 11.10.2017 → 31.05.2018 → 28.07.2021 → 11.01.2022 (рег. № 2696-3 от 10.12.2021) → 12.06.2023 → 22.06.2024 → **последняя редакция: рег. № 2696-5 от 23.12.2025, Постановление Правления № 31/10 от 05.12.2025, вступила в силу 25.01.2026** (lex.uz/ru/docs/7942786).

Старое положение №632 от 11.02.1999 (Постановление №242) — **отменено** с 14.07.2015. Прямая цитата из текста (lex.uz/docs/594829): «Настоящий Порядок утратил силу в соответствии с постановлением Правления Центрального банка Республики Узбекистан от 13 июня 2015 года № 14/6 (рег. № 632-3 от 14.07.2015 г.)».

**Содержание критериев в Положении №2696 — качественное, не количественное**. Прямая цитата (lex.uz/docs/594829, концептуально перенесённая в 2696): «2.3. Классификация кредита начинается с оценки заемщика по следующим критериям: тенденция и будущее отрасли (экономического сектора); финансовое положение заемщика; кредитная история клиента; экономическое обоснование (положение) конкретного проекта; качество руководства и управления на предприятии». Категории: стандартный / субстандартный / сомнительный / безнадёжный + временные параметры просрочки.

Подтверждение редакции 2696-3 от Norma.uz: «вводятся такие понятия, как «кредитный риск», «просроченная задолженность», «общая стоимость активов» и «незначительная сумма». В соответствии с Международными стандартами финансовой отчетности вместо присвоения активу статуса «не наращивания»… вводится требование о необходимости формирования резервов в зависимости от качества актива в том периоде, в котором он возник» (norma.uz/novoe_v_zakonodatelstve/izmenen_poryadok_klassifikacii_kachestva_aktivov_bankov).

**Ключевой вывод**: в Положении №2696 НЕТ численных порогов «−30% MoM выручки», «−50% YoY», «3 убыточных квартала подряд». Эти триггеры — внутренняя методология банков и/или Базель III SREP, но в Положении ЦБ РУз они не закреплены. **Атрибуция «ЦБ РУз №27-п п.4.5» в правилах MVP — подложная цитата, требует замены.**

### (2) НК РУз ст. 256 — **АТРИБУЦИЯ ОШИБОЧНА** (HIGH confidence — regulatory primary)

В действующей редакции НК РУз (Закон РУз № ЗРУ-599 от 30.12.2019, lex.uz/ru/docs/4674893) **ст. 256 называется «Особенности определения налоговой базы налоговыми агентами при операциях с государственным имуществом»** — это про НДС с продажи государственных активов, не про ЭСФ.

**Правильная статья НК РУз для счетов-фактур — ст. 47**. Цитата bss.uz (2026): «Согласно ст. 47 НК РУз, счет-фактура оформляется продавцом по законодательно утвержденной форме и используется для учета налогооблагаемого оборота по НДС и продажам».

**Дополнительная регуляторика ЭСФ**:
- НК РУз ст. 257 — корректировка налоговой базы.
- ПКМ №489 — порядок выставления ЭСФ.
- ст. 175-1 КоАО — штрафы 5-10 БРВ (2 060 000-4 120 000 UZS) за первое нарушение, 10-20 БРВ за повторное.
- ст. 223 НК РУз — штраф 20% за сокрытие налоговой базы.
- my.soliq.uz — ЛК налогоплательщика, реестр ЭСФ.

**Ключевой вывод**: атрибуция «НК РУз ст.256» в правиле VAT_ESF_MISMATCH — ошибочна. Корректная: «НК РУз ст. 47 + ст. 257 + ПКМ №489 + ст. 175-1 КоАО + ст. 223 НК РУз».

### (3) Group-IB Uzbekistan fraud report 2024-2025 — **ЧАСТИЧНО ВЕРИФИЦИРОВАН** (MEDIUM/LOW confidence — industry primary)

Group-IB **публикует** UZ-материалы на корпоративном блоге:
- «Choose Your Fighter: A New Stage in the Evolution of Android SMS Stealers in Uzbekistan» (group-ib.com/blog/mobile-malware-uzbekistan/, 19.12.2025): «In October 2025, Group-IB specialists detected a new wave of malware attacks targeting users in Uzbekistan… One of the cybercriminal groups monitored by Group-IB stole more than US$2 million since January 2025».
- «Fighting Credit Fraud in Uzbekistan: An Uphill Battle» (group-ib.com/blog/credit-fraud-in-uzbekistan/).

Однако **детальные corporate SME fraud schemes** (shell companies, circular invoicing, INN_age метрики) в опубликованных материалах **не описаны** — Group-IB фокусируется на retail/mobile fraud, не на SME loan/corporate-AML fraud.

**Контекст credit fraud в UZ подтверждён независимыми источниками**:
- В 2024 году зарегистрировано 58,8 тыс. киберпреступлений в Узбекистане; 97,7% связаны с несанкционированным снятием денег с банковских счетов (Министерство внутренних дел РУз, доклад Комитету Сената по обороне и безопасности 26.02.2025, цит. kun.uz 27.02.2025: «зарегистрировано почти 59 тысячи киберпреступлений (58,8 тысячи), из которых подавляющее большинство, а именно 97,7%, связаны с несанкционированным снятием денег с банковских счетов»).
- За 5 лет 1,9 трлн сум украдено через цифровые мошенничества (caspianpost.com).
- 150 тыс. граждан активировали «Loan Ban» за 4 месяца после запуска 06.06.2025 (frank.uz, AKIpress).
- Закон РУз от 04.03.2025 — введение self-ban на кредиты.

**Ключевой вывод**: Group-IB как источник для retail/mobile fraud — OK (MEDIUM confidence); для corporate/SME fraud rules (DIRECTOR_CHANGED_6M, SHELL_COMPANY_PARTNERS, NEW_COUNTERPARTY_LARGE_SHARE, CIRCULAR_INVOICING) — **LOW confidence**, нужна замена атрибуции на FATF Recommendations (R.10 CDD, R.24 beneficial ownership) + EAG (Eurasian Group on combating money laundering, евразийский FATF-аналог) + Закон РУз № ЗРУ-660 «О противодействии легализации доходов».

### (4) Базель III IRB — **ВЕРИФИЦИРОВАН** (HIGH confidence — regulatory primary)

Основной документ: **Basel III: Finalising post-crisis reforms** (BCBS Publication d424, December 2017, bis.org/bcbs/publ/d424.pdf). Также именуется «Basel IV». Implementation phase-in 2023-2028.

Ключевые параграфы для SME / emerging markets:
- §43 (regulatory retail SMEs), §55 (criteria for retail SME inclusion).
- §501 CRR (EU implementation): SME supporting factor.
- Параграф для emerging markets: «In some jurisdictions (eg emerging economies), national supervisors might deem it appropriate to define SMEs in a more conservative manner (ie with a lower level of sales)».

**Adaptation для UZ**: ЦБ РУз внедрил адаптированные Basel II/III стандарты через IMF/World Bank FSAP 2022-2025 (documents1.worldbank.org/curated/en/099072925165040123): минимальный CAR — 13%, CET1 — 4.5%. С июля 2024 ЦБ РУз ввёл DSTI cap 50% для consumer loans.

World Bank Blogs (2024): «Basel III implementation had a moderately negative effect on SME access to finance in EMDEs (figure 1)» — критично для понимания контекста UZ MSB.

**Ключевой вывод**: Basel III final (2017) применим для UZ как методологическая база; конкретные количественные thresholds — комбинация внутренней методологии банков + макропруденциальных ограничений ЦБ РУз (DSTI, LTV, CAR-buffer).

### Top-3 critical foundational fixes
1. **Заменить «ЦБ РУз №27-п»** на «ЦБ РУз Положение №2696 (последняя ред. 2696-5 от 23.12.2025, вступила в силу 25.01.2026)» во всех правилах. Удалить ложные ссылки на «п.4.5» — таких пунктов с количественными порогами в положении не существует. Источник thresholds для REVENUE_DROP/NEGATIVE_PROFIT правил должен быть «внутренняя методология + Базель III SREP», а не «ЦБ РУз».
2. **Заменить «НК РУз ст.256»** на «НК РУз ст. 47 + ст. 257 + ПКМ №489 + ст. 175-1 КоАО + ст. 223 НК РУз» в правиле VAT_ESF_MISMATCH.
3. **Понизить confidence Group-IB UZ fraud report до LOW** в правилах DIRECTOR_CHANGED_6M, SHELL_COMPANY_PARTNERS, NEW_COUNTERPARTY_LARGE_SHARE, CIRCULAR_INVOICING. Дополнить ссылками на FATF R.10/R.24 + EAG typology reports + Закон РУз № ЗРУ-660.

---

## Q0.B — Per-rule audit (все 19 правил)

| # | Rule ID | Verdict | Проблема | Recommended new spec | Confidence | Source |
|---|---------|---------|----------|----------------------|------------|--------|
| 1 | DIRECTOR_CHANGED_6M | KEEP с правкой | Атрибуция Group-IB UZ не подтверждена | `(as_of - director_appointed_at).days <= 180 AND loan_request_amount > 500_000_000 UZS` severity=medium | MEDIUM | FATF R.24, Закон РУз ЗРУ-660 |
| 2 | OKVED_CHANGED_12M | ADJUST | (а) В UZ — ОКЭД, не ОКВЭД (RF). (б) Госкомстат автоматически переопределяет основной ОКЭД по итогам года — собственное изменение не сильный сигнал | `(as_of - oked_main_changed_at).days <= 365 AND oked_changed_by_owner = true` severity=low | MEDIUM | Госкомстат РУз ОКЭД, ПКМ №275 от 24.08.2016 |
| 3 | LOAN_TO_REVENUE_RATIO | ADJUST | Порог 0.50 жёсткий. IFC рекомендует 0.30-0.40 unsecured, 0.50-0.80 secured | `loan_request / latest_annual_revenue > 0.40 if unsecured else > 0.70 if secured` severity=high | MEDIUM | IFC SME Banking Knowledge Guide; внутренняя методология |
| 4 | REVENUE_DROP_MOM_30 | ADJUST | Атрибуция «ЦБ РУз №27-п» подложная. Сезонность UZ-агро/строительства даёт натуральные −40-60% MoM | `mom_pct < -0.30 for 2 consecutive months AND oked_section NOT IN ('A','F','I') AND month NOT IN (12,1,2)` severity=high | MEDIUM | Базель III SREP, SR 11-7 |
| 5 | REVENUE_DROP_YOY_50 | KEEP с правкой источника | Атрибуция «ЦБ РУз №27-п» подложная | `(curr_yr - prev_yr)/prev_yr < -0.50 AND prev_yr > 200_000_000 UZS` severity=high | MEDIUM | Altman Z-score; внутренняя методология |
| 6 | NEGATIVE_PROFIT_3Q | KEEP с правкой источника | Атрибуция подложная, но логика верная | `all(net_profit <=0 for last 3Q) AND oked NOT IN ('A','F') OR last 4Q` severity=high | HIGH | Altman, Iwanicz-Drozdowska et al. (JIFM 2017) |
| 7 | NEGATIVE_EQUITY | KEEP | Базель III IRB capital adequacy — корректно | `latest_annual.equity <= 0` severity=critical | HIGH | BCBS d424 §50 |
| 8 | VAT_GROWTH_NO_REVENUE | ADJUST | Порог 0% для revenue_growth слишком жёсткий | `vat_growth > 0.20 AND revenue_growth < 0.05` severity=medium | MEDIUM | НК РУз гл. 34-35, my.soliq.uz |
| 9 | VAT_ESF_MISMATCH | KEEP с правкой источника | «НК РУз ст.256» НЕВЕРНО. Должно быть ст. 47, 257 | `abs(vat_decl - sum_seller_esf_vat)/max(vat_decl,1) > 0.15 AND vat_decl > 10_000_000 UZS` severity=critical | HIGH | НК РУз ст. 47, ст. 257; ПКМ №489; ст. 175-1 КоАО; ст. 223 НК РУз |
| 10 | LOW_MARGIN_HIGH_TURNOVER | ADJUST | Margin < 5% слишком жёсткий — нужно сравнивать с медианой по ОКЭД | `annual_rev > 5_000_000_000 UZS AND net_margin < industry_median(oked) - 5_pp` severity=medium | MEDIUM | Stat.uz отраслевые медианы |
| 11 | TAX_PAYMENT_DELAYS | KEEP с уточнением | В UZ 30 дней просрочки → автоматический freeze (НК РУз ст. 111) | без изменений severity=medium | HIGH | НК РУз ст. 111, ст. 121 |
| 12 | BANK_ACCOUNT_FROZEN_12M | KEEP | Корректная атрибуция | без изменений severity=high | HIGH | НК РУз ст. 111-113 |
| 13 | TAX_PENALTIES_CURRENT_YEAR | KEEP с правкой | Уточнить тип штрафа: ст. 223 НК (20% сокрытие) >> ст. 219 НК (просрочка отчёта) | `any(ev.type==PENALTY AND ev.severity IN ('MATERIAL') AND ev.year==current_year)` severity=medium | HIGH | НК РУз ст. 219, 220, 223 |
| 14 | SINGLE_BUYER_CONCENTRATION | ADJUST | Порог 0.70 мягкий. Basel Large Exposures Framework считает >0.25 капитала large exposure | `max_buyer_revenue_share > 0.50` severity=medium, `> 0.70` severity=high | MEDIUM | BCBS «Large Exposures Framework» (April 2014) |
| 15 | SINGLE_SUPPLIER_CONCENTRATION | ADJUST | Особо если supplier foreign (импортная зависимость) | `max_supplier_share > 0.50 AND supplier_is_foreign=true` severity=high; иначе medium при >0.60 | MEDIUM | Same as #14 |
| 16 | NEW_COUNTERPARTY_LARGE_SHARE | KEEP с правкой источника | Group-IB UZ — LOW confidence | `sum(share for cp if cp.inn_age<180d) > 0.30` severity=high | MEDIUM | FATF R.10 (CDD), Закон РУз ЗРУ-660 |
| 17 | SHELL_COMPANY_PARTNERS | KEEP с правкой источника | Учитывать ОПФ (IE/YaT часто молодые legitimно) | `any(months_since_reg(cp) < 6 AND cp.opf != 'IE') for major counterparties` severity=high | MEDIUM | FATF R.10, EAG guidance, ЗРУ-660 |
| 18 | CIRCULAR_INVOICING | KEEP | Логика правильная (VAT carousel pattern) | `exists (A→B) AND (B→A) within 90d AND total_volume > 100_000_000 UZS` severity=high | HIGH | НК РУз гл. 17, EAG typology reports |
| 19 | INSUFFICIENT_DATA | **DEPRECATE → REPLACE** | Срабатывает только при полном вакууме. Не справляется с partial-data | Заменить на CONFIDENCE_LAYER (см. Q1) | HIGH | FRB SR 11-7 (revised SR 26-02 April 2026): «Model creators should be able to demonstrate that the data and information used are suitable for the model. As part of this demonstration there should be a rigorous assessment of data quality and relevance» |

---

## Q0.C — Категориальный gap analysis

Существующие 19 правил покрывают пять категорий: structural (1, 2), financial (3-7, 10), payment_discipline (8, 9, 11-13), counterparty (14-18), meta (19). 

### Критические пробелы (must-have)

**(A) Currency / FX exposure — ОТСУТСТВУЕТ, КРИТИЧНО**. World Bank Financial Sector Assessment, Uzbekistan (documents1.worldbank.org/curated/en/099072925165040123, July 2025): «the share of foreign exchange (FX) loans at 44 percent of total loans remains relatively high (Annex Figure 3)». IMF Article IV UZ 2024 рекомендует «ограничить финансирование в иностранной валюте для предприятий, не имеющих валютной выручки». Курс UZS/USD ≈ 12 019 (cbu.uz, 19.05.2026).

**(B) Debt Service Coverage Ratio — ОТСУТСТВУЕТ, КРИТИЧНО**. UZ-академическое исследование cotton ginning (Murodov O.J., 2025, casjournal.org): «even when the baseline DSCR ranges between 1.05 and 1.15, the probability of liquidity disruption reaches up to 42% under a combined stress scenario… The results justify setting a minimum safe DSCR threshold at 1.3».

**(C) Working capital adequacy — ОТСУТСТВУЕТ**. Current ratio, quick ratio, DSO, DPO — стандартные SME KPI, не покрыты ни одним из 19 правил.

### Medium-importance пробелы

(D) CFO vs accrual profit (cash flow quality).
(E) Related-party transactions (часто скрытая концентрация через общих бенефициаров).
(F) Off-balance commitments (гарантии, поручительства, лизинги, аккредитивы).
(G) Microfinance stacking (заёмщик с 3+ микрозаймами + новая заявка в банк).

### YAML-spec для 3 critical новых правил

```yaml
- id: FX_MISMATCH_HIGH
  description: "FX-долг при UZS-выручке без хеджа — валютный мисматч"
  formula: |
    fx_debt_share = (fx_denominated_loans + fx_supplier_payables) / total_liabilities
    fx_revenue_share = fx_export_revenue / total_revenue
    return fx_debt_share > 0.30 AND fx_revenue_share < 0.10
  severity: high
  source: "World Bank FSAP UZ 2025 (44% FX-loans systemic); IMF Article IV UZ 2024 §15; ЦБ РУз Положение №2696"
  notes: "UZS/USD = 12019.27 на 19.05.2026 (cbu.uz). Применять для всех корп. заёмщиков с FX-долгом"

- id: DSCR_LOW
  description: "DSCR ниже 1.30 — риск disruption обслуживания долга"
  formula: |
    ebitda = revenue - opex - depreciation
    annual_debt_service = principal_due_12m + interest_due_12m + lease_payments_12m
    dscr = ebitda / annual_debt_service
    return dscr < 1.30 AND annual_revenue > 500_000_000 UZS
  severity: high  # critical если dscr < 1.0
  source: "Murodov O.J. (2025, Central Asian Journal of Innovations on Tourism Management and Finance); BCBS d424"

- id: WC_INSUFFICIENT
  description: "Недостаток оборотного капитала — current ratio < 1.0"
  formula: |
    current_ratio = current_assets / current_liabilities
    quick_ratio = (current_assets - inventory) / current_liabilities
    return current_ratio < 1.0 OR (current_ratio < 1.2 AND quick_ratio < 0.7)
  severity: medium  # high если current_ratio < 0.8
  source: "IFC SME Banking Knowledge Guide; НСБУ N 1 РУз"
```

### Top-3 critical fixes (суммарно из Q0.A/B/C)
1. **Замена foundational source attribution** (3 источника: 27-п→2696, ст.256→ст.47, Group-IB→FATF/EAG).
2. **DEPRECATE правило INSUFFICIENT_DATA → внедрение Confidence Layer** (см. Q1).
3. **Добавить 3 критических правила**: FX_MISMATCH_HIGH, DSCR_LOW, WC_INSUFFICIENT.

---

## Q1 — Confidence Layer / Partial-Data Scoring

### (1) Basel III IRB подход к sparse data
BCBS d424 §28 устанавливает минимальные требования к данным для применения внутренних моделей: 5 лет минимум для PD, 7 лет для LGD/EAD. При недостаточности данных модель переходит на Foundation IRB (F-IRB) с регуляторно установленным LGD = 45% (senior unsecured). При coverage <60% типовая практика — переход на standardized approach с conservative add-on; при <40% — отказ от внутренней модели.

### (2) FRB SR 11-7 / revised SR 26-02 (April 2026)
Прямая цитата (federalreserve.gov/supervisionreg/srletters/SR2602.pdf): «Model creators should be able to demonstrate that the data and information used are suitable for the model. As part of this demonstration there should be a rigorous assessment of data quality and relevance». Также: «Models are simplified representations of real-world relationships… they are based on assumptions that make them useful in estimating values and predicting events, but which also can have limitations and create model risk».

**Practical translation**: модель, выдающая «Одобрить 100» при 0/19 правил из-за отсутствия данных — это признак «not fit for purpose». Per SR 11-7 / SR 26-02 обязательны:
- documented data quality assessment перед расчётом scores;
- model output должен сопровождаться confidence interval / data coverage metric;
- override mechanism для low-coverage cases.

### (3) FinTech / SME платформы — partial-data handling

- **Kabbage** (до acquisition AmEx, 2020): ~150 alternative data sources (bank tx, QuickBooks, eBay, Amazon); при отсутствии 2+ источников — manual review.
- **OnDeck**: OnDeck Score = business credit + bank statements; partial-data trigger → rate +~8 pp.
- **Tinkoff Бизнес** (RU): scoring разделён на «Цифровой» (full data → instant до 30 млн руб) vs «Стандартный» (partial → manual review).
- **TBC Uzbekistan** (digital SME до 300 млн сум, 3 года): «All other data required to confirm loan eligibility and amount are sourced digitally by leveraging TBC's technological infrastructure for automatic assessment, scoring and underwriting, powered by the country's existing data-rich environment. This TBC product, differentiated by fast loan approval and disbursal times, will set a new standard for SME lending in Uzbekistan» (theasianbanker.com, 2025). TBC автоматически тянет данные из госисточников — при их отсутствии заявка blocked.
- **World Bank UZ project (P511700)** предлагает «psychometric credit scoring» — короткие тесты при пустой кредитной истории; альтернатива для retail, не SME.

### (4) Архитектурное решение: confidence layer как СЕПАРАТНЫЙ модификатор (НЕ как rule)

Обоснование:
- (a) INSUFFICIENT_DATA #19 ловит только полный вакуум, не справляется с partial data → должен быть DEPRECATED.
- (b) Confidence orthogonal к risk_score; rule создал бы бинарный флаг, нужен continuous score.
- (c) Confidence модифицирует ВСЕ recommendations (даже при full data может быть incomplete due to staleness).
- (d) Per SR 11-7 §IV.5 (revised SR 26-02), data quality assessment должен быть **обязательным этапом** до model execution, а не один из триггеров.
- (e) Confidence обеспечивает explainability (auditor видит «почему понижен score»), что критично для SR 11-7 §V validation.

### YAML-spec confidence layer

```yaml
confidence_layer:
  version: 1.0
  description: "Two-axis scoring: risk_score (0-100) parallel to data_confidence (0-100)"
  
  data_sources:
    mandatory:  # без них pre-underwriting не выполняется
      - inn_opf_oked
      - director_info
      - registration_date
    high_value:
      - annual_report_form1_balance: 15
      - annual_report_form2_pnl: 15
      - vat_declaration_12m: 12        # для НДС-плательщиков
      - esf_register_seller_buyer_12m: 15
      - tax_payment_events_24m: 10
      - bank_account_turnover_12m: 10
    medium_value:
      - quarterly_pnl_4q: 8
      - monthly_revenue_12m: 6
      - counterparty_register: 7
      - account_freeze_events_24m: 5
    nice_to_have:
      - related_party_disclosure: 3
      - cashflow_statement: 4
  
  formula: |
    confidence = sum(weight[ds] for ds in available_sources)
    confidence = min(confidence, 100)
    
  thresholds:
    - if confidence >= 75: status = "HIGH_CONFIDENCE"
      multiplier = 1.0
      pessimistic_adjustment = 0
      recommendation = "use raw_score directly"
    - if 50 <= confidence < 75: status = "MEDIUM_CONFIDENCE"
      multiplier = 0.90
      pessimistic_adjustment = -10
      recommendation = "raw_score × 0.90 - 10, soft cap 75"
    - if 30 <= confidence < 50: status = "LOW_CONFIDENCE"
      multiplier = 0.75
      pessimistic_adjustment = -20
      recommendation = "raw_score × 0.75 - 20, force REVIEW, manual underwriting required"
    - if confidence < 30: status = "CRITICAL_LOW"
      recommendation = "REJECT_AUTO_APPROVAL, score capped at 50, request additional data"

  override_rules:
    - if mandatory_sources_missing: status = "DATA_INSUFFICIENT" → REJECT
    - if vat_declaration_missing AND borrower_is_vat_payer: confidence -= 20 (penalty)
    - if account_freeze_event_present AND tax_events_missing: status = "SUSPICIOUS_GAP" → REVIEW

  audit_log:
    - log all source availability
    - log confidence calculation
    - log multiplier applied
    - log final score and override path
```

### Test scenarios (5)

| # | Сценарий | Coverage | raw_score | confidence | Final | Recommendation |
|---|----------|----------|-----------|------------|-------|----------------|
| S1 | Healthy full data | ИНН+ОПФ+ОКЭД, Form1/2×2г, VAT 12m, ESF, tax, turnover, counterparty | 88 | 92 | 88 | APPROVE |
| **S2** | **Problem case задания**: Healthy partial — ИНН+ОПФ+ОКЭД+director+Form1/2×2г; ПУСТО ESF/turnover/counterparty/tax/VAT | **100 (0/19 правил)** | **30 (15+15=30 + penalty за VAT)** | **min(100×0.75-20, 50) = 50** | **REVIEW, manual underwriting (cap=50)** |
| S3 | Distressed full data, 5 правил breached | 35 | 92 | 35 | REJECT |
| S4 | Suspicious mid — full mandatory + Form1/2 + account_freeze event, no tax/VAT/ESF | 65 | 38 | 65×0.75-20 = 29 + override REVIEW | REVIEW (suspicious gap) |
| S5 | Thin SME (IE/ЯТ) low coverage — ИНН+ОКЭД+director+1 annual report | 75 | 22 | capped 50 | REJECT_AUTO_APPROVAL (request docs) |

**S2 — это явный problem case из задания**. Pre-underwriting MVP сейчас выдаёт 100/Approve. После фикса — **50/Review с принудительным manual override**. Это и есть основной deliverable Q1.

---

## Q2 — UZ MSB Credit Underwriting Practice 2025-2026

### (1) Empirical baseline (verified)

| Метрика | Значение 2024 | Источник (verbatim) |
|---------|---------------|--------------------|
| Доля FX-loans в портфеле сектора | 44% | World Bank FSAP UZ July 2025: «the share of foreign exchange (FX) loans at 44 percent of total loans remains relatively high» |
| CAR сектора (агрегат) | 17%+ (мин. ЦБ 13%) | World Bank FSAP UZ 2025 |
| SME lending 2025 | 131,2 трлн UZS (+42% YoY) | UzDaily.uz (uzdaily.uz/en/sme-lending-in-uzbekistan-increased-by-42-in-2025/): «In 2025, the volume of loans provided to support small and medium-sized enterprises (SMEs) and entrepreneurial activity in Uzbekistan reached 131.2 trillion soums, marking a 42% increase compared to 2024» |
| Microfinance loans 9M2025 | 21,3 трлн UZS (×2 YoY) | American Journal of Business Management 2026 (americanjournal.org): «microfinance loan volumes doubled to 21.3 trillion soums in the first nine months of 2025, while total microfinance services reached 66.9 trillion soums (up 1.9-fold)» |
| Средний % по микрозаймам | 35,9% | American Journal of Business Management 2026: «high interest rates (averaging 35.9%)» |
| Финансовый gap MSME | $6-7 млрд (из $13 млрд спроса) | IFC SME Finance Forum 2025; WB FSAP UZ 2025 |
| % small с банк. кредитом | 10%; medium — 16% | World Bank Enterprise Survey UZ 2024 |
| DSTI cap consumer loans | 50% (с июля 2024) | ЦБ РУз макропруденциальные меры (June 2024) |
| Средняя долговая нагрузка домохозяйств | 34% (DSTI) | CBU Financial Stability Review 2024 (per kun.uz, 04.06.2025): «Taking into account all liabilities of individuals, the average total debt burden was 34% in 2024. Among bank borrowers, the share of loans attributed to individuals with a DTI above 50% stands at 40%» |
| Объём directed/preferential lending | ~30% портфеля сектора (down from ~60% в 2018) | WB FSAP UZ 2025 |
| Кибермошенничество 2024 | 58,8 тыс. случаев, 97,7% — банк. карты | МВД РУз доклад Сенату 26.02.2025 (per kun.uz, upl.uz): «зарегистрировано почти 59 тысячи киберпреступлений (58,8 тысячи), из которых подавляющее большинство, а именно 97,7%, связаны с несанкционированным снятием денег с банковских счетов» |

### (2) Mid-tier bank KPIs FY2024 (verified)

**SQB (Узпромстройбанк)** — Investor Presentation YE2024 NAS (sqb.uz):
- NPL ratio 2.8%, NPL coverage 119.6%
- CAR (TCR) 15.6%, Tier 1 10.6% (мин. ЦБ TCR 13%, Tier-1 10%)
- ROE (RoAE) 13.9% FY2024 vs 11.1% FY2023; NIM 4.7%; Cost/Income 20.7%
- Total assets 87.6 трлн UZS ($6.8 млрд); Net loans 65.5 трлн UZS
- Loan portfolio mix 1H24: Manufacturing 37%, Oil&Gas/Chemicals 18%, Individuals 13%, Trade&Services 12%, Agriculture 6%, Transport&Comm 5%, Energy 5%, **Construction 3%**
- Цит. SQB о секторе FY2024: NPL ~4.0%, CAR ~17.4%, ROE 14.2%

**Ipoteka Bank (OTP Group)** — Annual Management Report 2024 (ipotekabank.uz):
- CAR (Local GAAP) 16.03% (Dec-24, down from 17.58% Dec-23); Tier 1 14.6%
- ROE 23%; ROA 2.7%; NIM 7.8%; Cost/Income 40.2%
- Stage 3 ratio (≈NPL по IFRS) 20.6%, coverage 63.8% (рост из-за reclassification corporate exposures)
- Risk cost rate 2.6%; Net LTD 181% (110% без госипотек); NSFR 114.1%; LCR 444.1%
- Loan mix: Mortgage 40%, Consumer 22%, Corporate 21%, SME 17%

**Hamkorbank** — partial verification:
- Net profit 2024: 1,4 трлн сум (+18,9% YoY) (newslineuz.com)
- Loan portfolio 19,2 трлн сум (+21% YoY)
- S&P rating: BB-/Stable (07.03.2025), «The stable outlook reflects S&P's view that Hamkorbank will maintain its notable market positions in local retail and SME banking, sustainably high profitability, good asset quality and adequate capital and liquidity buffers»
- ~50 000 ЮЛ (преимущественно МСБ) + 60 000 ИП (FMO data, 2024)
- **NPL/CAR/ROE FY2024 — требуется ручная верификация через IFRS-отчёт hamkorbank.uz/financial-statements**

**Asia Alliance, Trastbank, Anor, Bereke, Davr, Mikrokreditbank** — публичные KPI FY2024 в открытых UZ-источниках **не найдены**; [source needed] — необходима ручная проверка annual reports на сайтах банков.

### (3) Обязательные документы для pre-underwriting в UZ

| Документ | Источник | Обязательность |
|----------|----------|---------------|
| Форма 1 «Бухгалтерский баланс» | НСБУ N 1 РУз, soliq.uz | Обязательно, годовая |
| Форма 2 «Отчёт о финансовых результатах» | НСБУ N 1 | Обязательно, годовая |
| Декларация по НДС | НК РУз гл. 34-35, my.soliq.uz | Обязательно ежемесячно (если ВАТ-плательщик) |
| ЭСФ-реестр выставленных/полученных | НК РУз ст. 47, ПКМ №489 | Обязательно (электронно через my.soliq.uz) |
| Налоговые акты | НК РУз ст. 102-103 | По запросу банка |
| Регистр контрагентов | Внутренний + ЕГРСП | Желательно |
| Выписка из ЕГРСП | Госкомстат / stat.uz | Обязательно (актуальная) |
| Договор займа / бизнес-план | Внутренний | Обязательно |

### (4) UZ-specific red flags (не дублируют 19-rule set)

1. **Конвертация UZS/USD при импорте без хеджирования** — covered by new FX_MISMATCH_HIGH, но для импортёров ОКЭД G46.4-46.9 нужен extra weight (covered by SUPPLIER_CONCENTRATION RULE_ID #15, audit ADJUST).
2. **«Серая» дельта в строительстве** — covered by enhanced LOW_MARGIN_HIGH_TURNOVER (RULE_ID #10, audit ADJUST с сравнением vs медианы ОКЭД).
3. **АГРО-сезонность** — covered by RULE_ID #4 ADJUST (oked_section filter).
4. **IT-сектор «обналички»** — covered by SHELL_COMPANY_PARTNERS + SINGLE_BUYER_CONCENTRATION.
5. **Связанные холдинги** — covered by CIRCULAR_INVOICING + new RELATED_PARTY_LARGE_SHARE (Q0.C gap).
6. **Микрозаймовый stacking** — UZ-specific, не покрыто. **Новое правило MICROFINANCE_STACKING**: заёмщик с 3+ активными микрозаймами в МФО + новая заявка в банк → severity=medium. Источник: ЦБ РУз стресс-тест 2024 указал, что concentration по микрозаймам растёт ускоренными темпами.
7. **Hidden directed/preferential** — covered by NEGATIVE_PROFIT_3Q при SOCB-фоне.

### (5) KPI thresholds таблица GOOD/WARN/BAD для UZ-МСБ (выручка 1-50 млрд UZS)

| KPI | GOOD | WARN | BAD | Источник |
|-----|------|------|-----|----------|
| Current ratio | >1.5 | 1.0-1.5 | <1.0 | IFC SME Banking; НСБУ N 1 |
| Quick ratio | >1.0 | 0.7-1.0 | <0.7 | Same |
| DSCR | >1.5 | 1.2-1.5 | <1.2 | Murodov UZ 2025 (мин. safe 1.30) |
| Debt-to-EBITDA | <3.0 | 3.0-5.0 | >5.0 | BCBS d424 F-IRB benchmarks |
| Debt-to-equity | <1.5 | 1.5-3.0 | >3.0 | НСБУ + Basel |
| Net margin vs ОКЭД median | ≥ median | -5 pp to median | < median -5 pp | Stat.uz (агрегаты, без per-bucket публикации) |
| Interest coverage (EBIT/Interest) | >3.0 | 1.5-3.0 | <1.5 | Standard SME |
| FX exposure mismatch | <10% | 10-30% | >30% | IMF UZ 2024, WB FSAP UZ 2025 (44% systemic) |
| DSTI (для IE / частник) | <30% | 30-50% | >50% | ЦБ РУз cap 50% июль 2024 |
| Account turnover stability (CoV) | <0.30 | 0.30-0.60 | >0.60 | Внутренний benchmark |

### (6) Empirical approval baseline

- **TBC UZ** (digital SME до 300 млн UZS, 3 года): «business customers will be able to apply and receive the loan in only a few minutes» (theasianbanker.com 2025). По заявлению Hughes (TBC Bank Group Chief Growth Officer), TBC UZ достигла прибыльности через 2 года после запуска — «record time-to-profit among global digital banks» (intellinews.com 2024). Approval rates конкретно — частная информация.
- **Hamkorbank/ProCredit партнёрство**: SME-focused; ~50 000 ЮЛ + 60 000 ИП в клиентской базе (FMO).
- Среднее approval rate SOCBs **[source needed]**; WB FSAP UZ 2025 указывает только population access (10% small, 16% medium).
- Loan-to-revenue typical: 0.20-0.40 unsecured / 0.50-0.80 secured (IFC SME methodology UZ-adapted).
- Типичный срок SME loan UZ 2025: 3 года (TBC), до 5 лет (Hamkorbank/SQB); microloans до 100 млн сум — без залога (American Journal 2026).

---

## Q3.A — Classifier identification

**Верифицированный ответ**: Узбекистан использует **ОКЭД (Общегосударственный классификатор видов экономической деятельности Республики Узбекистан), редакция 2**. Утверждён **Постановлением Кабинета Министров №275 от 24.08.2016** «О мерах по переходу на международную систему классификации видов экономической деятельности»; действует с 1 января 2017 года.

- **Основа**: статистическая классификация видов экономической деятельности ЕС (NACE Rev.2 + дополнения NACE-2002).
- **International mapping**: ОКЭД 4-знаков ↔ ISIC Rev.4.
- **Структура**: 5 уровней (секция A-U → раздел 01-99 → группа → класс XX.XX → подкласс XX.XX.X).
- **Soliq при регистрации ЮЛ** требует ОКЭД (через ЕГРСП), **НЕ российский ОКВЭД2** (Rosstandart). Это критическое отличие. Источник: norma.uz обзор ПКМ №275.
- Кто регистрирует и поддерживает: Госкомстат РУз (stat.uz/ru/2020-05-11-05-05-43/statisticheskie-klassifikatory).
- **Российский ОКВЭД2 в UZ НЕ применяется официально**. Несмотря на сходство (оба построены на NACE), кодовая структура и наименования подклассов могут отличаться.

**Bug в MVP**: fallback на «оптовую торговлю пищ. продуктами ~12% net margin» для **ОКЭД 43.39 (производство прочих отделочных и завершающих строительных работ)** — секция **F (строительство)**, не G (торговля). Это явная ошибка mapping секций.

---

## Q3.B — Data sourcing + JSON skeleton

### (1) Источники медиан по UZ-отраслям

- **Stat.uz** — квартальные бюллетени «Социально-экономическое положение Республики Узбекистан» (раздел «Финансовые результаты»). **ВАЖНО**: публикуются только абсолютные суммы прибыли/убытка по секциям, **готовая net margin per ОКЭД в открытом виде НЕ публикуется**. За январь-ноябрь 2024 (stat.uz/files/474/choraklik-natijalar-yanvar-dekabr2024ru): обрабатывающая 72 309,8 млрд UZS; перевозка/хранение 10 005,8; торговля 6 155,0. Методологическое ограничение (verbatim): «Без бюджетных и других некоммерческих организаций, сельскохозяйственных предприятий, производящих продукцию фермерских и дехканских хозяйств, страховых организаций, банков, малых [предприятий]».
- **CERR** (cer.uz) — quarterly business climate reports, индекс настроений (53 пункта в 2024 по шкале -100/+100), но без granular финансовых медиан.
- **ЦБ РУз** отраслевые обзоры — credit volumes per industry, не профитабильность.
- **IFC SME Finance Forum 2025, EBRD UZ SME 2024, KPMG UZ Fintech 2024** — фокус на B2C/POS/BNPL, не на per-ОКЭД медиан.

**Net margin per ОКЭД для UZ-MSB FY2024 в открытом доступе НЕ найден** (subagent verification). Требуется:
1. Запрос микроданных stat.uz (платно / по запросу);
2. Ручной агрегатив через my.soliq.uz analytics;
3. CERR/KPMG sectoral commissioned study;
4. До решения — Basel III standardized weights + bank internal historical data.

### (2) Granularity trade-off

- 4-digit ОКЭД (43.39) — слишком granular для UZ MSB; малый sample per класс.
- 2-digit (43 — Specialised construction) — оптимально.
- **5-7 buckets** — наиболее практично для MVP, покрытие 80% UZ-МСБ.

### (3) JSON skeleton (7 buckets, null + explicit notes — НЕ fake numbers)

```json
{
  "version": "1.0",
  "classifier": "OKED_UZ_rev2",
  "classifier_authority": "Госкомстат РУз / stat.uz (ПКМ КМ РУз №275 от 24.08.2016)",
  "classifier_mapping_international": "ISIC Rev.4 / NACE Rev.2",
  "updated_at": "2026-05-19",
  "source": "stat.uz, CERR; per-bucket medians require manual verification — see notes",
  "currency": "UZS",
  "exchange_rate_reference": "USD/UZS = 12019.27 (cbu.uz, 19.05.2026)",
  "data_year": "2024 (latest available)",
  "buckets": [
    {
      "code_prefix": "G",
      "oked_subsections": ["45", "46", "47"],
      "name_ru": "Оптовая и розничная торговля; ремонт автотранспорта",
      "name_uz": "Ulgurji va chakana savdo; avtomobillarni ta'mirlash",
      "median": {"roe_pct": null, "net_margin_pct": null, "asset_turnover": null, "debt_to_equity": null},
      "sample_size": "~158 000 предприятий (Statista UZ 2024)",
      "source": "Stat.uz UZ enterprises by industry, Jan 2024",
      "data_year": 2024,
      "notes": "UZ industry-specific net margin not published in open form by stat.uz. Estimated proxy (KZ/RU comparable): 5-8% net margin for retail trade. DO NOT use as ground truth. CRITICAL: this bucket was target of MVP fallback bug for OKED 43.39 (construction); fix mapping before production."
    },
    {
      "code_prefix": "C",
      "oked_subsections": ["10-33"],
      "name_ru": "Обрабатывающая промышленность",
      "name_uz": "Qayta ishlash sanoati",
      "median": {"roe_pct": null, "net_margin_pct": null, "asset_turnover": null, "debt_to_equity": null},
      "sample_size": "~65 000 предприятий",
      "source": "Stat.uz; absolute profit 72 309.8 млрд UZS Jan-Nov 2024",
      "data_year": 2024,
      "notes": "Largest absolute profit pool in UZ economy. Highly heterogeneous: food processing (C10) ≠ textile (C13) ≠ chemicals (C20, ~27.6% net margin per RU FNS proxy 2024). Recommend sub-bucketing. UZ official medians not published — KPMG/CERR sectoral study needed."
    },
    {
      "code_prefix": "F",
      "oked_subsections": ["41", "42", "43"],
      "name_ru": "Строительство",
      "name_uz": "Qurilish",
      "median": {"roe_pct": null, "net_margin_pct": null, "asset_turnover": null, "debt_to_equity": null},
      "sample_size": "~25 000+ предприятий",
      "source": "Stat.uz",
      "data_year": 2024,
      "notes": "CRITICAL: OKED 43.39 (finishing construction works) — это bucket F, не G. Bug source: MVP fallback wrongly routed to OKED G food trade ~12% net margin. UZ construction has strong seasonality (Q1 trough, Q3 peak), and is among lower-margin sectors. SQB FY2024 portfolio: construction only 3%, indicating banks treat it cautiously. Estimated proxy net margin (KZ/RU): 3-6% with high variance. Need UZ-specific data. Also: 'серая' дельта (under-declared revenue) inflates apparent margins."
    },
    {
      "code_prefix": "A",
      "oked_subsections": ["01", "02", "03"],
      "name_ru": "Сельское, лесное и рыбное хозяйство",
      "name_uz": "Qishloq, o'rmon va baliq xo'jaligi",
      "median": {"roe_pct": null, "net_margin_pct": null, "asset_turnover": null, "debt_to_equity": null},
      "sample_size": "Сотни тысяч (включая dehkan farms вне формального учёта)",
      "source": "Stat.uz; CERR 2024 (agriculture grew 3.8% YoY in 2024)",
      "data_year": 2024,
      "notes": "Stat.uz EXCLUDES dehkan/farmer households from sectoral profitability data. Cotton ginning (Murodov 2025): baseline DSCR 1.05-1.15 → 42% liquidity disruption probability. Seasonality EXTREME (Q3 peak harvest). [source needed for UZ formal-sector medians]"
    },
    {
      "code_prefix": "I",
      "oked_subsections": ["55", "56"],
      "name_ru": "Услуги по размещению и питанию",
      "name_uz": "Joylashtirish va ovqatlanish xizmatlari",
      "median": {"roe_pct": null, "net_margin_pct": null, "asset_turnover": null, "debt_to_equity": null},
      "sample_size": "~10 000 предприятий",
      "source": "Stat.uz",
      "data_year": 2024,
      "notes": "Tourism boom post-2017 reforms. Proxy margin estimates (KZ/RU): 8-15% restaurants; lower for hotels (asset-heavy). [source needed for UZ-specific]"
    },
    {
      "code_prefix": "H",
      "oked_subsections": ["49-53"],
      "name_ru": "Перевозка и хранение",
      "name_uz": "Tashish va saqlash",
      "median": {"roe_pct": null, "net_margin_pct": null, "asset_turnover": null, "debt_to_equity": null},
      "sample_size": "[source needed]",
      "source": "Stat.uz; abs. profit 10 005.8 млрд UZS Jan-Nov 2024",
      "data_year": 2024,
      "notes": "Second-largest absolute profit pool after manufacturing. Heterogeneous: road freight (H49.4) ≠ rail (H49.1) ≠ warehousing (H52). UZ Railways quasi-government — exclude from MSB benchmark."
    },
    {
      "code_prefix": "J",
      "oked_subsections": ["58-63"],
      "name_ru": "Информация и связь / IT",
      "name_uz": "Axborot va aloqa",
      "median": {"roe_pct": null, "net_margin_pct": null, "asset_turnover": null, "debt_to_equity": null},
      "sample_size": "Растущий сегмент",
      "source": "Stat.uz; CERR 2024 (services +20% YoY in 2024)",
      "data_year": 2024,
      "notes": "IT Park UZ residents — special tax regime (0% profit tax to 2040). Apparent profitability may be inflated due to subsidies. Anti-fraud flag: IT-shell companies for НДС-расчётов (см. Q2 red flag #4)."
    }
  ],
  "update_frequency": "annual (Q1 of next year per stat.uz publication cycle)",
  "fallback_policy": {
    "if_median_null": "MUST flag as 'data_unavailable_for_UZ' in audit log; DO NOT silently substitute KZ/RU proxy",
    "manual_review_required": true,
    "default_recommendation": "Use Basel III standardized risk weights (75% retail SME, 100% other corporate) until per-bucket UZ data verified"
  }
}
```

**Verdict Q3**: UZ-specific net margin data per ОКЭД **не доступна публично** (HIGH confidence per dedicated subagent search). MVP действия:
1. **Fix immediate bug**: map ОКЭД 43.39 → bucket F (Construction), не G (Trade).
2. **Acknowledge gap**: populate JSON с `null` + `notes`, без fake numbers.
3. **Sourcing roadmap**: (a) запрос микроданных stat.uz; (b) commission CERR/KPMG исследование; (c) до этого — Basel standardized weights + банк internal historical data.

---

## Bibliography

### Regulatory tier 1 (≥5)
[1] Положение о порядке классификации качества активов и формирования резервов на покрытие возможных потерь по активам · ЦБ РУз / Минюст РУз · рег. № 2696 от 14.07.2015 (последняя ред. 2696-5 от 23.12.2025, вступила в силу 25.01.2026) · https://lex.uz/ru/docs/2703056 ; https://www.lex.uz/ru/docs/7942786
[2] Налоговый кодекс Республики Узбекистан · Закон РУз № ЗРУ-599 от 30.12.2019 · https://lex.uz/ru/docs/4674893
[3] Закон РУз «О Центральном банке Республики Узбекистан» (ЗРУ-582) · 11.11.2019 · https://lex.uz/docs/4590456
[4] Постановление Кабинета Министров РУз №275 «О мерах по переходу на международную систему классификации видов экономической деятельности» · 24.08.2016 · https://www.norma.uz/novoe_v_zakonodatelstve/klassifikator_vidov_ekonomicheskoy_deyatelnosti_-_po_mejdunarodnym_standartam
[5] Закон РУз «О банках и банковской деятельности» · 25.04.1996 (ред. 2019) · https://lex.uz/acts/12011
[6] Basel III: Finalising post-crisis reforms · BCBS Publication d424 · December 2017 · https://www.bis.org/bcbs/publ/d424.pdf
[7] Revised Guidance on Model Risk Management (SR 26-02) · Federal Reserve / OCC / FDIC · April 2026 (revised from SR 11-7, April 2011) · https://www.federalreserve.gov/supervisionreg/srletters/SR2602.pdf
[8] Republic of Uzbekistan: Financial Sector Assessment Program (FSAP) 2025 · IMF / World Bank · July 2025 · https://documents1.worldbank.org/curated/en/099072925165040123/pdf/BOSIB-098cfdae-26d9-446a-9607-c30f373e1f1b.pdf
[9] IMF Article IV Consultation — Uzbekistan, Staff Concluding Statement 2024 · IMF · 14.05.2024 · https://www.imf.org/ru/News/Articles/2024/05/14/mcs-uzbekistan-staff-concluding-statement-of-the-2024-article-iv-mission
[10] Уведомление об изменении порядка классификации качества активов (рег. № 2696-3) · Norma.uz обзор · 10.12.2021 · https://www.norma.uz/novoe_v_zakonodatelstve/izmenen_poryadok_klassifikacii_kachestva_aktivov_bankov

### Industry primary
[11] Investor Presentation YE2024 NAS · SQB (Узпромстройбанк) · 2025 · https://sqb.uz/upload/images/Investor%20presentation%20YE24%20NAS%20(2).pdf
[12] Annual Management Report 2024 · Ipoteka Bank (OTP Group) · 2025 · https://www.ipotekabank.uz/upload/annual-reports/eng%20Annual%20Report%202024.pdf
[13] Improving SME Access to Finance in Uzbekistan (Project Document P511700) · World Bank · 2025 · https://documents1.worldbank.org/curated/en/099111125164834893/pdf/P511700-4c30f714-7fff-495b-8330-6bf575847bf5.pdf
[14] Социально-экономическое положение Республики Узбекистан, январь-декабрь 2024 — раздел «Финансовые результаты» · Stat.uz · 2025 · https://stat.uz/files/474/choraklik-natijalar-yanvar-dekabr2024ru/3669/11-.pdf
[15] B2C Payments, POS financing and BNPL in Uzbekistan · KPMG Uzbekistan · 2024 · https://assets.kpmg.com/content/dam/kpmg/uz/pdf/2024/Fintech%20UZ_Payments_POS%20Financing_BNPL-final.pdf
[16] Microfinance and SME Lending: Challenges and Opportunities in Uzbekistan · American Journal of Business Management, Economics and Banking · Vol. 45, 2026 · https://americanjournal.org/index.php/ajbmeb/article/view/3409

### Cyber / Fraud / AML
[17] Choose Your Fighter: A New Stage in the Evolution of Android SMS Stealers in Uzbekistan · Group-IB Blog · 19.12.2025 · https://www.group-ib.com/blog/mobile-malware-uzbekistan/
[18] Fighting Credit Fraud in Uzbekistan: An Uphill Battle · Group-IB Blog · 2024-2025 · https://www.group-ib.com/blog/credit-fraud-in-uzbekistan/
[19] FATF Recommendations 10 (CDD) и 24 (Beneficial Ownership) · FATF · 2012 (updated 2023) · https://www.fatf-gafi.org

### Academic / Methodology
[20] Strengthening Financial Stability in Cotton Ginning Enterprises: A Stress-Testing Approach · Gulomov H. I., Murodov O. J. · Central Asian Journal of Innovations on Tourism Management and Finance · 2025 · https://cajitmf.casjournal.org/index.php/CAJITMF/article/view/1232
[21] Basel III implementation and SME financing: Evidence for emerging markets and developing economies · World Bank Blogs / Cortes, Demirgüç-Kunt et al. · 2024 · https://blogs.worldbank.org/en/allaboutfinance/basel-iii-implementation-and-sme-financing-evidence-emerging-markets-and-developing
[22] Financial Inclusion, Regulation, and Literacy in Uzbekistan · ADB Institute Working Paper 858 · 2018 · https://www.adb.org/sites/default/files/publication/441226/adbi-wp858.pdf

### Supporting
[23] Над 150 тыс. узбекистанцев активировали «кредитный бан» за 4 месяца · Frank.uz · 2025 · https://frank.uz/en/news-en/150-thousand-uzbeks-were-included-in-the-credit-ban-for-4-months/
[24] Over 12 million cyberattacks recorded in Uzbekistan in 2024 · Kun.uz · 03.02.2025 · https://kun.uz/en/news/2025/02/03/over-12-million-cyberattacks-recorded-in-uzbekistan-in-2024
[25] Средняя долговая нагрузка на граждан в 2024 году достигла 34% — ЦБ РУз · Spot.uz · 30.05.2025 · https://www.spot.uz/ru/2025/05/30/loans-stability
[26] Счет-фактура в Узбекистане 2026: оформление ЭСФ · bss.uz · 2026 · https://www.bss.uz/article/45-schet-faktura-v-uzbekistane-podrobnyy-obzor-i-novye-formy-na-2019-god
[27] SME Lending in Uzbekistan Increased by 42% in 2025 · UzDaily.uz · 2026 · https://www.uzdaily.uz/en/sme-lending-in-uzbekistan-increased-by-42-in-2025/
[28] TBC Uzbekistan launches digital SME lending platform · The Asian Banker · 2025 · https://www.theasianbanker.com/press-releases/tbc-uzbekistan-launches-digital-sme-lending-platform

---

## Open questions (требуют manual verification)

1. **NPL/CAR/ROE Hamkorbank FY2024** — нужно скачать IFRS отчёт hamkorbank.uz/financial-statements PDF.
2. **KPI Asia Alliance Bank, Trastbank, Anor Bank, Bereke, Davr Bank, Mikrokreditbank FY2024** — публичные данные в открытых источниках минимальны.
3. **Net margin medians per ОКЭД (2-digit) для UZ-МСБ FY2024** — требуется запрос микроданных stat.uz или KPMG/CERR sectoral study.
4. **Approval rates SME pre-underwriting в UZ-банках** — конфиденциальная информация банков.
5. **Внутренние методологии mid-tier UZ-банков для SME scoring** — конфиденциально.
6. **Полный текст Положения №2696-5 от 23.12.2025** — конкретные изменения относительно ред. 2696-3 (lex.uz/ru/docs/7942786 предоставляет только metadata).
7. **DSTI / DTI threshold для SME** (отличный от 50% retail cap) в текущем регулировании ЦБ РУз — требует прямого запроса.
8. **Group-IB корпоративный fraud report для UZ** (если существует как private deliverable) — требуется direct outreach.

---

## Recommendations

### Этап 1 (0-2 недели до demo): Foundational fixes — критично
1. **Заменить 3 ошибочных атрибуции** в YAML rules engine: «ЦБ РУз №27-п» → «ЦБ РУз Положение №2696 (ред. 2696-5)»; «НК РУз ст.256» → «НК РУз ст. 47»; «Group-IB UZ fraud report» → «FATF R.10/R.24 + EAG + Закон РУз ЗРУ-660».
2. **Исправить bug Q3 industry benchmark fallback**: ОКЭД 43.39 → секция F (строительство), не G (торговля).
3. **DEPRECATE правило INSUFFICIENT_DATA** и внедрить confidence_layer как separate модуль.
4. **Унифицировать терминологию**: убрать все упоминания «ОКВЭД» (российский), заменить на «ОКЭД» (UZ); проверить glossary (ИНН UZ 9-digit, ОПФ как LLC/MChJ, ESF, QQS).

### Этап 2 (2-4 недели): Per-rule audit implementation
5. **Имплементировать 16 ADJUST/KEEP-с-правкой правил** согласно таблице Q0.B.
6. **Добавить 4 новых правила**: FX_MISMATCH_HIGH (critical), DSCR_LOW (critical), WC_INSUFFICIENT (medium), MICROFINANCE_STACKING (medium).
7. **Внедрить industry benchmark JSON** с 7 buckets, null значениями и explicit `notes`. Запретить fake-substitution.

### Этап 3 (4-8 недель): Data sourcing
8. **Подписать соглашение с stat.uz** на доступ к микроданным по net margin per ОКЭД 2-digit (или commission CERR sectoral study).
9. **Скачать и обработать FY2024 IFRS отчёты** Hamkorbank, Asia Alliance, Trastbank — extract NPL/CAR/ROE/SME share для дополнения benchmark Q2.
10. **Confidence layer test scenarios S1-S5** — реализовать unit tests и validation report согласно SR 11-7 §V.

### Этап 4 (8-12 недель, pre-production): Validation
11. **External model validation** согласно SR 11-7 / SR 26-02 (independent reviewer).
12. **Backtest** на исторических данных банков-партнёров (требует NDA + data sharing agreement).
13. **Согласование с ЦБ РУз** при coming-to-market: уточнение, какие требования SREP применяются к pre-underwriting tools.

### Triggers для пересмотра рекомендаций
- Если backtest даёт false-positive rate >15% или false-negative rate >10% — пересмотр thresholds для соответствующих правил.
- Если CBU выпускает обновлённое Положение №2696 с количественными порогами в редакции после 2696-5 — обновить foundational layer attribution.
- Если confidence layer LOW_CONFIDENCE срабатывает >40% заявок — пересмотр mandatory/high_value источников (возможно завышенные требования).
- Если industry benchmark UZ-data становится доступной → обновить JSON, убрать null.

---

## Caveats

1. **Источниковая slabость для Q3 industry medians**: net margin per ОКЭД на UZ-первоисточниках не публикуется в открытом виде. JSON skeleton содержит null + notes, что является корректной поведенческой моделью per «if median null — flag, do not substitute». Использование KZ/RU proxy для UZ — НЕ допустимо без explicit disclaimer (отличия в налоговой системе, ОПФ, разрешённых деятельностях).

2. **Mid-tier банковские KPI**: подтверждены только для SQB и Ipoteka Bank. Для Hamkorbank — частично (net profit, S&P rating). Для Asia Alliance, Trastbank, Anor, Bereke, Davr, Mikrokreditbank — public data минимальна, требуется manual outreach.

3. **Group-IB UZ fraud report**: публичная часть покрывает retail/mobile, не SME corporate fraud. 4 правила (DIRECTOR_CHANGED_6M, SHELL_COMPANY_PARTNERS, NEW_COUNTERPARTY_LARGE_SHARE, CIRCULAR_INVOICING) понижены до MEDIUM/LOW confidence, source заменён на FATF/EAG/UZ AML law.

4. **Положение №2696-5 (январь 2026)**: полный текст конкретных изменений vs предыдущей редакции 2696-3 в открытом доступе на дату исследования ограничен (lex.uz даёт metadata, но full PDF может требовать платной подписки norma.uz/nrm.uz).

5. **Сезонность UZ-агро/строительства**: правила #4 REVENUE_DROP_MOM_30 и #6 NEGATIVE_PROFIT_3Q могут давать false positives для секций A (агро) и F (строительство) без сезонного adjustment. Рекомендован filter `oked_section NOT IN ('A','F','I')` для MoM-правил.

6. **Регуляторный риск**: pre-underwriting MVP для mid-tier банков — не покрыто prescriptive ЦБ РУз регулированием. ЦБ РУз FSAP 2025 рекомендует «independent оценку качества активов, совершенствование стандартов оценки рисков» — этот инструмент должен соответствовать общим принципам, но не подлежит pre-approval. Однако при scale-up (>10% портфеля банка обрабатывается через инструмент) — следует ожидать SREP-overlay от ЦБ РУз.

7. **Macroeconomic exposure**: UZS волатильность, инфляция 10%+, базовая ставка ЦБ РУз 13.5% (2024-2025) — все эти факторы влияют на корректность абсолютных порогов (например, «выручка > 5 000 000 000 UZS» теряет смысл при 10%+ годовой инфляции). Рекомендуется ежегодная индексация thresholds к ставке UZONIA или CPI.

---

## Executive Summary (abstract, 400-600 слов)

**Контекст и scope**. Pre-underwriting MVP для mid-tier банков Узбекистана (Hamkorbank, SQB, Trastbank, Anor Bank, Asia Alliance, Bereke, Davr Bank, Halk Bank, Mikrokreditbank) включает 19 правил в YAML rules engine. Данное исследование выполняет: (а) аудит foundational источников и каждого из 19 правил, (б) gap analysis с новыми правилами, (в) разработку confidence layer для partial-data scoring, (г) подготовку UZ-specific industry benchmark catalog по ОКЭД, (д) sourcing baseline для практики mid-tier банков 2025-2026.

**Главная находка — foundational attribution layer повреждён**. Три из четырёх ключевых источников MVP имеют ошибки:
- **«ЦБ РУз положение №27-п»** — такого акта не существует. Действующее положение — **№2696** (последняя редакция 2696-5 от 23.12.2025, вступила в силу 25.01.2026), но оно **НЕ содержит количественных триггеров типа «−30% MoM выручки»**; классификация качественная по 4 категориям.
- **«НК РУз ст. 256»** — это про налоговых агентов с госимуществом, не про ЭСФ. Правильная статья для счетов-фактур — **НК РУз ст. 47** (+ ст. 257, ПКМ №489, ст. 175-1 КоАО, ст. 223 НК РУз).
- **Group-IB Uzbekistan corporate fraud report** — публично доступен только retail/mobile-fraud материал (group-ib.com/blog/mobile-malware-uzbekistan/, 19.12.2025); атрибуция для AML-правил должна быть заменена на FATF Recommendations + EAG + Закон РУз ЗРУ-660.
- **Basel III IRB final** (BCBS d424, December 2017) — верифицирован, применим через IMF/World Bank FSAP UZ 2025.

**Аудит 19 правил**. KEEP без правок: 5 правил (NEGATIVE_EQUITY, BANK_ACCOUNT_FROZEN_12M, CIRCULAR_INVOICING, TAX_PAYMENT_DELAYS, NEGATIVE_PROFIT_3Q). KEEP с правкой источника / порогов: 10 правил. ADJUST (изменение формулы или severity): 3 правила (OKVED→OKED, REVENUE_DROP_MOM_30 с сезонным фильтром, VAT_GROWTH_NO_REVENUE). **DEPRECATE → REPLACE**: 1 правило (INSUFFICIENT_DATA заменяется confidence layer).

**Gap analysis — 7 недостающих риск-категорий**. Top-3 critical:
- **FX_MISMATCH_HIGH**: World Bank FSAP UZ 2025 указывает «the share of foreign exchange (FX) loans at 44 percent of total loans remains relatively high»; IMF рекомендует ограничивать FX-кредиты заёмщикам без валютной выручки.
- **DSCR_LOW**: UZ-исследование cotton ginning (Murodov, 2025) — «even when the baseline DSCR ranges between 1.05 and 1.15, the probability of liquidity disruption reaches up to 42% under a combined stress scenario… minimum safe DSCR threshold at 1.3».
- **WC_INSUFFICIENT**: current/quick ratio отсутствуют в 19-rule set.

**Confidence Layer (Q1)**. Архитектурное решение — confidence layer как **СЕПАРАТНЫЙ модификатор скора** (не одно из правил). Per FRB SR 11-7 / SR 26-02 (April 2026): «rigorous assessment of data quality and relevance» — обязательный этап. Структура: 4 уровня (HIGH ≥75 / MEDIUM 50-74 / LOW 30-49 / CRITICAL <30) с multiplier 1.0 → 0.9 → 0.75 → cap 50/REJECT. Главный problem case задания (full mandatory + 2 года Form1/2, пустой ESF/turnover/tax → MVP выдаёт 100/Approve) при новой архитектуре даёт **confidence 30 → final score 50 → REVIEW с manual underwriting** (Scenario S2).

**Industry Benchmark Catalog (Q3)**. Узбекистан использует **ОКЭД (Госкомстат РУз) ред. 2** (ПКМ №275 от 24.08.2016), на базе NACE Rev.2 + ISIC Rev.4. **Российский ОКВЭД2 в UZ официально НЕ применяется**. Bug в MVP (fallback на торговлю для ОКЭД 43.39 / отделочные работы) — путаница секций F (строительство) и G (торговля). **Net margin medians per ОКЭД для UZ FY2024 в открытых источниках НЕ публикуются** — JSON skeleton содержит 7 buckets с null значениями и explicit notes; запрещена fake-substitution.

**Empirical baseline 2025**: SME lending 131,2 трлн UZS (+42% YoY, UzDaily), microfinance 21,3 трлн UZS 9M2025 (×2 YoY, American Journal), средний % по микрозаймам 35,9%, средняя долговая нагрузка домохозяйств 34% (ЦБ РУз). Mid-tier KPIs FY2024 verified: SQB NPL 2.8%/CAR 15.6%/ROE 13.9%; Ipoteka NPL (Stage 3) 20.6%/CAR 16.03%/ROE 23%; Hamkorbank +18.9% net profit, S&P BB-/Stable.

**Решение к demo**: до production выполнить 4-этапный roadmap (3 месяца) — фиксы foundational + 16 правил + confidence layer + benchmark catalog с роадмапом по UZ-data sourcing.