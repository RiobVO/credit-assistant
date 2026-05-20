# Disaster Recovery and Business Continuity Plan

> DRP/BCP план для Credit Assistant MSB. Аудитория — DevOps / SRE / Incident
> Commander банка-клиента.
>
> **Документ — draft skeleton (T4 compliance pack).** Версия 0.1. RTO/RPO
> targets — placeholder, требуют пересмотра банком на основе business impact
> analysis.

---

## Russian

### 1. Scope и цели

**Disaster Recovery (DR):** процедуры восстановления продукта после
catastrophic event (data loss, infrastructure failure, outage).

**Business Continuity (BC):** процедуры поддержания критичных операций при
degraded state (частичный отказ компонента).

**Scope документа:**

- Credit Assistant MSB infrastructure (Docker compose stack).
- Postgres БД с PII data.
- Redis (refresh-token denylist).
- Backup/restore procedures.

**Out of scope (ответственность банка):**

- АБС (Automated Banking System) интеграция.
- Корпоративная сеть, DNS, AD/LDAP.
- Электропитание ЦОД, климат, физическая инфраструктура.

### 2. RTO / RPO targets

**Baseline targets (proposed, требует пересмотра):**

| Метрика | Target | Обоснование |
|---------|--------|-------------|
| RTO (Recovery Time Objective) | 4 часа | Не критичный для real-time банковских операций — аналитик может вернуться к manual workflow на 4 часа |
| RPO (Recovery Point Objective) | 1 час | Daily backup + WAL retention позволяет восстановить state с потерей ≤1 час работы |
| MTPD (Maximum Tolerable Period of Disruption) | 24 часа | Через 24 часа банк должен иметь fallback процесс или продлить SLA |

**Service tiers:**

| Tier | Сервис | RTO | RPO |
|------|--------|-----|-----|
| Critical | API + Postgres | 4h | 1h |
| Important | Redis (refresh denylist) | 8h | N/A (можно потерять) |
| Deferrable | GlitchTip / Prometheus / Grafana | 24h | N/A |

**Примечание:** банк должен провести Business Impact Analysis (BIA) и
скорректировать targets. Текущие — placeholder.

### 3. Backup strategy

**Daily Postgres backup:**

- Sidecar контейнер `credit-db-backup` — ежедневный `pg_dump` в `./backups/`.
- Retention: 30 дней (конфигурируется `BACKUP_RETENTION_DAYS`).
- Полная процедура — `docs/operations/db-backup.md`.

**Off-site backup (банк responsibility):**

- Рекомендация: rsync `./backups/` на внешний storage (другой ЦОД, S3-compatible).
- Шифрование канала: SSH/TLS.
- Шифрование at-rest: симметричное (GPG или native S3 encryption).
- Retention: 90 дней рекомендация (соответствует Закону РУз №547 о хранении ПДн).

**WAL archiving (для RPO <1 час):**

- В baseline configuration WAL archiving НЕ настроен — RPO зависит только
  от cadence daily dump'а.
- Опция для банков с requirement RPO <1 час — настроить `archive_mode=on`
  + `archive_command` с rsync на off-site.

**Restore drill:**

- Quarterly (раз в квартал) — обязательная процедура.
- Скрипт `./deploy/restore-drill.sh <backup-file>` — поднимает shadow-инстанс,
  проверяет integrity (row counts, encryption sanity check), exit 0 при PASS.
- Результаты документируются (timestamp, operator, PASS/FAIL, lessons).

### 4. Сценарии и runbooks

#### 4.1 Postgres data loss

**Detection signals:**

- API возвращает 500 на запросах к БД.
- Prometheus alert `pg_up == 0`.
- Logs: `OperationalError: connection refused` или `relation does not exist`.
- БД healthcheck failed.

**Recovery steps:**

1. **Stop API:** `docker compose stop api` (предотвратить дальнейшую
   запись).
2. **Identify latest valid backup:** `ls -lt ./backups/ | head -5`.
3. **Stop Postgres:** `docker compose stop postgres`.
4. **Restore:** `./deploy/restore.sh <backup-file>` (подробности —
   `docs/operations/db-backup.md`).
5. **Verify PII decryption:** seed `PII_ENC_KEYS` тем же значением, что
   использовалось при backup'е (см. ADR-0017).
6. **Start Postgres + API:** `docker compose up -d postgres api`.
7. **Sanity check:** `curl https://<host>/health` → 200.
8. **Verify через UI:** login → search известного borrower → dossier view.

**Validation:**

- Row count `borrowers` соответствует ожидаемому ≥ baseline.
- Audit log записи существуют до backup timestamp.
- PII columns расшифровываются без ошибок.

**Escalation:**

- Если restore fail (corrupt backup) → попробовать предыдущий backup.
- Если все backups corrupt → L3 (vendor) + потеря данных от последнего
  valid backup до incident.

#### 4.2 API container crash

**Detection signals:**

- Healthcheck `/health` returns non-200 или timeout.
- Prometheus alert `up{job="credit-api"} == 0`.
- GlitchTip alert на unhandled exception (если crash через exception).

**Recovery steps:**

1. **Initial restart:** `docker compose restart api`.
2. **Verify health:** `curl https://<host>/health` после 30s.
3. **Если crash повторился (>2 раза за 10 минут):**
   - Check logs: `docker compose logs --tail=200 api`.
   - Check resources: `docker stats credit-api`.
   - Если OOM → temporary увеличить `mem_limit` в compose, restart.
   - Если bug → rollback на предыдущий image: `docker compose up -d --no-deps api:<prev-tag>`.

**Validation:**

- `/health` returns 200.
- Audit log пишется (test login).
- Random sample requests (search, dossier view) проходят.

**Escalation:**

- 3+ crashes за час → L2 (Tech Lead).
- Невосстановимый crash после rollback → L3 (vendor).

#### 4.3 Redis down

**Detection signals:**

- Prometheus alert `redis_up == 0`.
- Logs: `redis.exceptions.ConnectionError` в `/refresh` endpoint.
- В prod при `REDIS_URL` задан, Redis недоступен → **fail closed** на
  `/refresh` (compromised tokens не должны проскочить).

**Degraded mode behavior (per ADR-0016):**

- Существующие access tokens (15м TTL) продолжают работать.
- Existing sessions работают до access token expiration.
- `/refresh` возвращает 503 → пользователь должен re-login.

**Recovery steps:**

1. **Diagnose:** `docker compose logs redis --tail=100`.
2. **Restart:** `docker compose restart redis`.
3. **Verify:** `docker compose exec redis redis-cli PING` → `PONG`.
4. **Verify API recovery:** `/refresh` endpoint возвращает 200 на test request.

**Communication:**

- Если Redis down >15 минут — уведомить аналитиков о возможной
  необходимости re-login.
- Audit log это событие явно не записывает (Redis не критичен для audit
  trail).

**Escalation:**

- Redis повторно crashes → L2 (Tech Lead) + investigate Redis OOM/eviction
  policy.
- Persistent Redis failure → переключиться на `REDIS_URL=` (stateless
  fallback) как temporary measure, но ослабляет security (refresh tokens
  не могут быть денилистнуты).

#### 4.4 ЦОД full outage

**Detection signals:**

- Полная недоступность production host (ping/SSH timeout).
- Внешний мониторинг банка триггерит alert.
- Обращения от аналитиков о недоступности.

**Recovery steps (high-level, требует расширения):**

1. **Activate incident response team** (L1 → L2 → Incident Commander).
2. **Confirm scope:** инфраструктурный отказ vs targeted attack vs natural
   disaster.
3. **Decide on recovery target:** secondary ЦОД (если есть DR site) или
   восстановление primary после resolution.
4. **Off-site backup recovery (если primary lost):**
   - Pull latest backup из off-site storage.
   - Provision new infrastructure (Docker host + Postgres + Redis).
   - Restore Postgres backup.
   - Configure `.env` (включая `PII_ENC_KEYS` из Vault/secure storage).
   - Deploy через `./deploy/install.sh`.
   - DNS/network failover на новый host.
5. **Communication plan:**
   - L1 → Incident Commander → банк CIO/CISO.
   - Customer-facing message: «технические работы, восстановление ETA Xh».
   - Post-incident: внутренний postmortem + report для регулятора при
     necessary (PII breach подозрение → Закон РУз №547).

**Validation:**

- Full smoke test playbook `docs/operations/pre-demo-smoke.md`.
- Audit log сохранён до точки outage.
- PII decryption работает.

**Maximum tolerable downtime:** 24 часа (MTPD). Через 24 часа банк должен
активировать manual fallback workflow (аналитики работают как до
Credit Assistant — manual data collection).

### 5. Roles & responsibilities

**Placeholder — банк должен заполнить конкретными именами/ролями:**

| Роль | Ответственность |
|------|------------------|
| Incident Commander | Координация incident response, communication с stakeholders |
| Technical Lead | Принятие технических решений, escalation в vendor |
| DBA | Postgres restore, integrity check |
| Network Ops | DNS failover, firewall, periphery |
| Security Officer | PII breach assessment, Закон РУз №547 compliance |
| Vendor Liaison | Эскалация в Credit Assistant vendor (L3) |
| Communications | Internal/external messaging |

**On-call rotation:**

- L1 — 24/7 dispatch (банк responsibility).
- L2 — business hours + on-call после hours.
- L3 (vendor) — SLA-defined, документируется в контракте.

### 6. Contact escalation matrix

**Placeholder — заполняется банком и vendor'ом:**

| Уровень | Роль | Контакт | SLA ответа | Условия эскалации |
|---------|------|---------|------------|---------------------|
| L1 | DevOps дежурный (банк) | TBD | 15 мин (24/7) | Любой incident |
| L2 | Tech Lead (банк) | TBD | 1 час (business hours) | L1 не resolve >30 мин |
| L3 | Credit Assistant vendor | TBD | 4 часа | Невосстановимая ошибка, requires vendor expertise |
| Security | Security Officer (банк) | TBD | 30 мин (24/7) | PII breach подозрение |
| Regulator | ЦБ РУз / Госинспекция по защите ПДн | TBD | per Закон РУз №547 | PII breach подтверждён |
| Legal | Legal counsel (банк) | TBD | 4 часа | PII breach, contractual issues |

**Внешние:**

- ЦБ РУз reporting — при significant operational incident согласно
  банковским требованиям.
- Госинспекция по защите ПДн — при PII breach, Закон РУз №547.

### 7. Testing и drills

**Quarterly restore drill (mandatory):**

- Скрипт `./deploy/restore-drill.sh`.
- Документируется: timestamp, operator, backup tested, integrity result.
- Lessons learned → update этого документа.

**Annual full DR exercise (recommended):**

- Симуляция ЦОД outage с восстановлением на secondary infrastructure.
- Включает: backup retrieval, restore, network failover,
  end-to-end smoke test.
- Coordinated с банком ops team.

**Tabletop exercises (recommended quarterly):**

- Сценарии: ransomware attack, insider threat (analyst exfiltration),
  partial Postgres corruption.
- Walkthrough без actual recovery — focus на decision making, communication,
  roles.

### 8. Post-incident review

**Blameless postmortem template:**

```markdown
# Incident <ID> — <Title>

## Timeline
- HH:MM — событие (detection, action, recovery step)
- ...

## Impact
- Затронуто пользователей: N
- Downtime: X минут
- Data loss: Y минут (RPO)
- PII implications: yes/no

## Root cause
<technical explanation>

## What went well
- ...

## What went poorly
- ...

## Action items
- [ ] [Owner] [Deadline] Specific corrective action
- ...

## Lessons learned
<update DRP/runbooks based on this>
```

**Cadence:**

- В течение 5 рабочих дней после resolution.
- Review meeting с участниками incident response team.
- Action items tracked до closure.
- Updates DRP/BCP документа — pull request с change history.

---

## O'zbek

> Eslatma: ushbu bo'lim mashinaviy tarjima asosida tayyorlangan skelet.
> Har bir bo'limga `TODO[CA-T4-UZ]` belgisi qo'yilgan — yakuniy tahrir
> uchun o'zbek mutaxassisi kerak.

### 1. Hujjat doirasi va maqsadlari

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

Disaster Recovery (DR) — falokat keyin tiklash. Business Continuity (BC) —
qisman buzilish holatida kritik operatsiyalarni davom ettirish.

### 2. RTO / RPO maqsadlari

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

Boshlang'ich (taklif etilgan, qayta ko'rib chiqilishi kerak): RTO 4 soat,
RPO 1 soat, MTPD 24 soat. Bank Business Impact Analysis o'tkazishi kerak.

### 3. Zaxira nusxa strategiyasi

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

Kunlik Postgres `pg_dump` sidecar orqali, 30 kun retention. Off-site backup
bank javobgarligida (rsync external storagega). Choraklik restore drill.

### 4. Stsenariylar va runbooklar

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

To'rtta stsenariy: 4.1 Postgres ma'lumotlarini yo'qotish, 4.2 API
container crash, 4.3 Redis ishlamay qolishi (degraded mode per ADR-0016),
4.4 ma'lumotlar markazi to'liq buzilishi.

### 5. Rollar va mas'uliyat

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

Placeholder — bank to'ldirishi kerak. Rollar: Incident Commander, Technical
Lead, DBA, Network Ops, Security Officer, Vendor Liaison, Communications.

### 6. Eskalatsiya matritsasi

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

L1 → L2 → L3 timeline. PII breach holatida — Security Officer +
Davlatinspektsiya bo'yicha №547-sonli Qonun talablari.

### 7. Test va mashqlar

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

Choraklik restore drill majburiy, yillik to'liq DR mashq tavsiya etiladi,
choraklik tabletop exercise tavsiya etiladi.

### 8. Hodisadan keyingi tahlil

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

Blameless postmortem shabloni, 5 ish kuni ichida. Action items closure
gacha tracked. DRP/BCP yangilanadi pull request orqali.
