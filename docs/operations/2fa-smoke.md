# End-user 2FA guide (smoke + pilot setup)

> Документация для smoke-тестирования 2FA flow или для IT-офицера банка при onboarding'е аналитика.
> Вынесено из CLAUDE.md (2026-05-14 cleanup).

## Подготовка окружения

1. Backend в Docker bank-mode:
   ```powershell
   $env:APP_MODE='bank'; docker compose up -d --build api
   ```
   ⚠️ Если запустить без `$env:APP_MODE='bank'` префикса — bank-router не зарегистрируется, login будет 404. .env с APP_MODE=bank — TODO.

2. Seed admin с известным паролем (upsert по email):
   ```powershell
   docker compose exec -T api bash -c "cd /app/src && uv run --no-sync python -m interfaces.cli.seed_analysts --email admin@bank.uz --password 'Admin2026!' --full-name 'Admin A.' --role senior_analyst"
   ```

3. Frontend dev:
   ```powershell
   cd web; $env:NEXT_PUBLIC_APP_MODE='bank'; $env:NEXT_PUBLIC_BRAND_ID='uzbekbank'; npm run dev
   ```

4. TOTP app на телефоне — поставь **Microsoft Authenticator** или **Google Authenticator** (Google не имеет iCloud-quirk).

## Smoke 4 путей (≈10 минут)

### Путь 1 — Enrollment

1. Открой `http://localhost:3000/login` → `admin@bank.uz` / `Admin2026!` → Войти → `/search`
2. Sidebar → **Настройки** → nav **Безопасность**
3. Карточка «Двухфакторная аутентификация · Не настроена» → кнопка **«Включить 2FA»**
4. Модалка stage QR:
   - Сканируй QR в Authenticator-приложении
   - **Если MS Authenticator пишет «уже существует»** — нажми Отмена. Аккаунт всё равно добавится в список (после email-suffix patch label выглядит `admin+a1b2c3@bank.uz`)
   - Альтернативно — клик «Показать» под manual-entry secret → копируй → в Authenticator «+ → Other → Ввести вручную» → paste secret
5. Клик «Продолжить» → stage Verify
6. Введи 6-значный код из Authenticator → «Подтвердить»
7. Stage Backup-codes:
   - **СКАЧАЙ .txt** (обязательно — plain никогда не повторится)
   - Открой блокнотом, проверь 10 строк по 8 символов
   - Отметь checkbox «Я сохранил коды в надёжном месте» → «Готово»
8. Карточка 2FA стала зелёной «Активна» ✅

### Путь 2 — Login через TOTP

1. Sidebar внизу → user-card → Выйти
2. `/login` → email + пароль → Войти
3. Должен переключиться на step-2 «Двухфакторная аутентификация · Введите 6-значный код»
4. Свежий код из Authenticator → Подтвердить → `/search` ✅

### Путь 3 — Login через backup-код

1. Logout
2. `/login` → email + пароль → Войти → step-2
3. Клик ссылку **«Использовать резервный код»** (под input полем)
4. Поле меняется: placeholder `XXXXXXXX`, разрешает буквы и цифры
5. Введи **один** из сохранённых backup-кодов (8 символов, A-Z 0-9) → Подтвердить → `/search` ✅
6. ⚠️ Использованный код **сгорает** — повторный ввод того же даст invalid_code

### Путь 4 — Disable

1. Залогинен через Путь 2 или 3
2. `/settings` → Безопасность → карточка 2FA → красная кнопка **«Отключить»**
3. Модалка: пароль `Admin2026!` + свежий TOTP-код → Подтвердить
4. Карточка стала серой «Не настроена» ✅

## Если invalid_code не уходит

Backend ping для самопроверки:

```powershell
# 1. Текущий secret в БД для admin@
docker compose exec -T postgres psql -U credit -d credit_assistant -c "SELECT mfa_secret, mfa_enrolled_at FROM analysts WHERE email='admin@bank.uz';"

# 2. Скопируй secret, посмотри что сервер ожидает прямо сейчас
docker compose exec -T api bash -c "PYTHONPATH=/app/src uv run --no-sync python -c 'import pyotp,time; print(pyotp.TOTP(\"PASTE_SECRET_HERE\").now())'"
```

Если код из Authenticator **не совпадает** с тем что выдаёт probe — Authenticator имеет другой secret (старая запись от race-condition не очищенная + iCloud cache, либо вторая запись с тем же label). Удали ВСЕ «Credit Assistant» из Authenticator, добавь заново через manual entry.

## Восстановление в случае lockout

Через UI (требует second senior_analyst): `/settings → Безопасность → Admin: Reset MFA` — карточка под role-gate (CA-DS13 закрыт `f9dc928`).

Прямой SQL если admin'а нет:
```powershell
docker compose exec -T postgres psql -U credit -d credit_assistant -c "UPDATE analysts SET mfa_secret=NULL, mfa_enrolled_at=NULL, mfa_backup_codes_hash=NULL WHERE email='YOUR_EMAIL';"
```

После — login сразу пускает без 2FA, можешь заново enroll'нуться.
