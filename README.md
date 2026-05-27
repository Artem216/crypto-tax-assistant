# CryptoTax Assistant

ИИ-помощник для анализа криптовалютных транзакций и формирования налоговой отчётности по законодательству РФ.

Пользователь вводит адрес Ethereum-кошелька — система автоматически подтягивает историю транзакций, обогащает их историческими курсами ETH/USD, классифицирует с помощью ИИ и формирует налоговый отчёт с расчётом НДФЛ по прогрессивной шкале 2025 года.

---

## Авторы


| | Участник | Роль |
|--|----------|------|
| 👤 | Журавлева Ариана Андреевна | ИИ-интеграция (Groq, промпты, классификация, генерация отчёта) |
| 👤 | Демин Никита Игоревич | Telegram-бот, интеграция сервисов, блокчейн-верификация, Docker |
| 👤 | Матвеев Владимир Сергеевич | Смарт-контракты (ReportVerifier, ERC-20, деплой на Sepolia) |
| 👤 | Цыканов Артём Эдуардович | Данные и алгоритм (Etherscan, CoinGecko, P&L расчёт) |

---

## Архитектура

Проект состоит из пяти компонентов:

```
telegram-bot
└── orchestrator (8003)
    ├── etherscan-wallet-service (8000)  — транзакции кошелька
    ├── coingecko-rate-service (8001)    — исторические курсы ETH/USD
    └── ai-service (8002)                — классификация и генерация отчёта

contract/
└── ReportVerifier.sol                   — верификация отчётов в блокчейне
```

**telegram-bot** — пользовательский интерфейс на базе aiogram 3. Принимает адрес кошелька и период, отображает отчёт в формате HTML, поддерживает диалоговый режим Q&A. После каждого анализа автоматически записывает хэш отчёта в смарт-контракт на Sepolia.

**etherscan-wallet-service** — получает историю нативных ETH-транзакций и ERC-20 переводов через Etherscan API. Нормализует сырые данные, считает комиссии, определяет статус транзакций.

**coingecko-rate-service** — обогащает транзакции историческим курсом ETH/USD на дату каждой операции через CoinGecko API.

**ai-service** — классифицирует транзакции (DEX_SWAP, INCOME, SELF_TRANSFER и др.) и генерирует читаемый налоговый отчёт на русском языке. Простые случаи определяются алгоритмически, неоднозначные — через LLM (Groq llama-3.3-70b).

**orchestrator** — склеивает все сервисы в единый пайплайн, конвертирует wei → ETH → USD → RUB, рассчитывает налог по прогрессивной шкале НДФЛ РФ 2025.

**ReportVerifier.sol** — смарт-контракт на Solidity 0.8.20 для верификации отчётов в блокчейне Ethereum.

---

## Быстрый старт

### Требования

- Docker и Docker Compose
- API ключ Etherscan (бесплатно на [etherscan.io](https://etherscan.io))
- API ключ Groq (бесплатно на [console.groq.com](https://console.groq.com))
- Токен Telegram-бота (через [@BotFather](https://t.me/BotFather))

### Запуск

```bash
# 1. Клонировать репозиторий
git clone https://github.com/Artem216/crypto-tax-assistant.git
cd crypto-tax-assistant
git checkout develop

# 2. Создать файл с переменными окружения
cp .env.example .env

# 3. Вставить свои ключи в .env
# TELEGRAM_BOT_TOKEN=токен_от_BotFather
# ETHERSCAN_API_KEY=ваш_ключ
# GROQ_API_KEY=ваш_ключ
# WALLET_PRIVATE_KEY=приватный_ключ_для_подписи_транзакций  # опционально

# 4. Запустить все сервисы
docker compose up --build
```

После запуска сервисы доступны:

| Сервис | URL | Swagger |
|--------|-----|---------|
| Orchestrator | http://localhost:8080 | http://localhost:8080/docs |
| AI Service | http://localhost:8002 | http://localhost:8002/docs |
| CoinGecko Service | http://localhost:8001 | http://localhost:8001/docs |
| Etherscan Service | http://localhost:8000 | http://localhost:8000/docs |

---

## Telegram-бот

Бот доступен в Telegram: **@CryptoDeklarantBot**

### Сценарий работы

```
/start
  └── Ввод адреса ETH-кошелька (0x...)
        └── Выбор периода (2024 / 2025 / 2026 / другой)
              └── Анализ (30–60 секунд)
                    └── Готовый отчёт + ссылка на TX в Sepolia Etherscan
                          └── Режим Q&A — вопросы по отчёту
```

### FSM-состояния

| Состояние | Описание |
|-----------|----------|
| `waiting_wallet` | Ожидание ввода адреса кошелька |
| `waiting_period` | Выбор налогового периода через inline-кнопки |
| `waiting_custom_period` | Ввод произвольного периода |
| `analyzing` | Идёт анализ, отображается индикатор |
| `chatting` | Диалоговый режим вопросов по отчёту |

### Блокчейн-верификация

После каждого успешного анализа бот автоматически вычисляет keccak256-хэш отчёта и вызывает `submitReport()` в смарт-контракте ReportVerifier на Sepolia. В сообщении с отчётом пользователь получает прямую ссылку на транзакцию в Sepolia Etherscan.

---

## Смарт-контракт ReportVerifier

**Сеть:** Ethereum Sepolia (testnet)  
**Адрес:** `0xd00a12D1a67fE239cA9f628667a139087BFCB4Bd`  
**Etherscan:** https://sepolia.etherscan.io/address/0xd00a12D1a67fE239cA9f628667a139087BFCB4Bd

### Функции

| Функция | Тип | Описание |
|---------|-----|----------|
| `submitReport(wallet, reportHash)` | write | Записывает хэш отчёта с временной меткой блока |
| `verifyReport(wallet, reportHash) → bool` | read | Проверяет существование записи |
| `getRecord(wallet, reportHash)` | read | Возвращает полную запись: кошелёк, хэш, блок, timestamp |
| `getWalletReports(wallet) → bytes32[]` | read | Все хэши отчётов для кошелька |

### Вычисление хэша

```python
import hashlib, json

report_hash = hashlib.sha256(
    json.dumps(report, sort_keys=True, ensure_ascii=False).encode()
).hexdigest()
```

---

## Использование API

### Анализ кошелька

```bash
curl -X POST http://localhost:8080/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "period": "2024",
    "usd_rub_rate": 90.0,
    "page_size": 50
  }'
```

**Пример ответа:**
```json
{
  "wallet_address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
  "period": "2024",
  "transactions_analyzed": 50,
  "report": {
    "summary": "...",
    "taxable_events": [...],
    "non_taxable_events": [...],
    "tax_base_rub": 4367.4,
    "estimated_tax_rub": 567.76,
    "tax_rate_note": "Рассчитано по прогрессивной шкале НДФЛ РФ 2025",
    "recommendations": [...],
    "disclaimer": "..."
  }
}
```

### Вопрос по отчёту

```bash
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "question": "Нужно ли мне подавать декларацию?",
    "report": {"tax_base_rub": 4367.4, "estimated_tax_rub": 567.76}
  }'
```

---

## Категории транзакций

| Категория | Описание | Налогооблагаемая |
|-----------|----------|-----------------|
| `INCOME` | Получение крипты как доход | ✅ Да |
| `DEX_SWAP` | Обмен токенов на DEX | ✅ Да |
| `SALE` | Продажа крипты | ✅ Да |
| `DEFI_INCOME` | Доход от стейкинга, airdrop | ✅ Да |
| `SELF_TRANSFER` | Перевод между своими кошельками | ❌ Нет |
| `FEE` | Комиссия сети | ❌ Нет |
| `UNKNOWN` | Не удалось определить | ⚠️ Уточнить |

Транзакции с уверенностью классификации ниже 0.75 или категорией `UNKNOWN` получают флаг `requires_review` и не включаются в налоговую базу автоматически.

---

## Налоговые ставки НДФЛ РФ 2025

| Годовой доход | Ставка |
|---------------|--------|
| До 2 400 000 руб | 13% |
| 2 400 000 — 5 000 000 руб | 15% |
| 5 000 000 — 20 000 000 руб | 18% |
| 20 000 000 — 50 000 000 руб | 20% |
| Свыше 50 000 000 руб | 22% |

---

## Переменные окружения

| Переменная | Описание | Обязательная |
|------------|----------|--------------|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота от @BotFather | ✅ |
| `ETHERSCAN_API_KEY` | Ключ Etherscan API | ✅ |
| `GROQ_API_KEY` | Ключ Groq API | ✅ |
| `COINGECKO_API_KEY` | Ключ CoinGecko (для demo/pro-тира) | ❌ |
| `DEFAULT_CHAIN_ID` | ID сети (1 = Ethereum mainnet) | ❌ |
| `CONTRACT_ADDRESS` | Адрес смарт-контракта ReportVerifier | ❌ |
| `SEPOLIA_RPC_URL` | RPC-эндпоинт сети Sepolia | ❌ |
| `WALLET_PRIVATE_KEY` | Приватный ключ для подписи транзакций верификации | ❌ |

> ⚠️ На бесплатном тире CoinGecko доступны исторические данные только за последние 365 дней.

---

## Стек

- **Python 3.11–3.12** + **FastAPI** + **uvicorn**
- **aiogram 3.13** — Telegram-бот с FSM
- **web3.py 7.6** — взаимодействие со смарт-контрактом
- **Groq API** — llama-3.3-70b-versatile
- **Etherscan API** — история транзакций
- **CoinGecko API** — исторические курсы
- **Solidity 0.8.20** — смарт-контракт ReportVerifier
- **Docker** + **Docker Compose**

---

## Ограничения

- Поддерживается только сеть Ethereum (chain_id=1). BSC, Polygon и другие сети — в планах
- Анализируются только нативные ETH-транзакции. ERC-20 токены — в планах
- Суммы в рублях рассчитываются по курсу USD/RUB, указанному вручную
- Отчёт не является официальным налоговым документом
- Блокчейн-верификация работает в тестовой сети Sepolia

---

> Этот проект создан в учебных целях и не является юридической или налоговой консультацией.
