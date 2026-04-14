# CLAUDE.md

> Читай этот файл ПОСЛЕ PROJECT_BRIEF.md. Здесь — текущий статус проекта и рабочие соглашения.

---

## Current Status

**Phase:** 0 — Foundation (not started)
**Last completed task:** None
**Next task:** Init repo, setup Python project with `uv`, setup Next.js in `web/`

---

## Working Agreements

- Перед каждой задачей: перечитай PROJECT_BRIEF.md Section 4 (Architecture) и Section 11 (Anti-patterns)
- Plan mode обязателен если затрагивается >2 файлов
- Не начинай кодить без плана — сначала покажи декомпозицию
- Язык UI: русский. Язык кода: английский
- Коммиты: conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`)
- Никаких `TODO` без ID (`# TODO[CA-001]: описание`)

---

## Architecture Reminders

- `domain/` не знает про `infrastructure/` — никогда
- Все бизнес-правила — только в `domain/rules/`, ссылка на источник обязательна
- Новый банк = новый adapter, не правки в ядре
- Two modes (Bank / Accountant) — два UI поверх одного бизнес-ядра

---

## Security Hard Rules

- Данные заёмщиков не логируются
- Никаких внешних API в production (только on-premise)
- Soliq данные — только через официальный экспорт/API, не scraping
- `.env` не в git, secrets через Vault в production

---

## Start of Session Command

```
Прочитай @PROJECT_BRIEF.md целиком, потом @CLAUDE.md.
Скажи на каком phase мы сейчас и какая следующая atomic задача.
Не начинай кодить — сначала покажи план.
```

---

## Session Log

| Session | Phase | Completed | Notes |
|---------|-------|-----------|-------|
| — | 0 | — | Project not started |
